"""Per-task directory metadata for retention and cleanup."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import DOWNLOAD_DIR, FREE_FILE_RETENTION_SECONDS, VIP_FILE_RETENTION_SECONDS
from app.db.models import User

META_FILENAME = ".saveany-meta.json"


def retention_seconds_for_user(user: Optional[User]) -> int:
    if user is not None and user.is_vip:
        return VIP_FILE_RETENTION_SECONDS
    return FREE_FILE_RETENTION_SECONDS


def write_task_meta(task_id: str, user: Optional[User]) -> None:
    task_dir = DOWNLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    retention = retention_seconds_for_user(user)
    payload = {
        "user_id": user.id if user else None,
        "is_vip": bool(user and user.is_vip),
        "created_at": time.time(),
        "retention_seconds": retention,
    }
    (task_dir / META_FILENAME).write_text(json.dumps(payload), encoding="utf-8")


def read_task_meta(task_dir: Path) -> dict[str, Any] | None:
    meta_path = task_dir / META_FILENAME
    if not meta_path.is_file():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
