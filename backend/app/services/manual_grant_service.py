"""管理员手动开通 VIP（Phase 1：CLI / 内部服务，无公网 Admin API）。"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import Plan, User
from app.services.email_validation import EmailValidationError, validate_registration_email
from app.services.order_service import create_manual_pending_order, mark_order_paid
from app.services.plan_service import get_plan
from app.services.user_service import get_user_by_email

AUDIT_DIR = Path(__file__).resolve().parents[2] / "data" / "audit"
DEFAULT_AUDIT_PATH = AUDIT_DIR / "manual_grants.jsonl"

VALID_PLAN_CODES = frozenset({"monthly", "quarterly", "yearly", "lifetime"})


class ManualGrantError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


@dataclass
class VipSnapshot:
    vip_expire_at: Optional[int]
    is_lifetime_vip: int
    is_vip: bool

    def to_display(self) -> str:
        return (
            f"vip_expire_at={self.vip_expire_at}, "
            f"is_lifetime_vip={self.is_lifetime_vip}, "
            f"is_vip={self.is_vip}"
        )


@dataclass
class ManualGrantPreview:
    target_user_email: str
    target_user_id: int
    plan_code: str
    vip_granted_days: Optional[int]
    amount_cents: int
    vip_before: VipSnapshot
    vip_after: VipSnapshot
    order_no: str
    manual_grant_id: str
    warnings: list[str]


@dataclass
class ManualGrantResult:
    preview: ManualGrantPreview
    order_no: str
    audit_path: Path
    warnings: list[str]


def audit_log_path() -> Path:
    import os

    override = os.getenv("MANUAL_GRANT_AUDIT_PATH", "").strip()
    if override:
        return Path(override)
    return DEFAULT_AUDIT_PATH


def _snapshot(user: User) -> VipSnapshot:
    return VipSnapshot(
        vip_expire_at=user.vip_expire_at,
        is_lifetime_vip=int(user.is_lifetime_vip or 0),
        is_vip=bool(user.is_vip),
    )


def _preview_vip_after(user: User, plan: Plan) -> VipSnapshot:
    now = int(time.time())
    if plan.duration_days is None:
        return VipSnapshot(
            vip_expire_at=user.vip_expire_at,
            is_lifetime_vip=1,
            is_vip=True,
        )
    base = max(now, int(user.vip_expire_at or 0))
    expire_at = base + plan.duration_days * 86400
    return VipSnapshot(
        vip_expire_at=expire_at,
        is_lifetime_vip=int(user.is_lifetime_vip or 0),
        is_vip=True,
    )


def _normalize_email(email: str) -> str:
    try:
        return validate_registration_email(email)
    except EmailValidationError as exc:
        raise ManualGrantError("invalid_email", exc.message_zh) from exc


def _validate_plan_code(plan_code: str) -> str:
    code = (plan_code or "").strip().lower()
    if code not in VALID_PLAN_CODES:
        raise ManualGrantError("invalid_plan", f"非法套餐：{plan_code!r}，允许：{', '.join(sorted(VALID_PLAN_CODES))}")
    return code


def _check_lifetime_rules(user: User, plan: Plan, *, force: bool) -> list[str]:
    warnings: list[str] = []
    if not user.is_lifetime_vip:
        return warnings

    if plan.duration_days is None:
        warnings.append("用户已是终身会员，再次发放 lifetime 不会改变会员状态")
        return warnings

    if not force:
        raise ManualGrantError(
            "lifetime_force_required",
            "目标用户已是终身会员，发放非终身套餐需加 --force",
        )
    warnings.append("用户已是终身会员，已使用 --force 发放非终身套餐（is_lifetime_vip 仍为 1）")
    return warnings


def _request_id_exists(path: Path, request_id: str) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("request_id") == request_id and record.get("dry_run") is False:
            return True
    return False


def build_preview(
    db: Session,
    *,
    email: str,
    plan_code: str,
    force: bool = False,
) -> ManualGrantPreview:
    email_norm = _normalize_email(email)
    code = _validate_plan_code(plan_code)

    user = get_user_by_email(db, email_norm)
    if not user:
        raise ManualGrantError("user_not_found", f"用户不存在：{email_norm}")

    plan = get_plan(db, code)
    if not plan or not plan.is_active:
        raise ManualGrantError("invalid_plan", f"套餐不存在或已下架：{code}")

    warnings = _check_lifetime_rules(user, plan, force=force)
    manual_grant_id = str(uuid.uuid4())
    order_no = f"MAN{int(time.time())}DRYRUN"

    return ManualGrantPreview(
        target_user_email=email_norm,
        target_user_id=user.id,
        plan_code=plan.code,
        vip_granted_days=plan.duration_days,
        amount_cents=plan.price_cents,
        vip_before=_snapshot(user),
        vip_after=_preview_vip_after(user, plan),
        order_no=order_no,
        manual_grant_id=manual_grant_id,
        warnings=warnings,
    )


def grant_vip_manual(
    db: Session,
    *,
    email: str,
    plan_code: str,
    reason: str,
    admin_email: str,
    dry_run: bool = True,
    force: bool = False,
    amount_cents_reported: Optional[int] = None,
    request_id: Optional[str] = None,
) -> ManualGrantResult:
    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise ManualGrantError("invalid_reason", "备注 reason 不能为空")
    if len(reason_clean) > 200:
        raise ManualGrantError("invalid_reason", "备注 reason 过长（最多 200 字符）")

    admin_norm = _normalize_email(admin_email)
    preview = build_preview(db, email=email, plan_code=plan_code, force=force)

    audit_path = audit_log_path()
    if request_id and not dry_run:
        if _request_id_exists(audit_path, request_id):
            raise ManualGrantError("duplicate_request_id", f"request_id 已存在：{request_id}")

    if dry_run:
        return ManualGrantResult(preview=preview, order_no=preview.order_no, audit_path=audit_path, warnings=preview.warnings)

    user = get_user_by_email(db, preview.target_user_email)
    if not user:
        raise ManualGrantError("user_not_found", f"用户不存在：{preview.target_user_email}")

    plan = get_plan(db, preview.plan_code)
    if not plan:
        raise ManualGrantError("invalid_plan", f"套餐不存在：{preview.plan_code}")

    vip_before = _snapshot(user)
    manual_grant_id = str(uuid.uuid4())

    order = create_manual_pending_order(db, user, plan, manual_grant_id=manual_grant_id)
    mark_order_paid(db, order, stripe_event_id=order.stripe_event_id)

    db.refresh(user)
    vip_after = _snapshot(user)

    record: dict[str, Any] = {
        "manual_grant_id": manual_grant_id,
        "source": "manual_grant",
        "created_at": int(time.time()),
        "admin_email": admin_norm,
        "target_user_email": preview.target_user_email,
        "target_user_id": preview.target_user_id,
        "plan_code": preview.plan_code,
        "vip_granted_days": preview.vip_granted_days,
        "reason": reason_clean,
        "order_no": order.order_no,
        "amount_cents": preview.amount_cents,
        "amount_cents_reported": amount_cents_reported,
        "vip_expire_at_before": vip_before.vip_expire_at,
        "vip_expire_at_after": vip_after.vip_expire_at,
        "is_lifetime_vip_before": vip_before.is_lifetime_vip,
        "is_lifetime_vip_after": vip_after.is_lifetime_vip,
        "dry_run": False,
        "force": bool(force),
        "warnings": preview.warnings,
    }
    if request_id:
        record["request_id"] = request_id

    _append_audit(audit_path, record)

    preview.order_no = order.order_no
    preview.vip_after = vip_after
    return ManualGrantResult(
        preview=preview,
        order_no=order.order_no,
        audit_path=audit_path,
        warnings=preview.warnings,
    )


def _append_audit(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
