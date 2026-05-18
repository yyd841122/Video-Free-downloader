from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any

import requests
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MAX_TOKENS,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
    DOWNLOAD_DIR,
)
from app.models.schemas import AiChatMessage, AiChatResponse, AiSummaryResult, TranscriptSegment
from app.services.ai_task_store import ai_summary_task_store
from app.services.ytdlp_service import (
    apply_url_headers,
    base_ytdlp_options,
    create_cookie_file,
    normalize_browser_cookies,
)


SUBTITLE_EXTENSIONS = {".srt", ".vtt"}
PREFERRED_LANGUAGE_MARKERS = (
    ".zh-Hans.",
    ".zh-CN.",
    ".zh.",
    ".zh-Hant.",
    ".zh-TW.",
    ".cmn-Hans.",
    ".en.",
)
PREFERRED_SUBTITLE_LANGUAGES = (
    "zh-Hans",
    "zh-CN",
    "zh",
    "zh-Hant",
    "zh-TW",
    "cmn-Hans",
    "cmn",
    "en",
    "en-US",
    "en-GB",
)
MAX_TRANSCRIPT_CHARS = 45_000
MAX_CHAT_CONTEXT_CHARS = 32_000


class NoTranscriptError(RuntimeError):
    pass


def seconds_to_timestamp(value: float | None) -> str:
    if value is None:
        return "00:00"
    total = max(0, int(value))
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def timestamp_to_seconds(value: str) -> float:
    text = value.strip().replace(",", ".")
    parts = text.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Invalid timestamp: {value}")


def clean_subtitle_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\{\\.*?\}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_srt(content: str) -> list[TranscriptSegment]:
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n"))
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            continue
        timing = lines[timing_index]
        text = clean_subtitle_text(" ".join(lines[timing_index + 1 :]))
        if not text:
            continue
        start_text, end_text = [part.strip().split(" ", 1)[0] for part in timing.split("-->", 1)]
        try:
            start = timestamp_to_seconds(start_text)
            end = timestamp_to_seconds(end_text)
        except ValueError:
            continue
        segments.append(TranscriptSegment(start=start, end=end, text=text))
    return merge_duplicate_segments(segments)


def parse_vtt(content: str) -> list[TranscriptSegment]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", normalized)
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0].upper().startswith("WEBVTT"):
            continue
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            continue
        timing = lines[timing_index]
        text_lines = [
            line
            for line in lines[timing_index + 1 :]
            if not line.startswith(("NOTE", "STYLE", "REGION"))
        ]
        text = clean_subtitle_text(" ".join(text_lines))
        if not text:
            continue
        start_text, end_text = [part.strip().split(" ", 1)[0] for part in timing.split("-->", 1)]
        try:
            start = timestamp_to_seconds(start_text)
            end = timestamp_to_seconds(end_text)
        except ValueError:
            continue
        segments.append(TranscriptSegment(start=start, end=end, text=text))
    return merge_duplicate_segments(segments)


def merge_duplicate_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    merged: list[TranscriptSegment] = []
    previous_key = ""
    for segment in segments:
        key = f"{round(segment.start, 1)}:{segment.text}"
        if key == previous_key:
            continue
        previous_key = key
        merged.append(segment)
    return merged


def parse_subtitle_file(path: Path) -> list[TranscriptSegment]:
    content = path.read_text(encoding="utf-8-sig", errors="ignore")
    if path.suffix.lower() == ".srt":
        return parse_srt(content)
    return parse_vtt(content)


def choose_subtitle_file(task_dir: Path) -> Path | None:
    candidates = [path for path in task_dir.iterdir() if path.suffix.lower() in SUBTITLE_EXTENSIONS]
    if not candidates:
        return None
    for marker in PREFERRED_LANGUAGE_MARKERS:
        match = next((path for path in candidates if marker.lower() in path.name.lower()), None)
        if match:
            return match
    return max(candidates, key=lambda path: path.stat().st_size)


