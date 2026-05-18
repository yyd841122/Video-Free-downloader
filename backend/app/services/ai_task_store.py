from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import TASK_RETENTION_SECONDS
from app.models.schemas import AiSummaryResult, TranscriptSegment


@dataclass
class AiSummaryTask:
    task_id: str
    url: str
    status: str = "queued"
    progress: float = 0
    message: str | None = None
    title: str | None = None
    webpage_url: str | None = None
    transcript_language: str | None = None
    transcript_segments: list[TranscriptSegment] = field(default_factory=list)
    summary: AiSummaryResult | None = None
    error: str | None = None
    task_dir: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class AiSummaryTaskStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._tasks: dict[str, AiSummaryTask] = {}

    def create(self, url: str) -> AiSummaryTask:
        with self._lock:
            self.cleanup_locked()
            task = AiSummaryTask(task_id=str(uuid.uuid4()), url=url)
            self._tasks[task.task_id] = task
            return task

    def get(self, task_id: str) -> AiSummaryTask | None:
        with self._lock:
            return self._tasks.get(task_id)

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


ai_summary_task_store = AiSummaryTaskStore()
