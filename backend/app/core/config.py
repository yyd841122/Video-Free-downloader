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

# --- Runtime environment ---
# APP_ENV 决定一切"按环境裁剪"的默认值，例如 MOCK_PAYMENT、ENABLE_MOCK_PAY_ROUTE。
# 取值：development / test / production；未配置时按最保守的非生产语义（development）走，
# 但 main.py 的 lifespan 会对 APP_ENV=production 做硬校验。
APP_ENV = (os.getenv("APP_ENV", "development").strip().lower()) or "development"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value == "":
        return default
    return value in ("true", "1", "yes")


DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}")

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

# CORS origin 正则白名单：默认禁止任意 chrome-extension://*
# 如需放行特定扩展，请在环境变量中明确指定其 ID，例如：
#   ALLOWED_ORIGIN_REGEX=chrome-extension://abcdef0123456789abcdef0123456789
# 或 ALLOWED_EXTENSION_IDS=abcdef...,012345... （二选一）
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None
ALLOWED_EXTENSION_IDS = parse_csv_env("ALLOWED_EXTENSION_IDS", [])
if not ALLOWED_ORIGIN_REGEX and ALLOWED_EXTENSION_IDS:
    # 仅允许指定 extension id 的 chrome-extension origin
    _ext_ids_pattern = "|".join(item for item in ALLOWED_EXTENSION_IDS if item)
    if _ext_ids_pattern:
        ALLOWED_ORIGIN_REGEX = rf"^chrome-extension://({_ext_ids_pattern})$"

# 生产环境默认仅允许业务实际使用的 HTTP 方法；如需 PUT/DELETE/PATCH，可通过
# ALLOWED_METHODS=GET,POST,PUT,DELETE,PATCH,OPTIONS 覆盖
ALLOWED_METHODS = parse_csv_env(
    "ALLOWED_METHODS",
    ["GET", "POST", "OPTIONS"],
)

