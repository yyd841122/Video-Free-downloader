from __future__ import annotations

import secrets
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Order, Plan, User
from app.services.plan_service import _format_price


class OrderError(Exception):
    pass


def generate_order_no() -> str:
    """订单号同时作为 Stripe idempotency_key，全局唯一即可。"""

    return f"FVD{int(time.time())}{secrets.token_hex(4).upper()}"


def generate_manual_order_no() -> str:
    """人工开通 VIP 订单号，与 Stripe FVD* 订单区分。"""

    return f"MAN{int(time.time())}{secrets.token_hex(4).upper()}"


def create_manual_pending_order(
    db: Session,
    user: User,
    plan: Plan,
    *,
    manual_grant_id: str,
) -> Order:
    """创建待支付的人工订单（is_mock=0，供 mark_order_paid 发放 VIP）。"""

    order = Order(
        order_no=generate_manual_order_no(),
        user_id=user.id,
        plan_code=plan.code,
        plan_name=plan.name,
        amount_cents=plan.price_cents,
        currency=plan.currency,
        status="pending",
        is_mock=0,
        vip_granted_days=plan.duration_days,
        stripe_event_id=f"manual-grant-{manual_grant_id}",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def create_pending_order(db: Session, user: User, plan: Plan, is_mock: bool) -> Order:
    order = Order(
        order_no=generate_order_no(),
        user_id=user.id,
        plan_code=plan.code,
        plan_name=plan.name,
        amount_cents=plan.price_cents,
        currency=plan.currency,
        status="pending",
        is_mock=1 if is_mock else 0,
        vip_granted_days=plan.duration_days,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order_by_no(db: Session, order_no: str) -> Optional[Order]:
    return db.execute(select(Order).where(Order.order_no == order_no)).scalar_one_or_none()


def get_order_by_stripe_session(db: Session, session_id: str) -> Optional[Order]:
    return db.execute(select(Order).where(Order.stripe_session_id == session_id)).scalar_one_or_none()


def list_user_orders(db: Session, user_id: int, limit: int = 50) -> list[Order]:
    return (
        db.execute(select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(limit))
        .scalars()
        .all()
    )


def mark_order_paid(
    db: Session,
    order: Order,
    *,
    stripe_payment_intent_id: Optional[str] = None,
    stripe_event_id: Optional[str] = None,
) -> bool:
    """状态机：仅 pending → paid 才发会员。返回是否真正发生了状态变更。"""

    if order.status == "paid":
        return False
    if order.status != "pending":
        raise OrderError(f"订单状态 {order.status} 不允许标记为已支付")

    user = db.get(User, order.user_id)
    if not user:
        raise OrderError("订单关联用户不存在")

    now = int(time.time())
    order.status = "paid"
    order.paid_at = now
    if stripe_payment_intent_id:
        order.stripe_payment_intent_id = stripe_payment_intent_id
    if stripe_event_id:
        order.stripe_event_id = stripe_event_id

    if order.vip_granted_days is None:
        user.is_lifetime_vip = 1
    else:
        base = max(now, int(user.vip_expire_at or 0))
        user.vip_expire_at = base + order.vip_granted_days * 86400

    db.add(order)
    db.add(user)
    db.commit()
    db.refresh(order)
    return True


def cancel_order(db: Session, order: Order) -> bool:
    if order.status != "pending":
        return False
    order.status = "canceled"
    db.add(order)
    db.commit()
    return True


def format_amount(order: Order) -> str:
    return _format_price(order.amount_cents, order.currency)
