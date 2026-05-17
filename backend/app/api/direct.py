from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from app.services.direct_link_store import direct_link_store

router = APIRouter()


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

    url_request = UrlRequest(link.url, headers=headers)
    try:
        upstream = urlopen(url_request, timeout=120)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"代理请求失败：{exc}") from exc

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
    response_headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    media_type = upstream.headers.get("Content-Type") or "application/octet-stream"
    status_code = 206 if range_header else 200
    return StreamingResponse(iterator(), status_code=status_code, media_type=media_type, headers=response_headers)
