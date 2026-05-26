"""Manual VIP grant CLI / service tests (isolated SQLite, no network).

Usage:
    cd backend
    python scripts/test_admin_grant_vip.py
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

TEST_DB_PATH = BACKEND_DIR / "data" / f"test_admin_grant_{uuid.uuid4().hex[:8]}.db"
AUDIT_PATH = BACKEND_DIR / "data" / f"test_audit_{uuid.uuid4().hex[:8]}.jsonl"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["MANUAL_GRANT_AUDIT_PATH"] = str(AUDIT_PATH)
os.environ["JWT_SECRET"] = "test-secret-key-for-admin-grant"

from app.core.security import hash_password  # noqa: E402
from app.db.database import init_db, session_scope  # noqa: E402
from app.db.models import Order, User  # noqa: E402
from app.services.manual_grant_service import ManualGrantError, VipSnapshot, grant_vip_manual  # noqa: E402
from app.services.plan_service import seed_default_plans  # noqa: E402
from app.services.user_service import create_user  # noqa: E402

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
    except ManualGrantError as exc:
        if exc.error_code == code:
            print(f"  {PASS} {label}: {code}")
            return
        print(f"  {FAIL} {label}: 期望 {code}, 实际 {exc.error_code}")
        raise
    print(f"  {FAIL} {label}: 未抛出 ManualGrantError")
    raise AssertionError(label)


def _create_user(db, email: str) -> User:
    return create_user(db, email, "secret123", nickname="test")


def _grant(**kwargs):
    with session_scope() as db:
        return grant_vip_manual(db, **kwargs)


def _count_orders() -> int:
    with session_scope() as db:
        return db.query(Order).count()


def _user_snapshot(email: str) -> VipSnapshot:
    with session_scope() as db:
        from app.services.user_service import get_user_by_email

        user = get_user_by_email(db, email)
        assert user is not None
        return VipSnapshot(
            vip_expire_at=user.vip_expire_at,
            is_lifetime_vip=int(user.is_lifetime_vip or 0),
            is_vip=bool(user.is_vip),
        )


def main() -> int:
    print("SaveAny manual VIP grant tests\n")
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if AUDIT_PATH.exists():
        AUDIT_PATH.unlink()

    init_db()
    seed_default_plans()

    suffix = uuid.uuid4().hex[:8]
    missing_email = f"missing_{suffix}@cozyguidehub.com"
    user_a_email = f"grant_a_{suffix}@cozyguidehub.com"
    vip_active_email = f"grant_vip_{suffix}@cozyguidehub.com"
    lifetime_email = f"grant_life_{suffix}@cozyguidehub.com"

    with session_scope() as db:
        _create_user(db, user_a_email)
        _create_user(db, vip_active_email)
        _create_user(db, lifetime_email)

    with session_scope() as db:
        from app.services.user_service import get_user_by_email

        u = get_user_by_email(db, vip_active_email)
        now = int(time.time())
        u.vip_expire_at = now + 10 * 86400
        db.add(u)
        db.commit()

    with session_scope() as db:
        from app.services.user_service import get_user_by_email

        u = get_user_by_email(db, lifetime_email)
        u.is_lifetime_vip = 1
        db.add(u)
        db.commit()

    print("[1] 不存在用户 → fail")
    assert_raises(
        "user_not_found",
        lambda: _grant(
            email=missing_email,
            plan_code="monthly",
            reason="test",
            admin_email="admin@cozyguidehub.com",
            dry_run=True,
        ),
        "user_not_found",
    )

    print("\n[2] 非法邮箱 → fail")
    assert_raises(
        "invalid_email",
        lambda: _grant(
            email="not-an-email",
            plan_code="monthly",
            reason="test",
            admin_email="admin@cozyguidehub.com",
            dry_run=True,
        ),
        "invalid_email",
    )

    print("\n[3] 非法 plan → fail")
    assert_raises(
        "invalid_plan",
        lambda: _grant(
            email=user_a_email,
            plan_code="weekly",
            reason="test",
            admin_email="admin@cozyguidehub.com",
            dry_run=True,
        ),
        "invalid_plan",
    )

    orders_before = _count_orders()

    print("\n[4] dry-run 不写数据库")
    _grant(
        email=user_a_email,
        plan_code="monthly",
        reason="dry",
        admin_email="admin@cozyguidehub.com",
        dry_run=True,
    )
    assert_eq(_count_orders(), orders_before, "订单数不变")
    assert_true(not AUDIT_PATH.exists() or AUDIT_PATH.read_text(encoding="utf-8").strip() == "", "dry-run 不写审计")

    print("\n[5] monthly 给非 VIP → now + 30 天")
    before = _user_snapshot(user_a_email)
    assert_eq(before.is_vip, False, "开通前非 VIP")
    result = _grant(
        email=user_a_email,
        plan_code="monthly",
        reason="wechat",
        admin_email="admin@cozyguidehub.com",
        dry_run=False,
    )
    after = _user_snapshot(user_a_email)
    assert_true(after.is_vip, "开通后 is_vip")
    assert_true(after.vip_expire_at is not None, "有到期时间")
    now = int(time.time())
    assert_true(after.vip_expire_at > now + 29 * 86400, "约 +30 天")
    assert_true(result.order_no.startswith("MAN"), "人工订单号 MAN*")
    with session_scope() as db:
        order = db.query(Order).filter(Order.order_no == result.order_no).one()
        assert_eq(order.status, "paid", "订单 paid")
        assert_eq(order.is_mock, 0, "is_mock=0")
        assert_true(order.stripe_event_id.startswith("manual-grant-"), "stripe_event_id 标记")

    print("\n[6] monthly 给未过期 VIP → 原到期 + 30 天")
    expire_before = after.vip_expire_at
    result2 = _grant(
        email=user_a_email,
        plan_code="monthly",
        reason="stack",
        admin_email="admin@cozyguidehub.com",
        dry_run=False,
    )
    after2 = _user_snapshot(user_a_email)
    assert_true(after2.vip_expire_at - expire_before >= 29 * 86400, "叠加约 30 天")

    print("\n[7] yearly 新用户 → +365 天")
    yearly_email = f"grant_y_{uuid.uuid4().hex[:6]}@cozyguidehub.com"
    with session_scope() as db:
        _create_user(db, yearly_email)
    _grant(
        email=yearly_email,
        plan_code="yearly",
        reason="year",
        admin_email="admin@cozyguidehub.com",
        dry_run=False,
    )
    u_y = _user_snapshot(yearly_email)
    assert_true(u_y.vip_expire_at > now + 364 * 86400, "yearly +365d")

    print("\n[8] lifetime → is_lifetime_vip = 1")
    life_new = f"grant_ln_{uuid.uuid4().hex[:6]}@cozyguidehub.com"
    with session_scope() as db:
        _create_user(db, life_new)
    _grant(
        email=life_new,
        plan_code="lifetime",
        reason="lifetime buy",
        admin_email="admin@cozyguidehub.com",
        dry_run=False,
    )
    u_l = _user_snapshot(life_new)
    assert_eq(u_l.is_lifetime_vip, 1, "终身标记")
    assert_true(u_l.is_vip, "终身 is_vip")

    print("\n[9] 审计日志字段完整")
    assert_true(AUDIT_PATH.is_file(), "审计文件存在")
    lines = [ln for ln in AUDIT_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert_true(len(lines) >= 4, "有多条审计")
    last = json.loads(lines[-1])
    for key in (
        "manual_grant_id",
        "source",
        "admin_email",
        "target_user_email",
        "target_user_id",
        "plan_code",
        "reason",
        "order_no",
        "vip_expire_at_before",
        "vip_expire_at_after",
        "is_lifetime_vip_before",
        "is_lifetime_vip_after",
        "dry_run",
    ):
        assert_true(key in last, f"审计含 {key}")
    assert_eq(last["source"], "manual_grant", "source")
    assert_eq(last["dry_run"], False, "dry_run false on confirm")

    print("\n[10] lifetime 用户发 monthly 默认 fail")
    assert_raises(
        "lifetime_force_required",
        lambda: _grant(
            email=lifetime_email,
            plan_code="monthly",
            reason="should fail",
            admin_email="admin@cozyguidehub.com",
            dry_run=False,
        ),
        "lifetime_force_required",
    )

    print("\n[11] lifetime 用户发 monthly + --force 允许")
    orders_before_force = _count_orders()
    _grant(
        email=lifetime_email,
        plan_code="monthly",
        reason="force stack",
        admin_email="admin@cozyguidehub.com",
        dry_run=False,
        force=True,
    )
    assert_true(_count_orders() > orders_before_force, "force 后新增订单")
    u_force = _user_snapshot(lifetime_email)
    assert_eq(u_force.is_lifetime_vip, 1, "force 后仍终身")

    print("\n[12] request-id 重复拒绝")
    rid = f"req-{uuid.uuid4().hex[:8]}"
    dup_email = f"grant_dup_{uuid.uuid4().hex[:6]}@cozyguidehub.com"
    with session_scope() as db:
        _create_user(db, dup_email)
    _grant(
        email=dup_email,
        plan_code="monthly",
        reason="first",
        admin_email="admin@cozyguidehub.com",
        dry_run=False,
        request_id=rid,
    )
    assert_raises(
        "duplicate_request_id",
        lambda: _grant(
            email=dup_email,
            plan_code="monthly",
            reason="dup",
            admin_email="admin@cozyguidehub.com",
            dry_run=False,
            request_id=rid,
        ),
        "duplicate_request_id",
    )

    print("\n[13] mark_order_paid 幂等：同订单不重复发")
    with session_scope() as db:
        from app.services.order_service import get_order_by_no, mark_order_paid

        order = get_order_by_no(db, result.order_no)
        changed = mark_order_paid(db, order)
        assert_eq(changed, False, "已 paid 订单幂等")

    print(f"\n{PASS} 全部 manual grant 测试通过")
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
        AUDIT_PATH.unlink(missing_ok=True)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError:
        raise SystemExit(1)
