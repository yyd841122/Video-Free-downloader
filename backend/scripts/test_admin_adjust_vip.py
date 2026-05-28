"""Manual VIP adjustment CLI / service tests (isolated SQLite, no network).

Usage:
    cd backend
    python scripts/test_admin_adjust_vip.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB_PATH = BACKEND_DIR / "data" / f"test_admin_adjust_{uuid.uuid4().hex[:8]}.db"
GRANT_AUDIT_PATH = BACKEND_DIR / "data" / f"test_grant_audit_{uuid.uuid4().hex[:8]}.jsonl"
ADJUST_AUDIT_PATH = BACKEND_DIR / "data" / f"test_adjust_audit_{uuid.uuid4().hex[:8]}.jsonl"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["MANUAL_GRANT_AUDIT_PATH"] = str(GRANT_AUDIT_PATH)
os.environ["MANUAL_VIP_ADJUSTMENT_AUDIT_PATH"] = str(ADJUST_AUDIT_PATH)
os.environ["JWT_SECRET"] = "test-secret-key-for-admin-adjust"

from app.db.database import init_db, session_scope  # noqa: E402
from app.db.models import Order  # noqa: E402
from app.services.manual_grant_service import VipSnapshot, grant_vip_manual  # noqa: E402
from app.services.manual_vip_adjustment_service import (  # noqa: E402
    ManualVipAdjustmentError,
    list_manual_grants,
    revoke_vip,
    rollback_last_manual_grant,
)
from app.services.plan_service import seed_default_plans  # noqa: E402
from app.services.user_service import create_user, get_user_by_email  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"


def assert_true(cond: bool, label: str) -> None:
    if cond:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}")
        raise AssertionError(label)


def assert_eq(actual, expected, label: str) -> None:
    if actual == expected:
        print(f"  {PASS} {label}: {actual!r}")
    else:
        print(f"  {FAIL} {label}: 期望 {expected!r}, 实际 {actual!r}")
        raise AssertionError(label)


def assert_raises(code: str, fn, label: str) -> None:
    try:
        fn()
    except ManualVipAdjustmentError as exc:
        if exc.error_code == code:
            print(f"  {PASS} {label}: {code}")
            return
        print(f"  {FAIL} {label}: 期望 {code}, 实际 {exc.error_code}")
        raise
    print(f"  {FAIL} {label}: 未抛出 ManualVipAdjustmentError")
    raise AssertionError(label)


def _user_snapshot(email: str) -> VipSnapshot:
    with session_scope() as db:
        user = get_user_by_email(db, email)
        assert user is not None
        return VipSnapshot(
            vip_expire_at=user.vip_expire_at,
            is_lifetime_vip=int(user.is_lifetime_vip or 0),
            is_vip=bool(user.is_vip),
        )


def _grant(email: str, request_id: str) -> str:
    with session_scope() as db:
        result = grant_vip_manual(
            db,
            email=email,
            plan_code="monthly",
            reason="test grant",
            admin_email="admin@cozyguidehub.com",
            dry_run=False,
            request_id=request_id,
        )
        return result.order_no


def main() -> int:
    print("SaveAny manual VIP adjustment tests\n")
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    for p in (GRANT_AUDIT_PATH, ADJUST_AUDIT_PATH):
        if p.exists():
            p.unlink()

    init_db()
    seed_default_plans()

    suffix = uuid.uuid4().hex[:8]
    user_email = f"adjust_user_{suffix}@cozyguidehub.com"
    missing_email = f"missing_{suffix}@cozyguidehub.com"
    life_email = f"adjust_life_{suffix}@cozyguidehub.com"

    with session_scope() as db:
        create_user(db, user_email, "secret123")
        create_user(db, life_email, "secret123")
        u = get_user_by_email(db, life_email)
        u.is_lifetime_vip = 1
        db.add(u)

    grant_rid = f"grant-{suffix}"
    order_no = _grant(user_email, grant_rid)

    print("[1] list-grants 不存在用户 → fail")

    def _list_missing():
        with session_scope() as db:
            list_manual_grants(db, email=missing_email)

    assert_raises("user_not_found", _list_missing, "user_not_found")

    print("\n[2] list-grants 存在用户 → 有记录")
    with session_scope() as db:
        views = list_manual_grants(db, email=user_email, limit=10)
    assert_true(len(views) >= 1, "至少 1 条 grant")
    assert_eq(views[0].order_no, order_no, "order_no 匹配")
    assert_eq(views[0].rolled_back, False, "未 rollback")

    print("\n[3] rollback dry-run → 不写库")
    snap_before = _user_snapshot(user_email)
    assert_true(snap_before.is_vip, "rollback 前是 VIP")

    def _rollback_dry():
        with session_scope() as db:
            return rollback_last_manual_grant(
                db,
                email=user_email,
                reason="dry rollback",
                admin_email="admin@cozyguidehub.com",
                request_id=f"adjust-dry-{suffix}",
                dry_run=True,
            )

    _rollback_dry()
    snap_after_dry = _user_snapshot(user_email)
    assert_true(snap_after_dry.is_vip, "dry-run 后仍是 VIP")
    assert_true(not ADJUST_AUDIT_PATH.exists() or ADJUST_AUDIT_PATH.read_text().strip() == "", "dry-run 无 adjustment audit")

    print("\n[4] rollback confirm → 恢复 before")
    with session_scope() as db:
        rollback_last_manual_grant(
            db,
            email=user_email,
            reason="rollback test",
            admin_email="admin@cozyguidehub.com",
            request_id=f"adjust-rb-{suffix}",
            dry_run=False,
            mark_order_refunded=True,
        )
    snap_rolled = _user_snapshot(user_email)
    assert_eq(snap_rolled.is_vip, False, "rollback 后非 VIP")
    assert_eq(snap_rolled.vip_expire_at, None, "expire 恢复 null")

    with session_scope() as db:
        views = list_manual_grants(db, email=user_email)
    assert_eq(views[0].rolled_back, True, "标记已 rollback")

    with session_scope() as db:
        order = db.query(Order).filter(Order.order_no == order_no).one()
        assert_eq(order.status, "refunded", "订单 refunded")

    print("\n[5] rollback 同一 grant 两次 → already_rolled_back")

    def _rollback_twice():
        with session_scope() as db:
            rollback_last_manual_grant(
                db,
                email=user_email,
                reason="dup",
                admin_email="admin@cozyguidehub.com",
                request_id=f"adjust-rb2-{suffix}",
                dry_run=False,
                order_no=order_no,
            )

    assert_raises("already_rolled_back", _rollback_twice, "already_rolled_back")

    print("\n[6] rollback 非 manual 订单（Stripe session）→ not_manual_order")
    bad_man_no = f"MAN{int(time.time())}STRIPEFAKE"
    with session_scope() as db:
        user = get_user_by_email(db, user_email)
        assert user is not None
        user_id = user.id
        db.add(
            Order(
                order_no=bad_man_no,
                user_id=user_id,
                plan_code="monthly",
                plan_name="月度会员",
                amount_cents=1900,
                currency="cny",
                status="paid",
                is_mock=0,
                vip_granted_days=30,
                stripe_session_id="cs_test_fake",
                stripe_event_id="manual-grant-fake-id",
                paid_at=int(time.time()),
            )
        )
        db.commit()
    with GRANT_AUDIT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "manual_grant_id": str(uuid.uuid4()),
                    "source": "manual_grant",
                    "created_at": int(time.time()) + 1,
                    "admin_email": "admin@cozyguidehub.com",
                    "target_user_email": user_email,
                    "target_user_id": user_id,
                    "plan_code": "monthly",
                    "vip_granted_days": 30,
                    "reason": "fake stripe man",
                    "order_no": bad_man_no,
                    "amount_cents": 1900,
                    "vip_expire_at_before": None,
                    "vip_expire_at_after": int(time.time()) + 86400,
                    "is_lifetime_vip_before": 0,
                    "is_lifetime_vip_after": 0,
                    "dry_run": False,
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    def _rollback_stripe_man():
        with session_scope() as db:
            rollback_last_manual_grant(
                db,
                email=user_email,
                reason="bad",
                admin_email="admin@cozyguidehub.com",
                request_id=f"adjust-stripe-{suffix}",
                dry_run=True,
                order_no=bad_man_no,
            )

    assert_raises("not_manual_order", _rollback_stripe_man, "not_manual_order")

    print("\n[7] revoke 普通 VIP dry-run")
    user2 = f"adjust_revoke_{suffix}@cozyguidehub.com"
    with session_scope() as db:
        create_user(db, user2, "secret123")
    _grant(user2, f"grant2-{suffix}")

    def _revoke_dry():
        with session_scope() as db:
            revoke_vip(
                db,
                email=user2,
                reason="dry revoke",
                admin_email="admin@cozyguidehub.com",
                request_id=f"adjust-rev-dry-{suffix}",
                dry_run=True,
            )

    _revoke_dry()
    assert_true(_user_snapshot(user2).is_vip, "dry-run revoke 仍 VIP")

    print("\n[8] revoke 普通 VIP confirm → 非 VIP")
    with session_scope() as db:
        revoke_vip(
            db,
            email=user2,
            reason="revoke test",
            admin_email="admin@cozyguidehub.com",
            request_id=f"adjust-rev-{suffix}",
            dry_run=False,
        )
    snap_revoked = _user_snapshot(user2)
    assert_eq(snap_revoked.is_vip, False, "revoke 后非 VIP")
    assert_eq(snap_revoked.is_lifetime_vip, 0, "非终身")

    print("\n[9] revoke lifetime 无 force → fail")

    def _revoke_life_no_force():
        with session_scope() as db:
            revoke_vip(
                db,
                email=life_email,
                reason="no force",
                admin_email="admin@cozyguidehub.com",
                request_id=f"adjust-life-fail-{suffix}",
                dry_run=True,
            )

    assert_raises("lifetime_force_required", _revoke_life_no_force, "lifetime_force_required")

    print("\n[10] revoke lifetime + force → success")
    with session_scope() as db:
        revoke_vip(
            db,
            email=life_email,
            reason="force revoke",
            admin_email="admin@cozyguidehub.com",
            request_id=f"adjust-life-ok-{suffix}",
            dry_run=False,
            force=True,
        )
    assert_eq(_user_snapshot(life_email).is_lifetime_vip, 0, "lifetime 已清除")

    print("\n[11] request-id 重复 → fail")
    dup_rid = f"adjust-dup-{suffix}"
    user3 = f"adjust_dup_{suffix}@cozyguidehub.com"
    with session_scope() as db:
        create_user(db, user3, "secret123")
    with session_scope() as db:
        revoke_vip(
            db,
            email=user3,
            reason="first",
            admin_email="admin@cozyguidehub.com",
            request_id=dup_rid,
            dry_run=False,
        )

    def _dup_request():
        with session_scope() as db:
            revoke_vip(
                db,
                email=user3,
                reason="dup",
                admin_email="admin@cozyguidehub.com",
                request_id=dup_rid,
                dry_run=False,
            )

    assert_raises("duplicate_request_id", _dup_request, "duplicate_request_id")

    print("\n[12] adjustment audit 字段完整")
    lines = [ln for ln in ADJUST_AUDIT_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert_true(len(lines) >= 2, "有多条 adjustment")
    last = json.loads(lines[-1])
    for key in (
        "adjustment_id",
        "source",
        "action",
        "admin_email",
        "target_user_email",
        "reason",
        "vip_expire_at_before",
        "vip_expire_at_after",
        "is_lifetime_vip_before",
        "is_lifetime_vip_after",
        "dry_run",
        "request_id",
    ):
        assert_true(key in last, f"audit 含 {key}")
    assert_eq(last["source"], "manual_vip_adjustment", "source")

    print(f"\n{PASS} 全部 adjustment 测试通过")
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
        GRANT_AUDIT_PATH.unlink(missing_ok=True)
        ADJUST_AUDIT_PATH.unlink(missing_ok=True)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError:
        raise SystemExit(1)
