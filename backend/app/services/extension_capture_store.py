from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from time import time
from typing import Optional
from uuid import uuid4

from app.models.schemas import ExtensionCaptureRequest

# 全局最大记录数；超过后按 FIFO 淘汰最旧记录
MAX_CAPTURES = 1000


@dataclass
class ExtensionCapture:
    capture_id: str
    payload: ExtensionCaptureRequest
    user_id: Optional[int] = None
    created_at: float = field(default_factory=time)


class ExtensionCaptureStore:
    def __init__(self, max_size: int = MAX_CAPTURES) -> None:
        self._captures: "OrderedDict[str, ExtensionCapture]" = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def create(
        self,
        payload: ExtensionCaptureRequest,
        user_id: Optional[int] = None,
    ) -> ExtensionCapture:
        capture = ExtensionCapture(
            capture_id=uuid4().hex,
            payload=payload,
            user_id=user_id,
        )
        with self._lock:
            self._captures[capture.capture_id] = capture
            self._captures.move_to_end(capture.capture_id)
            while len(self._captures) > self._max_size:
                self._captures.popitem(last=False)
        return capture

    def get(self, capture_id: str) -> ExtensionCapture | None:
        with self._lock:
            return self._captures.get(capture_id)


extension_capture_store = ExtensionCaptureStore()
