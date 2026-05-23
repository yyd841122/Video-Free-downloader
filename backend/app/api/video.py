import re
from threading import BoundedSemaphore
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.core.config import DIRECT_LINK_TTL_SECONDS, MAX_CONCURRENT_INFO_TASKS
from app.core.deps import get_optional_user
from app.db.models import User
from app.models.schemas import (
    DirectLinkResponse,
    DownloadTaskResponse,
    VideoDirectRequest,
    VideoDownloadRequest,
    VideoInfoRequest,
    VideoInfoResponse,
)
from app.services.bilibili_auth_store import bili_auth_store
from app.services.quota_service import QuotaExceededError, check_concurrent_download, check_resolution_allowed
from app.services.task_meta import write_task_meta
from app.services.task_store import task_store
from app.services.ytdlp_service import download_video_task, extract_direct_link, extract_info

router = APIRouter(prefix="/video")
info_semaphore = BoundedSemaphore(MAX_CONCURRENT_INFO_TASKS)


_FORMAT_HEIGHT_PATTERN = re.compile(r"(\d{3,4})")


def _guess_height_from_format(format_str: str) -> int:
    """从 yt-dlp 的 format 字符串里粗略猜测请求的最高画质，用于免费用户分辨率拦截。

    例如 "137+140"（YouTube 1080p）→ 137 不会被识别为高度，返回 0；
    但 "best[height<=720]" 或前端传入的 "1080p" 等可识别情况会返回对应数值。"""

    if not format_str or format_str.lower() in {"best", "bestvideo", "worst"}:
        return 0
    matches = _FORMAT_HEIGHT_PATTERN.findall(format_str)
    if not matches:
        return 0
    heights = [int(m) for m in matches if 240 <= int(m) <= 4320]
    if not heights:
        return 0
    return max(heights)


def _humanize_extract_error(exc: Exception) -> str:
    """把 yt-dlp 抛出来的"对普通用户不友好"的英文报错转成可操作的中文提示。

    目前只处理 Bilibili 412 风控（yt-dlp issue #14830 的已知 open 问题），
    其他错误透传 raw 字符串，留给上层或后续 PR 继续覆盖。"""

    raw = str(exc).strip()
    lower = raw.lower()
    if "412" in raw or "precondition failed" in lower:
        # Bilibili WAF 对数据中心 IP 直接抛 412 挑战，目前 yt-dlp 无代码层根治办法。
        # 唯一可靠出路是带登录态请求；后端已支持 cookies 字段 + /auth/bilibili/qrcode 扫码。
        if "bilibili" in lower:
            return (
                "B 站暂时拒绝了服务器的解析请求（HTTP 412 风控挑战）。\n"
                "这是 Bilibili 对机房 IP 的反爬限制，yt-dlp 社区已知问题（#14830）。你可以：\n"
                "1）点击右上角「Bilibili 扫码登录」，扫码后再解析（最稳定，可拿 1080P）；\n"
                "2）或在「高级选项」处粘贴浏览器导出的 Bilibili Cookies（包含 SESSDATA）；\n"
                "3）或稍后重试 / 换一条公开视频链接。"
            )
        return (
            "目标站点暂时拒绝了请求（HTTP 412 Precondition Failed）。"
            "可尝试稍后重试，或在「高级选项」处粘贴登录 Cookies 后再试。"
        )
    return raw


@router.post("/info", response_model=VideoInfoResponse)
def video_info(payload: VideoInfoRequest) -> VideoInfoResponse:
    if not info_semaphore.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="当前解析请求较多，请稍后再试")
    try:
        cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
        return extract_info(str(payload.url), cookies, payload.browser_cookies)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_humanize_extract_error(exc)) from exc
    finally:
        info_semaphore.release()


@router.post("/download", response_model=DownloadTaskResponse)
def create_download_task(
    payload: VideoDownloadRequest,
    background_tasks: BackgroundTasks,
    user: Optional[User] = Depends(get_optional_user),
) -> DownloadTaskResponse:
    cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
    return _start_download_job(
        background_tasks=background_tasks,
        user=user,
        url=str(payload.url),
        format_choice=payload.format,
        with_subtitle=payload.with_subtitle,
        cookies=cookies,
        browser_cookies=payload.browser_cookies,
    )


def _start_download_job(
    *,
    background_tasks: BackgroundTasks,
    user: Optional[User],
    url: str,
    format_choice: str,
    with_subtitle: bool,
    cookies: str | None,
    browser_cookies: str | None,
) -> DownloadTaskResponse:
    try:
        check_concurrent_download(user)
        check_resolution_allowed(user, _guess_height_from_format(format_choice))
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    task = task_store.create(url, user_id=user.id if user else None)
    write_task_meta(task.task_id, user)
    background_tasks.add_task(
        download_video_task,
        task.task_id,
        url,
        format_choice,
        with_subtitle,
        cookies,
        browser_cookies,
    )
    return DownloadTaskResponse(task_id=task.task_id, status=task.status)


@router.post("/direct", response_model=DirectLinkResponse)
def create_direct_link(
    payload: VideoDirectRequest,
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
) -> DirectLinkResponse:
    try:
        check_resolution_allowed(user, _guess_height_from_format(payload.format))
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    try:
        cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
        info, token, selected_url = extract_direct_link(
            str(payload.url),
            payload.format,
            cookies,
            payload.browser_cookies,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_humanize_extract_error(exc)) from exc

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
