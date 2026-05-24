from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import DOWNLOAD_DIR, SUBTITLE_UPLOAD_MAX_BYTES
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.models.schemas import AiChatRequest, AiChatResponse, AiSummaryCreateResponse, AiSummaryRequest, AiSummaryStatusResponse
from app.services.ai_summary_service import call_deepseek_video_chat, generate_ai_summary_from_subtitle_task, generate_ai_summary_task
from app.services.ai_task_store import ai_summary_task_store
from app.services.bilibili_auth_store import bili_auth_store
from app.services.quota_service import (
    QuotaExceededError,
    check_and_consume_ai_chat,
    check_concurrent_ai,
    consume_ai_quota,
)
from app.services.history_service import load_ai_task_from_disk, record_task_created
from app.services.task_meta import write_task_meta
from app.utils.url_normalize import UrlNormalizeError, normalize_video_url

router = APIRouter(prefix="/ai")


def _coerce_video_url(raw: str) -> str:
    try:
        return normalize_video_url(raw)
    except UrlNormalizeError as exc:
        raise HTTPException(status_code=400, detail="未能识别有效视频链接，请检查链接格式。") from exc
ALLOWED_SUBTITLE_SUFFIXES = {".srt", ".vtt"}


@router.post("/summary", response_model=AiSummaryCreateResponse)
def create_ai_summary_task(
    payload: AiSummaryRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiSummaryCreateResponse:
    try:
        check_concurrent_ai(user)
        consume_ai_quota(db, user)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    normalized_url = _coerce_video_url(str(payload.url))
    task = ai_summary_task_store.create(normalized_url, user_id=user.id)
    write_task_meta(task.task_id, user)
    record_task_created(
        user_id=user.id,
        task_id=task.task_id,
        kind="ai_summary",
        url=normalized_url,
    )
    cookies = payload.cookies or bili_auth_store.get_cookies(payload.auth_session_id)
    background_tasks.add_task(
        generate_ai_summary_task,
        task.task_id,
        normalized_url,
        cookies,
        payload.browser_cookies,
    )
    return AiSummaryCreateResponse(task_id=task.task_id, status=task.status)


@router.post("/summary/subtitle", response_model=AiSummaryCreateResponse)
async def create_ai_summary_from_subtitle(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=512),
    url: str | None = Form(default=None, max_length=20_000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiSummaryCreateResponse:
    try:
        check_concurrent_ai(user)
        consume_ai_quota(db, user)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUBTITLE_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持上传 .srt 或 .vtt 字幕文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="字幕文件为空")
    if len(content) > SUBTITLE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail="字幕文件过大，请上传更小的 SRT/VTT 文件")

    task = ai_summary_task_store.create(url or file.filename or "uploaded-subtitle", user_id=user.id)
    write_task_meta(task.task_id, user)
    record_task_created(
        user_id=user.id,
        task_id=task.task_id,
        kind="ai_summary",
        url=url or file.filename or "uploaded-subtitle",
        title=title,
    )
    task_dir = DOWNLOAD_DIR / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    subtitle_path = task_dir / f"uploaded{suffix}"
    subtitle_path.write_bytes(content)
    background_tasks.add_task(
        generate_ai_summary_from_subtitle_task,
        task.task_id,
        subtitle_path,
        title,
        url,
    )
    return AiSummaryCreateResponse(task_id=task.task_id, status=task.status)


@router.get("/summary/{task_id}", response_model=AiSummaryStatusResponse)
def get_ai_summary_task(task_id: str) -> AiSummaryStatusResponse:
    task = ai_summary_task_store.get(task_id)
    if not task:
        restored = load_ai_task_from_disk(task_id)
        if restored:
            ai_summary_task_store.restore(restored)
            task = restored
    if not task:
        raise HTTPException(status_code=404, detail="AI 总结任务不存在或已过期")
    return AiSummaryStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        message=task.message,
        title=task.title,
        webpage_url=task.webpage_url,
        transcript_language=task.transcript_language,
        transcript_segments=task.transcript_segments,
        summary=task.summary,
        error=task.error,
    )


@router.post("/summary/{task_id}/chat", response_model=AiChatResponse)
def chat_with_ai_summary(
    task_id: str,
    payload: AiChatRequest,
    user: User = Depends(get_current_user),
) -> AiChatResponse:
    task = ai_summary_task_store.get(task_id)
    if not task:
        restored = load_ai_task_from_disk(task_id)
        if restored:
            ai_summary_task_store.restore(restored)
            task = restored
    if not task:
        raise HTTPException(status_code=404, detail="AI 总结任务不存在或已过期")
    if task.user_id is not None and task.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该 AI 总结任务")
    if task.status != "completed":
        raise HTTPException(status_code=409, detail="AI 总结任务尚未完成，暂时不能问答")
    try:
        check_and_consume_ai_chat(task, user)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    try:
        return call_deepseek_video_chat(
            title=task.title,
            summary=task.summary,
            segments=task.transcript_segments,
            question=payload.question,
            history=payload.history,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
