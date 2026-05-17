from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, direct, files, health, tasks, video
from app.core.config import ALLOWED_ORIGINS, API_PREFIX, APP_NAME

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(video.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(direct.router, prefix=API_PREFIX)
