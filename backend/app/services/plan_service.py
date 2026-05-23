from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import (
    BILLING_CURRENCY,
    PLAN_PRICE_LIFETIME,
    PLAN_PRICE_MONTHLY,
    PLAN_PRICE_QUARTERLY,
    PLAN_PRICE_YEARLY,
    STRIPE_PRICE_LIFETIME,
    STRIPE_PRICE_MONTHLY,
    STRIPE_PRICE_QUARTERLY,
    STRIPE_PRICE_YEARLY,
)
from app.db.database import session_scope
from app.db.models import Plan
from app.models.schemas import PlanPublic


@dataclass
class PlanSeed:
    code: str
    name: str
    duration_days: Optional[int]
    price_cents: int
    stripe_price_id: str
    sort_order: int
    description: str


def _default_seeds() -> list[PlanSeed]:
    return [
        PlanSeed("monthly", "月度会员", 30, PLAN_PRICE_MONTHLY, STRIPE_PRICE_MONTHLY, 10, "体验完整能力，30 天高级权益"),
        PlanSeed("quarterly", "季度会员", 90, PLAN_PRICE_QUARTERLY, STRIPE_PRICE_QUARTERLY, 20, "性价比之选，平均月费更低"),
        PlanSeed("yearly", "年度会员", 365, PLAN_PRICE_YEARLY, STRIPE_PRICE_YEARLY, 30, "最受欢迎，节省约 26%"),
        PlanSeed("lifetime", "终身会员", None, PLAN_PRICE_LIFETIME, STRIPE_PRICE_LIFETIME, 40, "一次买断，永久享有"),
    ]


def seed_default_plans() -> None:
    """启动时确保数据库里有默认套餐；价格/Price ID 以最新配置为准（覆盖）。"""

    with session_scope() as db:
        for seed in _default_seeds():
            plan = db.get(Plan, seed.code)
            if plan is None:
                db.add(
                    Plan(
                        code=seed.code,
                        name=seed.name,
                        duration_days=seed.duration_days,
                        price_cents=seed.price_cents,
                        currency=BILLING_CURRENCY,
                        stripe_price_id=seed.stripe_price_id or None,
                        is_active=1,
                        sort_order=seed.sort_order,
                        description=seed.description,
                    )
                )
            else:
                plan.name = seed.name
                plan.duration_days = seed.duration_days
                plan.price_cents = seed.price_cents
                plan.currency = BILLING_CURRENCY
                plan.stripe_price_id = seed.stripe_price_id or None
                plan.description = seed.description
                plan.sort_order = seed.sort_order


def _format_price(cents: int, currency: str) -> str:
    amount = cents / 100
    if currency.lower() == "cny":
        return f"¥{amount:.2f}".rstrip("0").rstrip(".")
    if currency.lower() == "usd":
        return f"${amount:.2f}"
    return f"{amount:.2f} {currency.upper()}"


def list_active_plans(db: Session) -> list[PlanPublic]:
    rows = db.execute(select(Plan).where(Plan.is_active == 1).order_by(Plan.sort_order)).scalars().all()
    result: list[PlanPublic] = []
    for plan in rows:
        result.append(
            PlanPublic(
                code=plan.code,
                name=plan.name,
                duration_days=plan.duration_days,
                price_cents=plan.price_cents,
                price_display=_format_price(plan.price_cents, plan.currency),
                currency=plan.currency,
                description=plan.description,
                is_lifetime=plan.duration_days is None,
                sort_order=plan.sort_order,
                recommended=plan.code == "yearly",
            )
        )
    return result


def get_plan(db: Session, code: str) -> Optional[Plan]:
    return db.get(Plan, code)
