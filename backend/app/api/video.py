from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.config import DIRECT_LINK_TTL_SECONDS
from app.models.schemas import (
    DirectLinkResponse,
    DownloadTaskResponse,
    VideoDirectRequest,
    VideoDownloadRequest,
    VideoInfoRequest,
    VideoInfoResponse,
)
from app.services.ytdlp_service import download_video_task, extract_direct_link, extract_info
from app.services.task_store import task_store
from app.services.bilibili_auth_store import bili_auth_store

router = APIRouter(prefix="/video")


@router.post("/info", response_model=VideoInfoResponse)
def video_info(payload: VideoInfoRequest) -> VideoInfoResponse:
    try:
        cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
        return extract_info(str(payload.url), cookies, payload.browser_cookies)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/download", response_model=DownloadTaskResponse)
def create_download_task(payload: VideoDownloadRequest, background_tasks: BackgroundTasks) -> DownloadTaskResponse:
    task = task_store.create(str(payload.url))
    cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
    background_tasks.add_task(
        download_video_task,
        task.task_id,
        str(payload.url),
        payload.format,
        payload.with_subtitle,
        cookies,
        payload.browser_cookies,
    )
    return DownloadTaskResponse(task_id=task.task_id, status=task.status)


@router.post("/direct", response_model=DirectLinkResponse)
def create_direct_link(payload: VideoDirectRequest, request: Request) -> DirectLinkResponse:
    try:
        cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
        info, token, selected_url = extract_direct_link(
            str(payload.url),
            payload.format,
            cookies,
            payload.browser_cookies,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_url = str(request.base_url).rstrip("/")
    return DirectLinkResponse(
        title=info.get("title"),
        format_id=str(info.get("format_id") or ""),
        ext=info.get("ext"),
        direct_url=selected_url,
        redirect_url=f"{base_url}/api/redirect/{token}",
        proxy_url=f"{base_url}/api/proxy/{token}",
        expires_in=DIRECT_LINK_TTL_SECONDS,
    )
