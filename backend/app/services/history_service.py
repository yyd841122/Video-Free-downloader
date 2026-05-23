"""Persist and list user download / AI summary task metadata."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DOWNLOAD_DIR
from app.db.database import session_scope
from app.db.models import User, UserTaskHistory
from app.models.schemas import AiSummaryResult, TranscriptSegment
from app.services.ai_task_store import AiSummaryTask, ai_summary_task_store
from app.services.task_store import task_store

logger = logging.getLogger(__name__)

HISTORY_LIST_LIMIT = 50


def _touch_ts() -> int:
    import time

    return int(time.time())


def record_task_created(
    *,
    user_id: int,
    task_id: str,
    kind: str,
    url: str,
    title: str | None = None,
    format: str | None = None,
    status: str = "queued",
) -> None:
    now = _touch_ts()
    with session_scope() as db:
        existing = db.execute(
            select(UserTaskHistory).where(UserTaskHistory.task_id == task_id)
        ).scalar_one_or_none()
        if existing:
            return
        db.add(
            UserTaskHistory(
                user_id=user_id,
                task_id=task_id,
                kind=kind,
                url=url,
                title=title,
                format=format,
                status=status,
                created_at=now,
                updated_at=now,
            )
        )


def sync_download_task(task_id: str) -> None:
    task = task_store.get(task_id)
    if not task or task.user_id is None:
        return
    with session_scope() as db:
        row = db.execute(select(UserTaskHistory).where(UserTaskHistory.task_id == task_id)).scalar_one_or_none()
        if row is None:
            record_task_created(
                user_id=task.user_id,
                task_id=task_id,
                kind="download",
                url=task.url,
                status=task.status,
            )
            row = db.execute(select(UserTaskHistory).where(UserTaskHistory.task_id == task_id)).scalar_one_or_none()
        if row is None:
            return
        row.status = task.status
        row.filename = task.filename
        row.error = task.error
        if task.filename and not row.title:
            row.title = task.filename
        row.updated_at = _touch_ts()
        db.add(row)


def sync_ai_task(task_id: str) -> None:
    task = ai_summary_task_store.get(task_id)
    if not task or task.user_id is None:
        return
    with session_scope() as db:
        row = db.execute(select(UserTaskHistory).where(UserTaskHistory.task_id == task_id)).scalar_one_or_none()
        if row is None:
            record_task_created(
                user_id=task.user_id,
                task_id=task_id,
                kind="ai_summary",
                url=task.url,
                title=task.title,
                status=task.status,
            )
            row = db.execute(select(UserTaskHistory).where(UserTaskHistory.task_id == task_id)).scalar_one_or_none()
        if row is None:
            return
        row.status = task.status
        row.title = task.title or row.title
        row.error = task.error
        row.updated_at = _touch_ts()
        db.add(row)


def _download_file_available(task_id: str) -> bool:
    task = task_store.get(task_id)
    if task and task.file_path and task.file_path.is_file():
        return True
    task_dir = DOWNLOAD_DIR / task_id
    if not task_dir.is_dir():
        return False
    for path in task_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".mp4", ".webm", ".mkv", ".m4a", ".mp3", ".mov"}:
            if path.stat().st_size > 1024:
                return True
    return False


def _ai_artifacts_available(task_id: str) -> bool:
    task_dir = DOWNLOAD_DIR / task_id
    return (task_dir / "summary.json").is_file()


def list_history_for_user(db: Session, user: User, *, limit: int = HISTORY_LIST_LIMIT) -> list[dict]:
    rows = db.execute(
        select(UserTaskHistory)
        .where(UserTaskHistory.user_id == user.id)
        .order_by(UserTaskHistory.created_at.desc())
        .limit(limit)
    ).scalars().all()

    items: list[dict] = []
    for row in rows:
        file_available = _download_file_available(row.task_id) if row.kind == "download" else _ai_artifacts_available(row.task_id)
        download_url = f"/api/files/{row.task_id}" if row.kind == "download" and file_available and row.status == "completed" else None
        items.append(
            {
                "id": row.id,
                "task_id": row.task_id,
                "kind": row.kind,
                "url": row.url,
                "title": row.title,
                "format": row.format,
                "status": row.status,
                "filename": row.filename,
                "error": row.error,
                "file_available": file_available,
                "download_url": download_url,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )
    return items


def load_ai_task_from_disk(task_id: str) -> AiSummaryTask | None:
    """从任务目录恢复已完成的 AI 总结（内存任务过期后仍可查看）。"""
    task_dir = DOWNLOAD_DIR / task_id
    summary_path = task_dir / "summary.json"
    if not summary_path.is_file():
        return None
    try:
        summary = AiSummaryResult.model_validate_json(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load summary.json for %s: %s", task_id, exc)
        return None

    segments: list[TranscriptSegment] = []
    transcript_path = task_dir / "transcript.json"
    if transcript_path.is_file():
        try:
            payload = json.loads(transcript_path.read_text(encoding="utf-8"))
            for item in payload.get("segments") or []:
                segments.append(TranscriptSegment.model_validate(item))
        except Exception as exc:
            logger.warning("Failed to load transcript.json for %s: %s", task_id, exc)

    meta_path = task_dir / ".saveany-meta.json"
    user_id = None
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            user_id = meta.get("user_id")
        except Exception:
            pass

    return AiSummaryTask(
        task_id=task_id,
        url="",
        user_id=user_id,
        status="completed",
        progress=100,
        title=summary.title,
        transcript_segments=segments,
        summary=summary,
        task_dir=task_dir,
    )
