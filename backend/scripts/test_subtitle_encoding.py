"""Lightweight tests for uploaded subtitle encoding detection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai_summary_service import (  # noqa: E402
    SubtitleDecodeError,
    decode_subtitle_bytes,
    looks_mojibake,
    parse_srt,
    parse_vtt,
)

SAMPLE_SRT = """1
00:00:01,000 --> 00:00:03,000
这是 UTF-8 中文字幕测试

2
00:00:04,000 --> 00:00:06,000
SaveAny 字幕编码修复
"""

SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
这是 VTT 中文字幕测试
"""


def assert_contains_chinese(text: str, label: str) -> None:
    if "中文" not in text and "字幕" not in text and "SaveAny" not in text:
        raise AssertionError(f"{label}: expected readable Chinese text, got {text[:80]!r}")


def test_utf8_srt() -> None:
    text = decode_subtitle_bytes(SAMPLE_SRT.encode("utf-8"))
    segments = parse_srt(text)
    assert segments, "utf-8 srt should parse segments"
    assert_contains_chinese(segments[0].text, "utf-8 srt")


def test_utf8_bom_srt() -> None:
    text = decode_subtitle_bytes(SAMPLE_SRT.encode("utf-8-sig"))
    segments = parse_srt(text)
    assert segments, "utf-8 bom srt should parse segments"
    assert_contains_chinese(segments[0].text, "utf-8 bom srt")


def test_gbk_srt() -> None:
    text = decode_subtitle_bytes(SAMPLE_SRT.encode("gbk"))
    segments = parse_srt(text)
    assert segments, "gbk srt should parse segments"
    assert_contains_chinese(segments[0].text, "gbk srt")
    assert not looks_mojibake(segments[0].text), "gbk srt should not look like mojibake"


def test_gb18030_srt() -> None:
    text = decode_subtitle_bytes(SAMPLE_SRT.encode("gb18030"))
    segments = parse_srt(text)
    assert segments, "gb18030 srt should parse segments"
    assert_contains_chinese(segments[0].text, "gb18030 srt")


def test_vtt_utf8() -> None:
    text = decode_subtitle_bytes(SAMPLE_VTT.encode("utf-8"))
    segments = parse_vtt(text)
    assert segments, "utf-8 vtt should parse segments"
    assert_contains_chinese(segments[0].text, "utf-8 vtt")


def test_empty_file() -> None:
    try:
        decode_subtitle_bytes(b"   \n")
        raise AssertionError("empty subtitle should raise SubtitleDecodeError")
    except SubtitleDecodeError:
        pass


def test_invalid_binary() -> None:
    data = bytes(range(256))
    try:
        decode_subtitle_bytes(data)
    except SubtitleDecodeError:
        return
    raise AssertionError("random binary should raise SubtitleDecodeError")


def main() -> int:
    tests = [
        test_utf8_srt,
        test_utf8_bom_srt,
        test_gbk_srt,
        test_gb18030_srt,
        test_vtt_utf8,
        test_empty_file,
        test_invalid_binary,
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
