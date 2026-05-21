import shutil

from fastapi import APIRouter

from app.core.config import ASR_BASE_URL, ASR_ENABLED

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "dependencies": {
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "ffprobe": bool(shutil.which("ffprobe")),
            "asr_enabled": ASR_ENABLED,
            "asr_base_url": ASR_BASE_URL if ASR_ENABLED else None,
        },
    }
