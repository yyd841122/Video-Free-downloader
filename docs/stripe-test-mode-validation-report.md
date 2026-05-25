# SaveAny Stripe Test Mode 验收报告

本文档记录 SaveAny 在 **Stripe Test Mode** 下完成的首轮真实联调验收结果，供后续 Live Mode 切换与公开推广前参考。

---

## 1. 验收时间

| 项 | 内容 |
|---|---|
| 验收日期 | 2026-05-24 |
| 验收阶段 | Stripe Test Mode 首轮联调 |
| 关联文档 | [stripe-test-mode-setup.md](./stripe-test-mode-setup.md) |
| 关联 commit | P0 硬化 `22ce6a6`；设置文档 `11b4ba4` |

---

## 2. 测试环境

| 项 | 值 |
|---|---|
| 前端 | `https://videodown.cozyguidehub.com` |
| 后端 API | `https://api-videodown.cozyguidehub.com` |
| Stripe 模式 | **Test mode**（测试密钥与测试 Price，非 Live 收款） |
| 测试套餐 | monthly（月度会员，¥19） |
| 测试支付方式 | Stripe Checkout + 测试卡 |

---

## 3. 后端配置状态

以下配置项已在生产 backend 生效（具体密钥与 Price ID **不在本文档中记录**）：

| 配置项 | 预期值 | 验收结果 |
|---|---|---|
| `APP_ENV` | `production` | ✅ 已切换 |
| `MOCK_PAYMENT` | `false` | ✅ 已关闭 Mock |
| `ENABLE_MOCK_PAY_ROUTE` | `false` | ✅ Mock 路由未注册 |
| `STRIPE_SECRET_KEY` | `sk_test_...`（Test mode） | ✅ 已配置 |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...`（Test mode endpoint） | ✅ 已配置 |
| `STRIPE_PRICE_*` | 四个 Test mode Price ID | ✅ 已配置（monthly 已用于联调） |
| `FRONTEND_URL` | `https://videodown.cozyguidehub.com` | ✅ 回跳正常 |
| `BILLING_CURRENCY` | `cny` | ✅ 与 Checkout 展示一致 |

**说明：** 本轮未在文档中输出任何 API 密钥、Webhook secret 或完整 Price ID。

---

## 4. 安全硬化验证

P0 支付安全硬化（commit `22ce6a6`）在生产环境验收通过：

| 检查项 | 方法 | 结果 |
|---|---|---|
| Billing 模式非 Mock | `GET /api/billing/mode` | ✅ 返回 `"mock": false` |
| Mock 支付路由已关闭 | `POST /api/billing/mock/pay/foo` | ✅ 返回 **404**（路由不存在） |
| 无法通过 Mock 白嫖 VIP | 上述 404 + mock=false | ✅ 生产 Mock 入口已封堵 |
| 真实 Checkout 路径可用 | 用户下单跳转 Stripe Hosted Checkout | ✅ 正常外跳 |

**结论：** 生产环境不再暴露 Mock 支付能力；Stripe 为唯一有效收款路径。

---

## 5. Stripe Checkout 验证

| 步骤 | 结果 |
|---|---|
| 用户注册 / 登录 | ✅ 正常 |
| 打开 `/pricing` | ✅ 正常；无 MOCK 模拟支付提示条（mock=false） |
| 选择 **monthly（¥19）** 并下单 | ✅ 正常 |
| 跳转 Stripe Checkout 页面 | ✅ 成功打开（Hosted Checkout） |
| 使用 Stripe 测试卡完成支付 | ✅ **Monthly ¥19 测试支付成功** |
| 回跳 `/payment/success` | ✅ 正常回跳 |
| Stripe Dashboard 测试付款记录 | ✅ 显示测试付款成功 |

**测试卡（Stripe 标准）：** `4242 4242 4242 4242`，任意未来有效期与 CVC。

---

## 6. Webhook 验证

| 检查项 | 结果 |
|---|---|
| Endpoint URL | `POST https://api-videodown.cozyguidehub.com/api/billing/webhook` |
| HTTP 响应 | ✅ **200 OK** |
| 事件类型（推断） | `checkout.session.completed`（同步卡支付典型路径） |
| 签名校验 | ✅ 通过（否则不会返回 200） |
| 订单状态推进 | ✅ 本地订单由 pending → paid（见第 7 节） |

**结论：** Webhook 闭环可用；支付成功后 backend 能正确处理 Stripe 回调并更新订单。

---

## 7. Account 订单验证

| 检查项 | 结果 |
|---|---|
| 个人中心 → 我的订单 | ✅ 显示新订单 |
| 订单状态 | ✅ **paid（已支付）** |
| MOCK 标签 | ✅ **无 MOCK 标签**（`is_mock=false`，符合 Stripe 真实订单） |
| 订单金额 / 套餐 | ✅ 与 monthly ¥19 一致 |

