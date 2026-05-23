from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.db.database import get_db
from app.db.models import User
from app.models.schemas import LoginRequest, QuotaPublic, RegisterRequest, TokenResponse, UserPublic
from app.services.quota_service import QuotaInfo, get_quota
from app.services.user_service import UserError, authenticate, create_user

router = APIRouter(prefix="/users")


def _quota_to_public(info: QuotaInfo) -> QuotaPublic:
    return QuotaPublic(
        is_vip=info.is_vip,
        ai_used_today=info.ai_used_today,
        ai_daily_limit=info.ai_daily_limit,
        ai_remaining=info.ai_remaining,
        max_resolution=info.max_resolution,
        max_concurrent=info.max_concurrent,
        ai_chat_per_task=info.ai_chat_per_task,
        active_download_tasks=info.active_download_tasks,
        active_ai_tasks=info.active_ai_tasks,
    )


def _to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        is_vip=user.is_vip,
        is_lifetime_vip=bool(user.is_lifetime_vip),
        vip_expire_at=user.vip_expire_at,
    )


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = create_user(db, payload.email, payload.password, payload.nickname)
    except UserError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token, user=_to_public(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = authenticate(db, payload.email, payload.password)
    except UserError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token, user=_to_public(user))


@router.get("/me", response_model=UserPublic)
def get_me(user: User = Depends(get_current_user)) -> UserPublic:
    return _to_public(user)


@router.get("/me/quota", response_model=QuotaPublic)
def get_my_quota(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> QuotaPublic:
    return _quota_to_public(get_quota(db, user))
