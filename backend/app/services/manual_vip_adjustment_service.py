"""管理员手动调整 / 撤销 VIP（Phase 1：CLI，与 grant 分离）。"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import Order, User
from app.services.email_validation import EmailValidationError, validate_registration_email
from app.services.manual_grant_service import VipSnapshot, audit_log_path as grant_audit_log_path
from app.services.order_service import get_order_by_no
from app.services.user_service import get_user_by_email

AUDIT_DIR = Path(__file__).resolve().parents[2] / "data" / "audit"
DEFAULT_ADJUSTMENT_AUDIT_PATH = AUDIT_DIR / "manual_vip_adjustments.jsonl"

VALID_ACTIONS = frozenset({"list-grants", "rollback-last-manual-grant", "revoke-vip"})
ROLLBACK_ACTION = "rollback-last-manual-grant"
REVOKE_ACTION = "revoke-vip"


class ManualVipAdjustmentError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


@dataclass
class ManualGrantRecordView:
    manual_grant_id: str
    order_no: str
    target_user_email: str
    target_user_id: int
    plan_code: str
    amount_cents_reported: Optional[int]
    vip_expire_at_before: Optional[int]
    vip_expire_at_after: Optional[int]
    is_lifetime_vip_before: int
    is_lifetime_vip_after: int
    reason: str
    admin_email: str
    request_id: Optional[str]
    created_at: int
    rolled_back: bool

    def vip_before_display(self) -> str:
        return (
            f"vip_expire_at={self.vip_expire_at_before}, "
            f"is_lifetime_vip={self.is_lifetime_vip_before}"
        )

    def vip_after_display(self) -> str:
        return (
            f"vip_expire_at={self.vip_expire_at_after}, "
            f"is_lifetime_vip={self.is_lifetime_vip_after}"
        )


@dataclass
class AdjustmentPreview:
    action: str
    target_user_email: str
    target_user_id: int
    vip_before: VipSnapshot
    vip_after: VipSnapshot
    related_order_no: Optional[str]
    related_manual_grant_id: Optional[str]
    related_request_id: Optional[str]
    order_status_before: Optional[str]
    order_status_after: Optional[str]
    warnings: list[str]


@dataclass
class AdjustmentResult:
    preview: AdjustmentPreview
    adjustment_audit_path: Path
    warnings: list[str]


def adjustment_audit_log_path() -> Path:
    override = os.getenv("MANUAL_VIP_ADJUSTMENT_AUDIT_PATH", "").strip()
    if override:
        return Path(override)
    return DEFAULT_ADJUSTMENT_AUDIT_PATH


def _normalize_email(email: str) -> str:
    try:
        return validate_registration_email(email)
    except EmailValidationError as exc:
        raise ManualVipAdjustmentError("invalid_email", exc.message_zh) from exc


def _snapshot(user: User) -> VipSnapshot:
    return VipSnapshot(
        vip_expire_at=user.vip_expire_at,
        is_lifetime_vip=int(user.is_lifetime_vip or 0),
        is_vip=bool(user.is_vip),
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _rolled_back_grant_ids(adjustment_path: Path) -> set[str]:
    ids: set[str] = set()
    for record in _load_jsonl(adjustment_path):
        if record.get("dry_run") is True:
            continue
        if record.get("action") != ROLLBACK_ACTION:
            continue
        grant_id = record.get("related_manual_grant_id")
        if grant_id:
            ids.add(str(grant_id))
    return ids


def _adjustment_request_id_exists(path: Path, request_id: str) -> bool:
    for record in _load_jsonl(path):
        if record.get("request_id") == request_id and record.get("dry_run") is False:
            return True
    return False


def _is_manual_grant_record(record: dict[str, Any]) -> bool:
    if record.get("source") != "manual_grant":
        return False
    if record.get("dry_run") is True:
        return False
    order_no = str(record.get("order_no") or "")
    return order_no.startswith("MAN")


def _validate_manual_order(order: Order) -> None:
    if not order.order_no.startswith("MAN"):
        raise ManualVipAdjustmentError("not_manual_order", f"非人工订单，无法调整：{order.order_no}")
    event_id = order.stripe_event_id or ""
    if not event_id.startswith("manual-grant-"):
        raise ManualVipAdjustmentError("not_manual_order", f"订单缺少 manual-grant 标记：{order.order_no}")
    if order.stripe_session_id:
        raise ManualVipAdjustmentError("not_manual_order", f"Stripe 订单不可通过调整工具处理：{order.order_no}")


def _load_manual_grants(grant_path: Path) -> list[dict[str, Any]]:
    return [r for r in _load_jsonl(grant_path) if _is_manual_grant_record(r)]


def _require_user(db: Session, email: str) -> User:
    email_norm = _normalize_email(email)
    user = get_user_by_email(db, email_norm)
    if not user:
        raise ManualVipAdjustmentError("user_not_found", f"用户不存在：{email_norm}")
    return user


def _validate_write_params(*, reason: str, admin_email: str, request_id: str) -> str:
    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise ManualVipAdjustmentError("invalid_reason", "备注 reason 不能为空")
    if len(reason_clean) > 200:
        raise ManualVipAdjustmentError("invalid_reason", "备注 reason 过长（最多 200 字符）")
    if not (request_id or "").strip():
        raise ManualVipAdjustmentError("invalid_request_id", "写操作必须提供 request-id")
    return _normalize_email(admin_email)


def list_manual_grants(
    db: Session,
    *,
    email: str,
    limit: int = 10,
    order_no: Optional[str] = None,
    request_id: Optional[str] = None,
) -> list[ManualGrantRecordView]:
    user = _require_user(db, email)
    email_norm = user.email.lower()
    grant_path = grant_audit_log_path()
    adjustment_path = adjustment_audit_log_path()
    rolled_back = _rolled_back_grant_ids(adjustment_path)

    grants = _load_manual_grants(grant_path)
    grants = [g for g in grants if (g.get("target_user_email") or "").lower() == email_norm]

    if order_no:
        grants = [g for g in grants if g.get("order_no") == order_no]
    if request_id:
        grants = [g for g in grants if g.get("request_id") == request_id]

    grants.sort(key=lambda g: int(g.get("created_at") or 0), reverse=True)
    grants = grants[: max(1, limit)]

    views: list[ManualGrantRecordView] = []
    for g in grants:
        grant_id = str(g.get("manual_grant_id") or "")
        views.append(
            ManualGrantRecordView(
                manual_grant_id=grant_id,
                order_no=str(g.get("order_no") or ""),
                target_user_email=str(g.get("target_user_email") or ""),
                target_user_id=int(g.get("target_user_id") or 0),
                plan_code=str(g.get("plan_code") or ""),
                amount_cents_reported=g.get("amount_cents_reported"),
                vip_expire_at_before=g.get("vip_expire_at_before"),
                vip_expire_at_after=g.get("vip_expire_at_after"),
                is_lifetime_vip_before=int(g.get("is_lifetime_vip_before") or 0),
                is_lifetime_vip_after=int(g.get("is_lifetime_vip_after") or 0),
                reason=str(g.get("reason") or ""),
                admin_email=str(g.get("admin_email") or ""),
                request_id=g.get("request_id"),
                created_at=int(g.get("created_at") or 0),
                rolled_back=grant_id in rolled_back,
            )
        )
    return views


def _find_grant_for_rollback(
    grant_path: Path,
    adjustment_path: Path,
    *,
    email: str,
    order_no: Optional[str] = None,
) -> dict[str, Any]:
    email_norm = _normalize_email(email)
    rolled_back = _rolled_back_grant_ids(adjustment_path)
    grants = _load_manual_grants(grant_path)
    grants = [g for g in grants if (g.get("target_user_email") or "").lower() == email_norm]

    if order_no:
        matches = [g for g in grants if g.get("order_no") == order_no]
        if not matches:
            raise ManualVipAdjustmentError("grant_not_found", f"未找到订单 {order_no} 对应的人工开通记录")
        grant = matches[0]
    else:
        candidates = [
            g
            for g in grants
            if str(g.get("manual_grant_id") or "") not in rolled_back
        ]
        candidates.sort(key=lambda g: int(g.get("created_at") or 0), reverse=True)
        if not candidates:
            raise ManualVipAdjustmentError("grant_not_found", "没有可回滚的 manual grant 记录")
        grant = candidates[0]

    grant_id = str(grant.get("manual_grant_id") or "")
    if grant_id in rolled_back:
        raise ManualVipAdjustmentError("already_rolled_back", f"该 manual grant 已回滚：{grant_id}")

    return grant


def _apply_vip_snapshot(user: User, snap: VipSnapshot) -> None:
    user.is_lifetime_vip = snap.is_lifetime_vip
    user.vip_expire_at = snap.vip_expire_at


def _mark_order_refunded(db: Session, order: Order) -> tuple[str, str]:
    before = order.status
    _validate_manual_order(order)
    if order.status == "refunded":
        return before, "refunded"
    if order.status != "paid":
        raise ManualVipAdjustmentError(
            "invalid_order_status",
            f"订单 {order.order_no} 状态为 {order.status}，无法标记 refunded",
        )
    order.status = "refunded"
    db.add(order)
    return before, "refunded"


def rollback_last_manual_grant(
    db: Session,
    *,
    email: str,
    reason: str,
    admin_email: str,
    request_id: str,
    dry_run: bool = True,
    order_no: Optional[str] = None,
    mark_order_refunded: bool = False,
) -> AdjustmentResult:
    _validate_write_params(reason=reason, admin_email=admin_email, request_id=request_id)
    admin_norm = _normalize_email(admin_email)
    user = _require_user(db, email)

    grant_path = grant_audit_log_path()
    adjustment_path = adjustment_audit_log_path()

    if not dry_run and _adjustment_request_id_exists(adjustment_path, request_id):
        raise ManualVipAdjustmentError("duplicate_request_id", f"request_id 已存在：{request_id}")

    grant = _find_grant_for_rollback(grant_path, adjustment_path, email=email, order_no=order_no)
    related_order_no = str(grant.get("order_no") or "")
    related_grant_id = str(grant.get("manual_grant_id") or "")

    order = get_order_by_no(db, related_order_no)
    if not order:
        raise ManualVipAdjustmentError("order_not_found", f"订单不存在：{related_order_no}")
    _validate_manual_order(order)

    vip_before = _snapshot(user)
    vip_after = VipSnapshot(
        vip_expire_at=grant.get("vip_expire_at_before"),
        is_lifetime_vip=int(grant.get("is_lifetime_vip_before") or 0),
        is_vip=False,
    )
    if vip_after.is_lifetime_vip:
        vip_after.is_vip = True
    elif vip_after.vip_expire_at and vip_after.vip_expire_at > int(time.time()):
        vip_after.is_vip = True

    order_status_before = order.status
    order_status_after = order.status
    warnings: list[str] = []
    if mark_order_refunded:
        order_status_after = "refunded"

    preview = AdjustmentPreview(
        action=ROLLBACK_ACTION,
        target_user_email=user.email,
        target_user_id=user.id,
        vip_before=vip_before,
        vip_after=vip_after,
        related_order_no=related_order_no,
        related_manual_grant_id=related_grant_id,
        related_request_id=grant.get("request_id"),
        order_status_before=order_status_before,
        order_status_after=order_status_after,
        warnings=warnings,
    )

    if dry_run:
        return AdjustmentResult(preview=preview, adjustment_audit_path=adjustment_path, warnings=warnings)

    _apply_vip_snapshot(user, vip_after)
    db.add(user)

    if mark_order_refunded:
        order_status_before, order_status_after = _mark_order_refunded(db, order)

    db.commit()
    db.refresh(user)

    record: dict[str, Any] = {
        "adjustment_id": str(uuid.uuid4()),
        "source": "manual_vip_adjustment",
        "action": ROLLBACK_ACTION,
        "created_at": int(time.time()),
        "admin_email": admin_norm,
        "target_user_email": user.email,
        "target_user_id": user.id,
        "related_order_no": related_order_no,
        "related_manual_grant_id": related_grant_id,
        "related_request_id": grant.get("request_id"),
        "reason": reason.strip(),
        "vip_expire_at_before": vip_before.vip_expire_at,
        "vip_expire_at_after": vip_after.vip_expire_at,
        "is_lifetime_vip_before": vip_before.is_lifetime_vip,
        "is_lifetime_vip_after": vip_after.is_lifetime_vip,
        "order_status_before": order_status_before,
        "order_status_after": order_status_after,
        "dry_run": False,
        "force": False,
        "warnings": warnings,
        "request_id": request_id,
    }
    _append_adjustment_audit(adjustment_path, record)

    preview.vip_after = _snapshot(user)
    return AdjustmentResult(preview=preview, adjustment_audit_path=adjustment_path, warnings=warnings)


def revoke_vip(
    db: Session,
    *,
    email: str,
    reason: str,
    admin_email: str,
    request_id: str,
    dry_run: bool = True,
    force: bool = False,
    order_no: Optional[str] = None,
    mark_order_refunded: bool = False,
) -> AdjustmentResult:
    _validate_write_params(reason=reason, admin_email=admin_email, request_id=request_id)
    admin_norm = _normalize_email(admin_email)
    user = _require_user(db, email)

    adjustment_path = adjustment_audit_log_path()
    if not dry_run and _adjustment_request_id_exists(adjustment_path, request_id):
        raise ManualVipAdjustmentError("duplicate_request_id", f"request_id 已存在：{request_id}")

    warnings: list[str] = []
    if user.is_lifetime_vip and not force:
        raise ManualVipAdjustmentError(
            "lifetime_force_required",
            "目标用户为终身会员，撤销 VIP 需加 --force",
        )
    if user.is_lifetime_vip and force:
        warnings.append("lifetime_force_used")

    now = int(time.time())
    vip_before = _snapshot(user)
    vip_after = VipSnapshot(vip_expire_at=now, is_lifetime_vip=0, is_vip=False)

    related_order_no: Optional[str] = None
    order_status_before: Optional[str] = None
    order_status_after: Optional[str] = None

    if order_no:
        order = get_order_by_no(db, order_no)
        if not order:
            raise ManualVipAdjustmentError("order_not_found", f"订单不存在：{order_no}")
        if order.user_id != user.id:
            raise ManualVipAdjustmentError("order_owner_mismatch", f"订单 {order_no} 不属于该用户")
        _validate_manual_order(order)
        related_order_no = order.order_no
        order_status_before = order.status
        order_status_after = order.status
        if mark_order_refunded:
            order_status_after = "refunded"

    preview = AdjustmentPreview(
        action=REVOKE_ACTION,
        target_user_email=user.email,
        target_user_id=user.id,
        vip_before=vip_before,
        vip_after=vip_after,
        related_order_no=related_order_no,
        related_manual_grant_id=None,
        related_request_id=None,
        order_status_before=order_status_before,
        order_status_after=order_status_after,
        warnings=warnings,
    )

    if dry_run:
        return AdjustmentResult(preview=preview, adjustment_audit_path=adjustment_path, warnings=warnings)

    _apply_vip_snapshot(user, vip_after)
    db.add(user)

    if mark_order_refunded and related_order_no:
        order = get_order_by_no(db, related_order_no)
        if order:
            order_status_before, order_status_after = _mark_order_refunded(db, order)

    db.commit()
    db.refresh(user)

    record: dict[str, Any] = {
        "adjustment_id": str(uuid.uuid4()),
        "source": "manual_vip_adjustment",
        "action": REVOKE_ACTION,
        "created_at": now,
        "admin_email": admin_norm,
        "target_user_email": user.email,
        "target_user_id": user.id,
        "related_order_no": related_order_no,
        "related_manual_grant_id": None,
        "related_request_id": None,
        "reason": reason.strip(),
        "vip_expire_at_before": vip_before.vip_expire_at,
        "vip_expire_at_after": vip_after.vip_expire_at,
        "is_lifetime_vip_before": vip_before.is_lifetime_vip,
        "is_lifetime_vip_after": vip_after.is_lifetime_vip,
        "order_status_before": order_status_before,
        "order_status_after": order_status_after,
        "dry_run": False,
        "force": bool(force),
        "warnings": warnings,
        "request_id": request_id,
    }
    _append_adjustment_audit(adjustment_path, record)

    preview.vip_after = _snapshot(user)
    return AdjustmentResult(preview=preview, adjustment_audit_path=adjustment_path, warnings=warnings)


def _append_adjustment_audit(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