def infer_subtitle_language(path: Path | None) -> str | None:
    if not path:
        return None
    name = path.name
    for marker in PREFERRED_LANGUAGE_MARKERS:
        if marker.lower() in name.lower():
            return marker.strip(".")
    parts = name.split(".")
    if len(parts) >= 3:
        return parts[-2]
    return None


def subtitle_language_rank(language: str) -> tuple[int, str]:
    normalized = language.lower()
    for index, preferred in enumerate(PREFERRED_SUBTITLE_LANGUAGES):
        preferred_normalized = preferred.lower()
        if normalized == preferred_normalized:
            return index, language
        if normalized.startswith(f"{preferred_normalized}-"):
            return index + 100, language
    return len(PREFERRED_SUBTITLE_LANGUAGES) + 500, language


def collect_subtitle_candidates(info: dict[str, Any]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    discovered: list[tuple[str, str]] = []
    for source, subtitles_key in (("manual", "subtitles"), ("automatic", "automatic_captions")):
        subtitles = info.get(subtitles_key) or {}
        if not isinstance(subtitles, dict):
            continue
        for language, entries in subtitles.items():
            if not entries:
                continue
            rank, _ = subtitle_language_rank(language)
            if rank >= len(PREFERRED_SUBTITLE_LANGUAGES) + 500:
                continue
            candidate = (source, language)
            if candidate not in seen:
                discovered.append(candidate)
                seen.add(candidate)
    return sorted(
        discovered,
        key=lambda item: (
            subtitle_language_rank(item[1]),
            0 if item[0] == "manual" else 1,
        ),
    )


def cleanup_subtitle_files(task_dir: Path) -> None:
    for path in task_dir.iterdir():
        if path.suffix.lower() in SUBTITLE_EXTENSIONS or path.name.endswith(".part"):
            path.unlink(missing_ok=True)


def build_platform_subtitle_options(
    url: str,
    task_dir: Path,
    output_template: str,
    cookies: str | None,
    browser_cookies: str | None,
) -> tuple[dict[str, Any], Path | None]:
    cookie_file = create_cookie_file(cookies, url)
    browser_cookie_config = normalize_browser_cookies(browser_cookies)
    options: dict[str, Any] = {
        **base_ytdlp_options(),
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "outtmpl": output_template,
    }
    apply_url_headers(options, url)
    if cookie_file:
        options["cookiefile"] = str(cookie_file)
    elif browser_cookie_config:
        options["cookiesfrombrowser"] = browser_cookie_config
    return options, cookie_file


def download_subtitle_candidate(
    url: str,
    task_dir: Path,
    base_options: dict[str, Any],
    source: str,
    language: str,
) -> tuple[Path, list[TranscriptSegment]]:
    cleanup_subtitle_files(task_dir)
    options = {
        **base_options,
        "writesubtitles": source == "manual",
        "writeautomaticsub": source == "automatic",
        "subtitleslangs": [language],
        "subtitlesformat": "srt/vtt/best",
    }
    with YoutubeDL(options) as ydl:
        ydl.download([url])

    subtitle_file = choose_subtitle_file(task_dir)
    if not subtitle_file:
        raise NoTranscriptError(f"未能下载 {language} 字幕。")
    segments = parse_subtitle_file(subtitle_file)
    if not segments:
        raise NoTranscriptError(f"已下载 {language} 字幕，但没有解析出有效字幕文本。")
    return subtitle_file, segments


def extract_platform_transcript(
    url: str,
    task_dir: Path,
    cookies: str | None = None,
    browser_cookies: str | None = None,
) -> tuple[dict[str, Any], Path, list[TranscriptSegment], str | None]:
    output_template = str(task_dir / "%(title).160B [%(id)s].%(ext)s")
    options, cookie_file = build_platform_subtitle_options(url, task_dir, output_template, cookies, browser_cookies)

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        candidates = collect_subtitle_candidates(info)
        if not candidates:
            raise NoTranscriptError("当前视频没有可提取的平台字幕或自动字幕。")

        errors: list[str] = []
        for source, language in candidates:
            try:
                subtitle_file, segments = download_subtitle_candidate(url, task_dir, options, source, language)
                return info, subtitle_file, segments, infer_subtitle_language(subtitle_file) or language
            except (DownloadError, NoTranscriptError) as exc:
                errors.append(f"{language}: {exc}")
                continue
        raise RuntimeError("已发现字幕轨道，但下载字幕失败：" + "；".join(errors[:3]))
    except DownloadError as exc:
        raise RuntimeError(str(exc)) from exc
    finally:
        if cookie_file:
            cookie_file.unlink(missing_ok=True)


def build_transcript_text(segments: list[TranscriptSegment]) -> tuple[str, bool]:
    lines: list[str] = []
    total = 0
    truncated = False
    for segment in segments:
        line = f"[{seconds_to_timestamp(segment.start)}] {segment.text}"
        if total + len(line) + 1 > MAX_TRANSCRIPT_CHARS:
            truncated = True
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines), truncated


