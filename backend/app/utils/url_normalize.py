from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_URL_IN_TEXT_RE = re.compile(r"https?://[^\s<>\"'\[\](){}]+", re.IGNORECASE)
_TRAILING_PUNCT_RE = re.compile(r"[,，。.;；!?！？)、】』」\]\/]+$", re.UNICODE)


class UrlNormalizeError(ValueError):
    pass


def _strip_trailing_punctuation(value: str) -> str:
    s = value.strip()
    while s and _TRAILING_PUNCT_RE.search(s):
        s = _TRAILING_PUNCT_RE.sub("", s)
    return s


def _extract_first_url(text: str) -> str | None:
    match = _URL_IN_TEXT_RE.search(text)
    if not match:
        return None
    return _strip_trailing_punctuation(match.group(0))


def _is_bilibili_host(hostname: str) -> bool:
    host = (hostname or "").lower().rstrip(".")
    return host.endswith("bilibili.com") or host == "b23.tv" or host.endswith(".b23.tv")


def _is_douyin_host(hostname: str) -> bool:
    host = (hostname or "").lower().rstrip(".")
    return host.endswith("douyin.com")


def _is_x_host(hostname: str) -> bool:
    host = (hostname or "").lower().rstrip(".")
    return host.endswith("twitter.com") or host.endswith("x.com")


def _is_mp4_url(url: str, path: str, query: str) -> bool:
    combined = f"{path}{query}"
    return bool(re.search(r"\.mp4(\?|#|$)", combined, re.IGNORECASE)) or bool(
        re.search(r"\.mp4", url, re.IGNORECASE)
    )


def _is_x_status_path(path: str) -> bool:
    return bool(re.search(r"/status/\d+", path or "", re.IGNORECASE))


def _normalize_bilibili(parts) -> str:
    path = (parts.path or "").rstrip("/") or ""
    if re.match(r"^/video/BV[\w-]+$", path, re.IGNORECASE):
        path = f"{path}/"
    elif path.startswith("/video/"):
        path = path
    new_parts = parts._replace(query="", fragment="", path=path)
    return urlunsplit(new_parts)


def _normalize_douyin(parts) -> str:
    path = parts.path or "/"
    if not path.endswith("/"):
        path = f"{path}/"
    new_parts = parts._replace(query="", fragment="", path=path)
    return urlunsplit(new_parts)


def _normalize_x(parts) -> str:
    new_parts = parts._replace(query="", fragment="")
    return urlunsplit(new_parts)


def normalize_video_url(raw: str) -> str:
    """Normalize user-pasted share text or URLs for video extraction."""
    trimmed = (raw or "").strip()
    if not trimmed:
        raise UrlNormalizeError("empty url")

    candidate = _extract_first_url(trimmed)
    if not candidate and re.match(r"^https?://", trimmed, re.IGNORECASE):
        candidate = _strip_trailing_punctuation(trimmed)
    if not candidate:
        raise UrlNormalizeError("no url found in input")

    parts = urlsplit(candidate)
    if not parts.scheme or not parts.netloc:
        raise UrlNormalizeError("invalid url")

    host = parts.hostname or ""
    url_for_check = candidate

    if _is_mp4_url(url_for_check, parts.path or "", parts.query or ""):
        return candidate
    if _is_bilibili_host(host):
        return _normalize_bilibili(parts)
    if _is_douyin_host(host):
        return _normalize_douyin(parts)
    if _is_x_host(host) and _is_x_status_path(parts.path or ""):
        return _normalize_x(parts)
    return candidate
