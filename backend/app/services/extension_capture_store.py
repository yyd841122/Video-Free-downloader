from dataclasses import dataclass, field
from time import time
from uuid import uuid4

from app.models.schemas import ExtensionCaptureRequest


@dataclass
class ExtensionCapture:
    capture_id: str
    payload: ExtensionCaptureRequest
    created_at: float = field(default_factory=time)


class ExtensionCaptureStore:
    def __init__(self) -> None:
        self._captures: dict[str, ExtensionCapture] = {}

    def create(self, payload: ExtensionCaptureRequest) -> ExtensionCapture:
        capture = ExtensionCapture(capture_id=uuid4().hex, payload=payload)
        self._captures[capture.capture_id] = capture
        return capture

    def get(self, capture_id: str) -> ExtensionCapture | None:
        return self._captures.get(capture_id)


extension_capture_store = ExtensionCaptureStore()
