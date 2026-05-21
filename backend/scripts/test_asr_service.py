"""Standalone test script for asr_service.py.

Run from project root:
    python backend/scripts/test_asr_service.py

Requires docker-whisper running at http://127.0.0.1:9000
and test audio files in tmp/.
"""

import os
import sys
from pathlib import Path

# Ensure backend is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Enable ASR for this test script.
os.environ.setdefault("ASR_ENABLED", "true")

from app.services.asr_service import (  # noqa: E402
    ASRServiceDisabledError,
    ASRServiceUnavailableError,
    ASRTranscriptionError,
    transcribe_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "tmp" / "asr-test-service"

TEST_FILES = [
    (PROJECT_ROOT / "tmp" / "test-en.wav", "en"),
    (PROJECT_ROOT / "tmp" / "test-zh.wav", "zh"),
]

FORMATS = ("text", "srt", "vtt")


def run_single_test(
    audio_path: Path,
    language: str,
    fmt: str,
) -> bool:
    """Run one transcription test and save output."""
    tag = f"{audio_path.stem}-{fmt}"
    out_file = OUTPUT_DIR / f"transcript-{tag}.{fmt}"

    print(f"  [{tag}] ...", end=" ", flush=True)
    try:
        result = transcribe_file(
            file_path=audio_path,
            response_format=fmt,
            language=language,
        )
    except ASRServiceDisabledError as exc:
        print(f"SKIPPED ({exc})")
        return False
    except ASRServiceUnavailableError as exc:
        print(f"UNAVAILABLE ({exc})")
        return False
    except ASRTranscriptionError as exc:
        print(f"FAILED ({exc})")
        return False

    out_file.write_text(result.raw_content, encoding="utf-8")

    preview = result.text[:120].replace("\n", " ")
    size = len(result.raw_content)
    print(f"OK ({size} chars) -> {out_file.name}")
    print(f"    preview: {preview}")
    return True


def main() -> None:
    print("=== ASR Service Standalone Test ===")
    print(f"Output dir: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results: list[str] = []

    for audio_path, language in TEST_FILES:
        if not audio_path.exists():
            print(f"\nSkip {audio_path.name} (not found)")
            continue

        print(f"\n--- {audio_path.name} (lang={language}) ---")
        for fmt in FORMATS:
            ok = run_single_test(audio_path, language, fmt)
            results.append(f"{'PASS' if ok else 'FAIL'} {audio_path.stem} {fmt}")

    print("\n=== Summary ===")
    for r in results:
        print(f"  {r}")

    passed = sum(1 for r in results if r.startswith("PASS"))
    total = len(results)
    print(f"\n{passed}/{total} tests passed.")


if __name__ == "__main__":
    main()
