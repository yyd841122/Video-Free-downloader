from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


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
    has_subtitles: bool | None = None
    subtitle_status: Literal["available", "unavailable", "unknown"] = "unknown"
    subtitle_languages: list[str] = Field(default_factory=list)
    subtitle_source: Literal["manual", "automatic", "none", "unknown"] = "unknown"
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


class ExtensionHeader(BaseModel):
    name: str = Field(max_length=128)
    value: str = Field(max_length=16_384)  # 16KB 上限，避免 header value 内存占用过大


class ExtensionMediaRequest(BaseModel):
    url: str = Field(max_length=20_000)
    method: str = Field(default="GET", max_length=16)
    type: str | None = Field(default=None, max_length=64)
    content_type: str | None = Field(default=None, max_length=256)
    request_headers: list[ExtensionHeader] = Field(default_factory=list, max_length=64)
    timestamp: float | None = None


class ExtensionCaptureRequest(BaseModel):
    page_url: str = Field(max_length=20_000)
    page_title: str | None = Field(default=None, max_length=512)
    include_sensitive_headers: bool = False
    media_requests: list[ExtensionMediaRequest] = Field(default_factory=list, max_length=100)


class ExtensionCaptureResponse(BaseModel):
    capture_id: str
    media_count: int


class AiSummaryRequest(BaseModel):
    url: HttpUrl
    cookies: str | None = Field(default=None, max_length=1_000_000)
    browser_cookies: str | None = Field(default=None, max_length=64)
    auth_session_id: str | None = Field(default=None, max_length=128)


class TranscriptSegment(BaseModel):
    start: float
    end: float | None = None
    text: str


class AiTimelineItem(BaseModel):
    time: str
    title: str
    summary: str


class AiSummaryResult(BaseModel):
    title: str | None = None
    one_sentence: str
    outline: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    timeline: list[AiTimelineItem] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    audience: str | None = None
    learning_suggestions: list[str] = Field(default_factory=list)
    mindmap_markdown: str | None = None


class AiSummaryCreateResponse(BaseModel):
    task_id: str
    status: str


class AiSummaryStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0
    message: str | None = None
    title: str | None = None
    webpage_url: str | None = None
    transcript_language: str | None = None
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)
    summary: AiSummaryResult | None = None
    error: str | None = None


class AiChatMessage(BaseModel):
    role: str = Field(max_length=16)
    content: str = Field(max_length=20_000)


class AiChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    history: list[AiChatMessage] = Field(default_factory=list, max_length=12)


class AiChatResponse(BaseModel):
    answer: str
    references: list[str] = Field(default_factory=list)


# ===================== 用户与会员 =====================


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)
    nickname: Optional[str] = Field(default=None, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: "UserPublic"


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    nickname: Optional[str] = None
    is_vip: bool = False
    is_lifetime_vip: bool = False
    vip_expire_at: Optional[int] = None


class TaskHistoryItem(BaseModel):
    id: int
    task_id: str
    kind: Literal["download", "ai_summary"]
    url: str
    title: Optional[str] = None
    format: Optional[str] = None
    status: str
    filename: Optional[str] = None
    error: Optional[str] = None
    file_available: bool = False
    download_url: Optional[str] = None
    created_at: int
    updated_at: int


class TaskHistoryListResponse(BaseModel):
    items: list[TaskHistoryItem] = Field(default_factory=list)


class BatchDownloadRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=20)
    format: str = Field(default="best", max_length=256)
    with_subtitle: bool = False
    cookies: str | None = Field(default=None, max_length=1_000_000)
    browser_cookies: str | None = Field(default=None, max_length=64)
    auth_session_id: str | None = Field(default=None, max_length=128)


class BatchDownloadTaskItem(BaseModel):
    url: str
    task_id: str | None = None
    status: str = "queued"
    error: str | None = None


class BatchDownloadResponse(BaseModel):
    tasks: list[BatchDownloadTaskItem] = Field(default_factory=list)


class QuotaPublic(BaseModel):
    is_vip: bool = False
    ai_used_today: int = 0
    ai_daily_limit: int = 0
    ai_remaining: int = 0
    max_resolution: int = 720
    max_concurrent: int = 1
    ai_chat_per_task: int = 5
    active_download_tasks: int = 0
    active_ai_tasks: int = 0


TokenResponse.model_rebuild()


# ===================== 套餐与订单 =====================


class PlanPublic(BaseModel):
    code: str
    name: str
    duration_days: Optional[int] = None
    price_cents: int
    price_display: str
    currency: str
    description: Optional[str] = None
    is_lifetime: bool = False
    sort_order: int = 0
    recommended: bool = False


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)


class CheckoutResponse(BaseModel):
    order_no: str
    checkout_url: str
    mode: Literal["stripe", "mock"]


class OrderPublic(BaseModel):
    order_no: str
    plan_code: str
    plan_name: str
    amount_cents: int
    amount_display: str
    currency: str
    status: str
    is_mock: bool
    paid_at: Optional[int] = None
    created_at: int
    vip_granted_days: Optional[int] = None


class OrderListResponse(BaseModel):
    items: list[OrderPublic] = Field(default_factory=list)


class MockPayRequest(BaseModel):
    outcome: Literal["success", "fail", "cancel"] = "success"

