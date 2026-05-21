"""ASR (Automatic Speech Recognition) service.

Calls a local docker-whisper API to transcribe audio/video files
into text, SRT, or VTT subtitles. This module is independent of the
main AI summary pipeline and is only used when platform subtitles
are unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests

from app.core.config import (
    ASR_BASE_URL,
    ASR_ENABLED,
    ASR_LANGUAGE,
    ASR_MAX_INPUT_BYTES,
    ASR_MAX_AUDIO_MINUTES,
    ASR_MODEL,
    ASR_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ("text", "srt", "vtt")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ASRServiceError(RuntimeError):
    """Base exception for ASR service errors."""


class ASRServiceDisabledError(ASRServiceError):
    """Raised when ASR is not enabled."""


class ASRServiceUnavailableError(ASRServiceError):
    """Raised when the docker-whisper server cannot be reached."""


class ASRTranscriptionError(ASRServiceError):
    """Raised when transcription fails."""


class ASRFileError(ASRServiceError):
    """Raised when the input file is invalid."""


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class ASRTranscriptionResult:
    """Result of an ASR transcription call."""

    text: str
    response_format: str
    language: str | None
    model: str
    raw_content: str
    file_path: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_file(file_path: Path) -> None:
    """Validate that the input file exists and is not empty."""
    if not file_path.exists():
        raise ASRFileError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise ASRFileError(f"Not a file: {file_path}")
    if file_path.stat().st_size == 0:
        raise ASRFileError(f"File is empty: {file_path}")
    if file_path.stat().st_size > ASR_MAX_INPUT_BYTES:
        max_mb = ASR_MAX_INPUT_BYTES / 1024 / 1024
        raise ASRFileError(f"ASR input file is too large. Max allowed is {max_mb:.0f}MB.")


def _health_check(base_url: str, timeout: int) -> None:
    """Verify the ASR server is reachable."""
    try:
        resp = requests.get(f"{base_url}/health", timeout=timeout)
        resp.raise_for_status()
    except requests.ConnectionError:
        raise ASRServiceUnavailableError(
            f"Cannot connect to ASR service at {base_url}. "
            "Is docker-whisper running?"
        )
    except requests.HTTPError as exc:
        raise ASRServiceUnavailableError(
            f"ASR service health check failed: {exc}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe_file(
    file_path: Path | str,
    response_format: str = "srt",
    language: str | None = None,
    model: str | None = None,
    timeout_seconds: int | None = None,
) -> ASRTranscriptionResult:
    """Transcribe an audio/video file via docker-whisper.

    Args:
        file_path: Path to the audio/video file.
        response_format: Output format — "text", "srt", or "vtt".
        language: BCP-47 language code (e.g. "zh", "en").
            None means auto-detect.
        model: Whisper model name. None uses config default.
        timeout_seconds: HTTP request timeout. None uses config default.

    Returns:
        ASRTranscriptionResult with the transcription.

    Raises:
        ASRServiceDisabledError: If ASR_ENABLED is False.
        ASRFileError: If the input file is missing or empty.
        ASRServiceUnavailableError: If the ASR server is unreachable.
        ASRTranscriptionError: If the server returns an error.
    """
    if not ASR_ENABLED:
        raise ASRServiceDisabledError(
            "ASR is disabled. Set ASR_ENABLED=true to enable."
        )

    if response_format not in SUPPORTED_FORMATS:
        raise ASRTranscriptionError(
            f"Unsupported format '{response_format}'. "
            f"Supported: {SUPPORTED_FORMATS}"
        )

    file_path = Path(file_path).resolve()
    _check_file(file_path)

    base_url = ASR_BASE_URL.rstrip("/")
    endpoint = f"{base_url}/v1/audio/transcriptions"
    model = model or ASR_MODEL
    timeout = timeout_seconds or ASR_TIMEOUT_SECONDS

    # Optional health check with short timeout.
    _health_check(base_url, min(timeout, 10))

    # Build multipart form data.
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        data: dict[str, str] = {
            "model": model,
            "response_format": response_format,
        }
        if language:
            data["language"] = language

        logger.info(
            "ASR transcribe: file=%s model=%s format=%s lang=%s",
            file_path.name, model, response_format, language or "auto",
        )

        try:
            resp = requests.post(
                endpoint,
                files=files,
                data=data,
                timeout=timeout,
            )
        except requests.ConnectionError:
            raise ASRServiceUnavailableError(
                f"Lost connection to ASR service at {base_url}."
            )
        except requests.Timeout:
            raise ASRTranscriptionError(
                f"ASR request timed out after {timeout}s. "
                f"File may be too long (max ~{ASR_MAX_AUDIO_MINUTES} min)."
            )

    if resp.status_code >= 400:
        raise ASRTranscriptionError(
            f"ASR transcription failed (HTTP {resp.status_code}): "
            f"{resp.text[:500]}"
        )

    raw_content = resp.text
    detected_language = resp.headers.get("x-language", language or "auto")

    return ASRTranscriptionResult(
        text=raw_content.strip(),
        response_format=response_format,
        language=detected_language,
        model=model,
        raw_content=raw_content,
        file_path=str(file_path),
    )
