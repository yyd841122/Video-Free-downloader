from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class VideoInfoRequest(BaseModel):
    url: HttpUrl
    cookies: str | None = Field(default=None, max_length=1_000_000)
    browser_cookies: str | None = Field(default=None, max_length=64)
    auth_session_id: str | None = Field(default=None, max_length=128)


class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    format: str = Field(default="best", max_length=256)
    with_subtitle: bool = False
    cookies: str | None = Field(default=None, max_length=1_000_000)
    browser_cookies: str | None = Field(default=None, max_length=64)
    auth_session_id: str | None = Field(default=None, max_length=128)


class VideoDirectRequest(BaseModel):
    url: HttpUrl
    format: str = Field(default="best", max_length=256)
    cookies: str | None = Field(default=None, max_length=1_000_000)
    browser_cookies: str | None = Field(default=None, max_length=64)
    auth_session_id: str | None = Field(default=None, max_length=128)


class FormatInfo(BaseModel):
    format_id: str
    ext: str | None = None
    resolution: str | None = None
    filesize: int | None = None
    filesize_approx: int | None = None
    fps: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    note: str | None = None


class VideoInfoResponse(BaseModel):
    title: str | None = None
    webpage_url: str | None = None
    thumbnail: str | None = None
    thumbnail_proxy_url: str | None = None
    duration: int | None = None
    uploader: str | None = None
    extractor: str | None = None
    formats: list[FormatInfo] = []
    warnings: list[str] = []
    raw: dict[str, Any] | None = None


class DownloadTaskResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0
    speed: str | None = None
    eta: int | None = None
    filename: str | None = None
    download_url: str | None = None
    error: str | None = None


class DirectLinkResponse(BaseModel):
    title: str | None = None
    format_id: str | None = None
    ext: str | None = None
    direct_url: str
    redirect_url: str
    proxy_url: str
    expires_in: int


class BiliQrCreateResponse(BaseModel):
    session_id: str
    login_url: str
    qrcode_image: str


class BiliQrStatusResponse(BaseModel):
    status: str
    message: str
    is_logged_in: bool = False
