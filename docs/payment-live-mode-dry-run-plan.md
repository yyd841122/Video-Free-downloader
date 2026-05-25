# SaveAny 支付全流程收尾与 Live Mode Dry Run 计划

本文档描述 SaveAny 在 **Stripe Test Mode 技术闭环已基本完成** 的前提下，如何继续打磨支付产品化流程，并为后续 **Stripe Live、Creem 或其他收款渠道** 的切换做铺垫。

**重要说明：** 本文档是 **计划与清单**，不是切换指令。当前 **不切 Stripe Live、不接真实收款**。

---

## 1. 文档目的

| 项 | 说明 |
|---|---|
| 当前阶段定位 | **不是** 立即切换到 Stripe Live 或开启真实收款 |
| 核心目标 | 把支付全流程梳理完整，形成可复用的流程资产与验收标准 |
| 复用范围 | 后续 SaveAny 切 Stripe Live、评估 Creem、或在其他项目中复用同一套支付产品化思路 |
| 业务背景 | 业务方暂无可稳定提现的海外账户，因此 **真实收款渠道暂不确定** |
| 文档性质 | 流程收尾清单 + Live Mode **Dry Run（演练）** 手册，不含密钥与部署操作 |

**关联文档：**

- [stripe-test-mode-setup.md](./stripe-test-mode-setup.md) — Test Mode 配置指南
- [stripe-test-mode-validation-report.md](./stripe-test-mode-validation-report.md) — 已完成的 Test Mode 验收记录

---

## 2. 当前已完成能力

以下能力已在 SaveAny **Stripe Test Mode** 下验证通过（详见验收报告）：

### 2.1 Mock 支付阶段（历史）

| 能力 | 状态 |
|---|---|
| Mock 下单与 mock-pay 页面 | ✅ 开发/联调阶段可用 |
| Mock 订单 VIP 发放 | ✅ 已验证 |
| 生产环境 Mock 路由关闭 | ✅ `mock-pay` 返回 404 |

### 2.2 Stripe Test Mode 基础设施

| 能力 | 状态 |
|---|---|
| Stripe Test Mode Product / Price | ✅ 已配置（monthly / quarterly / yearly / lifetime） |
| Stripe Test Mode Webhook Endpoint | ✅ 已配置，`POST /api/billing/webhook` 返回 200 |
| 后端 production 配置校验 | ✅ `APP_ENV=production`、`MOCK_PAYMENT=false`、`ENABLE_MOCK_PAY_ROUTE=false` |
| Billing 模式检测 | ✅ `GET /api/billing/mode` → `mock=false` |

### 2.3 支付主链路

| 能力 | 状态 |
|---|---|
| Stripe Hosted Checkout | ✅ 外跳正常（monthly 完整支付已测） |
| Webhook 订单推进 | ✅ pending → paid |
| Account 订单展示 | ✅ 新 Stripe 订单 paid、无 MOCK 标签 |
| VIP 发放 | ✅ 会员有效期正确延长 |
| 高清下载权限 | ✅ VIP 可下载 1920p |
| 续费叠加 | ✅ 再次购买 monthly 有效期累加 |

### 2.4 异常与恢复路径

| 能力 | 状态 |
|---|---|
| resume checkout（待支付继续支付） | ✅ `/account` pending 订单 → Stripe Checkout（commit `7c718c6`） |
| cancel flow（Checkout 取消/返回） | ✅ 订单保持 pending、支付时间为空、VIP 未误发、仍可继续支付 |

### 2.5 文档与治理

| 能力 | 状态 |
|---|---|
| P0 支付安全硬化 | ✅ 生产 Mock 封堵、启动期配置校验 |
| Stripe Test Mode 验收报告 | ✅ 已更新并 push（含 resume checkout、cancel flow） |

---

## 3. 当前不做的事

以下事项 **明确不在当前阶段执行**：

| # | 不做的事 | 原因 |
|---|---|---|
| 1 | **不切 Stripe Live** | 无可稳定提现的海外账户，Live 收款无法闭环 |
| 2 | **不接真实收款** | 避免产生真实资金与合规义务 |
| 3 | **不启用支付宝 / 微信** | 需额外 Stripe 配置与 async_payment 验收，当前非优先级 |
| 4 | **不接 Creem API** | 仅做可行性评估入口，本轮不接入代码 |
| 5 | **不重构支付架构** | 现有 Stripe 闭环可用，避免引入不必要风险 |
| 6 | **不公开大规模推广收费** | Live 复验、退款政策、文案复查未完成 |
| 7 | **不承诺正式商用支付** | 对外不应暗示已开启真实收款 |

