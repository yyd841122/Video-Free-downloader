from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.services.email_validation import EmailValidationError, validate_registration_email


class UserError(Exception):
    pass


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    email_norm = email.strip().lower()
    if not email_norm:
        return None
    return db.execute(select(User).where(User.email == email_norm)).scalar_one_or_none()


def create_user(db: Session, email: str, password: str, nickname: Optional[str] = None) -> User:
    try:
        email_norm = validate_registration_email(email)
    except EmailValidationError as exc:
        raise UserError(exc.message_zh) from exc
    if get_user_by_email(db, email_norm):
        raise UserError("该邮箱已被注册")
    user = User(
        email=email_norm,
        password_hash=hash_password(password),
        nickname=(nickname or email_norm.split("@", 1)[0])[:64],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise UserError("邮箱或密码错误")
    return user
