from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import ENABLE_MOCK_PAY_ROUTE
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import Order, User
from app.models.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    MockPayRequest,
    OrderListResponse,
    OrderPublic,
    PlanPublic,
)
from app.services.order_service import create_pending_order, format_amount, get_order_by_no, list_user_orders
from app.services.payment_service import (
    PaymentError,
    build_mock_checkout_url,
    confirm_mock_payment,
    create_stripe_checkout_session,
    handle_stripe_event,
    is_mock_mode,
    parse_stripe_webhook,
)
from app.services.plan_service import get_plan, list_active_plans

router = APIRouter(prefix="/billing")
logger = logging.getLogger("billing")


def _to_public_order(order: Order) -> OrderPublic:
    return OrderPublic(
        order_no=order.order_no,
        plan_code=order.plan_code,
        plan_name=order.plan_name,
        amount_cents=order.amount_cents,
        amount_display=format_amount(order),
        currency=order.currency,
        status=order.status,
        is_mock=bool(order.is_mock),
        paid_at=order.paid_at,
        created_at=order.created_at,
        vip_granted_days=order.vip_granted_days,
    )


@router.get("/plans", response_model=list[PlanPublic])
def get_plans(db: Session = Depends(get_db)) -> list[PlanPublic]:
    return list_active_plans(db)


@router.get("/mode")
def get_billing_mode() -> dict:
    from app.services.payment_service import build_checkout_payment_params

    methods, _ = build_checkout_payment_params()
    return {"mock": is_mock_mode(), "payment_methods": methods}


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    plan = get_plan(db, payload.plan_code)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="套餐不存在或已下架")

    mock = is_mock_mode()
    order = create_pending_order(db, user, plan, is_mock=mock)

    if mock:
        return CheckoutResponse(order_no=order.order_no, checkout_url=build_mock_checkout_url(order.order_no), mode="mock")

    try:
        url = create_stripe_checkout_session(db, user, plan, order)
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return CheckoutResponse(order_no=order.order_no, checkout_url=url, mode="stripe")


@router.get("/orders", response_model=OrderListResponse)
def get_orders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    orders = list_user_orders(db, user.id)
    return OrderListResponse(items=[_to_public_order(order) for order in orders])


@router.get("/orders/{order_no}", response_model=OrderPublic)
def get_order(
    order_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderPublic:
    order = get_order_by_no(db, order_no)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return _to_public_order(order)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    raw_payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        constructed = parse_stripe_webhook(raw_payload, sig_header)
        message = handle_stripe_event(db, constructed)
    except PaymentError as exc:
        logger.warning("webhook 处理失败：%s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "message": message}


# ============== Mock 支付（仅在 ENABLE_MOCK_PAY_ROUTE=true 时注册路由）==============
#
# 安全决策：把"路由是否注册"放在导入期判定，而不是运行时返回 403。
# 这样一旦 APP_ENV=production（默认 ENABLE_MOCK_PAY_ROUTE=false），
# OpenAPI 与 router 表里都不会出现 /api/billing/mock/pay/{order_no}，
# 即使运维误改 MOCK_PAYMENT=true 也没有路由可以被调用。

if ENABLE_MOCK_PAY_ROUTE:

    @router.post("/mock/pay/{order_no}", response_model=OrderPublic)
    def mock_pay(
        order_no: str,
        payload: MockPayRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> OrderPublic:
        if not is_mock_mode():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前未启用 Mock 支付模式")
        order = get_order_by_no(db, order_no)
        if not order or order.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
        try:
            updated, _msg = confirm_mock_payment(db, order_no, payload.outcome)
        except PaymentError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return _to_public_order(updated)
