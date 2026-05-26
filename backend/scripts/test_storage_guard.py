"""Unit-style tests for downloads storage guard (no real large files)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import config  # noqa: E402
from app.services import storage_guard  # noqa: E402
from app.services.storage_guard import (  # noqa: E402
    StoragePressureError,
    TaskDirectoryEntry,
    check_storage_before_large_download,
    collect_storage_stats,
    evaluate_storage_status,
    execute_cleanup_plan,
    is_likely_large_download,
    plan_emergency_cleanup,
    plan_normal_cleanup,
)


def _patch_thresholds(**kwargs: int) -> None:
    for key, value in kwargs.items():
        setattr(config, key, value)
        setattr(storage_guard, key, value)


def test_status_ok_under_warn() -> None:
    _patch_thresholds(
        DOWNLOADS_WARN_BYTES=10,
        DOWNLOADS_CLEANUP_BYTES=15,
        DISK_CLEANUP_USAGE_PERCENT=70,
        DISK_EMERGENCY_USAGE_PERCENT=85,
    )
    assert evaluate_storage_status(5, 10.0) == "ok"


def test_status_warn_over_10g() -> None:
    _patch_thresholds(
        DOWNLOADS_WARN_BYTES=10,
        DOWNLOADS_CLEANUP_BYTES=20,
        DISK_CLEANUP_USAGE_PERCENT=70,
        DISK_EMERGENCY_USAGE_PERCENT=85,
    )
    assert evaluate_storage_status(12, 10.0) == "warn"


def test_status_cleanup_required_downloads() -> None:
    _patch_thresholds(
        DOWNLOADS_WARN_BYTES=10,
        DOWNLOADS_CLEANUP_BYTES=15,
        DISK_CLEANUP_USAGE_PERCENT=70,
        DISK_EMERGENCY_USAGE_PERCENT=85,
    )
    assert evaluate_storage_status(16, 10.0) == "cleanup_required"


def test_status_cleanup_required_disk_70() -> None:
    _patch_thresholds(
        DOWNLOADS_WARN_BYTES=100,
        DOWNLOADS_CLEANUP_BYTES=200,
        DISK_CLEANUP_USAGE_PERCENT=70,
        DISK_EMERGENCY_USAGE_PERCENT=85,
    )
    assert evaluate_storage_status(5, 71.0) == "cleanup_required"


def test_status_emergency_disk_85() -> None:
    _patch_thresholds(
        DOWNLOADS_WARN_BYTES=100,
        DOWNLOADS_CLEANUP_BYTES=200,
        DISK_CLEANUP_USAGE_PERCENT=70,
        DISK_EMERGENCY_USAGE_PERCENT=85,
    )
    assert evaluate_storage_status(5, 85.0) == "emergency_cleanup_required"


def test_emergency_keeps_recent_10_task_dirs() -> None:
    _patch_thresholds(
        DOWNLOADS_EMERGENCY_KEEP_RECENT_TASKS=10,
        DOWNLOADS_WARN_BYTES=1,
        DOWNLOADS_CLEANUP_BYTES=2,
    )
    now = 1_000_000.0
    entries = [
        TaskDirectoryEntry(
            task_id=f"task-{index:02d}",
            path=Path(f"/downloads/task-{index:02d}"),
            total_bytes=100,
            latest_mtime=now - index,
            is_active=False,
            has_in_progress_files=False,
        )
        for index in range(15)
    ]
    stats = storage_guard.StorageStats(
        downloads_bytes=sum(item.total_bytes for item in entries),
        disk_total_bytes=1000,
        disk_used_bytes=900,
        disk_free_bytes=100,
        disk_usage_percent=90.0,
        status="emergency_cleanup_required",
        task_directories=entries,
    )
    plan = plan_emergency_cleanup(stats)
    assert len(plan.keep_task_ids) == 10
    assert len(plan.delete_paths) == 5
    assert plan.delete_paths[0].name == "task-10"


def test_normal_cleanup_skips_recent_6h() -> None:
    _patch_thresholds(
        DOWNLOADS_CLEANUP_MIN_AGE_SECONDS=6 * 3600,
        DOWNLOADS_CLEANUP_BYTES=1,
        DISK_CLEANUP_USAGE_PERCENT=70,
        DISK_EMERGENCY_USAGE_PERCENT=85,
    )
    now = 10_000.0
    old = TaskDirectoryEntry(
        task_id="old",
        path=Path("/downloads/old"),
        total_bytes=500,
        latest_mtime=now - 7 * 3600,
        is_active=False,
        has_in_progress_files=False,
    )
    recent = TaskDirectoryEntry(
        task_id="recent",
        path=Path("/downloads/recent"),
        total_bytes=500,
        latest_mtime=now - 3600,
        is_active=False,
        has_in_progress_files=False,
    )
    stats = storage_guard.StorageStats(
        downloads_bytes=1000,
        disk_total_bytes=1000,
        disk_used_bytes=800,
        disk_free_bytes=200,
        disk_usage_percent=80.0,
        status="cleanup_required",
        task_directories=[old, recent],
    )
    with mock.patch.object(storage_guard, "read_task_meta", return_value=None):
        with mock.patch.object(storage_guard, "time") as mock_time:
            mock_time.time.return_value = now
            plan = plan_normal_cleanup(stats, now=now)
    assert any(path.name == "old" for path in plan.delete_paths)
    assert all(path.name != "recent" for path in plan.delete_paths)


def test_active_task_not_deleted_in_emergency() -> None:
    _patch_thresholds(
        DOWNLOADS_EMERGENCY_KEEP_RECENT_TASKS=2,
        DOWNLOADS_WARN_BYTES=1,
        DOWNLOADS_CLEANUP_BYTES=2,
    )
    active = TaskDirectoryEntry(
        task_id="active-old",
        path=Path("/downloads/active-old"),
        total_bytes=900,
        latest_mtime=1.0,
        is_active=True,
        has_in_progress_files=False,
    )
    recent = TaskDirectoryEntry(
        task_id="recent",
        path=Path("/downloads/recent"),
        total_bytes=100,
        latest_mtime=100.0,
        is_active=False,
        has_in_progress_files=False,
    )
    stats = storage_guard.StorageStats(
        downloads_bytes=1000,
        disk_total_bytes=1000,
        disk_used_bytes=900,
        disk_free_bytes=100,
        disk_usage_percent=90.0,
        status="emergency_cleanup_required",
        task_directories=[active, recent],
    )
    plan = plan_emergency_cleanup(stats)
    assert "active-old" in plan.skipped_active
    assert active.path not in plan.delete_paths


def test_execute_cleanup_plan_dry_run_no_delete() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "task-a"
        task_dir.mkdir()
        (task_dir / "video.mp4").write_bytes(b"x" * 128)
        plan = storage_guard.CleanupPlan(
            mode="normal",
            delete_paths=[task_dir],
            keep_task_ids=[],
            estimated_release_bytes=128,
        )
        deleted, freed = execute_cleanup_plan(plan, dry_run=True)
        assert deleted == 1
        assert freed == 128
        assert task_dir.exists()


def test_large_download_allowed_after_successful_cleanup() -> None:
    _patch_thresholds(DISK_EMERGENCY_USAGE_PERCENT=85)

    def fake_collect(*, now=None):
        if fake_collect.calls == 0:
            fake_collect.calls += 1
            return storage_guard.StorageStats(
                downloads_bytes=0,
                disk_total_bytes=100,
                disk_used_bytes=90,
                disk_free_bytes=10,
                disk_usage_percent=90.0,
                status="emergency_cleanup_required",
                task_directories=[],
            )
        return storage_guard.StorageStats(
            downloads_bytes=0,
            disk_total_bytes=100,
            disk_used_bytes=70,
            disk_free_bytes=30,
            disk_usage_percent=70.0,
            status="cleanup_required",
            task_directories=[],
        )

    fake_collect.calls = 0
    with mock.patch.object(storage_guard, "collect_storage_stats", side_effect=fake_collect):
        with mock.patch.object(storage_guard, "run_emergency_cleanup", return_value=storage_guard.GuardCycleResult(
            status_before="emergency_cleanup_required",
            status_after="cleanup_required",
        )):
            check_storage_before_large_download()


def test_large_download_blocked_when_still_emergency() -> None:
    _patch_thresholds(DISK_EMERGENCY_USAGE_PERCENT=85)
    stuck = storage_guard.StorageStats(
        downloads_bytes=0,
        disk_total_bytes=100,
        disk_used_bytes=90,
        disk_free_bytes=10,
        disk_usage_percent=90.0,
        status="emergency_cleanup_required",
        task_directories=[],
    )
    with mock.patch.object(storage_guard, "collect_storage_stats", return_value=stuck):
        with mock.patch.object(storage_guard, "run_emergency_cleanup", return_value=storage_guard.GuardCycleResult(
            status_before="emergency_cleanup_required",
            status_after="emergency_cleanup_required",
        )):
            try:
                check_storage_before_large_download()
            except StoragePressureError:
                return
    raise AssertionError("expected StoragePressureError when disk still >= 85%")


def test_is_likely_large_download() -> None:
    assert is_likely_large_download("1080p")
    assert is_likely_large_download("best")
    assert not is_likely_large_download("720p")


def main() -> int:
    tests = [
        test_status_ok_under_warn,
        test_status_warn_over_10g,
        test_status_cleanup_required_downloads,
        test_status_cleanup_required_disk_70,
        test_status_emergency_disk_85,
        test_emergency_keeps_recent_10_task_dirs,
        test_normal_cleanup_skips_recent_6h,
        test_active_task_not_deleted_in_emergency,
        test_execute_cleanup_plan_dry_run_no_delete,
        test_large_download_allowed_after_successful_cleanup,
        test_large_download_blocked_when_still_emergency,
        test_is_likely_large_download,
    ]
    passed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"PASS {name}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {name}: {exc}")
    print(f"\n{passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
