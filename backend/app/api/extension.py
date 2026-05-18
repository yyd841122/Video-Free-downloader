from fastapi import APIRouter, HTTPException

from app.models.schemas import ExtensionCaptureRequest, ExtensionCaptureResponse
from app.services.extension_capture_store import extension_capture_store

router = APIRouter(prefix="/extension")


@router.post("/captures", response_model=ExtensionCaptureResponse)
def create_extension_capture(payload: ExtensionCaptureRequest) -> ExtensionCaptureResponse:
    capture = extension_capture_store.create(payload)
    return ExtensionCaptureResponse(
        capture_id=capture.capture_id,
        media_count=len(payload.media_requests),
    )


@router.get("/captures/{capture_id}", response_model=ExtensionCaptureRequest)
def get_extension_capture(capture_id: str) -> ExtensionCaptureRequest:
    capture = extension_capture_store.get(capture_id)
    if not capture:
        raise HTTPException(status_code=404, detail="capture not found")
    return capture.payload