def build_chat_context(segments: list[TranscriptSegment]) -> str:
    lines: list[str] = []
    total = 0
    for segment in segments:
        line = f"[{seconds_to_timestamp(segment.start)}] {segment.text}"
        if total + len(line) + 1 > MAX_CHAT_CONTEXT_CHARS:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_summary_payload(parsed: dict[str, Any], title: str | None, transcript_text: str) -> dict[str, Any]:
    if not parsed.get("title"):
        parsed["title"] = title
    if not parsed.get("one_sentence"):
        first_line = next((line for line in transcript_text.splitlines() if line.strip()), "")
        parsed["one_sentence"] = clean_subtitle_text(first_line) or "已根据字幕生成视频学习摘要。"
    if not parsed.get("outline"):
        parsed["outline"] = [parsed["one_sentence"]]
    if not parsed.get("key_points"):
        parsed["key_points"] = [parsed["one_sentence"]]
    if not parsed.get("keywords"):
        parsed["keywords"] = []
    if not parsed.get("learning_suggestions"):
        parsed["learning_suggestions"] = ["先浏览摘要和时间轴，再按需回看对应片段。"]
    if not parsed.get("timeline"):
        first_time = re.search(r"\[(\d{2}:\d{2}(?::\d{2})?)\]", transcript_text)
        parsed["timeline"] = [
            {
                "time": first_time.group(1) if first_time else "00:00",
                "title": "主要内容",
                "summary": parsed["one_sentence"],
            }
        ]
    if parsed.get("audience") is None:
        parsed["audience"] = "希望快速了解视频内容的学习者"
    return parsed


def request_deepseek_chat(messages: list[dict[str, str]], max_tokens: int, response_format: dict[str, str] | None = None) -> str:
    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    response = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=DEEPSEEK_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Deepseek 请求失败：HTTP {response.status_code} {detail}")
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Deepseek 未返回有效内容。")
    return content