TASK_RETENTION_SECONDS = 60 * 60 * 6
FREE_FILE_RETENTION_SECONDS = int(os.getenv("FREE_FILE_RETENTION_SECONDS", str(TASK_RETENTION_SECONDS)))
VIP_FILE_RETENTION_SECONDS = int(os.getenv("VIP_FILE_RETENTION_SECONDS", str(60 * 60 * 24 * 3)))
DIRECT_LINK_TTL_SECONDS = 60 * 10
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
MAX_DOWNLOAD_SECONDS = int(os.getenv("MAX_DOWNLOAD_SECONDS", "3600"))
MAX_DOWNLOAD_BYTES = int(os.getenv("MAX_DOWNLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
DOWNLOAD_CLEANUP_MAX_AGE_SECONDS = int(os.getenv("DOWNLOAD_CLEANUP_MAX_AGE_SECONDS", str(TASK_RETENTION_SECONDS)))
DOWNLOAD_CLEANUP_INTERVAL_SECONDS = int(os.getenv("DOWNLOAD_CLEANUP_INTERVAL_SECONDS", "1800"))

# --- Downloads disk guard (Soft Launch / small VPS) ---
DOWNLOADS_WARN_BYTES = int(os.getenv("DOWNLOADS_WARN_BYTES", str(10 * 1024 * 1024 * 1024)))
DOWNLOADS_CLEANUP_BYTES = int(os.getenv("DOWNLOADS_CLEANUP_BYTES", str(15 * 1024 * 1024 * 1024)))
DISK_CLEANUP_USAGE_PERCENT = int(os.getenv("DISK_CLEANUP_USAGE_PERCENT", "70"))
DISK_EMERGENCY_USAGE_PERCENT = int(os.getenv("DISK_EMERGENCY_USAGE_PERCENT", "85"))
DOWNLOADS_EMERGENCY_KEEP_RECENT_TASKS = int(os.getenv("DOWNLOADS_EMERGENCY_KEEP_RECENT_TASKS", "10"))
DOWNLOADS_CLEANUP_MIN_AGE_HOURS = int(os.getenv("DOWNLOADS_CLEANUP_MIN_AGE_HOURS", "6"))
DOWNLOADS_LARGE_FILE_BYTES = int(os.getenv("DOWNLOADS_LARGE_FILE_BYTES", str(100 * 1024 * 1024)))
DOWNLOADS_CLEANUP_MIN_AGE_SECONDS = DOWNLOADS_CLEANUP_MIN_AGE_HOURS * 3600
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

# --- Auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "").strip() or "dev-insecure-jwt-secret-please-change"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))  # 默认 7 天

# --- Billing & Payment ---
# 安全默认：
#   - 非生产环境（development / test）默认 MOCK_PAYMENT=true，便于本地无网联调；
#   - 生产环境（APP_ENV=production）默认 false，且 is_mock_mode()/lifespan 会硬拒绝 true。
# 不再使用旧的"无脑 true"默认，以免运维误配让生产白嫖 VIP。
MOCK_PAYMENT = _env_bool("MOCK_PAYMENT", APP_ENV != "production")

# /api/billing/mock/pay/{order_no} 是否注册到 FastAPI 路由：
#   - 非生产默认 true（开发与 staging 联调需要）
#   - 生产默认 false（即使 MOCK_PAYMENT 被误开，也没有路由可用，从根上堵死白嫖）
# main.py lifespan 在 APP_ENV=production 时会硬要求该值为 false。
ENABLE_MOCK_PAY_ROUTE = _env_bool("ENABLE_MOCK_PAY_ROUTE", APP_ENV != "production")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
# Checkout 展示的支付方式，逗号分隔。国内常用：card,alipay,wechat_pay
# 须在 Stripe Dashboard → Payment methods 中一并开启对应方式
STRIPE_PAYMENT_METHODS = [
    item.strip()
    for item in os.getenv("STRIPE_PAYMENT_METHODS", "card,alipay,wechat_pay").split(",")
    if item.strip()
] or ["card"]

# 套餐价格（单位：分；¥19 = 1900 分）。可通过环境变量覆盖
BILLING_CURRENCY = (os.getenv("BILLING_CURRENCY", "cny").strip().lower() or "cny")
PLAN_PRICE_MONTHLY = int(os.getenv("PLAN_PRICE_MONTHLY_CENTS", "1900"))
PLAN_PRICE_QUARTERLY = int(os.getenv("PLAN_PRICE_QUARTERLY_CENTS", "4900"))
PLAN_PRICE_YEARLY = int(os.getenv("PLAN_PRICE_YEARLY_CENTS", "16800"))
PLAN_PRICE_LIFETIME = int(os.getenv("PLAN_PRICE_LIFETIME_CENTS", "39900"))

# Stripe Price ID（启用真 Stripe 模式时必填，可在 Stripe Dashboard 创建）
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "").strip()
STRIPE_PRICE_QUARTERLY = os.getenv("STRIPE_PRICE_QUARTERLY", "").strip()
STRIPE_PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY", "").strip()
STRIPE_PRICE_LIFETIME = os.getenv("STRIPE_PRICE_LIFETIME", "").strip()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")

# --- Quota / Membership Benefits ---
FREE_AI_SUMMARY_PER_DAY = int(os.getenv("FREE_AI_SUMMARY_PER_DAY", "3"))
VIP_AI_SUMMARY_PER_DAY = int(os.getenv("VIP_AI_SUMMARY_PER_DAY", "50"))
FREE_MAX_RESOLUTION = int(os.getenv("FREE_MAX_RESOLUTION", "720"))
FREE_CONCURRENT_DOWNLOAD = int(os.getenv("FREE_CONCURRENT_DOWNLOAD", "1"))
VIP_CONCURRENT_DOWNLOAD = int(os.getenv("VIP_CONCURRENT_DOWNLOAD", "3"))
FREE_AI_CHAT_PER_TASK = int(os.getenv("FREE_AI_CHAT_PER_TASK", "5"))
VIP_AI_CHAT_PER_TASK = int(os.getenv("VIP_AI_CHAT_PER_TASK", "0"))  # 0 = 不限
FREE_BATCH_MAX_URLS = int(os.getenv("FREE_BATCH_MAX_URLS", "1"))
VIP_BATCH_MAX_URLS = int(os.getenv("VIP_BATCH_MAX_URLS", "10"))
