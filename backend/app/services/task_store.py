from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.core.config import TASK_RETENTION_SECONDS


@dataclass
class DownloadTask:
    task_id: str
    url: str
    user_id: int | None = None
    status: str = "queued"
    progress: float = 0
    speed: str | None = None
    eta: int | None = None
    filename: str | None = None
    file_path: Path | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class TaskStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._tasks: dict[str, DownloadTask] = {}

    def create(self, url: str, user_id: int | None = None) -> DownloadTask:
        with self._lock:
            self.cleanup_locked()
            task = DownloadTask(task_id=str(uuid.uuid4()), url=url, user_id=user_id)
            self._tasks[task.task_id] = task
            return task

    def get(self, task_id: str) -> DownloadTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    _ACTIVE_STATUSES = frozenset({"queued", "starting", "downloading", "processing"})

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for task in self._tasks.values() if task.status in self._ACTIVE_STATUSES)

    def active_count_for_user(self, user_id: int | None) -> int:
        with self._lock:
            return sum(
                1
                for task in self._tasks.values()
                if task.user_id == user_id and task.status in self._ACTIVE_STATUSES
            )

    def update(self, task_id: str, **kwargs: object) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = time.time()

    def cleanup_locked(self) -> None:
        now = time.time()
        expired = [
            task_id
            for task_id, task in self._tasks.items()
            if now - task.updated_at > TASK_RETENTION_SECONDS
        ]
        for task_id in expired:
            self._tasks.pop(task_id, None)


task_store = TaskStore()