def repair_deepseek_summary_json(raw_content: str) -> dict[str, Any]:
    repair_messages = [
        {
            "role": "system",
            "content": (
                "你是 JSON 修复器。用户会给你一段不合法的 JSON。"
                "请只修复语法错误，保留原意，返回严格 JSON 对象，不要输出 Markdown。"
            ),
        },
        {
            "role": "user",
            "content": f"""
请把下面内容修复成严格 JSON 对象。字段必须只包含：
title, one_sentence, outline, key_points, timeline, keywords, audience, learning_suggestions。
timeline 必须是数组，元素必须包含 time、title、summary。

待修复内容：
{raw_content}
""".strip(),
        },
    ]
    repaired = request_deepseek_chat(
        repair_messages,
        max_tokens=DEEPSEEK_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    return extract_json_object(repaired)


def fallback_summary_from_transcript(title: str | None, transcript_text: str) -> AiSummaryResult:
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    cleaned_lines = [clean_subtitle_text(re.sub(r"^\[[^\]]+\]\s*", "", line)) for line in lines]
    unique_lines = list(dict.fromkeys(line for line in cleaned_lines if line))
    one_sentence = unique_lines[0] if unique_lines else "已根据字幕生成视频学习摘要。"
    outline = unique_lines[:6] or [one_sentence]
    key_points = unique_lines[:5] or [one_sentence]
    timeline = []
    for line in lines[:6]:
        match = re.match(r"\[(\d{2}:\d{2}(?::\d{2})?)\]\s*(.+)", line)
        if not match:
            continue
        text = clean_subtitle_text(match.group(2))
        if text:
            timeline.append({"time": match.group(1), "title": text[:18], "summary": text})
    if not timeline:
        timeline = [{"time": "00:00", "title": "主要内容", "summary": one_sentence}]
    return AiSummaryResult.model_validate(
        {
            "title": title,
            "one_sentence": one_sentence,
            "outline": outline,
            "key_points": key_points,
            "timeline": timeline,
            "keywords": [],
            "audience": "希望快速了解视频内容的学习者",
            "learning_suggestions": ["先浏览摘要和时间轴，再按需回看对应片段。"],
        }
    )


def call_deepseek_summary(
    title: str | None,
    webpage_url: str | None,
    transcript_text: str,
    truncated: bool,
) -> AiSummaryResult:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Deepseek API Key 未配置。请在 .env 中设置 DEEPSEEK_API_KEY 后重启后端。")

    system_prompt = (
        "你是专业的视频学习助理。请阅读用户提供的字幕内容，生成可用于快速学习的视频总结。"
        "只能根据字幕内容总结，不要编造字幕外的信息。必须输出严格 JSON，不要输出 Markdown 或解释文字。"
        "所有字段都必须尽量填写，数组字段至少给出 3 项，除非字幕内容确实不足。"
    )
    user_prompt = f"""
视频标题：{title or "未知"}
视频链接：{webpage_url or ""}
字幕是否被截断：{"是" if truncated else "否"}

请返回如下 JSON 对象，字段名必须完全一致：
{{
  "title": "视频标题",
  "one_sentence": "用一句中文概括视频核心内容，不能为空",
  "outline": ["按视频讲解顺序列出章节大纲"],
  "key_points": ["提炼最重要的知识点或结论"],
  "timeline": [
    {{"time": "00:00", "title": "时间点主题", "summary": "该时间点讲了什么"}}
  ],
  "keywords": ["关键词"],
  "audience": "适合观看的人群",
  "learning_suggestions": ["如何高效学习或复习这个视频"]
}}

字幕内容：
{transcript_text}
""".strip()
    content = request_deepseek_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=DEEPSEEK_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    try:
        parsed = extract_json_object(content)
    except json.JSONDecodeError:
        try:
            parsed = repair_deepseek_summary_json(content)
        except Exception:
            return fallback_summary_from_transcript(title, transcript_text)
    try:
        parsed = normalize_summary_payload(parsed, title, transcript_text)
        return AiSummaryResult.model_validate(parsed)
    except Exception:
        return fallback_summary_from_transcript(title, transcript_text)


def call_deepseek_video_chat(
    *,
    title: str | None,
    summary: AiSummaryResult | None,
    segments: list[TranscriptSegment],
    question: str,
    history: list[AiChatMessage],
) -> AiChatResponse:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Deepseek API Key 未配置。请在 .env 中设置 DEEPSEEK_API_KEY 后重启后端。")
    if not segments:
        raise RuntimeError("当前任务没有可用于问答的字幕/转录内容。")

    summary_text = summary.model_dump_json() if summary else "{}"
    transcript_text = build_chat_context(segments)
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是视频内容问答助手。只能根据提供的视频摘要和字幕回答。"
                "如果问题超出视频内容，请明确说明字幕中没有相关信息。"
                "回答要简洁、中文优先；如果引用到具体片段，请带上时间戳。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"视频标题：{title or '未知'}\n\n"
                f"结构化摘要：\n{summary_text}\n\n"
                f"字幕/转录：\n{transcript_text}"
            ),
        },
    ]
    for item in history[-6:]:
        if item.role in {"user", "assistant"} and item.content.strip():
            messages.append({"role": item.role, "content": item.content.strip()})
    messages.append({"role": "user", "content": question.strip()})

    response = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": min(DEEPSEEK_MAX_TOKENS, 2048),
        },
        timeout=DEEPSEEK_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Deepseek 请求失败：HTTP {response.status_code} {detail}")
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Deepseek 未返回有效回答。")
    references = sorted(set(re.findall(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", content)))
    return AiChatResponse(answer=content.strip(), references=references)


def write_summary_artifacts(
    task_dir: Path,
    segments: list[TranscriptSegment],
    summary: AiSummaryResult,
    subtitle_file: Path,
) -> None:
    transcript_payload = {
        "source_file": subtitle_file.name,
        "segments": [segment.model_dump() for segment in segments],
    }
    (task_dir / "transcript.json").write_text(
        json.dumps(transcript_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (task_dir / "summary.json").write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )


def generate_ai_summary_task(
    task_id: str,
    url: str,
    cookies: str | None = None,
    browser_cookies: str | None = None,
) -> None:
    task_dir = DOWNLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    ai_summary_task_store.update(
        task_id,
        status="extracting",
        progress=12,
        message="正在提取平台字幕",
        task_dir=task_dir,
    )
    try:
        info, subtitle_file, segments, language = extract_platform_transcript(url, task_dir, cookies, browser_cookies)
        transcript_text, truncated = build_transcript_text(segments)
        ai_summary_task_store.update(
            task_id,
            status="summarizing",
            progress=62,
            message="已提取字幕，正在调用 Deepseek 生成总结",
            title=info.get("title"),
            webpage_url=info.get("webpage_url") or url,
            transcript_language=language,
            transcript_segments=segments,
        )
        summary = call_deepseek_summary(
            title=info.get("title"),
            webpage_url=info.get("webpage_url") or url,
            transcript_text=transcript_text,
            truncated=truncated,
        )
        write_summary_artifacts(task_dir, segments, summary, subtitle_file)
        ai_summary_task_store.update(
            task_id,
            status="completed",
            progress=100,
            message="AI 总结已完成",
            summary=summary,
            error=None,
        )
    except NoTranscriptError as exc:
        ai_summary_task_store.update(
            task_id,
            status="no_transcript",
            progress=100,
            message="未找到可用字幕",
            error=str(exc),
        )
    except Exception as exc:
        ai_summary_task_store.update(
            task_id,
            status="failed",
            progress=100,
            message="AI 总结失败",
            error=str(exc),
        )


def generate_ai_summary_from_subtitle_task(
    task_id: str,
    subtitle_path: Path,
    title: str | None = None,
    webpage_url: str | None = None,
) -> None:
    task_dir = subtitle_path.parent
    ai_summary_task_store.update(
        task_id,
        status="extracting",
        progress=18,
        message="正在解析上传的字幕文件",
        task_dir=task_dir,
        title=title,
        webpage_url=webpage_url,
    )
    try:
        segments = parse_subtitle_file(subtitle_path)
        if not segments:
            raise NoTranscriptError("上传的字幕文件没有解析出有效字幕文本。")
        transcript_text, truncated = build_transcript_text(segments)
        ai_summary_task_store.update(
            task_id,
            status="summarizing",
            progress=64,
            message="已解析字幕，正在调用 Deepseek 生成总结",
            title=title,
            webpage_url=webpage_url,
            transcript_language=infer_subtitle_language(subtitle_path),
            transcript_segments=segments,
        )
        summary = call_deepseek_summary(
            title=title,
            webpage_url=webpage_url,
            transcript_text=transcript_text,
            truncated=truncated,
        )
        write_summary_artifacts(task_dir, segments, summary, subtitle_path)
        ai_summary_task_store.update(
            task_id,
            status="completed",
            progress=100,
            message="AI 总结已完成",
            summary=summary,
            error=None,
        )
    except NoTranscriptError as exc:
        ai_summary_task_store.update(
            task_id,
            status="no_transcript",
            progress=100,
            message="未解析出可用字幕",
            error=str(exc),
        )
    except Exception as exc:
        ai_summary_task_store.update(
            task_id,
            status="failed",
            progress=100,
            message="AI 总结失败",
            error=str(exc),
        )
