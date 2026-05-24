"""Lightweight checks for _guess_height_from_format resolution parsing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.video import _guess_height_from_format


CASES: list[tuple[str, int]] = [
    ("720p", 720),
    ("480p", 480),
    ("1080p", 1080),
    ("best[height<=720]", 720),
    ("bestvideo[height<=720]+bestaudio/best[height<=720]", 720),
    ("1280x720", 720),
    ("1920x1080", 1080),
    ("720", 720),
    ("3006", 0),
    ("30280", 0),
    ("3006+bestaudio/3006", 0),
    ("137+140", 0),
    ("best", 0),
]


def main() -> int:
    failed = 0
    for format_str, expected in CASES:
        actual = _guess_height_from_format(format_str)
        ok = actual == expected
        status = "OK" if ok else "FAIL"
        print(f"{status}  {format_str!r} -> {actual} (expected {expected})")
        if not ok:
            failed += 1

    if failed:
        print(f"\n{failed} case(s) failed")
        return 1

    print(f"\nAll {len(CASES)} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
