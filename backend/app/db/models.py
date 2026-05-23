from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_vip(self) -> bool:
        if self.is_lifetime_vip:
            return True
        return bool(self.vip_expire_at and self.vip_expire_at > _now_ts())


class Plan(Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = lifetime
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="cny", nullable=False)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # pending / paid / canceled / expired / refunded
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stripe_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_mock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vip_granted_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paid_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, onupdate=_now_ts, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="orders")


Index("idx_orders_user_status", Order.user_id, Order.status)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AiUsage(Base):
    """记录用户每天 AI 总结调用次数，用于按日配额限制。"""

    __tablename__ = "ai_usage"
    __table_args__ = (UniqueConstraint("user_id", "date_key", name="uq_ai_usage_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date_key: Mapped[str] = mapped_column(String(16), nullable=False)  # YYYY-MM-DD UTC
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, onupdate=_now_ts, nullable=False)


class UserTaskHistory(Base):
    """登录用户的下载 / AI 总结任务记录（元数据；文件仍按目录保留策略清理）。"""

    __tablename__ = "user_task_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # download | ai_summary
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=_now_ts, onupdate=_now_ts, nullable=False)


Index("idx_history_user_created", UserTaskHistory.user_id, UserTaskHistory.created_at)
