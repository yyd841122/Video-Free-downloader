from __future__ import annotations

import tempfile
import os
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.core.config import DEFAULT_FORMAT, DOWNLOAD_DIR
from app.models.schemas import FormatInfo, VideoInfoResponse
from app.services.direct_link_store import DirectLink, direct_link_store
from app.services.task_store import task_store


class YtdlpWarningLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def debug(self, message: str) -> None:
        return None

    def info(self, message: str) -> None:
        return None

    def warning(self, message: str) -> None:
        if message:
            self.warnings.append(message)

    def error(self, message: str) -> None:
        if message:
            self.warnings.append(message)


def build_js_runtime_options() -> dict[str, Any]:
    runtime = os.getenv("YTDLP_JS_RUNTIME", "node").strip().lower()
    if not runtime or runtime == "none":
        return {"js_runtimes": {}}

    supported = {"node", "deno", "bun", "quickjs"}
    if runtime not in supported:
        runtime = "node"

    configured_path = os.getenv("YTDLP_JS_RUNTIME_PATH", "").strip()
    executable_path = configured_path or shutil.which(runtime)
    config = {"path": executable_path} if executable_path else {}
    return {"js_runtimes": {runtime: config}}


def base_ytdlp_options() -> dict[str, Any]:
    return {
        **build_js_runtime_options(),
        "remote_components": ["ejs:github"],
        "socket_timeout": 120,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "http_chunk_size": 10 * 1024 * 1024,
    }


def map_format(format_choice: str) -> str:
    mapping = {
        "best": "bestvideo+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "audio": "bestaudio/best",
    }
    return mapping.get(format_choice, format_choice or DEFAULT_FORMAT)


def create_cookie_file(cookies: str | None, url: str) -> Path | None:
    text = (cookies or "").strip()
    if not text:
        return None

    fd, raw_path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    cookie_path = Path(raw_path)
    if "# Netscape HTTP Cookie File" in text or "\t" in text:
        cookie_path.write_text(text, encoding="utf-8")
        return cookie_path

    hostname = urlparse(url).hostname or "bilibili.com"
    domain = ".bilibili.com" if "bilibili" in hostname else f".{hostname}"
    lines = ["# Netscape HTTP Cookie File"]
    for part in text.split(";"):
        if "=" not in part:
            continue
        name, value = part.strip().split("=", 1)
        if not name:
            continue
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}")
    cookie_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cookie_path


def normalize_browser_cookies(value: str | None) -> tuple[str, ...] | None:
    browser = (value or "").strip().lower()
    if not browser or browser == "none":
        return None
    allowed = {"chrome", "edge", "firefox", "brave", "chromium", "vivaldi", "opera"}
    if browser not in allowed:
        raise ValueError(f"暂不支持读取 {browser} 浏览器登录态")
    return (browser,)


def human_speed(bytes_per_second: float | int | None) -> str | None:
    if not bytes_per_second:
        return None
    units = ["B/s", "KiB/s", "MiB/s", "GiB/s"]
    value = float(bytes_per_second)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return None


def normalize_duration(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, round(float(value)))
    except (TypeError, ValueError):
        return None


def build_proxy_url(url: str | None, info: dict[str, Any]) -> str | None:
    if not url:
        return None
    headers = {}
    for key, value in (info.get("http_headers") or {}).items():
        if isinstance(value, str):
            headers[key] = value
    if info.get("webpage_url") and "Referer" not in headers:
        headers["Referer"] = str(info["webpage_url"])
    token = direct_link_store.create(DirectLink(url=url, headers=headers, title=info.get("title")))
    return f"/api/proxy/{token}"


def normalize_formats(info: dict[str, Any]) -> list[FormatInfo]:
    formats: list[FormatInfo] = []
    for item in info.get("formats") or []:
        format_id = str(item.get("format_id") or "")
        if not format_id:
            continue
        height = item.get("height")
        width = item.get("width")
        resolution = item.get("resolution")
        if not resolution and height:
            resolution = f"{height}p"
        elif not resolution and width:
            resolution = f"{width}w"
        formats.append(
            FormatInfo(
                format_id=format_id,
                ext=item.get("ext"),
                resolution=resolution,
                filesize=item.get("filesize"),
                filesize_approx=item.get("filesize_approx"),
                fps=item.get("fps"),
                vcodec=item.get("vcodec"),
                acodec=item.get("acodec"),
                note=item.get("format_note") or item.get("format"),
            )
        )
    has_video_format = any(
        (item.vcodec and item.vcodec != "none") or (item.ext or "").lower() in {"mp4", "webm", "mkv", "mov", "flv"}
        for item in formats
    )
    if not has_video_format and info.get("url"):
        height = info.get("height")
        width = info.get("width")
        resolution = info.get("resolution")
        if not resolution and width and height:
            resolution = f"{width}x{height}"
        elif not resolution and height:
            resolution = f"{height}p"
        formats.append(
            FormatInfo(
                format_id=str(info.get("format_id") or "best"),
                ext=info.get("ext") or "mp4",
                resolution=resolution or "original",
                filesize=info.get("filesize"),
                filesize_approx=info.get("filesize_approx"),
                fps=info.get("fps"),
                vcodec=info.get("vcodec") or "unknown",
                acodec=info.get("acodec") or "unknown",
                note=info.get("format_note") or "original",
            )
        )
    return formats[:80]


