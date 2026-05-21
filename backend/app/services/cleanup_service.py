from __future__ import annotations

import logging
import shutil
import threading
import time
from pathlib import Path

from app.core.config import DOWNLOAD_CLEANUP_INTERVAL_SECONDS, DOWNLOAD_CLEANUP_MAX_AGE_SECONDS, DOWNLOAD_DIR

logger = logging.getLogger(__name__)
_cleanup_thread: threading.Thread | None = None
_stop_event = threading.Event()


def cleanup_downloads_once(now: float | None = None) -> int:
    """Remove expired task directories from the downloads folder."""
    current = now or time.time()
    removed = 0
    if not DOWNLOAD_DIR.exists():
        return removed

    for path in DOWNLOAD_DIR.iterdir():
        if path.name == ".gitkeep" or not path.exists():
            continue
        try:
            mtime = path.stat().st_mtime
            if current - mtime <= DOWNLOAD_CLEANUP_MAX_AGE_SECONDS:
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed += 1
        except OSError as exc:
            logger.warning("Failed to cleanup download artifact %s: %s", path, exc)
    return removed


def _cleanup_loop() -> None:
    while not _stop_event.wait(DOWNLOAD_CLEANUP_INTERVAL_SECONDS):
        removed = cleanup_downloads_once()
        if removed:
            logger.info("Cleaned up %d expired download artifacts", removed)


def start_cleanup_worker() -> None:
    global _cleanup_thread
    if _cleanup_thread and _cleanup_thread.is_alive():
        return
    _stop_event.clear()
    _cleanup_thread = threading.Thread(target=_cleanup_loop, name="download-cleanup", daemon=True)
    _cleanup_thread.start()


def stop_cleanup_worker() -> None:
    _stop_event.set()