---

## 4. 剩余 Test Mode 收尾项

在 **不切 Live** 的前提下，建议在 Stripe Test Mode 下补齐以下可选验收项：

| # | 收尾项 | 验收方法 | 优先级 |
|---|---|---|---|
| 4.1 | **quarterly 完整 Test 支付** | 选季度套餐 → Checkout → 测试卡支付 → 订单 paid + VIP 时长正确 | P1（可选） |
| 4.2 | **yearly 完整 Test 支付或金额验证** | 完成支付或至少验证 Checkout 展示金额与本地 plan 一致 | P1（可选） |
| 4.3 | **lifetime 完整 Test 支付或金额验证** | 支付后确认 `is_lifetime_vip=true`；或验证 Checkout 金额 | P1（可选） |
| 4.4 | **payment cancel 后 pending 订单继续支付** | cancel → Account pending → resume checkout → 完成支付 | ✅ 已通过（可回归） |
| 4.5 | **多个 pending 订单的订单列表体验** | 创建 ≥2 笔 pending → Account 列表排序、状态、操作按钮是否清晰 | P2 |
| 4.6 | **Webhook Dashboard 事件 200 记录** | Stripe Dashboard → Webhooks → 查看近期事件 HTTP 200、无持续失败 | P2 |

**说明：** 4.4 已在 cancel flow + resume checkout 验收中覆盖；4.1–4.3 为套餐维度补充，不影响主链路结论。

---

## 5. Live Mode Dry Run 清单

本节为 **流程演练清单**：按步骤走一遍 Live 切换所需动作，**不填入真实 Live key、不执行真实切换**。

### 5.1 Stripe Live 账户激活状态检查

- [ ] Stripe Dashboard 切换到 **Live mode**
- [ ] 确认账户 **激活状态**（未完成 KYC / 资料时无法收款）
- [ ] 确认 **可绑定提现银行账户** 或符合业务方条件的 payout 方式
- [ ] 确认 **业务描述 / 网站 URL** 与 SaveAny 实际站点一致
- [ ] 记录检查日期与负责人（不写密钥）

### 5.2 Live Product / Price 创建步骤（演练）

- [ ] 在 Live mode 创建 Product（与 Test 命名规范对齐，便于对照）
- [ ] 创建 4 个 Price：monthly / quarterly / yearly / lifetime（CNY，金额与 Test 一致）
- [ ] 在内部表格记录 **Price 别名 → Live Price ID 占位符**（本文档不写完整 ID）
- [ ] 对照 Test Mode Price 结构，确认 metadata / 币种 / 计费周期无遗漏

### 5.3 Live Webhook 创建步骤（演练）

- [ ] Live mode 新建 Webhook Endpoint：`https://api-videodown.cozyguidehub.com/api/billing/webhook`
- [ ] 订阅事件（至少）：`checkout.session.completed`、`checkout.session.expired`、`checkout.session.async_payment_succeeded`、`checkout.session.async_payment_failed`
- [ ] 演练 **Signing secret 存放位置**（仅说明写入 backend `.env` 的变量名 `STRIPE_WEBHOOK_SECRET`，不写值）
- [ ] 演练 Dashboard **Send test webhook** 与 backend 日志对照（Dry Run 可不真发）

### 5.4 Live `.env` 变量映射（演练）

以下为 **变量名映射表**，Dry Run 只核对名称与来源，**不填写真实值**：

| 变量名 | 来源 / 说明 |
|---|---|
| `APP_ENV` | `production` |
| `MOCK_PAYMENT` | `false` |
| `ENABLE_MOCK_PAY_ROUTE` | `false` |
| `STRIPE_SECRET_KEY` | Stripe Live Dashboard → API keys（`sk_live_...`） |
| `STRIPE_WEBHOOK_SECRET` | Live Webhook Endpoint → Signing secret |
| `STRIPE_PRICE_MONTHLY` | Live Price ID（monthly） |
| `STRIPE_PRICE_QUARTERLY` | Live Price ID（quarterly） |
| `STRIPE_PRICE_YEARLY` | Live Price ID（yearly） |
| `STRIPE_PRICE_LIFETIME` | Live Price ID（lifetime） |
| `FRONTEND_URL` | `https://videodown.cozyguidehub.com`（须 https） |
| `BILLING_CURRENCY` | `cny` |
| `JWT_SECRET` | 生产强随机值（≥32 字符，非默认值） |

