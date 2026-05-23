from __future__ import annotations

import json
import logging
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from app.core.config import (
    FRONTEND_URL,
    MOCK_PAYMENT,
    STRIPE_PAYMENT_METHODS,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from app.db.models import Order, Plan, User, WebhookEvent
from app.services.order_service import OrderError, get_order_by_no, get_order_by_stripe_session, mark_order_paid

logger = logging.getLogger("payment")


class PaymentError(Exception):
    pass


def is_mock_mode() -> bool:
    """没填 Stripe Secret 时强制 Mock，避免误用导致请求 https://api.stripe.com"""

    if MOCK_PAYMENT:
        return True
    if not STRIPE_SECRET_KEY:
        logger.warning("STRIPE_SECRET_KEY 未配置，自动切换为 MOCK 支付模式")
        return True
    return False


def _stripe_client() -> stripe.StripeClient:
    if not STRIPE_SECRET_KEY:
        raise PaymentError("未配置 STRIPE_SECRET_KEY，无法调用 Stripe API")
    return stripe.StripeClient(STRIPE_SECRET_KEY)


def build_mock_checkout_url(order_no: str) -> str:
    return f"{FRONTEND_URL}/mock-pay?order_no={order_no}"


def build_success_url(order_no: str) -> str:
    return f"{FRONTEND_URL}/payment/success?order_no={order_no}&session_id={{CHECKOUT_SESSION_ID}}"


def build_cancel_url(order_no: str) -> str:
    return f"{FRONTEND_URL}/payment/cancel?order_no={order_no}"


def build_checkout_payment_params() -> tuple[list[str], dict[str, dict]]:
    """组装 Checkout 的支付方式；微信 Web 结账需 client=web。"""

    methods = list(STRIPE_PAYMENT_METHODS)
    options: dict[str, dict] = {}
    if "wechat_pay" in methods:
        options["wechat_pay"] = {"client": "web"}
    return methods, options


def create_stripe_checkout_session(db: Session, user: User, plan: Plan, order: Order) -> str:
    """调用真实 Stripe API，返回 Checkout URL。"""

    client = _stripe_client()

    # 优先使用预先在 Stripe 后台创建的 Price ID；否则用 price_data 内联（适合本地快速跑通）
    if plan.stripe_price_id:
        line_items = [{"price": plan.stripe_price_id, "quantity": 1}]
    else:
        line_items = [
            {
                "quantity": 1,
                "price_data": {
                    "currency": plan.currency,
                    "unit_amount": plan.price_cents,
                    "product_data": {
                        "name": plan.name,
                        "description": plan.description or plan.name,
                    },
                },
            }
        ]

    payment_method_types, payment_method_options = build_checkout_payment_params()
    session_params: dict = {
        "mode": "payment",
        "line_items": line_items,
        "payment_method_types": payment_method_types,
        "success_url": build_success_url(order.order_no),
        "cancel_url": build_cancel_url(order.order_no),
        "client_reference_id": order.order_no,
        "customer_email": user.email,
        "metadata": {
            "order_no": order.order_no,
            "user_id": str(user.id),
            "plan_code": plan.code,
        },
    }
    if payment_method_options:
        session_params["payment_method_options"] = payment_method_options

    try:
        session = client.checkout.sessions.create(
            params=session_params,
            options={"idempotency_key": f"checkout-{order.order_no}"},
        )
    except stripe.StripeError as exc:
        raise PaymentError(f"Stripe 创建支付会话失败：{exc.user_message or exc}") from exc

    order.stripe_session_id = session.id
    db.add(order)
    db.commit()
    if not session.url:
        raise PaymentError("Stripe 未返回 Checkout URL")
    return session.url


# ============== Webhook 处理 ==============


class _ConstructedEvent:
    """封装 Stripe Event 与原始 payload，便于幂等存档。"""

    def __init__(self, event: dict, raw_payload: bytes):
        self.event = event
        self.raw_payload = raw_payload

    @property
    def id(self) -> str:
        return str(self.event.get("id") or "")

    @property
    def type(self) -> str:
        return str(self.event.get("type") or "")


def parse_stripe_webhook(raw_payload: bytes, sig_header: Optional[str]) -> _ConstructedEvent:
    if not STRIPE_WEBHOOK_SECRET:
        raise PaymentError("未配置 STRIPE_WEBHOOK_SECRET，无法验证 webhook")
    if not sig_header:
        raise PaymentError("缺少 Stripe-Signature 请求头")
    try:
        event = stripe.Webhook.construct_event(raw_payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError as exc:
        raise PaymentError(f"Webhook 签名校验失败：{exc}") from exc
    except ValueError as exc:
        raise PaymentError(f"Webhook payload 解析失败：{exc}") from exc
    # stripe SDK 返回的是 Event 对象；统一转 dict 便于序列化
    event_dict = event.to_dict() if hasattr(event, "to_dict") else dict(event)
    return _ConstructedEvent(event_dict, raw_payload)


def handle_stripe_event(db: Session, constructed: _ConstructedEvent) -> str:
    """处理 Stripe webhook 事件，幂等 + 状态机 + 金额校验。

    返回处理结果文案，便于排查。"""

    event_id = constructed.id
    event_type = constructed.type
    if not event_id:
        raise PaymentError("Stripe 事件缺少 id")

    # 1）幂等：先尝试落 webhook_events 表。重复事件会被唯一约束挡掉。
    existing = db.get(WebhookEvent, event_id)
    if existing:
        return f"duplicate event {event_id}, ignored"

    payload_text = constructed.raw_payload.decode("utf-8", errors="replace")
    record = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        processed=0,
        payload=payload_text[:200_000],
    )
    db.add(record)
    db.commit()

    try:
        message = _dispatch_event(db, constructed)
    except Exception as exc:  # 保持事件已持久化但 processed=0，便于人工排查
        logger.exception("处理 Stripe 事件失败：%s", exc)
        raise

    record.processed = 1
    db.add(record)
    db.commit()
    return message


def _dispatch_event(db: Session, constructed: _ConstructedEvent) -> str:
    event_type = constructed.type
    obj = (constructed.event.get("data") or {}).get("object") or {}
    if event_type == "checkout.session.completed":
        return _handle_checkout_session_completed(db, constructed, obj)
    if event_type == "checkout.session.expired":
        return _handle_checkout_session_expired(db, obj)
    logger.info("unhandled stripe event: %s", event_type)
    return f"unhandled event {event_type}"


def _handle_checkout_session_completed(db: Session, constructed: _ConstructedEvent, session_obj: dict) -> str:
    payment_status = session_obj.get("payment_status")
    if payment_status not in ("paid", "no_payment_required"):
        return f"session not paid (status={payment_status}), ignored"

    order_no = session_obj.get("client_reference_id") or (session_obj.get("metadata") or {}).get("order_no")
    if not order_no:
        raise PaymentError("Checkout Session 缺少 client_reference_id / metadata.order_no，无法定位订单")

    order = get_order_by_no(db, order_no)
    if not order:
        # 兜底：用 session_id 反查（避免 metadata 被篡改/缺失）
        session_id = session_obj.get("id")
        if session_id:
            order = get_order_by_stripe_session(db, session_id)
    if not order:
        raise PaymentError(f"找不到订单 {order_no}")

    # 二次安全校验：金额与币种必须一致，防止前端被篡改后伪造低价订单
    amount_total = int(session_obj.get("amount_total") or 0)
    currency = str(session_obj.get("currency") or "").lower()
    if amount_total != order.amount_cents or currency != order.currency.lower():
        raise PaymentError(
            f"订单 {order_no} 金额/币种与 Stripe 不一致：local={order.amount_cents}{order.currency} stripe={amount_total}{currency}"
        )

    payment_intent_id = session_obj.get("payment_intent")
    try:
        changed = mark_order_paid(
            db,
            order,
            stripe_payment_intent_id=payment_intent_id if isinstance(payment_intent_id, str) else None,
            stripe_event_id=constructed.id,
        )
    except OrderError as exc:
        raise PaymentError(str(exc)) from exc
    return f"order {order_no} marked paid={changed}"


def _handle_checkout_session_expired(db: Session, session_obj: dict) -> str:
    order_no = session_obj.get("client_reference_id") or (session_obj.get("metadata") or {}).get("order_no")
    if not order_no:
        return "expired session without order_no"
    order = get_order_by_no(db, order_no)
    if order and order.status == "pending":
        order.status = "expired"
        db.add(order)
        db.commit()
        return f"order {order_no} marked expired"
    return f"expired session for order {order_no} ignored"


def confirm_mock_payment(db: Session, order_no: str, outcome: str) -> tuple[Order, str]:
    """MOCK 支付：模拟 Stripe webhook 路径，复用同一套状态机与幂等。"""

    order = get_order_by_no(db, order_no)
    if not order:
        raise PaymentError("订单不存在")
    if order.is_mock != 1:
        raise PaymentError("该订单非 Mock 订单，不能用模拟支付")

    if outcome == "cancel":
        cancelled = order.status == "pending"
        if cancelled:
            order.status = "canceled"
            db.add(order)
            db.commit()
        return order, "canceled" if cancelled else f"ignored, status={order.status}"

    if outcome == "fail":
        if order.status == "pending":
            order.status = "canceled"
            db.add(order)
            db.commit()
        return order, "failed"

    # outcome == "success"
    if order.status == "paid":
        return order, "already paid"
    try:
        mark_order_paid(db, order, stripe_event_id=f"mock-{order.order_no}")
    except OrderError as exc:
        raise PaymentError(str(exc)) from exc
    return order, "paid"
