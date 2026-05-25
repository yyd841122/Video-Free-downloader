#!/usr/bin/env python3
"""Manual tests for app.utils.url_normalize."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.url_normalize import UrlNormalizeError, normalize_video_url  # noqa: E402


def check(name: str, raw: str, expected: str) -> None:
    got = normalize_video_url(raw)
    assert got == expected, f"{name}: expected {expected!r}, got {got!r}"
    print(f"PASS {name}")


def check_error(name: str, raw: str) -> None:
    try:
        normalize_video_url(raw)
    except UrlNormalizeError:
        print(f"PASS {name}")
        return
    raise AssertionError(f"{name}: expected UrlNormalizeError")


def main() -> int:
    bili_in = (
        "https://www.bilibili.com/video/BV1gCLq6YEW4/"
        "?spm_id_from=333.1007.tianma.1-2-2.click&vd_source=b2b99f18f31787a9daec3c7210dc1bf3"
    )
    check(
        "bilibili_tracking",
        bili_in,
        "https://www.bilibili.com/video/BV1gCLq6YEW4/",
    )

    douyin_in = (
        "7.41 t@r.Eu :0pm fBg:/ 12/25 血法师出场！满屏残血兵，竟敢冲基地？"
        "TH000激战Moon # 怀旧游戏 # 经典游戏 # 电子竞技 # 魔兽争霸3  "
        "https://v.douyin.com/gq_pGPyTAyw/ 复制此链接，打开Dou音搜索，直接观看视频！"
    )
    check("douyin_share_text", douyin_in, "https://v.douyin.com/gq_pGPyTAyw/")

    check(
        "douyin_jingxuan_modal_id",
        "https://www.douyin.com/jingxuan?modal_id=7643509713572777266",
        "https://www.douyin.com/video/7643509713572777266",
    )

    check(
        "douyin_jingxuan_modal_id_extra_params",
        "https://www.douyin.com/jingxuan?modal_id=7643509713572777266&previous_page=app_code_link",
        "https://www.douyin.com/video/7643509713572777266",
    )

    check(
        "douyin_short_link",
        "https://v.douyin.com/RkYdrHyJWek/",
        "https://v.douyin.com/RkYdrHyJWek/",
    )

    check(
        "douyin_video_direct",
        "https://www.douyin.com/video/7643509713572777266",
        "https://www.douyin.com/video/7643509713572777266",
    )

    check(
        "douyin_non_numeric_modal_id",
        "https://www.douyin.com/jingxuan?modal_id=abc123",
        "https://www.douyin.com/jingxuan/",
    )

    check(
        "x_query",
        "https://x.com/realDonaldTrump/status/2057968277062582378?s=20",
        "https://x.com/realDonaldTrump/status/2057968277062582378",
    )

    check(
        "twitter_query",
        "https://twitter.com/user/status/1234567890?t=abc&s=19",
        "https://twitter.com/user/status/1234567890",
    )

    check(
        "mp4_query_preserved",
        "https://example.com/video.mp4?token=abc123",
        "https://example.com/video.mp4?token=abc123",
    )

    check_error("empty", "")
    check_error("no_url", "just some text without a link")

    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
