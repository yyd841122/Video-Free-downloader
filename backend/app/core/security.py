from __future__ import annotations

import time
from typing import Optional

import bcrypt
import jwt

from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET

# bcrypt 限制密码最长 72 字节。对超长密码进行右截断，避免抛错。
# 这是安全的处理方式：在世界范围内仍提供高熵入口。
_BCRYPT_MAX_BYTES = 72


def _normalize_password_bytes(plain: str) -> bytes:
    data = plain.encode("utf-8")
    if len(data) > _BCRYPT_MAX_BYTES:
        data = data[:_BCRYPT_MAX_BYTES]
    return data


def hash_password(plain: str) -> str:
    pwd_bytes = _normalize_password_bytes(plain)
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_normalize_password_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra: Optional[dict] = None, expires_minutes: Optional[int] = None) -> str:
    now = int(time.time())
    expire_min = expires_minutes if expires_minutes is not None else JWT_EXPIRE_MINUTES
    payload: dict = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expire_min * 60,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
