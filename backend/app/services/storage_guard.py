"""Downloads directory and disk usage guard for small VPS deployments."""

from __future__ import annotations

import logging
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.core.config import (
    DISK_CLEANUP_USAGE_PERCENT,
    DISK_EMERGENCY_USAGE_PERCENT,
    DOWNLOADS_CLEANUP_BYTES,
    DOWNLOADS_CLEANUP_MIN_AGE_SECONDS,
    DOWNLOADS_EMERGENCY_KEEP_RECENT_TASKS,
    DOWNLOADS_LARGE_FILE_BYTES,
    DOWNLOADS_WARN_BYTES,
    DOWNLOAD_DIR,
)
from app.services.ai_task_store import ai_summary_task_store
from app.services.task_meta import read_task_meta
from app.services.task_store import task_store

logger = logging.getLogger(__name__)

StorageStatus = Literal["ok", "warn", "cleanup_required", "emergency_cleanup_required"]

STORAGE_PRESSURE_MESSAGE_ZH = (
    "服务器临时存储空间紧张，已尝试自动清理，但空间仍不足。请稍后重试，或选择较低清晰度。"
)
STORAGE_PRESSURE_MESSAGE_EN = (
    "Temporary server storage is under pressure. Automatic cleanup was attempted, "
    "but space is still insufficient. Please try again later or choose a lower quality."
)

_FORMAT_HEIGHT_P_PATTERN = re.compile(r"(\d{3,4})p\b", re.I)
_FORMAT_HEIGHT_FILTER_PATTERN = re.compile(r"height\s*<=?\s*(\d{3,4})", re.I)
_FORMAT_RESOLUTION_PAIR_PATTERN = re.compile(r"\d+x(\d{3,4})\b")
_FORMAT_STANDALONE_HEIGHT_PATTERN = re.compile(r"^(\d{3,4})p?$", re.I)
_KNOWN_VIDEO_HEIGHTS = frozenset({240, 360, 480, 540, 576, 720, 1080, 1440, 2160, 4320})

_DOWNLOAD_ACTIVE_STATUSES = frozenset({"queued", "starting", "downloading", "processing"})
_AI_ACTIVE_STATUSES = frozenset({"queued", "extracting", "summarizing"})
_PART_SUFFIXES = (".part", ".ytdl", ".temp", ".tmp", ".download")


class StoragePressureError(Exception):
    """Raised when disk remains critically full after emergency cleanup."""

    def __init__(self, message_zh: str = STORAGE_PRESSURE_MESSAGE_ZH, message_en: str = STORAGE_PRESSURE_MESSAGE_EN) -> None:
        self.message_zh = message_zh
        self.message_en = message_en
        super().__init__(message_zh)


@dataclass
class FileEntry:
    path: Path
    size_bytes: int


@dataclass
class TaskDirectoryEntry:
    task_id: str
    path: Path
    total_bytes: int
    latest_mtime: float
    is_active: bool
    has_in_progress_files: bool


@dataclass
class StorageStats:
    downloads_bytes: int
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    disk_usage_percent: float
    status: StorageStatus
    task_directories: list[TaskDirectoryEntry] = field(default_factory=list)
    top_files: list[FileEntry] = field(default_factory=list)
    top_task_dirs: list[TaskDirectoryEntry] = field(default_factory=list)


@dataclass
class CleanupPlan:
    mode: Literal["normal", "emergency"]
    delete_paths: list[Path]
    keep_task_ids: list[str]
    estimated_release_bytes: int
    skipped_active: list[str] = field(default_factory=list)


@dataclass
class GuardCycleResult:
    status_before: StorageStatus
    status_after: StorageStatus
    normal_deleted: int = 0
    emergency_deleted: int = 0
    bytes_freed: int = 0
    dry_run: bool = False


