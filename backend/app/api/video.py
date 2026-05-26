import logging
import re
from threading import BoundedSemaphore
from typing import Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.core.config import (
    DIRECT_LINK_TTL_SECONDS,
    FREE_BATCH_MAX_URLS,
    MAX_CONCURRENT_INFO_TASKS,
    VIP_BATCH_MAX_URLS,
)
from app.core.deps import get_current_user
from app.core.deps import get_optional_user
from app.db.models import User
from app.models.schemas import (
    BatchDownloadRequest,
    BatchDownloadResponse,
    BatchDownloadTaskItem,
    DirectLinkResponse,
    DownloadTaskResponse,
    VideoDirectRequest,
    VideoDownloadRequest,
    VideoInfoRequest,
    VideoInfoResponse,
)
from app.services.history_service import record_task_created
from app.services.bilibili_auth_store import bili_auth_store
from app.services.quota_service import QuotaExceededError, check_concurrent_download, check_resolution_allowed
from app.services.storage_guard import StoragePressureError, check_storage_before_large_download, is_likely_large_download
from app.services.task_meta import write_task_meta
from app.services.task_store import task_store
from app.services.ytdlp_service import download_video_task, extract_direct_link, extract_info
from app.utils.url_normalize import UrlNormalizeError, normalize_video_url

router = APIRouter(prefix="/video")
info_semaphore = BoundedSemaphore(MAX_CONCURRENT_INFO_TASKS)
logger = logging.getLogger(__name__)


def _coerce_video_url(raw: str) -> str:
    try:
        return normalize_video_url(raw)
    except UrlNormalizeError as exc:
        raise HTTPException(status_code=400, detail="未能识别有效视频链接，请检查链接格式。") from exc

ExtractStage = Literal["info", "download"]

_FORMAT_HEIGHT_P_PATTERN = re.compile(r"(\d{3,4})p\b", re.I)
_FORMAT_HEIGHT_FILTER_PATTERN = re.compile(r"height\s*<=?\s*(\d{3,4})", re.I)
_FORMAT_RESOLUTION_PAIR_PATTERN = re.compile(r"\d+x(\d{3,4})\b")
_FORMAT_STANDALONE_HEIGHT_PATTERN = re.compile(r"^(\d{3,4})p?$", re.I)
_KNOWN_VIDEO_HEIGHTS = frozenset({240, 360, 480, 540, 576, 720, 1080, 1440, 2160, 4320})
_YOUTUBE_HOST_RE = re.compile(r"(^|\.)youtube\.com|(^|\.)youtube-nocookie\.com|youtu\.be", re.I)
_COOKIE_REDACT_PATTERNS = (
    re.compile(r"(?i)# Netscape HTTP Cookie File.*"),
    re.compile(r"(?i)\bcookies?\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bset-cookie\s*:\s*\S+"),
    re.compile(r"(?i)\bCookie\s*:\s*\S+"),
    re.compile(r"(?i)\bSESSDATA=[^\s;]+"),
    re.compile(r"(?i)\bLOGIN_INFO=[^\s;]+"),
    re.compile(r"(?i)\bSID=[^\s;]+"),
    re.compile(r"(?i)\bHSID=[^\s;]+"),
    re.compile(r"(?i)\bSSID=[^\s;]+"),
)


def _is_youtube_url(url: str | None) -> bool:
    hostname = urlparse(url or "").hostname or ""
    return bool(_YOUTUBE_HOST_RE.search(hostname))


def _sanitize_error_summary(raw: str, max_len: int = 200) -> str:
    text = str(raw or "").strip().replace("\n", " ").replace("\r", " ")
    for pattern in _COOKIE_REDACT_PATTERNS:
        text = pattern.sub("[redacted]", text)
    if "\t" in text and "TRUE" in text.upper():
        text = "[cookie file content redacted]"
    return text[:max_len]


def _is_requested_format_unavailable(raw: str) -> bool:
    lower = raw.lower()
    return "requested format is not available" in lower or "requested format not available" in lower


def _youtube_info_blocked_message() -> str:
    return (
        "YouTube 仍然拒绝了服务器解析请求。请确认 cookies.txt 是从 youtube.com 页面导出的，"
        "并且账号仍处于登录状态。若仍失败，可能是 YouTube 平台验证或地区限制导致，请稍后重试。"
    )


