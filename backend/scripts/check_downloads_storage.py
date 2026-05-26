"""Inspect downloads disk usage and optionally run storage guard cleanup.

Default: report only (no deletions).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import DOWNLOAD_DIR  # noqa: E402
from app.services.storage_guard import (  # noqa: E402
    collect_storage_stats,
    format_bytes,
    plan_emergency_cleanup,
    plan_normal_cleanup,
    run_emergency_cleanup,
    run_normal_cleanup,
)


def _print_stats(stats) -> None:
    print("=== SaveAny downloads storage check ===")
    print(f"downloads total: {format_bytes(stats.downloads_bytes)}")
    print(f"disk total:      {format_bytes(stats.disk_total_bytes)}")
    print(f"disk used:       {format_bytes(stats.disk_used_bytes)} ({stats.disk_usage_percent:.1f}%)")
    print(f"disk free:       {format_bytes(stats.disk_free_bytes)}")
    print(f"status:          {stats.status}")
    print(f"task directories: {len(stats.task_directories)}")

    if stats.top_task_dirs:
        print("\nTop task directories:")
        for entry in stats.top_task_dirs:
            active = "active" if entry.is_active else "idle"
            print(f"  - {entry.task_id}: {format_bytes(entry.total_bytes)} ({active})")

    if stats.top_files:
        print("\nTop files:")
        for entry in stats.top_files[:10]:
            try:
                rel = entry.path.relative_to(DOWNLOAD_DIR)
            except ValueError:
                rel = entry.path
            print(f"  - {rel}: {format_bytes(entry.size_bytes)}")


def _print_plan(title: str, plan) -> None:
    print(f"\n=== {title} ===")
    print(f"mode: {plan.mode}")
    print(f"keep task ids ({len(plan.keep_task_ids)}): {', '.join(plan.keep_task_ids[:15])}")
    if plan.skipped_active:
        print(f"skipped active: {', '.join(plan.skipped_active)}")
    print(f"would delete {len(plan.delete_paths)} path(s), est. release {format_bytes(plan.estimated_release_bytes)}")
    for path in plan.delete_paths[:20]:
        print(f"  - {path}")
    if len(plan.delete_paths) > 20:
        print(f"  ... and {len(plan.delete_paths) - 20} more")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check downloads storage and optionally clean up.")
    parser.add_argument("--dry-run-cleanup", action="store_true", help="Preview normal cleanup deletions only.")
    parser.add_argument("--dry-run-emergency", action="store_true", help="Preview emergency cleanup keep/delete plan.")
    parser.add_argument("--cleanup", action="store_true", help="Run normal storage cleanup (deletes files).")
    parser.add_argument("--emergency-cleanup", action="store_true", help="Run emergency cleanup (deletes files).")
    args = parser.parse_args()

    stats = collect_storage_stats()
    _print_stats(stats)

    if args.dry_run_cleanup:
        plan = plan_normal_cleanup(stats)
        _print_plan("Dry-run normal cleanup", plan)
        return 0

    if args.dry_run_emergency:
        plan = plan_emergency_cleanup(stats)
        _print_plan("Dry-run emergency cleanup", plan)
        return 0

    if args.cleanup:
        result = run_normal_cleanup(dry_run=False)
        print(f"\nNormal cleanup done: deleted={result.normal_deleted}, freed={format_bytes(result.bytes_freed)}")
        _print_stats(collect_storage_stats())
        return 0

    if args.emergency_cleanup:
        result = run_emergency_cleanup(dry_run=False)
        print(
            f"\nEmergency cleanup done: deleted={result.emergency_deleted}, freed={format_bytes(result.bytes_freed)}"
        )
        _print_stats(collect_storage_stats())
        return 0

    if stats.status not in ("ok", "warn"):
        print("\nNote: thresholds exceeded. Preview with --dry-run-cleanup or --dry-run-emergency.")
        print("Real cleanup requires --cleanup or --emergency-cleanup explicitly.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
