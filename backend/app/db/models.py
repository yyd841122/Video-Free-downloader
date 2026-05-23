from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import BigInteger, Integer, String
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