def _classify_extract_error(raw: str, stage: ExtractStage) -> str:
    lower = raw.lower()
    if "412" in raw or "precondition failed" in lower:
        return "http_412"
    if "429" in raw or "too many requests" in lower:
        return "rate_limit"
    if "sign in" in lower or "login required" in lower or "cookies are no longer valid" in lower:
        return "login_required"
    if "unsupported url" in lower:
        return "unsupported_url"
    if _is_requested_format_unavailable(raw):
        return "format_unavailable" if stage == "download" else "format_unavailable_misreported"
    if "unable to extract" in lower or "unable to download webpage" in lower:
        return "extract_failed"
    return "unknown"


def _log_extract_failure(
    *,
    endpoint: str,
    url: str | None,
    exc: Exception,
    stage: ExtractStage,
    provided_cookies: bool,
) -> None:
    raw = str(exc).strip()
    platform = "youtube" if _is_youtube_url(url) else "other"
    category = _classify_extract_error(raw, stage)
    logger.warning(
        "video_extract_failed endpoint=%s stage=%s platform=%s category=%s provided_cookies=%s summary=%s",
        endpoint,
        stage,
        platform,
        category,
        "yes" if provided_cookies else "no",
        _sanitize_error_summary(raw),
    )


def _humanize_extract_error(
    exc: Exception,
    *,
    stage: ExtractStage = "info",
    url: str | None = None,
) -> str:
    """yt-dlp 原始报错对普通用户不友好，转成可操作建议。"""

    raw = str(exc).strip()
    lower = raw.lower()
    is_youtube = _is_youtube_url(url)
    is_bilibili = "bilibili" in lower or "bilibili" in raw

    if _is_requested_format_unavailable(raw):
        if stage == "info":
            if is_youtube:
                return _youtube_info_blocked_message()
            return (
                "无法解析该视频的可用格式（尚未进入下载阶段）。"
                "请检查链接是否有效，或在「高级选项」处提供登录 Cookies 后重试。"
            )
        return "当前清晰度不可用，请切换「最佳」或较低清晰度后重试。"
    if "412" in raw or "precondition failed" in lower:
        # yt-dlp #14830 已知开放问题：Bilibili WAF 对数据中心 IP 直接抛 412 风控挑战。
        # 当前没有"代码层"修复手段；唯一可靠出路是带登录态请求。
        if is_bilibili:
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
    if "429" in raw or "too many requests" in lower:
        return (
            "该视频平台暂时限制了解析频率（HTTP 429 Too Many Requests）。建议：\n"
            "1）稍等 1–5 分钟后再试；\n"
            "2）若是 YouTube/Bilibili，可在「高级选项」处粘贴浏览器 Cookies 后重试；\n"
            "3）也可以先解析其他平台的视频。"
        )
    if "sign in" in lower or "login required" in lower or "cookies are no longer valid" in lower:
        if stage == "info" and is_youtube:
            return _youtube_info_blocked_message()
        return (
            "该视频需要登录才能解析。请先登录对应平台账号，然后导出浏览器 Cookies 粘贴到「高级选项」处再试。\n"
            f"原始信息：{_sanitize_error_summary(raw)}"
        )
    if "unsupported url" in lower:
        return f"暂不支持该链接的格式或站点。请确认链接完整且为公开可访问的视频页面。\n原始信息：{_sanitize_error_summary(raw)}"
    if "unable to extract" in lower or "unable to download webpage" in lower:
        if stage == "info" and is_youtube:
            return _youtube_info_blocked_message()
        return (
            "无法解析该视频页面（可能是平台改版、视频被删除、地区限制或需登录）。\n"
            "可尝试：1) 检查链接是否能在浏览器正常打开；2) 升级 yt-dlp：pip install -U yt-dlp；3) 提供 Cookies 重试。\n"
            f"原始信息：{_sanitize_error_summary(raw)}"
        )
    if stage == "info" and is_youtube:
        return _youtube_info_blocked_message()
    return _sanitize_error_summary(raw) if raw else "解析失败，请稍后重试。"


