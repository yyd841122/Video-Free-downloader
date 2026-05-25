from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from app.services.direct_link_store import direct_link_store

router = APIRouter()
logger = logging.getLogger(__name__)

# 仅允许的协议
_ALLOWED_SCHEMES = {"http", "https"}

# 跟随重定向的最大次数
_MAX_REDIRECTS = 3

# 显式拒绝的主机片段（小写匹配）
_BLOCKED_HOST_LITERALS = {
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
    "0.0.0.0",
    "broadcasthost",
}

# 显式拒绝的 hostname 后缀（小写匹配）
_BLOCKED_HOST_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
)


class _UnsafeUrlError(ValueError):
    """The provided URL points to a private / disallowed network."""


def _is_disallowed_ip(ip_obj: ipaddress._BaseAddress) -> bool:
    """Return True if the IP address points to internal/loopback/link-local space."""
    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _validate_url(url: str) -> str:
    """Validate that ``url`` is a public http(s) URL safe to proxy.

    Raises _UnsafeUrlError if the URL points to a disallowed scheme/host/IP.
    Returns the normalized URL (unchanged) on success.
    """
    if not url or not isinstance(url, str):
        raise _UnsafeUrlError("empty url")

    parsed = urlsplit(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise _UnsafeUrlError(f"disallowed scheme: {scheme!r}")

    host = (parsed.hostname or "").strip()
    if not host:
        raise _UnsafeUrlError("missing host")

    host_lower = host.lower().rstrip(".")
    if host_lower in _BLOCKED_HOST_LITERALS:
        raise _UnsafeUrlError(f"blocked host literal: {host_lower!r}")
    for suffix in _BLOCKED_HOST_SUFFIXES:
        if host_lower.endswith(suffix):
            raise _UnsafeUrlError(f"blocked host suffix: {suffix!r}")

    # 如果 hostname 本身是一个 IP（含 IPv6 字面量），直接判断
    candidate_ip: ipaddress._BaseAddress | None = None
    try:
        candidate_ip = ipaddress.ip_address(host_lower)
    except ValueError:
        candidate_ip = None

    if candidate_ip is not None:
        if _is_disallowed_ip(candidate_ip):
            raise _UnsafeUrlError(f"disallowed ip literal: {host_lower!r}")
        return url

    # 域名 -> 解析所有 A/AAAA，全部必须为公网地址
    try:
        infos = socket.getaddrinfo(host_lower, None)
    except socket.gaierror as exc:
        raise _UnsafeUrlError(f"dns resolution failed: {exc}") from exc

    if not infos:
        raise _UnsafeUrlError("no dns records")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        # IPv6 link-local 形如 fe80::1%eth0
        ip_str = ip_str.split("%", 1)[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise _UnsafeUrlError(f"invalid resolved ip: {ip_str!r}")
        if _is_disallowed_ip(ip_obj):
            raise _UnsafeUrlError(f"private/loopback ip resolved: {ip_str!r}")

    return url


def _open_with_safe_redirects(url: str, headers: dict[str, str], timeout: int = 120):
    """Open ``url`` while validating every redirect target."""
    current_url = _validate_url(url)
    last_exc: Exception | None = None
    for _ in range(_MAX_REDIRECTS + 1):
        request = UrlRequest(current_url, headers=headers, method="GET")
        try:
            response = urlopen(request, timeout=timeout)
        except HTTPError as exc:
            # urllib 默认会跟随 30x，但部分服务返回的 30x 可能未被默认 handler 处理
            # 在这里 HTTPError 通常是 4xx/5xx；保留以便上层捕获。
            last_exc = exc
            raise
        except URLError as exc:
            last_exc = exc
            raise
        status_code = getattr(response, "status", None) or response.getcode()
        if status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise _UnsafeUrlError("redirect without Location header")
            # 解析相对/绝对地址
            from urllib.parse import urljoin

            current_url = urljoin(current_url, location)
            current_url = _validate_url(current_url)
            continue
        return response, current_url
    raise _UnsafeUrlError("too many redirects") from last_exc


def safe_download_name(title: str | None, fallback: str = "video") -> str:
    name = (title or fallback).strip() or fallback
    for char in '<>:"/\\|?*\r\n\t':
        name = name.replace(char, "_")
    if "." not in name:
        name = f"{name}.mp4"
    return name[:180]


@router.get("/redirect/{token}")
def redirect_direct(token: str) -> RedirectResponse:
    link = direct_link_store.get(token)
    if not link:
        raise HTTPException(status_code=404, detail="直链不存在或已过期")
    try:
        _validate_url(link.url)
    except _UnsafeUrlError as exc:
        logger.warning("blocked unsafe direct redirect: %s", exc)
        raise HTTPException(status_code=502, detail="直链不可用，请稍后重试") from exc
    return RedirectResponse(link.url, status_code=302)


@router.get("/proxy/{token}")
def proxy_direct(token: str, request: Request) -> StreamingResponse:
    link = direct_link_store.get(token)
    if not link:
        raise HTTPException(status_code=404, detail="直链不存在或已过期")

    headers = dict(link.headers)
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    try:
        upstream, _final_url = _open_with_safe_redirects(link.url, headers, timeout=120)
    except _UnsafeUrlError as exc:
        logger.warning("blocked SSRF-like proxy request: %s", exc)
        raise HTTPException(status_code=400, detail="代理请求被拒绝，请稍后重试") from exc
    except (HTTPError, URLError) as exc:
        logger.warning("proxy upstream failed: %s", exc)
        raise HTTPException(status_code=502, detail="代理请求失败，请稍后重试") from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("proxy upstream unexpected error")
        raise HTTPException(status_code=502, detail="代理请求失败，请稍后重试") from exc

    def iterator():
        try:
            while True:
                chunk = upstream.read(1024 * 512)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()

    response_headers = {}
    for key in ("Content-Length", "Content-Range", "Accept-Ranges"):
        value = upstream.headers.get(key)
        if value:
            response_headers[key] = value
    filename = safe_download_name(link.title)
    media_type = upstream.headers.get("Content-Type") or "application/octet-stream"
    if media_type.startswith("image/"):
        response_headers["Content-Disposition"] = f'inline; filename="{quote(filename)}"'
        response_headers.setdefault("Cache-Control", "public, max-age=3600")
    else:
        response_headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    status_code = 206 if range_header else 200
    return StreamingResponse(iterator(), status_code=status_code, media_type=media_type, headers=response_headers)
