# SaveAny Stripe Test Mode 验收报告

本文档记录 SaveAny 在 **Stripe Test Mode** 下完成的联调验收结果（含首轮与补充验收），供后续 Live Mode 切换与公开推广前参考。

---

## 1. 验收时间

| 项 | 内容 |
|---|---|
| 首轮验收日期 | 2026-05-24 |
| 补充验收日期 | 2026-05-24（同日后续轮次） |
| resume checkout 验收日期 | 2026-05-24（P1 修复部署后） |
| cancel flow 验收日期 | 2026-05-24 |
| 验收阶段 | Stripe Test Mode 联调（首轮 + 补充 + resume checkout + cancel flow） |
| 关联文档 | [stripe-test-mode-setup.md](./stripe-test-mode-setup.md) |
| 关联 commit | P0 硬化 `22ce6a6`；设置文档 `11b4ba4`；本报告 `8596100`；resume checkout `7c718c6` |

---

## 2. 测试环境

| 项 | 值 |
|---|---|
| 前端 | `https://videodown.cozyguidehub.com` |
| 后端 API | `https://api-videodown.cozyguidehub.com` |
| Stripe 模式 | **Test mode**（测试密钥与测试 Price，非 Live 收款） |
| 已测套餐 | monthly（完整支付）；quarterly / yearly（订单创建）；续费叠加（monthly ×2） |
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
| `STRIPE_PRICE_*` | 四个 Test mode Price ID | ✅ 已配置（monthly / quarterly / yearly 已用于联调） |
| `FRONTEND_URL` | `https://videodown.cozyguidehub.com` | ✅ 回跳正常 |
| `BILLING_CURRENCY` | `cny` | ✅ 与 Checkout 展示一致 |

**说明：** 本文档不输出任何 API 密钥、Webhook secret 或完整 Price ID。

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
| 订单状态推进 | ✅ 本地订单由 pending → paid |

**结论：** Webhook 闭环可用；支付成功后 backend 能正确处理 Stripe 回调并更新订单。

---

## 7. Account 订单验证

| 检查项 | 结果 |
|---|---|
| 个人中心 → 我的订单 | ✅ 显示新订单 |
| 新 Stripe 订单状态 | ✅ **已支付 / paid** |
| 新 Stripe 订单 MOCK 标签 | ✅ **无 MOCK 标签**（`is_mock=false`） |
| 历史 Mock 订单 | ✅ 仍正确显示 **MOCK** 标签（与 Stripe 订单区分） |
| 订单金额 / 套餐 | ✅ 与所选套餐一致 |

---

## 8. 验证项状态汇总

### 8.1 已通过（首轮 + 补充验收）

| # | 验证项 | 状态 | 备注 |
|---|---|---|---|
| 8.1 | Account VIP 到期时间 | ✅ 已通过 | 月度支付后会员有效期延长；示例：**会员有效期至 2026-11-19** |
| 8.2 | VIP 高清下载权限 | ✅ 已通过 | 已付费会员可下载 **1920p** 高清；不再被免费 720p 门禁拦截 |
| 8.3 | 订单列表展示 | ✅ 已通过 | 新 Stripe 订单「已支付」且无 MOCK；历史 Mock 订单仍带 MOCK 标签 |
| 8.4 | 扩展套餐订单创建 | ✅ 已通过 | **monthly / quarterly / yearly** 均可创建 Stripe 订单；pending 显示「继续支付」 |
| 8.5 | 续费叠加 | ✅ 已通过 | 再次购买月度后，会员有效期在原有基础上继续延长 |
| 8.12 | **待支付订单继续支付（resume checkout）** | ✅ 已通过 | `/account` pending Stripe 订单点「继续支付」→ 直接跳转 Stripe Checkout；不再跳转 `/pricing`（commit `7c718c6`） |
| 8.8 | **Cancel flow（Checkout 取消/返回）** | ✅ 已通过 | 用户在 Stripe Checkout 取消后回跳；订单保持 pending；支付时间为空；仍可「继续支付」；VIP 未错误增加 |
| — | 主链路 Checkout + Webhook + paid | ✅ 已通过 | 见第 5–7 节 |
| — | P0 安全硬化 | ✅ 已通过 | 见第 4 节 |

### 8.2 仍待验证（Live Mode / 公开推广前）