### 5.5 `.env` 备份（演练）

- [ ] 切换前 **完整备份** 当前 backend `.env`（含 Test key 版本）
- [ ] 备份文件命名规范，例如：`.env.backup.YYYYMMDD-test-mode`
- [ ] 备份存放位置与访问权限仅运维/负责人可读写
- [ ] 记录备份时间与操作人

### 5.6 切换前检查（演练）

- [ ] 运行 `backend/scripts/check_production.py`（或等价脚本）通过
- [ ] 启动日志无 `_validate_production_config` 报错
- [ ] `GET /api/billing/mode` → `mock=false`
- [ ] `POST /api/billing/mock/pay/foo` → 404
- [ ] 前端 pricing / account 文案无 Mock / Test 残留
- [ ] 退款政策、联系渠道、用户协议已就绪（见第 6 节）
- [ ] 团队确认 **可执行回滚**（见 5.8）

### 5.7 切换后验证（演练清单，真实切换时再执行）

| 步骤 | 预期 |
|---|---|
| 最小金额 Live 支付（如 monthly） | Checkout 打开 → 真实扣款 → Webhook 200 |
| Account 订单 | paid，无 MOCK |
| VIP | 有效期延长或 lifetime 标记正确 |
| 1920p 下载 | VIP 权限生效 |
| cancel / resume | pending 行为与 Test 一致 |
| Stripe Dashboard | Live 模式下有 Payment + Webhook 200 |
| 回滚演练 | 恢复 Test `.env` 后 mock-pay 仍 404、mode 仍 stripe 配置正确 |

### 5.8 回滚方案

| 场景 | 动作 |
|---|---|
| Live 切换后支付异常 | 立即恢复 **备份的 Test Mode `.env`**，重启 backend |
| Webhook 签名失败 | 核对 Live `STRIPE_WEBHOOK_SECRET` 是否与 Dashboard 一致；临时回滚 Test secret |
| 误用 Live Price | 恢复 Test `STRIPE_PRICE_*`，避免错误标价 |
| VIP 误发 | 按客服流程人工核对订单与 webhook 日志；必要时冻结新购入口 |
| 完全回退 | `.env` 回 Test → 重启 → 验证 mode / mock-pay / 一笔 Test 卡支付 |

**原则：** 任何 Live 切换必须 **可在一轮部署内回滚到 Test Mode 配置**。

---

## 6. Live Mode 前必须完成的业务条件

技术 Dry Run 通过后，**仍须满足以下业务条件** 才可考虑真实收款：

| # | 业务条件 | 说明 |
|---|---|---|
| 6.1 | **可提现账户确认** | Stripe（或其他渠道）payout 账户可正常绑定且符合业务方属地要求 |
| 6.2 | **账户 KYC 通过** | Dashboard 无「Restricted / Pending verification」等阻断状态 |
| 6.3 | **退款政策明确** | 法律页 / 帮助页有可执行的退款规则（期限、条件、联系方式） |
| 6.4 | **联系渠道可用** | 用户可联系客服处理支付争议（邮箱 / 表单 / 工单） |
| 6.5 | **支付文案无 Mock/Test 残留** | pricing、success/cancel 页、Account 无「模拟支付」「测试模式」等字样 |
| 6.6 | **用户协议包含数字服务/会员说明** | 明确 VIP 权益、有效期、非实物、自动续费（如有）等 |
| 6.7 | **订单页状态清晰** | pending / paid / canceled 展示一致，操作按钮语义明确 |
| 6.8 | **客服处理流程准备** | 争议订单、重复扣款、未到账 VIP 的处理 SOP |

---

## 7. Creem 作为替代方案的评估入口

> **本轮仅评估方向，不接入代码、不调用 Creem API。**

当 Stripe Live 因 **提现账户 / 属地限制** 无法使用时，可将 Creem 作为备选收款渠道。评估时可按以下维度调研（需查阅 Creem 官方文档与商务政策，本文档不给出结论性承诺）：