def guess_height_from_format(format_str: str) -> int:
    if not format_str or format_str.strip().lower() in {"best", "bestvideo", "worst"}:
        return 0
    text = format_str.strip()
    heights: list[int] = []
    heights.extend(int(match.group(1)) for match in _FORMAT_HEIGHT_P_PATTERN.finditer(text))
    heights.extend(int(match.group(1)) for match in _FORMAT_HEIGHT_FILTER_PATTERN.finditer(text))
    heights.extend(int(match.group(1)) for match in _FORMAT_RESOLUTION_PAIR_PATTERN.finditer(text))
    standalone = _FORMAT_STANDALONE_HEIGHT_PATTERN.match(text)
    if standalone:
        value = int(standalone.group(1))
        if value in _KNOWN_VIDEO_HEIGHTS:
            heights.append(value)
    valid = [height for height in heights if 240 <= height <= 4320]
    return max(valid) if valid else 0


def is_likely_large_download(format_choice: str) -> bool:
    """Heuristic: downloads likely to exceed DOWNLOADS_LARGE_FILE_BYTES."""
    height = guess_height_from_format(format_choice)
    if height >= 1080:
        return True
    lowered = (format_choice or "").strip().lower()
    if not lowered or lowered in {"best", "bestvideo+bestaudio/best", "bestvideo+bestaudio"}:
        return True
    if "best" in lowered and not any(token in lowered for token in ("720", "480", "360", "240")):
        return True
    return False


def _disk_usage_for_downloads() -> tuple[int, int, int]:
    usage = shutil.disk_usage(DOWNLOAD_DIR)
    return int(usage.total), int(usage.used), int(usage.free)


def _path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


def _latest_mtime(path: Path) -> float:
    if not path.exists():
        return 0.0
    try:
        latest = path.stat().st_mtime
    except OSError:
        latest = 0.0
    if path.is_file():
        return latest
    for child in path.rglob("*"):
        if child.is_file():
            try:
                latest = max(latest, child.stat().st_mtime)
            except OSError:
                continue
    return latest


def _has_in_progress_files(task_dir: Path) -> bool:
    for child in task_dir.iterdir():
        if not child.is_file():
            continue
        name = child.name.lower()
        if any(name.endswith(suffix) for suffix in _PART_SUFFIXES):
            return True
    return False


def _is_download_task_active(task_id: str) -> bool:
    task = task_store.get(task_id)
    return bool(task and task.status in _DOWNLOAD_ACTIVE_STATUSES)


def _is_ai_task_active(task_id: str) -> bool:
    task = ai_summary_task_store.get(task_id)
    return bool(task and task.status in _AI_ACTIVE_STATUSES)


def is_task_directory_active(task_id: str, task_dir: Path) -> bool:
    if _is_download_task_active(task_id) or _is_ai_task_active(task_id):
        return True
    return _has_in_progress_files(task_dir)


def _iter_task_directories() -> list[TaskDirectoryEntry]:
    entries: list[TaskDirectoryEntry] = []
    if not DOWNLOAD_DIR.exists():
        return entries
    for path in DOWNLOAD_DIR.iterdir():
        if path.name == ".gitkeep" or not path.is_dir():
            continue
        task_id = path.name
        entries.append(
            TaskDirectoryEntry(
                task_id=task_id,
                path=path,
                total_bytes=_path_size_bytes(path),
                latest_mtime=_latest_mtime(path),
                is_active=is_task_directory_active(task_id, path),
                has_in_progress_files=_has_in_progress_files(path),
            )
        )
    return entries


def _iter_all_files(limit: int = 20) -> list[FileEntry]:
    files: list[FileEntry] = []
    if not DOWNLOAD_DIR.exists():
        return files
    for path in DOWNLOAD_DIR.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        try:
            files.append(FileEntry(path=path, size_bytes=path.stat().st_size))
        except OSError:
            continue
    files.sort(key=lambda item: item.size_bytes, reverse=True)
    return files[:limit]


def evaluate_storage_status(downloads_bytes: int, disk_usage_percent: float) -> StorageStatus:
    if disk_usage_percent >= DISK_EMERGENCY_USAGE_PERCENT:
        return "emergency_cleanup_required"
    if downloads_bytes >= DOWNLOADS_CLEANUP_BYTES or disk_usage_percent >= DISK_CLEANUP_USAGE_PERCENT:
        return "cleanup_required"
    if downloads_bytes >= DOWNLOADS_WARN_BYTES:
        return "warn"
    return "ok"