| # | 验证项 | 建议方法 | 优先级 |
|---|---|---|---|
| 8.6 | **quarterly / yearly 完整支付** | 各完成一笔 Test 支付 → 订单 paid + VIP 时长叠加正确 | P1（可选剩余项） |
| 8.7 | **lifetime checkout** | 选终身套餐 → 支付 → 确认 `is_lifetime_vip=true` | P1（可选剩余项） |
| 8.9 | **PaymentSuccess 轮询边界** | webhook 延迟 >30s 时 success 页与 Account 刷新体验 | P2 |
| 8.10 | **async_payment 事件** | 启用 Alipay/WeChat Pay 时验证 async_* webhook | P1（启用异步支付时） |
| 8.11 | **Webhook 幂等** | Dashboard 重发同一 event，VIP 不重复累加 | P2 |

---

## 9. 补充验收结果

补充验收于 **2026-05-24** 完成，在首轮主链路通过后执行。

### 9.1 会员发放与到期时间

| 检查项 | 结果 |
|---|---|
| 月度支付后 VIP 状态 | ✅ Account 显示会员有效 |
| 到期时间延长 | ✅ 支付后有效期正确延长 |
| 示例 | 当前账号显示：**会员有效期至 2026-11-19**（具体日期随测试账号与叠加次数而异） |

**结论：** Stripe Test Mode 支付 → Webhook → VIP 发放 → Account 展示 **闭环正确**。

### 9.2 高清下载权限

| 检查项 | 结果 |
|---|---|
| 免费用户门禁 | 最高 720p（已知行为） |
| VIP 用户下载 | ✅ 可下载 **1920p** 高清格式 |
| 门禁拦截 | ✅ 已付费会员 **不再** 被 720p 限制拦截 |

**结论：** 会员权益（分辨率门禁）与订单 paid 状态一致，quota / VIP 判定生效。

### 9.3 订单列表与 Mock 区分

| 检查项 | 结果 |
|---|---|
| 新 Stripe 订单 | ✅ 状态「已支付」，**无 MOCK 标签** |
| 历史 Mock 订单 | ✅ 仍显示 **MOCK** 标签，便于区分测试数据 |
| pending 订单操作 | ✅ 显示「继续支付」；Stripe pending 调用 resume-checkout API 后跳转 Stripe Checkout（不再跳转 `/pricing`）；Mock pending 仍走 mock-pay（生产 mock-pay 404，仅历史 Mock 订单可见） |

### 9.4 扩展套餐与续费

| 检查项 | 结果 |
|---|---|
| monthly 完整支付 | ✅ 已测（首轮） |
| quarterly / yearly 订单创建 | ✅ Checkout 可创建，pending 正常 |
| quarterly / yearly 完整支付 | ⏳ 待测（见 8.2） |
| lifetime 订单 / 支付 | ⏳ 待测（见 8.2） |
| 续费叠加（monthly 再买 monthly） | ✅ 会员有效期在原有基础上 **继续延长** |

### 9.5 待支付订单继续支付（resume checkout）

P1 修复（commit `7c718c6` fix(payment): resume Stripe checkout for pending orders）部署后验收：

| 检查项 | 结果 |
|---|---|
| 后端已部署并重启 | ✅ |
| `GET /api/billing/mode` | ✅ 仍为 `"mock": false` |
| `POST /api/billing/mock/pay/foo` | ✅ 仍为 **404** |
| `/account` → 我的订单 → pending Stripe 订单 | ✅ 显示「继续支付」 |
| 点击「继续支付」 | ✅ **直接跳转 Stripe Hosted Checkout** |
| 错误跳转 `/pricing` | ✅ **已修复**，不再发生 |
| API 路径 | `POST /api/billing/orders/{order_no}/resume-checkout`（复用 pending 订单，新建 Checkout Session） |

**结论：** **resume checkout flow 已通过**；Account 待支付 Stripe 订单可正常恢复支付，与 pricing 页首次下单体验一致。

### 9.6 Cancel Flow 验收（Checkout 取消/返回）

用户在 Stripe Hosted Checkout 页面取消或返回后的验收结果：

| 检查项 | 结果 |
|---|---|
| 进入 Stripe Checkout 后取消 / 返回 | ✅ 正常回跳（`/payment/cancel` 或等价取消路径） |
| Account 订单状态 | ✅ 保持 **待支付 / pending**（未误标 paid 或 canceled） |
| 支付时间 | ✅ **为空**（未记录错误支付时间） |
| 订单操作 | ✅ 仍显示 **「继续支付」** |
| VIP 有效期 | ✅ **未错误增加**（取消未触发会员发放） |
| resume checkout 联动 | ✅ 同一 pending 订单可通过「继续支付」再次进入 Stripe Checkout |

**结论：** **cancel flow 已通过**；Checkout 取消不会误发 VIP，pending 订单可继续通过 resume checkout 完成支付。

---

## 10. 当前结论

### 已通过（Stripe Test Mode）

