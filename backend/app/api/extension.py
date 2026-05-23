from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.db.models import User
from app.models.schemas import ExtensionCaptureRequest, ExtensionCaptureResponse
from app.services.extension_capture_store import extension_capture_store

router = APIRouter(prefix="/extension")


@router.post("/captures", response_model=ExtensionCaptureResponse)
def create_extension_capture(
    payload: ExtensionCaptureRequest,
    current_user: User = Depends(get_current_user),
) -> ExtensionCaptureResponse:
    capture = extension_capture_store.create(payload, user_id=current_user.id)
    return ExtensionCaptureResponse(
        capture_id=capture.capture_id,
        media_count=len(payload.media_requests),
    )


@router.get("/captures/{capture_id}", response_model=ExtensionCaptureRequest)
def get_extension_capture(
    capture_id: str,
    current_user: User = Depends(get_current_user),
) -> ExtensionCaptureRequest:
    capture = extension_capture_store.get(capture_id)
    if not capture:
        raise HTTPException(status_code=404, detail="capture not found")
    if capture.user_id is not None and capture.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="capture not found")
    return capture.payload