def collect_storage_stats(*, now: float | None = None) -> StorageStats:
    _ = now  # reserved for tests injecting time
    task_dirs = _iter_task_directories()
    downloads_bytes = sum(entry.total_bytes for entry in task_dirs)
    disk_total, disk_used, disk_free = _disk_usage_for_downloads()
    disk_usage_percent = (disk_used / disk_total * 100.0) if disk_total else 0.0
    status = evaluate_storage_status(downloads_bytes, disk_usage_percent)
    top_task_dirs = sorted(task_dirs, key=lambda item: item.total_bytes, reverse=True)[:10]
    return StorageStats(
        downloads_bytes=downloads_bytes,
        disk_total_bytes=disk_total,
        disk_used_bytes=disk_used,
        disk_free_bytes=disk_free,
        disk_usage_percent=round(disk_usage_percent, 2),
        status=status,
        task_directories=task_dirs,
        top_files=_iter_all_files(20),
        top_task_dirs=top_task_dirs,
    )


def _task_age_seconds(entry: TaskDirectoryEntry, now: float) -> float:
    meta = read_task_meta(entry.path)
    if meta and meta.get("created_at"):
        try:
            created = float(meta["created_at"])
        except (TypeError, ValueError):
            created = entry.latest_mtime
    else:
        created = entry.latest_mtime
    return max(0.0, now - created)


def plan_normal_cleanup(stats: StorageStats, *, now: float | None = None) -> CleanupPlan:
    current = now or time.time()
    candidates: list[TaskDirectoryEntry] = []
    for entry in stats.task_directories:
        if entry.is_active or entry.has_in_progress_files:
            continue
        if _task_age_seconds(entry, current) < DOWNLOADS_CLEANUP_MIN_AGE_SECONDS:
            continue
        candidates.append(entry)

    candidates.sort(key=lambda item: (item.latest_mtime, -item.total_bytes))

    delete_paths: list[Path] = []
    estimated = 0
    projected_downloads = stats.downloads_bytes
    projected_disk_pct = stats.disk_usage_percent

    for entry in candidates:
        if projected_downloads < DOWNLOADS_CLEANUP_BYTES and projected_disk_pct < DISK_CLEANUP_USAGE_PERCENT:
            break
        delete_paths.append(entry.path)
        estimated += entry.total_bytes
        projected_downloads = max(0, projected_downloads - entry.total_bytes)
        if stats.disk_total_bytes:
            projected_used = max(0, stats.disk_used_bytes - estimated)
            projected_disk_pct = projected_used / stats.disk_total_bytes * 100.0

    return CleanupPlan(
        mode="normal",
        delete_paths=delete_paths,
        keep_task_ids=[entry.task_id for entry in stats.task_directories if entry.path not in delete_paths],
        estimated_release_bytes=estimated,
    )


def plan_emergency_cleanup(stats: StorageStats) -> CleanupPlan:
    sorted_dirs = sorted(stats.task_directories, key=lambda item: item.latest_mtime, reverse=True)
    keep_ids = {entry.task_id for entry in sorted_dirs[:DOWNLOADS_EMERGENCY_KEEP_RECENT_TASKS]}

    delete_paths: list[Path] = []
    skipped_active: list[str] = []
    estimated = 0

    for entry in sorted_dirs:
        if entry.is_active or entry.has_in_progress_files:
            skipped_active.append(entry.task_id)
            keep_ids.add(entry.task_id)
            continue
        if entry.task_id in keep_ids:
            continue
        delete_paths.append(entry.path)
        estimated += entry.total_bytes

    return CleanupPlan(
        mode="emergency",
        delete_paths=delete_paths,
        keep_task_ids=sorted(keep_ids),
        estimated_release_bytes=estimated,
        skipped_active=skipped_active,
    )


def _remove_path(path: Path) -> int:
    if not path.exists():
        return 0
    size = _path_size_bytes(path)
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as exc:
        logger.warning("Storage guard failed to remove %s: %s", path, exc)
        return 0
    return size


