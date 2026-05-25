"""Billing & membership end-to-end test (no internet, pure local Mock mode).

Usage:
    cd backend
    python scripts/test_billing.py

Covered cases (1..13):
1) Register / Login
2) Fetch plan list
3) Unauthorized access -> 401
4) Create order -> Mock pay success -> user becomes VIP
5) Pay same order twice -> idempotent, no double credit
6) Renewal stacks duration on existing VIP expiry
7) Lifetime purchase -> is_lifetime_vip = 1
8) AI quota: free user 3/day, 4th call returns 402
9) 720p gate: free user requesting 1080p -> blocked
10) Webhook idempotency: duplicate event ignored
11) Amount tamper rejected by webhook
12) Mock cancel path
13) Wrong plan code / wrong owner -> 400/404
14) GET /users/me/quota
15) Per-user concurrent download limit
16) AI chat per-task limit (free 5)
17) P0 hardening: is_mock_mode() refuses to fallback in APP_ENV=production
18) P0 hardening: _validate_production_config() fails fast on missing keys
19) P0 hardening: webhook metadata.plan_code mismatch is rejected
20) P0 hardening: async_payment_succeeded grants VIP; async_payment_failed cancels pending
21) P0 hardening: ENABLE_MOCK_PAY_ROUTE controls route registration
22) resume-checkout: pending Stripe order resumes without creating new order
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import uuid
from pathlib import Path

# Force stdout to UTF-8 on Windows so checkmarks render correctly
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

THIS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = THIS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# 让测试库不污染主 db 文件
TEST_DB_PATH = BACKEND_DIR / "data" / f"test_billing_{uuid.uuid4().hex[:8]}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["MOCK_PAYMENT"] = "true"
os.environ["JWT_SECRET"] = "test-secret-key-for-billing"
os.environ["FREE_AI_SUMMARY_PER_DAY"] = "3"

# 必须在设置环境变量之后导入 app
from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import init_db, session_scope  # noqa: E402
from app.db.models import AiUsage, Order, User, WebhookEvent  # noqa: E402
from app.main import app  # noqa: E402
from app.services.plan_service import seed_default_plans  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"


def assert_eq(actual, expected, label):
    if actual == expected:
        print(f"  {PASS} {label}: {actual!r}")
    else:
        print(f"  {FAIL} {label}: 期望 {expected!r}, 实际 {actual!r}")
        raise AssertionError(label)


def assert_true(cond, label):
    if cond:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}")
        raise AssertionError(label)


def main() -> None:
    print(f"{INFO} 使用临时数据库：{TEST_DB_PATH}")
    init_db()
    seed_default_plans()

    with TestClient(app) as client:
        run_all(client)

    print(f"\n{PASS} 全部测试通过 🎉")
    # 清理测试库
    try:
        TEST_DB_PATH.unlink()
        for ext in ("-shm", "-wal"):
            p = Path(str(TEST_DB_PATH) + ext)
            if p.exists():
                p.unlink()
    except OSError:
        pass


def run_all(client) -> None:
    # ============== 1. 注册 & 登录 ==============
    print("\n[1] 注册 & 登录")
    email = f"alice+{uuid.uuid4().hex[:6]}@example.com"
    password = "secret123"

    r = client.post("/api/users/register", json={"email": email, "password": password})
    assert_eq(r.status_code, 200, "注册接口返回 200")
    token = r.json()["access_token"]
    user_payload = r.json()["user"]
    assert_eq(user_payload["email"], email, "返回用户邮箱一致")
    assert_eq(user_payload["is_vip"], False, "新用户默认非 VIP")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/users/login", json={"email": email, "password": password})
    assert_eq(r.status_code, 200, "登录接口返回 200")

    r = client.post("/api/users/login", json={"email": email, "password": "wrong"})
    assert_eq(r.status_code, 401, "错误密码登录返回 401")

    # ============== 2. 套餐列表 ==============
    print("\n[2] 套餐列表")
    r = client.get("/api/billing/plans")
    assert_eq(r.status_code, 200, "套餐列表 200")
    plans = r.json()
    plan_codes = [p["code"] for p in plans]
    assert_true(set(plan_codes) >= {"monthly", "quarterly", "yearly", "lifetime"}, "套餐包含 4 档")
    monthly = next(p for p in plans if p["code"] == "monthly")
    assert_eq(monthly["price_cents"], 1900, "月度套餐价格 = 1900 分")

    r = client.get("/api/billing/mode")
    assert_eq(r.status_code, 200, "billing/mode 200")
    assert_eq(r.json()["mock"], True, "当前为 mock 模式")

    # ============== 3. 未登录访问受保护接口 ==============
    print("\n[3] 未登录访问受保护接口")
    r = client.post("/api/billing/checkout", json={"plan_code": "monthly"})
    assert_eq(r.status_code, 401, "未登录创建订单返回 401")
    r = client.get("/api/users/me")
    assert_eq(r.status_code, 401, "未登录 /users/me 返回 401")

    # ============== 4. 创建月度订单 + Mock 支付成功 ==============
    print("\n[4] 创建月度订单 + Mock 支付")
    r = client.post("/api/billing/checkout", json={"plan_code": "monthly"}, headers=headers)
    assert_eq(r.status_code, 200, "创建订单 200")
    body = r.json()
    assert_eq(body["mode"], "mock", "checkout 模式为 mock")
    assert_true("/mock-pay" in body["checkout_url"], "返回 mock 支付页 URL")
    order_no = body["order_no"]

    r = client.post(f"/api/billing/mock/pay/{order_no}", json={"outcome": "success"}, headers=headers)
    assert_eq(r.status_code, 200, "Mock 支付成功 200")
    assert_eq(r.json()["status"], "paid", "订单状态变为 paid")

    r = client.get("/api/users/me", headers=headers)
    user_info = r.json()
    assert_eq(user_info["is_vip"], True, "用户已成为 VIP")
    vip_expire_1 = user_info["vip_expire_at"]
    assert_true(vip_expire_1 > int(time.time()) + 29 * 86400, "VIP 到期时间约为 +30 天")

    # ============== 5. 重复 Mock 支付同订单 → 幂等 ==============
    print("\n[5] 重复支付同订单 (幂等)")
    r = client.post(f"/api/billing/mock/pay/{order_no}", json={"outcome": "success"}, headers=headers)
    assert_eq(r.status_code, 200, "重复支付仍 200（无副作用）")
    r = client.get("/api/users/me", headers=headers)
    assert_eq(r.json()["vip_expire_at"], vip_expire_1, "VIP 到期时间未被重复累加")

    # ============== 6. 续费叠加：VIP 期内再买季度 ==============
    print("\n[6] 续费叠加")
    r = client.post("/api/billing/checkout", json={"plan_code": "quarterly"}, headers=headers)
    order_no2 = r.json()["order_no"]
    client.post(f"/api/billing/mock/pay/{order_no2}", json={"outcome": "success"}, headers=headers)
    r = client.get("/api/users/me", headers=headers)
    vip_expire_2 = r.json()["vip_expire_at"]
    assert_true(
        vip_expire_2 - vip_expire_1 >= 89 * 86400,
        "续费 90 天后到期时间累加（差值 ≥ 89 天）",
    )

    # ============== 7. 终身会员 ==============
    print("\n[7] 终身会员")
    r = client.post("/api/billing/checkout", json={"plan_code": "lifetime"}, headers=headers)
    order_no3 = r.json()["order_no"]
    client.post(f"/api/billing/mock/pay/{order_no3}", json={"outcome": "success"}, headers=headers)
    r = client.get("/api/users/me", headers=headers)
    assert_eq(r.json()["is_lifetime_vip"], True, "is_lifetime_vip = True")
    assert_eq(r.json()["is_vip"], True, "终身会员 is_vip = True")

    # ============== 8. 订单列表查询 ==============
    print("\n[8] 订单列表")
    r = client.get("/api/billing/orders", headers=headers)
    assert_eq(r.status_code, 200, "订单列表 200")
    items = r.json()["items"]
    assert_eq(len(items), 3, "共 3 条订单")
    assert_eq(items[0]["plan_code"], "lifetime", "按时间倒序，最新是 lifetime")

    # ============== 9. AI 配额：用新免费用户验证 ==============
    print("\n[9] 免费用户 AI 总结每天 3 次限额")
    free_email = f"bob+{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/users/register", json={"email": free_email, "password": "secret123"})
    free_token = r.json()["access_token"]
    free_headers = {"Authorization": f"Bearer {free_token}"}
    free_user_id = r.json()["user"]["id"]

    # 由于真正调用 /api/ai/summary 会触发 yt-dlp 子进程，这里直接调内部配额服务
    from app.services.quota_service import QuotaExceededError, consume_ai_quota, get_quota

    with session_scope() as db:
        user = db.get(User, free_user_id)
        info = get_quota(db, user)
        assert_eq(info.ai_daily_limit, 3, "免费用户每日限额 = 3")
        for i in range(3):
            consume_ai_quota(db, user)
        ok = False
        try:
            consume_ai_quota(db, user)
        except QuotaExceededError:
            ok = True
        assert_true(ok, "第 4 次调用抛 QuotaExceededError")

    # ============== 10. 分辨率门禁 ==============
    print("\n[10] 免费用户 1080p 下载被拦截")
    from app.services.quota_service import check_resolution_allowed

    with session_scope() as db:
        free_user = db.get(User, free_user_id)
        # 720p 不会被拒
        check_resolution_allowed(free_user, 720)
        # 1080p 必须被拒
        ok = False
        try:
            check_resolution_allowed(free_user, 1080)
        except QuotaExceededError:
            ok = True
        assert_true(ok, "1080p 触发 QuotaExceededError")
        # 给免费用户人工置为 vip 测试解锁
        free_user.is_lifetime_vip = 1
        db.add(free_user)
    with session_scope() as db:
        free_user = db.get(User, free_user_id)
        check_resolution_allowed(free_user, 2160)  # 4K 不抛
        # 还原
        free_user.is_lifetime_vip = 0
        db.add(free_user)
    print(f"  {PASS} 升级 VIP 后 4K 可下载")

    # ============== 11. Webhook 幂等 + 签名安全 ==============
    print("\n[11] Webhook 幂等 + 金额校验")
    # 构造一个非 mock 的订单用于模拟 Stripe webhook
    with session_scope() as db:
        user = db.get(User, free_user_id)
        order = Order(
            order_no=f"WEBHOOKTEST{uuid.uuid4().hex[:6]}",
            user_id=user.id,
            plan_code="monthly",
            plan_name="月度会员",
            amount_cents=1900,
            currency="cny",
            status="pending",
            stripe_session_id=f"cs_test_{uuid.uuid4().hex[:8]}",
            is_mock=0,
            vip_granted_days=30,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        webhook_order_no = order.order_no
        webhook_session_id = order.stripe_session_id

    from app.services import payment_service

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    fake_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": webhook_session_id,
                "client_reference_id": webhook_order_no,
                "payment_status": "paid",
                "amount_total": 1900,
                "currency": "cny",
                "payment_intent": "pi_test_xxxx",
                "metadata": {"order_no": webhook_order_no},
            }
        },
    }
    constructed = payment_service._ConstructedEvent(fake_event, json.dumps(fake_event).encode())

    with session_scope() as db:
        msg = payment_service.handle_stripe_event(db, constructed)
        assert_true("marked paid=True" in msg, f"首次处理事件：{msg}")
    with session_scope() as db:
        msg = payment_service.handle_stripe_event(db, constructed)
        assert_true("duplicate event" in msg, f"重复事件被去重：{msg}")
        # webhook_events 表里只有 1 条
        cnt = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).count()
        assert_eq(cnt, 1, "webhook_events 表只有 1 条记录")

    # 金额被篡改：构造同订单不同金额事件 → 应抛 PaymentError
    bad_event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": webhook_session_id,
                "client_reference_id": webhook_order_no,
                "payment_status": "paid",
                "amount_total": 1,  # 被篡改！
                "currency": "cny",
                "payment_intent": "pi_test_yyyy",
                "metadata": {"order_no": webhook_order_no},
            }
        },
    }
    bad_constructed = payment_service._ConstructedEvent(bad_event, json.dumps(bad_event).encode())
    with session_scope() as db:
        threw = False
        try:
            payment_service.handle_stripe_event(db, bad_constructed)
        except payment_service.PaymentError as exc:
            threw = "金额/币种" in str(exc) or "金额" in str(exc)
        assert_true(threw, "金额被篡改的 webhook 被拒绝")

    # ============== 12. Mock 订单的"未支付"路径 ==============
    print("\n[12] Mock 支付：用户主动取消")
    r = client.post("/api/billing/checkout", json={"plan_code": "monthly"}, headers=headers)
    cancel_order_no = r.json()["order_no"]
    r = client.post(f"/api/billing/mock/pay/{cancel_order_no}", json={"outcome": "cancel"}, headers=headers)
    assert_eq(r.json()["status"], "canceled", "用户取消订单：status=canceled")

    # ============== 13. 套餐不存在 / 非本人订单 ==============
    print("\n[13] 错误处理")
    r = client.post("/api/billing/checkout", json={"plan_code": "not_exist"}, headers=headers)
    assert_eq(r.status_code, 400, "不存在的套餐返回 400")
    r = client.get(f"/api/billing/orders/{webhook_order_no}", headers=headers)
    assert_eq(r.status_code, 404, "查询非本人订单返回 404")

    # ============== 14. 配额 API ==============
    print("\n[14] GET /api/users/me/quota")
    quota_email = f"quota+{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/users/register", json={"email": quota_email, "password": "secret123"})
    quota_user_id = r.json()["user"]["id"]
    quota_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get("/api/users/me/quota", headers=quota_headers)
    assert_eq(r.status_code, 200, "配额接口 200")
    q = r.json()
    assert_eq(q["ai_daily_limit"], 3, "quota.ai_daily_limit")
    assert_eq(q["max_concurrent"], 1, "quota.max_concurrent")
    assert_eq(q["ai_chat_per_task"], 5, "quota.ai_chat_per_task")

    # ============== 15. 按用户并发下载 ==============
    print("\n[15] 免费用户下载并发 = 1")
    from app.services.quota_service import QuotaExceededError, check_concurrent_download
    from app.services.task_store import task_store

    with session_scope() as db:
        free_user = db.get(User, quota_user_id)
        t1 = task_store.create("https://example.com/1", user_id=free_user.id)
        task_store.update(t1.task_id, status="downloading")
        ok = False
        try:
            check_concurrent_download(free_user)
        except QuotaExceededError:
            ok = True
        assert_true(ok, "第 2 个下载任务被并发限制拦截")
        task_store.update(t1.task_id, status="completed")

    # ============== 16. AI 追问轮次 ==============
    print("\n[16] 免费用户每总结 AI 追问 5 轮")
    from app.services.ai_task_store import ai_summary_task_store
    from app.services.quota_service import check_and_consume_ai_chat

    with session_scope() as db:
        free_user = db.get(User, quota_user_id)
        ai_task = ai_summary_task_store.create("https://example.com/v", user_id=free_user.id)
        ai_summary_task_store.update(ai_task.task_id, status="completed")
        for _ in range(5):
            check_and_consume_ai_chat(ai_summary_task_store.get(ai_task.task_id), free_user)
        ok = False
        try:
            check_and_consume_ai_chat(ai_summary_task_store.get(ai_task.task_id), free_user)
        except QuotaExceededError:
            ok = True
        assert_true(ok, "第 6 轮追问被拦截")

    # ============== 17. P0 硬化：is_mock_mode 生产环境硬拒 ==============
    print("\n[17] P0 硬化：APP_ENV=production 下 is_mock_mode() 拒绝 fallback")
    from app.core import config as cfg
    from app.services import payment_service as ps

    orig_app_env = cfg.APP_ENV
    orig_mock = cfg.MOCK_PAYMENT
    orig_secret = cfg.STRIPE_SECRET_KEY
    try:
        cfg.APP_ENV = "production"

        # 17.1 生产 + MOCK_PAYMENT=true → 抛 PaymentConfigurationError
        cfg.MOCK_PAYMENT = True
        cfg.STRIPE_SECRET_KEY = "sk_test_dummy_for_unit_test"
        threw = False
        try:
            ps.is_mock_mode()
        except ps.PaymentConfigurationError as exc:
            threw = "MOCK_PAYMENT" in str(exc)
        assert_true(threw, "生产 + MOCK_PAYMENT=true 抛 PaymentConfigurationError")

        # 17.2 生产 + STRIPE_SECRET_KEY 空 → 抛 PaymentConfigurationError（不再静默 fallback）
        cfg.MOCK_PAYMENT = False
        cfg.STRIPE_SECRET_KEY = ""
        threw = False
        try:
            ps.is_mock_mode()
        except ps.PaymentConfigurationError as exc:
            threw = "STRIPE_SECRET_KEY" in str(exc)
        assert_true(threw, "生产 + STRIPE_SECRET_KEY 空 抛 PaymentConfigurationError")

        # 17.3 生产 + 配齐 → 走 Stripe（False），不抛
        cfg.STRIPE_SECRET_KEY = "sk_live_dummy_for_unit_test"
        assert_eq(ps.is_mock_mode(), False, "生产 + 配齐 STRIPE 走真 Stripe（不抛）")

        # 17.4 dev + MOCK_PAYMENT=true → True（向后兼容）
        cfg.APP_ENV = "development"
        cfg.MOCK_PAYMENT = True
        cfg.STRIPE_SECRET_KEY = ""
        assert_eq(ps.is_mock_mode(), True, "development + MOCK_PAYMENT=true 仍可 mock")

        # 17.5 dev + 没 MOCK 也没 key → True（仅本地无网联调时打 warning 后 fallback）
        cfg.MOCK_PAYMENT = False
        cfg.STRIPE_SECRET_KEY = ""
        assert_eq(ps.is_mock_mode(), True, "development 缺 key 仍可 fallback mock（仅本地）")
    finally:
        cfg.APP_ENV = orig_app_env
        cfg.MOCK_PAYMENT = orig_mock
        cfg.STRIPE_SECRET_KEY = orig_secret

    # ============== 18. P0 硬化：lifespan 启动期生产配置硬校验 ==============
    print("\n[18] P0 硬化：_validate_production_config() fail-fast")
    from app.main import _validate_production_config

    snapshot = {
        "APP_ENV": cfg.APP_ENV,
        "MOCK_PAYMENT": cfg.MOCK_PAYMENT,
        "ENABLE_MOCK_PAY_ROUTE": cfg.ENABLE_MOCK_PAY_ROUTE,
        "STRIPE_SECRET_KEY": cfg.STRIPE_SECRET_KEY,
        "STRIPE_WEBHOOK_SECRET": cfg.STRIPE_WEBHOOK_SECRET,
        "FRONTEND_URL": cfg.FRONTEND_URL,
        "JWT_SECRET": cfg.JWT_SECRET,
        "STRIPE_PRICE_MONTHLY": cfg.STRIPE_PRICE_MONTHLY,
        "STRIPE_PRICE_QUARTERLY": cfg.STRIPE_PRICE_QUARTERLY,
        "STRIPE_PRICE_YEARLY": cfg.STRIPE_PRICE_YEARLY,
        "STRIPE_PRICE_LIFETIME": cfg.STRIPE_PRICE_LIFETIME,
    }
    try:
        # 18.1 非生产 → 直接放行
        cfg.APP_ENV = "development"
        _validate_production_config()
        print(f"  {PASS} 非生产环境跳过校验")

        # 18.2 生产 + 一切都缺/不合法 → RuntimeError，且 message 应覆盖所有缺失项
        cfg.APP_ENV = "production"
        cfg.MOCK_PAYMENT = True
        cfg.ENABLE_MOCK_PAY_ROUTE = True
        cfg.STRIPE_SECRET_KEY = ""
        cfg.STRIPE_WEBHOOK_SECRET = ""
        cfg.FRONTEND_URL = "http://example.com"
        cfg.JWT_SECRET = "short"
        cfg.STRIPE_PRICE_MONTHLY = ""
        cfg.STRIPE_PRICE_QUARTERLY = ""
        cfg.STRIPE_PRICE_YEARLY = ""
        cfg.STRIPE_PRICE_LIFETIME = ""
        threw_msg = ""
        try:
            _validate_production_config()
        except RuntimeError as exc:
            threw_msg = str(exc)
        for key in (
            "MOCK_PAYMENT",
            "ENABLE_MOCK_PAY_ROUTE",
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_PRICE_MONTHLY",
            "STRIPE_PRICE_QUARTERLY",
            "STRIPE_PRICE_YEARLY",
            "STRIPE_PRICE_LIFETIME",
            "FRONTEND_URL",
            "JWT_SECRET",
        ):
            assert_true(key in threw_msg, f"错误信息包含缺失项 {key}")
        # 安全：错误信息不能含 sk_/whsec_/JWT 真实值（这里全是空/默认，确保不会泄露）
        assert_true("sk_" not in threw_msg and "whsec_" not in threw_msg, "错误信息不含密钥前缀")

        # 18.3 生产 + 全部配齐 → 不抛
        cfg.MOCK_PAYMENT = False
        cfg.ENABLE_MOCK_PAY_ROUTE = False
        cfg.STRIPE_SECRET_KEY = "sk_live_dummy_secret"
        cfg.STRIPE_WEBHOOK_SECRET = "whsec_dummy_secret"
        cfg.FRONTEND_URL = "https://videodown.cozyguidehub.com"
        cfg.JWT_SECRET = "x" * 40
        cfg.STRIPE_PRICE_MONTHLY = "price_dummy_m"
        cfg.STRIPE_PRICE_QUARTERLY = "price_dummy_q"
        cfg.STRIPE_PRICE_YEARLY = "price_dummy_y"
        cfg.STRIPE_PRICE_LIFETIME = "price_dummy_l"
        _validate_production_config()
        print(f"  {PASS} 配齐生产配置后 _validate_production_config 顺利通过")
    finally:
        for key, value in snapshot.items():
            setattr(cfg, key, value)

    # ============== 19. P0 硬化：webhook metadata.plan_code 显式校验 ==============
    print("\n[19] P0 硬化：metadata.plan_code 不一致被拒")
    with session_scope() as db:
        user = db.get(User, free_user_id)
        order = Order(
            order_no=f"PLANTEST{uuid.uuid4().hex[:6]}",
            user_id=user.id,
            plan_code="monthly",
            plan_name="月度会员",
            amount_cents=1900,
            currency="cny",
            status="pending",
            stripe_session_id=f"cs_plan_{uuid.uuid4().hex[:8]}",
            is_mock=0,
            vip_granted_days=30,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        plan_test_order_no = order.order_no
        plan_test_session_id = order.stripe_session_id

    plan_event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": plan_test_session_id,
                "client_reference_id": plan_test_order_no,
                "payment_status": "paid",
                "amount_total": 1900,
                "currency": "cny",
                "payment_intent": "pi_plan_test",
                "metadata": {"order_no": plan_test_order_no, "plan_code": "yearly"},  # 故意串台
            }
        },
    }
    plan_constructed = ps._ConstructedEvent(plan_event, json.dumps(plan_event).encode())
    with session_scope() as db:
        threw = False
        try:
            ps.handle_stripe_event(db, plan_constructed)
        except ps.PaymentError as exc:
            threw = "套餐" in str(exc) or "plan_code" in str(exc)
        assert_true(threw, "metadata.plan_code 与本地不一致被拒")

    # ============== 20. P0 硬化：异步支付 webhook ==============
    print("\n[20] P0 硬化：async_payment_succeeded 发放 VIP / async_payment_failed 取消订单")

    # 20.1 async_payment_succeeded → 标记 paid + 发 VIP
    with session_scope() as db:
        user = db.get(User, free_user_id)
        async_ok_order = Order(
            order_no=f"ASYNCOK{uuid.uuid4().hex[:5]}",
            user_id=user.id,
            plan_code="monthly",
            plan_name="月度会员",
            amount_cents=1900,
            currency="cny",
            status="pending",
            stripe_session_id=f"cs_async_ok_{uuid.uuid4().hex[:6]}",
            is_mock=0,
            vip_granted_days=30,
        )
        db.add(async_ok_order)
        db.commit()
        db.refresh(async_ok_order)
        async_ok_order_no = async_ok_order.order_no
        async_ok_session_id = async_ok_order.stripe_session_id

    async_ok_event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": "checkout.session.async_payment_succeeded",
        "data": {
            "object": {
                "id": async_ok_session_id,
                "client_reference_id": async_ok_order_no,
                "payment_status": "paid",
                "amount_total": 1900,
                "currency": "cny",
                "payment_intent": "pi_async_ok",
                "metadata": {"order_no": async_ok_order_no, "plan_code": "monthly"},
            }
        },
    }
    async_ok_constructed = ps._ConstructedEvent(async_ok_event, json.dumps(async_ok_event).encode())
    with session_scope() as db:
        msg = ps.handle_stripe_event(db, async_ok_constructed)
        assert_true("marked paid=True" in msg, f"async_payment_succeeded 标记 paid：{msg}")
        order_after = db.query(Order).filter(Order.order_no == async_ok_order_no).one()
        assert_eq(order_after.status, "paid", "异步成功后 status=paid")

    # 20.2 async_payment_failed → 标记 canceled
    with session_scope() as db:
        user = db.get(User, free_user_id)
        async_fail_order = Order(
            order_no=f"ASYNCFAIL{uuid.uuid4().hex[:4]}",
            user_id=user.id,
            plan_code="monthly",
            plan_name="月度会员",
            amount_cents=1900,
            currency="cny",
            status="pending",
            stripe_session_id=f"cs_async_fail_{uuid.uuid4().hex[:6]}",
            is_mock=0,
            vip_granted_days=30,
        )
        db.add(async_fail_order)
        db.commit()
        db.refresh(async_fail_order)
        async_fail_order_no = async_fail_order.order_no
        async_fail_session_id = async_fail_order.stripe_session_id

    async_fail_event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": "checkout.session.async_payment_failed",
        "data": {
            "object": {
                "id": async_fail_session_id,
                "client_reference_id": async_fail_order_no,
                "metadata": {"order_no": async_fail_order_no, "plan_code": "monthly"},
            }
        },
    }
    async_fail_constructed = ps._ConstructedEvent(async_fail_event, json.dumps(async_fail_event).encode())
    with session_scope() as db:
        msg = ps.handle_stripe_event(db, async_fail_constructed)
        assert_true("canceled" in msg, f"async_payment_failed 取消订单：{msg}")
        order_after = db.query(Order).filter(Order.order_no == async_fail_order_no).one()
        assert_eq(order_after.status, "canceled", "async_payment_failed 后 status=canceled")

    # ============== 21. P0 硬化：ENABLE_MOCK_PAY_ROUTE 路由开关 ==============
    print("\n[21] P0 硬化：ENABLE_MOCK_PAY_ROUTE 控制 mock-pay 路由是否注册")
    routes_paths = {getattr(r, "path", None) for r in app.routes}
    # 测试运行时 APP_ENV 未设置 = development，ENABLE_MOCK_PAY_ROUTE 默认 True → 路由已注册
    assert_true(
        "/api/billing/mock/pay/{order_no}" in routes_paths,
        "dev/test 下 mock-pay 路由按预期已注册",
    )
    print(
        f"  {INFO} 生产环境（APP_ENV=production / ENABLE_MOCK_PAY_ROUTE=false）下，"
        f"该路由在 backend/app/api/billing.py 模块导入期即不会被注册到 router；"
        f"完整集成验证建议在子进程里跑（避免污染当前 TestClient 的全局 app）。"
    )

    # ============== 22. resume-checkout：pending Stripe 订单继续支付 ==============
    print("\n[22] resume-checkout API")
    from unittest.mock import patch

    from app.api import billing as billing_api
    from app.services import payment_service as ps

    r = client.get("/api/users/me", headers=headers)
    owner_id = r.json()["id"]

    def _fake_stripe_session(db, user, plan, order):
        order.stripe_session_id = f"cs_resume_{uuid.uuid4().hex[:8]}"
        db.add(order)
        db.commit()
        return "https://checkout.stripe.com/c/pay/test_resume"

    resume_order_no = f"RESUME{uuid.uuid4().hex[:6].upper()}"
    with session_scope() as db:
        db.add(
            Order(
                order_no=resume_order_no,
                user_id=owner_id,
                plan_code="monthly",
                plan_name="月度会员",
                amount_cents=1900,
                currency="cny",
                status="pending",
                stripe_session_id=f"cs_old_{uuid.uuid4().hex[:6]}",
                is_mock=0,
                vip_granted_days=30,
            )
        )

    r = client.post("/api/billing/orders/RESUMENOEXIST/resume-checkout", headers=headers)
    assert_eq(r.status_code, 404, "不存在订单 resume 404")

    r = client.post(f"/api/billing/orders/{resume_order_no}/resume-checkout")
    assert_eq(r.status_code, 401, "未登录 resume 401")

    r = client.post(f"/api/billing/orders/{resume_order_no}/resume-checkout", headers=free_headers)
    assert_eq(r.status_code, 404, "非本人订单 resume 404")

    stripe_paid_no = f"PAIDSTR{uuid.uuid4().hex[:4].upper()}"
    with session_scope() as db:
        db.add(
            Order(
                order_no=stripe_paid_no,
                user_id=owner_id,
                plan_code="monthly",
                plan_name="月度会员",
                amount_cents=1900,
                currency="cny",
                status="paid",
                paid_at=int(time.time()),
                is_mock=0,
                vip_granted_days=30,
            )
        )
    r = client.post(f"/api/billing/orders/{stripe_paid_no}/resume-checkout", headers=headers)
    assert_eq(r.status_code, 400, "已 paid Stripe 订单 resume 400")
    assert_true("已支付" in r.json()["detail"], "paid 订单错误信息")

    stripe_canceled_no = f"CXLSTRIPE{uuid.uuid4().hex[:4].upper()}"
    with session_scope() as db:
        db.add(
            Order(
                order_no=stripe_canceled_no,
                user_id=owner_id,
                plan_code="monthly",
                plan_name="月度会员",
                amount_cents=1900,
                currency="cny",
                status="canceled",
                is_mock=0,
                vip_granted_days=30,
            )
        )
    r = client.post(f"/api/billing/orders/{stripe_canceled_no}/resume-checkout", headers=headers)
    assert_eq(r.status_code, 400, "已 canceled Stripe 订单 resume 400")
    assert_true("取消" in r.json()["detail"], "canceled 订单错误信息")

    mock_resume_no = f"MOCKRES{uuid.uuid4().hex[:4].upper()}"
    with session_scope() as db:
        db.add(
            Order(
                order_no=mock_resume_no,
                user_id=owner_id,
                plan_code="monthly",
                plan_name="月度会员",
                amount_cents=1900,
                currency="cny",
                status="pending",
                is_mock=1,
                vip_granted_days=30,
            )
        )
    r = client.post(f"/api/billing/orders/{mock_resume_no}/resume-checkout", headers=headers)
    assert_eq(r.status_code, 400, "mock pending 订单 resume 400")

    with session_scope() as db:
        order_count_before = db.query(Order).filter(Order.user_id == owner_id).count()

    with patch.object(billing_api, "create_stripe_checkout_session", side_effect=_fake_stripe_session):
        r = client.post(f"/api/billing/orders/{resume_order_no}/resume-checkout", headers=headers)
    assert_eq(r.status_code, 200, "pending Stripe 订单 resume 200")
    body = r.json()
    assert_eq(body["mode"], "stripe", "resume 模式 stripe")
    assert_eq(body["order_no"], resume_order_no, "resume 不新建订单号")
    assert_true(body["checkout_url"].startswith("https://checkout.stripe.com"), "返回 checkout_url")

    with session_scope() as db:
        order_count_after = db.query(Order).filter(Order.user_id == owner_id).count()
        resumed = db.query(Order).filter(Order.order_no == resume_order_no).one()
        resumed_session_id = resumed.stripe_session_id
    assert_eq(order_count_before, order_count_after, "resume 不增加订单数量")
    assert_true(resumed_session_id.startswith("cs_resume_"), "stripe_session_id 已更新")

    routes_paths = {getattr(r, "path", None) for r in app.routes}
    assert_true(
        "/api/billing/orders/{order_no}/resume-checkout" in routes_paths,
        "resume-checkout 路由已注册",
    )


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