- ✅ 生产环境 Stripe Test Mode 配置生效（`mock=false`）
- ✅ P0 安全硬化生效（mock-pay 404，无 Mock 白嫖路径）
- ✅ Stripe Checkout 外跳与测试卡支付成功（monthly）
- ✅ Webhook 200 OK，订单状态正确更新为 **paid**
- ✅ Account 订单列表正确；新 Stripe 订单无 MOCK，历史 Mock 仍标识
- ✅ **VIP 到期时间** 正确延长（示例：至 2026-11-19）
- ✅ **VIP 高清下载**（1920p）不再被 720p 门禁拦截
- ✅ **续费叠加** 正确（再次购买 monthly 延长有效期）
- ✅ **monthly / quarterly / yearly** Stripe 订单可创建
- ✅ **待支付订单继续支付（resume checkout）**：Account pending Stripe 订单 → Stripe Checkout（不再跳转 `/pricing`）
- ✅ **Cancel flow**：Checkout 取消后订单保持 pending、支付时间为空、仍可继续支付、VIP 未错误增加

### 总体评估

**Stripe Test Mode 主链路、resume checkout、cancel flow、VIP 发放、高清下载权限均已通过。**

当前状态适合：

- 团队内部继续使用 Test Mode 做可选剩余项（quarterly / yearly / lifetime 完整支付）
- 并行准备 Live Mode 配置与合规文案

### Live Mode 前仍待完成

| 项 | 说明 |
|---|---|
| Stripe Live Product / Price / Webhook | Dashboard Live mode 重新创建资源 |
| Live key 配置 | `sk_live_`、Live `whsec_`、Live `price_` 写入 `.env` |
| 退款政策 | 页脚 / 法律页补充可执行的退款说明 |
| 支付文案最终复查 | `pricing.trust1/trust2` 等去除 mock 残留 |
| 小额真实支付验证 | Live 模式下最小金额全流程复验 |
| Live Mode 前最终安全复核 | `_validate_production_config` + mock-pay 404 + webhook 200 |

当前状态 **尚不适合**：

- 大规模对外公开推广（待 Live 复验 + 退款政策 + 文案复查）
- 在未完成 Live 小额真实支付验证前切换公开收款

---

## 11. 下一步建议

| 顺序 | 动作 | 说明 |
|---|---|---|
| 1 | **补齐 Test 可选剩余项** | quarterly / yearly / lifetime 完整支付（cancel flow、resume checkout 已通过） |
| 2 | **Live Dashboard 配置** | Live Product + 4 Price + Webhook endpoint |
| 3 | **更新 `.env` 为 Live 密钥** | 按 [stripe-test-mode-setup.md 第 14 节](./stripe-test-mode-setup.md#14-test-mode-到-live-mode-切换提醒) |
| 4 | **退款政策与支付文案** | 法律页 + pricing trust 文案最终版 |
| 5 | **Live 小额真实支付** | 最小金额全流程：Checkout → Webhook → VIP → 1080p |
| 6 | **最终安全复核** | mock=false、mock-pay 404、check_production + 启动日志 |
| 7 | **更新本报告** | Live 验收通过后追加章节并勾选附录 |

---

## 附录：验收检查清单

```
首轮 + 补充已通过
[✅] GET /api/billing/mode → mock=false
[✅] POST /api/billing/mock/pay/foo → 404
[✅] Stripe Checkout 打开
[✅] monthly 测试支付成功
[✅] Webhook POST /api/billing/webhook → 200 OK
[✅] Account 新订单 paid，无 MOCK 标签
[✅] 历史 Mock 订单仍显示 MOCK 标签
[✅] Stripe Dashboard 测试付款成功
[✅] Account VIP 到期时间正确（示例：至 2026-11-19）
[✅] VIP 1920p 高清下载权限生效
[✅] monthly / quarterly / yearly 可创建 Stripe 订单
[✅] 续费叠加（再次 monthly 延长有效期）
[✅] Account pending Stripe 订单「继续支付」→ Stripe Checkout（resume checkout，commit 7c718c6）
[✅] Stripe Checkout cancel flow：订单 pending、支付时间为空、仍可继续支付、VIP 未错误增加

仍待完成（可选 Test 剩余项 + Live Mode 前）
[ ] quarterly / yearly 完整 Test 支付
[ ] lifetime checkout + is_lifetime_vip
[ ] Live Mode Product / Price / Webhook
[ ] Live key 配置 + 小额真实支付验证
[ ] 退款政策 + 支付文案复查
[ ] Live Mode 前最终安全复核
```

---

*报告版本：首轮（2026-05-24）+ 补充验收（2026-05-24）+ resume checkout 验收（2026-05-24，commit 7c718c6）+ cancel flow 验收（2026-05-24）。不含任何密钥、secret 或完整 Price ID。*