| 评估维度 | 需确认的问题 |
|---|---|
| **中国个人是否可用** | 注册主体要求、是否需要海外公司 / 身份证限制 |
| **Alipay payout 是否可用** | 提现到中国支付宝的路径、限额、手续费 |
| **用户付款方式** | 是否支持中国用户常用支付方式（卡 / 本地钱包等） |
| **视频下载类产品** | Acceptable Use / 品类限制是否覆盖「视频下载 + AI 总结」类 SaaS |
| **Webhook 与会员发放** | 是否支持 payment succeeded 类回调；能否映射到现有 `mark_order_paid` 流程 |
| **费用与周期** | 费率、结算周期、最低提现额 |
| **风控与争议** |  chargeback / 退款争议处理流程、冻结资金规则 |

**输出物建议：** 单独一份《Creem 可行性备忘录》（与本文档分离），包含 **Go / No-Go 建议** 与对比 Stripe Live 的表格。

---

## 8. Payment Provider 抽象的未来方向

当前实现以 **Stripe 为唯一生产收款路径**（Test Mode）。未来若同时支持 Stripe、Creem、或本地 Mock，可考虑配置：

```text
PAYMENT_PROVIDER=mock | stripe | creem
```

**本轮不实现。** 以下为未来抽象时可能需要的数据与接口扩展：

| 扩展点 | 说明 |
|---|---|
| `provider` 字段 | 订单表记录 `stripe` / `creem` / `mock` |
| `provider_order_id` | 第三方侧订单或 payment intent 标识 |
| `provider_session_id` | Checkout Session 或等价会话 ID |
| `provider_webhook_event_id` | Webhook 幂等去重（类似现有 `webhook_events`） |
| Provider-specific webhook router | `/api/billing/webhook` 按签名或 path 分发到不同 handler |
| Frontend 不写死 Stripe 文案 | pricing / success / account 使用 provider 中性文案或 i18n key |

**设计原则：** 抽象层应 **包裹现有 Stripe 流程**，而非推翻已验证的 Test Mode 闭环。

---

## 9. 推荐后续阶段

| 阶段 | 名称 | 主要动作 | 产出 |
|---|---|---|---|
| **Phase A** | Stripe Test Mode 收尾 | 补齐 quarterly / yearly / lifetime 可选验收；多 pending 列表体验 | 更新 [验收报告](./stripe-test-mode-validation-report.md) |
| **Phase B** | Live Mode Dry Run 文档化 | 按本文档第 5 节逐项演练（不填 Live key） | 勾选 Dry Run 清单 + 内部评审记录 |
| **Phase C** | Creem 可行性确认 | 按第 7 节维度调研 | Creem 可行性备忘录 |
| **Phase D** | Payment Provider 抽象设计 | 字段与接口设计评审（不写代码或仅 ADR） | 设计文档 / ADR |
| **Phase E** | 选择真实收款渠道 | Stripe Live vs Creem vs 其他，结合提现与合规 | 渠道决策记录 |
| **Phase F** | 小额真实支付验证 | 选定渠道后最小金额全流程 | Live 验收报告（新文档） |
| **Phase G** | 公开收费前最终安全复核 | mock-pay 404、配置校验、退款政策、文案、客服 SOP | Go-live 检查清单签字 |

**建议顺序：** A → B → C → E → F → G；Phase D 可与 C 并行，仅在确定多渠道并存时深入实现。

---

## 10. 当前结论

| 项 | 结论 |
|---|---|
| 技术闭环 | SaveAny **已具备支付产品化技术闭环**（Stripe Test Mode：Checkout → Webhook → paid → VIP → 权限） |
| 真实收款 | **真实收款渠道暂不确定**；因提现账户限制，**不急于切 Stripe Live** |
| 当前重心 | 以 **流程打磨、文档沉淀、Dry Run 演练、备选渠道评估** 为主，便于 SaveAny 及其他项目复用 |
| 已有成果 | **不因 Stripe Live 暂停而推翻**；Test Mode 验收、resume checkout、cancel flow、安全硬化均为有效资产 |
| 下一步 | 执行 Phase A 可选收尾 + Phase B Dry Run 勾选；并行启动 Phase C Creem 调研 |

---

*文档版本：2026-05-24。不含任何 API 密钥、Webhook secret 或完整 Price ID。关联验收报告见 [stripe-test-mode-validation-report.md](./stripe-test-mode-validation-report.md)。*
