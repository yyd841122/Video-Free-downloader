# SaveAny Stripe Test Mode 设置指南

本文档面向 **Stripe Test Mode 联调**：在真实收款（Live Mode）之前，于生产域名上完成 Dashboard 配置、环境变量、部署与验收。

---

## 1. 文档目的

- 把 Stripe Test Mode 的配置、部署、验收步骤文档化，避免 oral 传递导致漏配。
- 明确 **Dashboard 要建什么、`.env` 要填什么、部署后怎么验**。
- 当前阶段 **只做 Test Mode 联调**，不公开 Live 收款。

---

## 2. 当前前提

| 项 | 说明 |
|---|---|
| P0 支付安全硬化 | commit `22ce6a6e98b8944a308572c4bbded3430a053a0b`（`chore(payment): harden production payment configuration`）已 push 至 `origin/master` |
| 后端部署状态 | **尚未部署**本轮硬化后的后端；部署前须先完成本文档中的 Dashboard 与 `.env` 配置 |
| 支付模式目标 | 当前只做 **Stripe Test Mode**（`sk_test_` / Test mode Price / Test mode Webhook） |
| 线上域名 | 前端：`https://videodown.cozyguidehub.com`；后端 API：`https://api-videodown.cozyguidehub.com` |

P0 硬化已完成的能力（代码侧，无需再改）：

- `APP_ENV=production` 时禁止 Mock 支付 fallback
- 生产环境不注册 `/api/billing/mock/pay/{order_no}`
- 启动期 `_validate_production_config()` 硬校验 Stripe 相关配置
- Webhook 支持 `checkout.session.completed` / `async_payment_*` / `expired`
- Webhook 金额、币种、`plan_code` 校验

---

## 3. Stripe Dashboard Test Mode 创建步骤

### 3.1 开启 Test mode