def _guess_height_from_format(format_str: str) -> int:
    """从 yt-dlp 的 format 字符串里粗略猜测请求的最高画质，用于免费用户分辨率拦截。

    只识别明确的 height 语义（720p、height<=720、1280x720 等），
    不把 Bilibili/YouTube 的 format_id（如 3006、30280）误判为分辨率。"""

    if not format_str or format_str.strip().lower() in {"best", "bestvideo", "worst"}:
        return 0

    text = format_str.strip()
    heights: list[int] = []
    heights.extend(int(match.group(1)) for match in _FORMAT_HEIGHT_P_PATTERN.finditer(text))
    heights.extend(int(match.group(1)) for match in _FORMAT_HEIGHT_FILTER_PATTERN.finditer(text))
    heights.extend(int(match.group(1)) for match in _FORMAT_RESOLUTION_PAIR_PATTERN.finditer(text))
    standalone = _FORMAT_STANDALONE_HEIGHT_PATTERN.match(text)
    if standalone:
        value = int(standalone.group(1))
        if value in _KNOWN_VIDEO_HEIGHTS:
            heights.append(value)

    valid = [height for height in heights if 240 <= height <= 4320]
    if not valid:
        return 0
    return max(valid)



@router.post("/info", response_model=VideoInfoResponse)
def video_info(payload: VideoInfoRequest) -> VideoInfoResponse:
    if not info_semaphore.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="当前解析请求较多，请稍后再试")
    cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
    provided_cookies = bool((cookies or "").strip() or (payload.browser_cookies or "").strip())
    normalized_url = _coerce_video_url(str(payload.url))
    try:
        return extract_info(normalized_url, cookies, payload.browser_cookies)
    except Exception as exc:
        _log_extract_failure(
            endpoint="/api/video/info",
            url=normalized_url,
            exc=exc,
            stage="info",
            provided_cookies=provided_cookies,
        )
        raise HTTPException(
            status_code=400,
            detail=_humanize_extract_error(exc, stage="info", url=normalized_url),
        ) from exc
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
        url=_coerce_video_url(str(payload.url)),
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
    url = _coerce_video_url(url)
    try:
        check_concurrent_download(user)
        check_resolution_allowed(user, _guess_height_from_format(format_choice))
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    if is_likely_large_download(format_choice):
        try:
            check_storage_before_large_download()
        except StoragePressureError as exc:
            raise HTTPException(status_code=503, detail=exc.message_zh) from exc
    task = task_store.create(url, user_id=user.id if user else None)
    write_task_meta(task.task_id, user)
    if user is not None:
        record_task_created(
            user_id=user.id,
            task_id=task.task_id,
            kind="download",
            url=url,
            format=format_choice,
        )
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


@router.post("/batch", response_model=BatchDownloadResponse)
def create_batch_download_tasks(
    payload: BatchDownloadRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> BatchDownloadResponse:
    max_urls = VIP_BATCH_MAX_URLS if user.is_vip else FREE_BATCH_MAX_URLS
    if len(payload.urls) > max_urls:
        if user.is_vip:
            raise HTTPException(status_code=400, detail=f"批量下载最多 {max_urls} 个链接")
        raise HTTPException(
            status_code=402,
            detail="批量下载为会员功能，免费用户请每次提交一个链接，或升级会员后最多一次 10 个",
        )
    cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
    results: list[BatchDownloadTaskItem] = []
    for item_url in payload.urls:
        try:
            url = _coerce_video_url(str(item_url))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            results.append(BatchDownloadTaskItem(url=str(item_url), status="failed", error=detail))
            continue
        try:
            created = _start_download_job(
                background_tasks=background_tasks,
                user=user,
                url=url,
                format_choice=payload.format,
                with_subtitle=payload.with_subtitle,
                cookies=cookies,
                browser_cookies=payload.browser_cookies,
            )
            results.append(BatchDownloadTaskItem(url=url, task_id=created.task_id, status=created.status))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            results.append(BatchDownloadTaskItem(url=url, status="failed", error=detail))
        except QuotaExceededError as exc:
            results.append(BatchDownloadTaskItem(url=url, status="failed", error=str(exc)))
    return BatchDownloadResponse(tasks=results)


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
    normalized_url = _coerce_video_url(str(payload.url))
    try:
        cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
        info, token, selected_url = extract_direct_link(
            normalized_url,
            payload.format,
            cookies,
            payload.browser_cookies,
        )
    except Exception as exc:
        provided_cookies = bool((cookies or "").strip() or (payload.browser_cookies or "").strip())
        _log_extract_failure(
            endpoint="/api/video/direct",
            url=normalized_url,
            exc=exc,
            stage="download",
            provided_cookies=provided_cookies,
        )
        raise HTTPException(
            status_code=400,
            detail=_humanize_extract_error(exc, stage="download", url=normalized_url),
        ) from exc

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