def get_max_video_height(info: dict[str, Any]) -> int:
    max_height = 0
    for item in info.get("formats") or []:
        vcodec = item.get("vcodec")
        if not vcodec or vcodec == "none":
            continue
        height = item.get("height")
        if isinstance(height, int | float):
            max_height = max(max_height, int(height))
            continue
        resolution = str(item.get("resolution") or "")
        if "x" in resolution:
            try:
                max_height = max(max_height, int(resolution.rsplit("x", 1)[-1]))
            except ValueError:
                pass
    return max_height


def has_downloadable_video_formats(info: dict[str, Any]) -> bool:
    if info.get("url"):
        return True
    for item in info.get("formats") or []:
        if not item.get("format_id"):
            continue
        vcodec = item.get("vcodec")
        if vcodec and vcodec != "none":
            return True
    return False


def normalize_user_warning(message: str, extractor: str, has_formats: bool) -> str | None:
    text = (message or "").strip()
    lower = text.lower()
    if not text:
        return None

    if "impersonation" in lower and "no impersonate target" in lower:
        if has_formats:
            return None
        return "平台兼容性提示：当前环境未启用浏览器指纹模拟。如果该平台解析失败，请补充 yt-dlp impersonation 依赖后重试。"

    if "remote component challenge solver" in lower and "skipped" in lower:
        if has_formats:
            return None
        return "平台兼容性提示：当前环境缺少挑战脚本组件，可能导致部分平台解析失败。"

    if "n challenge solving failed" in lower:
        if has_formats:
            return "平台兼容性提示：已解析出可下载格式，但部分清晰度可能缺失。"
        return "平台兼容性提示：平台验证处理失败，请检查 JavaScript runtime 和 yt-dlp EJS 配置。"

    if "no supported javascript runtime" in lower:
        return "YouTube 需要 JavaScript runtime 才能稳定解析，请检查后端 yt-dlp JS runtime 配置。"

    if "deprecated" in lower and ("javascript" in lower or "js runtime" in lower):
        return None if has_formats else "平台兼容性提示：当前解析环境配置较旧，可能影响后续下载稳定性。"

    if "if you encounter errors" in lower and "install" in lower and has_formats:
        return None

    return text


def infer_access_warnings(info: dict[str, Any], warnings: list[str] | None = None) -> list[str]:
    extractor = str(info.get("extractor_key") or info.get("extractor") or "").lower()
    has_formats = has_downloadable_video_formats(info)
    merged = [
        normalized
        for warning in (warnings or [])
        if (normalized := normalize_user_warning(warning, extractor, has_formats))
    ]
    max_height = get_max_video_height(info)
    if "bilibili" in extractor and 0 < max_height < 720:
        merged.append(
            "当前未解析到 720P/1080P 等高清格式。Bilibili 的高清格式通常需要登录态、会员权限或有效 cookies；未提供这些信息时，yt-dlp 只能拿到公开视频可访问的低清格式。"
        )
    return list(dict.fromkeys(merged))


def build_info_response(info: dict[str, Any], include_raw: bool = False, warnings: list[str] | None = None) -> VideoInfoResponse:
    raw = None
    if include_raw:
        raw = {
            "id": info.get("id"),
            "extractor_key": info.get("extractor_key"),
            "webpage_url": info.get("webpage_url"),
        }
    return VideoInfoResponse(
        title=info.get("title"),
        webpage_url=info.get("webpage_url"),
        thumbnail=info.get("thumbnail"),
        thumbnail_proxy_url=build_proxy_url(info.get("thumbnail"), info),
        duration=normalize_duration(info.get("duration")),
        uploader=info.get("uploader"),
        extractor=info.get("extractor_key") or info.get("extractor"),
        formats=normalize_formats(info),
        warnings=infer_access_warnings(info, warnings),
        raw=raw,
    )


