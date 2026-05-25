#!/usr/bin/env python3
"""Manual tests for download error humanization."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ytdlp_service import (  # noqa: E402
    humanize_download_error,
    is_source_connection_interrupted_error,
    source_connection_interrupted_message,
)


def check_interrupted(name: str, raw: str) -> None:
    assert is_source_connection_interrupted_error(raw), f"{name}: should match interrupted"
    print(f"PASS {name}")


def check_humanize(name: str, raw: str, expected: str) -> None:
    got = humanize_download_error(raw)
    assert got == expected, f"{name}: expected {expected!r}, got {got!r}"
    print(f"PASS {name}")


def main() -> int:
    friendly = source_connection_interrupted_message()

    check_interrupted(
        "incomplete_read",
        "('Connection broken: IncompleteRead(97254010 bytes read, 436261992 more expected)', IncompleteRead(...))",
    )
    check_interrupted("connection_broken", "Connection broken")
    check_interrupted("remote_closed", "Remote end closed connection without response")
    check_interrupted("read_timeout", "Read timed out")
    check_interrupted("reset_by_peer", "Connection reset by peer")

    check_humanize(
        "douyin_retry_wrapper",
        "抖音下载多次重试仍失败：('Connection broken: IncompleteRead(97254010 bytes read, 436261992 more expected)', IncompleteRead(...))",
        friendly,
    )
    check_humanize(
        "plain_incomplete_read",
        "Connection broken: IncompleteRead(97254010 bytes read, 436261992 more expected)",
        friendly,
    )
    check_humanize(
        "read_timeout",
        "HTTPSConnectionPool(host='example.com', port=443): Read timed out.",
        friendly,
    )

    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
