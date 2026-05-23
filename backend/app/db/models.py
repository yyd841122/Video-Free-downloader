from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _now_ts() -> int:
    return int(time.time())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vip_expire_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_lifetime_vip: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, onupdate=_now_ts, nullable=False)

    @property
    def is_vip(self) -> bool:
        if self.is_lifetime_vip:
            return True
        return bool(self.vip_expire_at and self.vip_expire_at > _now_ts())


class AiUsage(Base):
    """记录用户每天 AI 总结调用次数，用于按日配额限制。"""

    __tablename__ = "ai_usage"
    __table_args__ = (UniqueConstraint("user_id", "date_key", name="uq_ai_usage_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date_key: Mapped[str] = mapped_column(String(16), nullable=False)  # YYYY-MM-DD UTC
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, onupdate=_now_ts, nullable=False)