def extract_info(url: str, cookies: str | None = None, browser_cookies: str | None = None) -> VideoInfoResponse:
    logger = YtdlpWarningLogger()
    cookie_file = create_cookie_file(cookies, url)
    browser_cookie_config = normalize_browser_cookies(browser_cookies)
    options = {
        **base_ytdlp_options(),
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        "logger": logger,
    }
    if cookie_file:
        options["cookiefile"] = str(cookie_file)
    elif browser_cookie_config:
        options["cookiesfrombrowser"] = browser_cookie_config
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        return build_info_response(info or {}, include_raw=True, warnings=logger.warnings)
    except DownloadError as exc:
        if browser_cookie_config:
            fallback_options = dict(options)
            fallback_options.pop("cookiesfrombrowser", None)
            fallback_logger = YtdlpWarningLogger()
            fallback_options["logger"] = fallback_logger
            with YoutubeDL(fallback_options) as ydl:
                info = ydl.extract_info(url, download=False)
            warning = (
                f"自动读取 {browser_cookie_config[0]} 登录态失败：{exc}。"
                "如果需要 720P/1080P，请关闭对应浏览器后重新解析，或改用其他已登录浏览器。"
            )
            return build_info_response(info or {}, include_raw=True, warnings=[warning, *fallback_logger.warnings])
        raise
    finally:
        if cookie_file:
            cookie_file.unlink(missing_ok=True)


def download_video_task(
    task_id: str,
    url: str,
    format_choice: str,
    with_subtitle: bool,
    cookies: str | None = None,
    browser_cookies: str | None = None,
) -> None:
    task_dir = DOWNLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(task_dir / "%(title).160B [%(id)s].%(ext)s")
    cookie_file = create_cookie_file(cookies, url)
    browser_cookie_config = normalize_browser_cookies(browser_cookies)

    def progress_hook(data: dict[str, Any]) -> None:
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes") or 0
            progress = 0.0
            if total:
                progress = min(99.0, max(0.0, downloaded * 100 / total))
            task_store.update(
                task_id,
                status="downloading",
                progress=round(progress, 1),
                speed=human_speed(data.get("speed")),
                eta=data.get("eta"),
                filename=Path(data.get("filename", "")).name or None,
            )
        elif status == "finished":
            filename = data.get("filename")
            task_store.update(
                task_id,
                status="processing",
                progress=99,
                filename=Path(filename).name if filename else None,
            )

    options: dict[str, Any] = {
        **base_ytdlp_options(),
        "format": map_format(format_choice),
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "merge_output_format": "mp4",
    }
    if with_subtitle:
        options.update(
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hans", "zh-CN", "en", "all"],
            }
        )
    if cookie_file:
        options["cookiefile"] = str(cookie_file)
    elif browser_cookie_config:
        options["cookiesfrombrowser"] = browser_cookie_config

    task_store.update(task_id, status="starting")
    try:
        with YoutubeDL(options) as ydl:
            ydl.download([url])
        candidates = [path for path in task_dir.iterdir() if path.is_file() and not path.name.endswith(".part")]
        if not candidates:
            raise RuntimeError("下载已结束，但没有找到输出文件。")
        media_candidates = [path for path in candidates if path.suffix.lower() in {".mp4", ".webm", ".mkv", ".m4a", ".mp3"}]
        final_file = max(media_candidates or candidates, key=lambda path: path.stat().st_size)
        task_store.update(
            task_id,
            status="completed",
            progress=100,
            filename=final_file.name,
            file_path=final_file,
            speed=None,
            eta=None,
            error=None,
        )
    except Exception as exc:
        task_store.update(task_id, status="failed", error=str(exc), speed=None, eta=None)
    finally:
        if cookie_file:
            cookie_file.unlink(missing_ok=True)


def extract_direct_link(
    url: str,
    format_choice: str,
    cookies: str | None = None,
    browser_cookies: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    cookie_file = create_cookie_file(cookies, url)
    browser_cookie_config = normalize_browser_cookies(browser_cookies)
    options = {
        **base_ytdlp_options(),
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "format": map_format(format_choice),
    }
    if cookie_file:
        options["cookiefile"] = str(cookie_file)
    elif browser_cookie_config:
        options["cookiesfrombrowser"] = browser_cookie_config
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        selected_url = info.get("url")
        requested = info.get("requested_downloads") or []
        if not selected_url and requested:
            selected_url = requested[0].get("url")
        if not selected_url:
            formats = info.get("formats") or []
            playable = [item for item in formats if item.get("url")]
            if playable:
                selected_url = playable[-1].get("url")
        if not selected_url:
            raise RuntimeError("未能解析出可直接下载的媒体链接，请尝试服务端下载模式。")
        headers = {}
        http_headers = info.get("http_headers") or {}
        for key, value in http_headers.items():
            if isinstance(value, str):
                headers[key] = value
        token = direct_link_store.create(DirectLink(url=selected_url, headers=headers, title=info.get("title")))
        return info, token, selected_url
    finally:
        if cookie_file:
            cookie_file.unlink(missing_ok=True)


def safe_file_response_path(task_id: str) -> Path | None:
    task = task_store.get(task_id)
    if not task or not task.file_path:
        return None
    try:
        resolved = task.file_path.resolve()
        resolved.relative_to(DOWNLOAD_DIR.resolve())
    except ValueError:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None
    return resolved