1. 登录 [Stripe Dashboard](https://dashboard.stripe.com)。
2. 右上角确认已切换到 **「测试模式 / Test mode」**（开关为测试状态）。
3. 后续创建的 Product、Price、Webhook、API 密钥均为 **Test mode** 资源。

### 3.2 创建 Product

1. 进入 **产品目录 → 添加产品**（Product catalog → Add product）。
2. 建议名称：**SaveAny VIP**。
3. 类型：**一次性付款**（One-time），非订阅（Subscription）。
4. 保存 Product。

> **说明：** 代码支持「1 个 Product + 4 个 Price」，也支持 4 个独立 Product；推荐 1 Product 便于维护。

### 3.3 创建 4 个 one-time Price

在 **SaveAny VIP** 下（或分别创建 4 个 Product）添加 **4 个一次性 Price**：

| 用途 | 名称建议 | 类型 | 币种 | 金额 |
|---|---|---|---|---|
| 月度 | 月度会员 | One-time | CNY | ¥19.00 |
| 季度 | 季度会员 | One-time | CNY | ¥49.00 |
| 年度 | 年度会员 | One-time | CNY | ¥168.00 |
| 终身 | 终身会员 | One-time | CNY | ¥399.00 |

创建完成后，每个 Price 会生成以 `price_` 开头的 ID，分别填入 `.env` 中对应的 `STRIPE_PRICE_*` 变量（见第 7 节）。

### 3.4 开启支付方式（Test Mode 联调阶段）

1. 进入 **设置 → 支付方式**（Settings → Payment methods）。
2. **Test Mode 联调建议先只开启 Card（银行卡）**，降低首轮复杂度。
3. Alipay / WeChat Pay 可在 Card 联调通过后再单独开启并测试异步 webhook。

---

## 4. 套餐和金额映射表

代码中套餐、本地订单金额、Stripe Price、环境变量对应关系如下。**Stripe Price 的 `unit_amount` 必须与「金额（分）」列完全一致**，否则 webhook 金额校验会拒绝发 VIP。

| plan_code | 展示价 | 金额（分） | 有效期 | 环境变量（Price ID） | 本地价格 env |
|---|---|---|---|---|---|
| monthly | ¥19 | 1900 | 30 天 | `STRIPE_PRICE_MONTHLY` | `PLAN_PRICE_MONTHLY_CENTS=1900` |
| quarterly | ¥49 | 4900 | 90 天 | `STRIPE_PRICE_QUARTERLY` | `PLAN_PRICE_QUARTERLY_CENTS=4900` |
| yearly | ¥168 | 16800 | 365 天 | `STRIPE_PRICE_YEARLY` | `PLAN_PRICE_YEARLY_CENTS=16800` |
| lifetime | ¥399 | 39900 | 终身 | `STRIPE_PRICE_LIFETIME` | `PLAN_PRICE_LIFETIME_CENTS=39900` |

数据库 `plans` 表在 backend 启动时由 `seed_default_plans()` 按上述 env 同步；**不要只在 Dashboard 改价而不同步 `.env`**。

---

## 5. Currency 说明

- 当前代码默认 **`BILLING_CURRENCY=cny`**，前端文案与定价均按 **人民币（CNY）** 设计。
- Stripe Dashboard 创建 Price 时，币种须选 **CNY**，且 `unit_amount` 使用「分」为单位（如 ¥19 → `1900`）。
- 若 Stripe 账户 **不支持 CNY 收款**，需要同步调整：
  - `.env` 中 `BILLING_CURRENCY`（如改为 `usd`）
  - Dashboard 中 Price 币种与金额
  - `PLAN_PRICE_*_CENTS` 与前端展示文案
- **不要**只改 Dashboard 不改 `.env`，也不要只改 `.env 不改 Dashboard。

---

## 6. Webhook endpoint 配置

### 6.1 创建 Endpoint

1. Stripe Dashboard → **开发者 → Webhooks**（Developers → Webhooks）。
2. 确认处于 **Test mode**。
3. 点击 **添加端点 / Add endpoint**。
4. **Endpoint URL** 填写：

```
https://api-videodown.cozyguidehub.com/api/billing/webhook
```

> 注意：路径是 `/api/billing/webhook`，不是 `/api/payment/webhook`。

5. 创建后复制 **Signing secret**（`whsec_...`）→ 写入 `STRIPE_WEBHOOK_SECRET`（勿提交 Git）。

### 6.2 必须监听的事件

在 Endpoint 中勾选以下事件（与 backend `payment_service.py` 已实现逻辑对应）：

| 事件 | 用途 |
|---|---|
| `checkout.session.completed` | 同步卡支付成功 → 订单 `paid` → 发放 VIP |
| `checkout.session.async_payment_succeeded` | Alipay / WeChat Pay 等异步支付成功 |
| `checkout.session.async_payment_failed` | 异步支付失败 → pending 订单标记为 `canceled` |
| `checkout.session.expired` | Checkout Session 过期 → pending 订单标记为 `expired` |

**Test Mode 首轮联调（仅 Card）：** 至少配置 `checkout.session.completed` 与 `checkout.session.expired` 即可跑通主链路；若计划启用 Alipay/WeChat，**必须**同时配置两个 `async_payment_*` 事件。

### 6.3 Nginx 要求

确保 `POST /api/billing/webhook` 由 Nginx 反向代理到 backend（uvicorn），**不要被 SPA 的 `try_files` 落到 `index.html`**。Webhook 必须返回 JSON，Stripe 才会认为投递成功。

---

## 7. backend/.env 模板

在服务器 `backend/.env` 中配置（**仅占位符，勿将真实密钥写入 Git**）：

```env
# --- 运行环境 ---
APP_ENV=production

# --- 支付模式（生产 + Stripe Test 联调）---
MOCK_PAYMENT=false
ENABLE_MOCK_PAY_ROUTE=false

# --- Stripe Test Mode 密钥（Dashboard → 开发者 → API 密钥，Test mode）---
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# --- Stripe Price ID（Test mode Dashboard 创建的 price_xxx）---
STRIPE_PRICE_MONTHLY=price_xxx
STRIPE_PRICE_QUARTERLY=price_xxx
STRIPE_PRICE_YEARLY=price_xxx
STRIPE_PRICE_LIFETIME=price_xxx

# --- 支付方式（须与 Dashboard 已开启方式一致；Test 联调可先只用 card）---
STRIPE_PAYMENT_METHODS=card

# --- 前端 / CORS ---
FRONTEND_URL=https://videodown.cozyguidehub.com
ALLOWED_ORIGINS=https://videodown.cozyguidehub.com

# --- 鉴权（至少 32 字符，可用 openssl rand -hex 32 生成）---
JWT_SECRET=<至少32字符随机串>

# --- 定价（须与 Stripe Price unit_amount 一致）---
BILLING_CURRENCY=cny
PLAN_PRICE_MONTHLY_CENTS=1900
PLAN_PRICE_QUARTERLY_CENTS=4900
PLAN_PRICE_YEARLY_CENTS=16800
PLAN_PRICE_LIFETIME_CENTS=39900
```

**说明：**

- Stripe Test Mode 可先只测 **card**；`STRIPE_PAYMENT_METHODS=card` 即可。
- Alipay / WeChat Pay 可在 Card 联调通过后，改为 `card,alipay,wechat_pay` 并单独验收异步 webhook。
- `APP_ENV=production` 会触发启动硬校验：缺 `STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、任一 `STRIPE_PRICE_*`、`JWT_SECRET` 不足 32 字符等，**进程会直接退出**。
- **不要把 `.env` 或真实密钥提交到 Git。**

其他可能需要的变量（非支付专用，但 `check_production.py` 可能检查）：

```env
DEEPSEEK_API_KEY=sk-xxx
```

---

## 8. 部署前检查

在服务器或本地（已配置好 `.env` 的环境）执行：

```bash
cd backend
python scripts/check_production.py
python -m compileall app
```

**关于 `check_production.py` 与启动校验的差异：**

| 场景 | `check_production.py` | `main.py` 启动校验 |
|---|---|---|
| `MOCK_PAYMENT=true` | 可能仅 **WARN** | **FAIL，进程不启动** |
| `STRIPE_PRICE_*` 缺失 | 可能仅 **WARN** | **FAIL，进程不启动** |
| `ENABLE_MOCK_PAY_ROUTE=true` | 不检查 | **FAIL，进程不启动** |
| `FRONTEND_URL` 非 https | 可能仅 **WARN** | **FAIL，进程不启动** |
| `sk_test_` 密钥 | **WARN**（提醒非 Live） | 允许（Test 联调预期） |

**结论：**

- `check_production.py` 当前可能比 `main.py` 启动校验 **更宽松**。
- **最终以后端能否成功启动为准**（`systemctl status` / 日志无 `RuntimeError`）。
- **WARN 不应忽略**；有 WARN 时应逐项确认后再部署。

---

## 9. 后端部署步骤

以下为命令模板，路径与服务名按实际环境调整：

```bash
cd /home/ubuntu/Video-Free-downloader
git pull origin master

cd backend
source .venv/bin/activate

python -m compileall app
python scripts/check_production.py

sudo systemctl restart videodown-backend
sudo systemctl status videodown-backend --no-pager
```

**部署后立刻查看日志**（若启动失败，通常是 `.env` 未通过 `_validate_production_config()`）：

```bash
sudo journalctl -u videodown-backend -n 50 --no-pager
```

常见启动失败原因：缺少 `STRIPE_PRICE_*`、`JWT_SECRET` 过短、`MOCK_PAYMENT=true`、`FRONTEND_URL` 非 `https://` 开头。日志中**只会列出缺失项名称，不会打印密钥内容**。

---

## 10. 部署后验收

### 10.1 检查 billing 模式

```bash
curl -s https://api-videodown.cozyguidehub.com/api/billing/mode
```

**预期（示例）：**

```json
{"mock": false, "payment_methods": ["card"]}
```

- `mock` 必须为 **`false`**。
- 若仍为 `true`：检查 `MOCK_PAYMENT`、`APP_ENV`、`STRIPE_SECRET_KEY` 是否配置正确。

### 10.2 检查 mock-pay 已关闭

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  https://api-videodown.cozyguidehub.com/api/billing/mock/pay/foo
```

**预期 HTTP 状态码：`404`**

- P0 硬化后，生产环境 **不注册** mock-pay 路由；404 表示白嫖入口已封堵。
- 若返回 403/200：检查 `ENABLE_MOCK_PAY_ROUTE` 与 `APP_ENV`，确认已部署 commit `22ce6a6` 及之后版本。

### 10.3 健康检查（可选）

```bash
curl -s https://api-videodown.cozyguidehub.com/api/health
```

---

## 11. Stripe 测试支付流程

完整用户路径验收（浏览器）：

1. 打开 `https://videodown.cozyguidehub.com`
2. **注册** 或 **登录** 测试账号
3. 进入 **套餐页** `/pricing`
4. 确认页面 **无** 黄色「MOCK / 模拟支付」提示条
5. 选择 **月度会员（monthly）**，点击购买
6. 浏览器跳转至 **Stripe Checkout**（Hosted 页面，域名为 `checkout.stripe.com`）
7. 使用 Stripe 测试卡：
   - 卡号：`4242 4242 4242 4242`
   - 有效期：任意未来日期（如 `12/34`）
   - CVC：任意三位（如 `123`）
   - 邮编：任意
8. 完成支付后回跳 **`/payment/success?order_no=...`**
9. 等待 success 页轮询（最多约 30 秒），应显示支付成功
10. 进入 **个人中心** `/account`：
    - 会员状态应为 VIP
    - **我的订单** 中该订单状态为 **已支付 / paid**
    - 订单 **不应** 带 MOCK 标签

---

## 12. Webhook 验收

### 12.1 Stripe Dashboard

1. 完成第 11 节测试支付后，进入 **开发者 → Webhooks → 对应 Endpoint → 事件**。
2. 找到 **`checkout.session.completed`**（Card 测试通常为此事件）。
3. 确认 **HTTP 状态码为 200**，响应体含 `"ok": true`。

### 12.2 本地数据一致性

| 检查项 | 预期 |
|---|---|
| 订单状态 | `paid` |
| VIP | 用户 `is_vip=true`，到期时间约 +30 天（monthly） |
| Webhook 幂等 | 同一 `event_id` 重复投递不会重复加 VIP |

### 12.3 可选：Stripe CLI 本地转发（开发机调试）

若在本地调试 webhook（非生产验收必需）：

```bash
stripe listen --forward-to http://127.0.0.1:8000/api/billing/webhook
```

生产验收以 **Dashboard 上 Endpoint 直连 `api-videodown.cozyguidehub.com`** 为准。

---

## 13. 常见问题排查

### 13.1 后端启动失败

检查 `.env` 是否满足 `APP_ENV=production` 下的硬校验：

| 配置项 | 要求 |
|---|---|
| `APP_ENV` | `production` |
| `MOCK_PAYMENT` | `false` |
| `ENABLE_MOCK_PAY_ROUTE` | `false` |
| `STRIPE_SECRET_KEY` | 非空 |
| `STRIPE_WEBHOOK_SECRET` | 非空 |
| `STRIPE_PRICE_MONTHLY/QUARTERLY/YEARLY/LIFETIME` | 四个均非空 |
| `FRONTEND_URL` | 以 `https://` 开头 |
| `JWT_SECRET` | 非默认值，且 ≥ 32 字符 |

查看日志：`sudo journalctl -u videodown-backend -n 100 --no-pager`

### 13.2 付了钱但没有 VIP

1. Stripe Dashboard → Webhooks → 查看该笔支付对应事件是否 **200**。
2. 若为 **4xx**：常见原因
   - `STRIPE_WEBHOOK_SECRET` 与 Dashboard Signing secret 不一致
   - Endpoint URL 错误（路径、HTTPS、Nginx 未转发）
   - 金额/币种与本地订单不一致（见 13.5）
   - `metadata.plan_code` 与订单不一致
3. 若为 **5xx**：查看 backend 日志中的 `webhook 处理失败`。
4. 用户可在 `/account` 刷新订单；success 页轮询超时后订单可能仍为 `pending`，以 webhook 成功为准。

### 13.3 `/api/billing/mode` 仍返回 `"mock": true`

- 确认 `MOCK_PAYMENT=false`
- 确认 `APP_ENV=production`
- 确认 `STRIPE_SECRET_KEY` 已配置且 backend 已重启
- 生产环境缺 `STRIPE_SECRET_KEY` **不会** fallback mock，而会报错；若仍 mock，可能是旧进程或未部署新代码

### 13.4 mock-pay 不是 404

- 确认 `ENABLE_MOCK_PAY_ROUTE=false`
- 确认 `APP_ENV=production`
- 确认已部署 commit `22ce6a6` 及之后版本
- 重启 backend 后再测

### 13.5 金额校验失败（Webhook 400）

日志或 Stripe 事件详情中可能出现「金额/币种与 Stripe 不一致」：

- 对比 `PLAN_PRICE_*_CENTS` 与 Dashboard Price 的 **unit_amount**
- 对比 `BILLING_CURRENCY` 与 Dashboard Price 的 **currency**
- 修改后须 **重启 backend**（`seed_default_plans` 会同步 DB）

### 13.6 check_production.py 通过但 uvicorn 起不来

- 以 **启动日志** 为准；脚本 WARN 项可能对应启动 FAIL 项（见第 8 节对照表）
- 逐项补齐 `.env` 后重试

---

## 14. Test Mode 到 Live Mode 切换提醒

Test Mode 联调通过后，切换真实收款前 **必须** 完成：

| 项 | Test Mode | Live Mode |
|---|---|---|
| Dashboard 开关 | Test mode | **Live mode** |
| API 密钥 | `sk_test_...` | `sk_live_...` |
| Webhook Signing secret | Test endpoint 的 `whsec_...` | **新建 Live endpoint** 的 `whsec_...` |
| Price ID | Test mode 的 `price_...` | **在 Live mode 重新创建** Product/Price |
| Webhook URL | 同上（建议 Live 单独 endpoint） | `https://api-videodown.cozyguidehub.com/api/billing/webhook` |

**切换步骤概要：**

1. Stripe Dashboard 切换到 **Live mode**。
2. 重新创建 Product / 4 个 Price（金额与 `PLAN_PRICE_*_CENTS` 一致）。
3. 新建 Live Webhook endpoint，勾选第 6.2 节全部事件。
4. 更新 `.env`：`STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、四个 `STRIPE_PRICE_*`。
5. 运行 `python scripts/check_production.py`（Live 下 `sk_test_` 不应再出现）。
6. 重启 backend，**重新跑一遍第 10–12 节验收**（可用 Live 小额真实支付验证）。

---

## 15. 不要做的事

- **不要**把真实密钥（`sk_*`、`whsec_*`、`.env` 全文）写入 Git 或发到公开渠道。
- **不要**在未确认 Webhook 稳定 200、VIP 正常发放前，对外公开收款或大规模推广。
- **不要**忽略 `check_production.py` 的 **WARN**（可能对应启动失败项）。
- **不要**把 Mock 支付用于真实用户收费；生产环境 mock-pay 路由应 **404**。
- **不要**只在 Stripe Dashboard 改价而不同步 `PLAN_PRICE_*_CENTS` 与 `STRIPE_PRICE_*`。
- **不要**用 Test mode 的 Price ID / Webhook secret 配 Live mode 密钥（或反之）。

---

## 附录：相关文档与代码位置

| 资源 | 路径 |
|---|---|
| 生产部署总清单 | [docs/生产部署清单.md](./生产部署清单.md) |
| 配置定义 | `backend/app/core/config.py` |
| 启动硬校验 | `backend/app/main.py` → `_validate_production_config()` |
| Webhook 处理 | `backend/app/services/payment_service.py` |
| 部署前脚本 | `backend/scripts/check_production.py` |
| 支付逻辑测试 | `backend/scripts/test_billing.py` |

---

*文档版本：与 commit `22ce6a6`（P0 支付安全硬化）对齐。*
