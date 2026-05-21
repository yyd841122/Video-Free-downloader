import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent
load_env_file(PROJECT_DIR / ".env")
load_env_file(BASE_DIR / ".env")

DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "Video Free Downloader"
API_PREFIX = "/api"

def parse_csv_env(name: str, fallback: list[str]) -> list[str]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return fallback
    return [item.strip() for item in raw_value.split(",") if item.strip()]


ALLOWED_ORIGINS = parse_csv_env(
    "ALLOWED_ORIGINS",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
)
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", r"chrome-extension://.*").strip() or None

TASK_RETENTION_SECONDS = 60 * 60 * 6
DIRECT_LINK_TTL_SECONDS = 60 * 10
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
MAX_DOWNLOAD_SECONDS = int(os.getenv("MAX_DOWNLOAD_SECONDS", "3600"))
MAX_DOWNLOAD_BYTES = int(os.getenv("MAX_DOWNLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
DOWNLOAD_CLEANUP_MAX_AGE_SECONDS = int(os.getenv("DOWNLOAD_CLEANUP_MAX_AGE_SECONDS", str(TASK_RETENTION_SECONDS)))
DOWNLOAD_CLEANUP_INTERVAL_SECONDS = int(os.getenv("DOWNLOAD_CLEANUP_INTERVAL_SECONDS", "1800"))
MAX_CONCURRENT_INFO_TASKS = int(os.getenv("MAX_CONCURRENT_INFO_TASKS", "4"))
MAX_CONCURRENT_DOWNLOAD_TASKS = int(os.getenv("MAX_CONCURRENT_DOWNLOAD_TASKS", "2"))
MAX_CONCURRENT_AI_TASKS = int(os.getenv("MAX_CONCURRENT_AI_TASKS", "2"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
DEEPSEEK_TIMEOUT_SECONDS = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "120"))
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
SUBTITLE_UPLOAD_MAX_BYTES = int(os.getenv("SUBTITLE_UPLOAD_MAX_BYTES", str(2 * 1024 * 1024)))

# --- ASR (Automatic Speech Recognition) ---
ASR_ENABLED = os.getenv("ASR_ENABLED", "false").strip().lower() in ("true", "1", "yes")
ASR_PROVIDER = os.getenv("ASR_PROVIDER", "docker-whisper").strip()
ASR_BASE_URL = os.getenv("ASR_BASE_URL", "http://127.0.0.1:9000").strip().rstrip("/")
ASR_MODEL = os.getenv("ASR_MODEL", "base").strip() or "base"
ASR_LANGUAGE = os.getenv("ASR_LANGUAGE", "zh").strip() or None
ASR_RESPONSE_FORMAT = os.getenv("ASR_RESPONSE_FORMAT", "srt").strip()
ASR_TIMEOUT_SECONDS = int(os.getenv("ASR_TIMEOUT_SECONDS", "900"))
ASR_MAX_AUDIO_MINUTES = int(os.getenv("ASR_MAX_AUDIO_MINUTES", "90"))
ASR_MAX_INPUT_BYTES = int(os.getenv("ASR_MAX_INPUT_BYTES", str(300 * 1024 * 1024)))