**说明：** 本轮已确认 **订单记录与 Stripe 支付一致**；VIP 会员状态与权益细节见第 8 节待补充项。

---

## 8. 待补充验证项

以下项目 **尚未在本轮报告中确认**，建议在进入 Live Mode 或公开推广前补齐：

| # | 验证项 | 建议方法 | 优先级 |
|---|---|---|---|
| 8.1 | **Account VIP 到期时间** | 支付 monthly 后查看 `/account` 会员有效期是否为约 +30 天；刷新 `/api/users/me` 核对 `vip_expire_at` | P0 |
| 8.2 | **VIP 1080p 下载权限** | 登录 VIP 账号，解析含 1080p 格式视频，确认不再被 720p 门禁拦截 | P0 |
| 8.3 | **quarterly checkout** | `/pricing` 选季度套餐 → Stripe Test 支付 → 订单 paid + VIP 叠加 | P1 |
| 8.4 | **yearly checkout** | 同上，年度套餐 | P1 |
| 8.5 | **lifetime checkout** | 同上，终身套餐；确认 `is_lifetime_vip=true` | P1 |
| 8.6 | **cancel flow** | Checkout 页点击取消 → 回跳 `/payment/cancel`；订单保持 pending 或变为 canceled/expired | P1 |
| 8.7 | **PaymentSuccess 轮询边界** | 模拟 webhook 延迟 >30s，确认 success 页 pending 提示与 Account 手动刷新体验 | P2 |
| 8.8 | **async_payment 事件** | 若启用 Alipay/WeChat Pay，单独验证 `async_payment_succeeded` / `async_payment_failed` | P1（启用异步支付时） |
| 8.9 | **Webhook 幂等** | Stripe Dashboard 重发同一 event，确认 VIP 不重复累加 | P2 |
| 8.10 | **续费叠加** | VIP 有效期内再购 quarterly，确认 `vip_expire_at` 在原有基础上延长 | P2 |

---

## 9. 当前结论

### 已通过（本轮 Test Mode）

- ✅ 生产环境 Stripe Test Mode 配置生效（`mock=false`）
- ✅ P0 安全硬化生效（mock-pay 404，无 Mock 白嫖路径）
- ✅ Stripe Checkout 外跳与测试卡支付成功（monthly ¥19）
- ✅ Webhook 200 OK，订单状态正确更新为 **paid**
- ✅ Account 订单列表正确展示，**无 MOCK 标签**
- ✅ Stripe Dashboard 测试付款记录成功

### 总体评估

**Stripe Test Mode 主链路（注册 → 下单 → Checkout → Webhook → 订单 paid）已跑通。**

当前状态适合：

- 继续补齐第 8 节待验证项（尤其 VIP 到期时间与 1080p 权限）
- 在团队内部扩大 Test Mode 试用范围

当前状态 **尚不适合**：

- 切换 Live Mode 公开收款（待 8.1–8.6 等核心项补齐）
- 大规模对外推广（待 P1 文案与退款政策复查）

---

## 10. 下一步建议

| 顺序 | 动作 | 说明 |
|---|---|---|
| 1 | **补齐 VIP 验收** | 确认 Account 显示 VIP 及到期时间；测 1080p 下载不再被 free 门禁拦截 |
| 2 | **扩展套餐测试** | quarterly / yearly / lifetime 各走一笔 Test 支付 |
| 3 | **Cancel 流程** | Stripe Checkout 取消 → `/payment/cancel` → 订单状态符合预期 |
| 4 | **更新本报告** | 每项待补充验证完成后，在本文件或附录中勾选并记录日期 |
| 5 | **P1 文案与工具** | `pricing.trust1/trust2` 去 mock 表述；`check_production.py` 与启动校验对齐 |
| 6 | **Live Mode 准备** | 全部 Test 项通过后，按 [stripe-test-mode-setup.md 第 14 节](./stripe-test-mode-setup.md#14-test-mode-到-live-mode-切换提醒) 切换 `sk_live_` / Live Price / Live Webhook，并重新跑一遍验收 |

---

## 附录：验收检查清单（可勾选）

```
[✅] GET /api/billing/mode → mock=false
[✅] POST /api/billing/mock/pay/foo → 404
[✅] Stripe Checkout 打开
[✅] monthly ¥19 测试支付成功
[✅] Webhook POST /api/billing/webhook → 200 OK
[✅] Account 订单 paid，无 MOCK 标签
[✅] Stripe Dashboard 测试付款成功
[ ] Account VIP 到期时间正确
[ ] VIP 1080p 下载权限生效
[ ] quarterly / yearly / lifetime checkout
[ ] cancel flow
[ ] Live Mode 切换与复验
```

---

*报告生成：Stripe Test Mode 首轮联调验收。不含任何密钥、secret 或完整 Price ID。*
