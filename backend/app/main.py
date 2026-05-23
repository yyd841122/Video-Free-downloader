from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, auth, direct, extension, files, health, tasks, video
from app.core.config import (
    ALLOWED_METHODS,
    ALLOWED_ORIGIN_REGEX,
    ALLOWED_ORIGINS,
    API_PREFIX,
    APP_NAME,
)
from app.services.cleanup_service import cleanup_downloads_once, start_cleanup_worker, stop_cleanup_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(video.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(direct.router, prefix=API_PREFIX)
app.include_router(extension.router, prefix=API_PREFIX)
