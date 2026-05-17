from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "Video Free Downloader"
API_PREFIX = "/api"

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

TASK_RETENTION_SECONDS = 60 * 60 * 6
DIRECT_LINK_TTL_SECONDS = 60 * 10
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
