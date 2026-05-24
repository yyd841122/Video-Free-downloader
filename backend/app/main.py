import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, auth, billing, direct, extension, files, health, history, tasks, users, video
from app.core.config import (
    ALLOWED_METHODS,
    ALLOWED_ORIGIN_REGEX,
    ALLOWED_ORIGINS,
    API_PREFIX,
    APP_NAME,
)
from app.db.database import init_db
from app.services.cleanup_service import cleanup_downloads_once, start_cleanup_worker, stop_cleanup_worker
from app.services.plan_service import seed_default_plans

logger = logging.getLogger("main")


def _validate_production_config() -> None:
    """生产环境（APP_ENV=production）启动期硬校验。

    任一关键项缺失/不合法 → 直接 RuntimeError 让进程退出。
    错误信息只列"缺失/不合法的配置项名"，不打印任何密钥/签名/原值。
    """

    # 在函数内 import，便于单元测试 monkey-patch app.core.config 模块属性后调用本函数。
    from app.core import config

    if config.APP_ENV != "production":
        return

    errors: list[str] = []

    if config.MOCK_PAYMENT:
        errors.append("MOCK_PAYMENT 必须为 false")
    if config.ENABLE_MOCK_PAY_ROUTE:
        errors.append("ENABLE_MOCK_PAY_ROUTE 必须为 false")

    if not config.STRIPE_SECRET_KEY:
        errors.append("STRIPE_SECRET_KEY 未配置")
    if not config.STRIPE_WEBHOOK_SECRET:
        errors.append("STRIPE_WEBHOOK_SECRET 未配置")

    for name, value in (
        ("STRIPE_PRICE_MONTHLY", config.STRIPE_PRICE_MONTHLY),
        ("STRIPE_PRICE_QUARTERLY", config.STRIPE_PRICE_QUARTERLY),
        ("STRIPE_PRICE_YEARLY", config.STRIPE_PRICE_YEARLY),
        ("STRIPE_PRICE_LIFETIME", config.STRIPE_PRICE_LIFETIME),
    ):
        if not value:
            errors.append(f"{name} 未配置")

    if not (config.FRONTEND_URL or "").startswith("https://"):
        errors.append("FRONTEND_URL 必须以 https:// 开头")

    if (
        not config.JWT_SECRET
        or config.JWT_SECRET == "dev-insecure-jwt-secret-please-change"
        or len(config.JWT_SECRET) < 32
    ):
        errors.append("JWT_SECRET 缺失/为默认值/不足 32 字符")

    if errors:
        # 仅记录配置项名，不打印任何敏感值。
        logger.error("生产环境配置校验失败：%s", "; ".join(errors))
        raise RuntimeError(
            "生产环境配置校验失败（请按 docs/生产部署清单.md 修正 backend/.env 后重启）："
            + "; ".join(errors)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_production_config()
    init_db()
    seed_default_plans()
    cleanup_downloads_once()
    start_cleanup_worker()
    try:
        yield
    finally:
        stop_cleanup_worker()


app = FastAPI(title=APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=["*"],
)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(history.router, prefix=API_PREFIX)
app.include_router(billing.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(video.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(direct.router, prefix=API_PREFIX)
app.include_router(extension.router, prefix=API_PREFIX)