def execute_cleanup_plan(plan: CleanupPlan, *, dry_run: bool = False) -> tuple[int, int]:
    deleted = 0
    freed = 0
    for path in plan.delete_paths:
        if dry_run:
            freed += _path_size_bytes(path)
            deleted += 1
            continue
        freed += _remove_path(path)
        if path.exists():
            continue
        deleted += 1
        logger.info("Storage guard (%s) removed %s", plan.mode, path)
    return deleted, freed


def run_emergency_cleanup(*, dry_run: bool = False, now: float | None = None) -> GuardCycleResult:
    stats_before = collect_storage_stats(now=now)
    plan = plan_emergency_cleanup(stats_before)
    deleted, freed = execute_cleanup_plan(plan, dry_run=dry_run)
    stats_after = collect_storage_stats(now=now)
    if not dry_run and deleted:
        logger.warning(
            "Emergency storage cleanup: removed %d task dirs, freed ~%.1f MB, disk %.1f%% -> %.1f%%",
            deleted,
            freed / (1024 * 1024),
            stats_before.disk_usage_percent,
            stats_after.disk_usage_percent,
        )
    return GuardCycleResult(
        status_before=stats_before.status,
        status_after=stats_after.status,
        emergency_deleted=deleted,
        bytes_freed=freed,
        dry_run=dry_run,
    )


def run_normal_cleanup(*, dry_run: bool = False, now: float | None = None) -> GuardCycleResult:
    stats_before = collect_storage_stats(now=now)
    plan = plan_normal_cleanup(stats_before, now=now)
    deleted, freed = execute_cleanup_plan(plan, dry_run=dry_run)
    stats_after = collect_storage_stats(now=now)
    if not dry_run and deleted:
        logger.info(
            "Normal storage cleanup: removed %d task dirs, freed ~%.1f MB, downloads %.1f GB, disk %.1f%%",
            deleted,
            freed / (1024 * 1024),
            stats_after.downloads_bytes / (1024**3),
            stats_after.disk_usage_percent,
        )
    return GuardCycleResult(
        status_before=stats_before.status,
        status_after=stats_after.status,
        normal_deleted=deleted,
        bytes_freed=freed,
        dry_run=dry_run,
    )


def run_storage_guard_cycle(*, dry_run: bool = False, now: float | None = None) -> GuardCycleResult:
    """Evaluate disk/downloads and run cleanup when thresholds require it."""
    stats = collect_storage_stats(now=now)
    if stats.status == "warn":
        logger.warning(
            "Downloads folder size %.2f GB exceeds warn threshold %.2f GB (disk %.1f%%)",
            stats.downloads_bytes / (1024**3),
            DOWNLOADS_WARN_BYTES / (1024**3),
            stats.disk_usage_percent,
        )
        return GuardCycleResult(status_before=stats.status, status_after=stats.status, dry_run=dry_run)

    if stats.status == "emergency_cleanup_required":
        return run_emergency_cleanup(dry_run=dry_run, now=now)

    if stats.status == "cleanup_required":
        return run_normal_cleanup(dry_run=dry_run, now=now)

    return GuardCycleResult(status_before=stats.status, status_after=stats.status, dry_run=dry_run)


def check_storage_before_large_download(*, now: float | None = None) -> None:
    """Try emergency cleanup when disk is critical; block only if still >= emergency threshold."""
    stats = collect_storage_stats(now=now)
    if stats.disk_usage_percent < DISK_EMERGENCY_USAGE_PERCENT:
        return
    run_emergency_cleanup(dry_run=False, now=now)
    stats_after = collect_storage_stats(now=now)
    if stats_after.disk_usage_percent >= DISK_EMERGENCY_USAGE_PERCENT:
        raise StoragePressureError()


def format_bytes(num: int) -> str:
    if num >= 1024**3:
        return f"{num / (1024**3):.2f} GB"
    if num >= 1024**2:
        return f"{num / (1024**2):.1f} MB"
    if num >= 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num} B"
