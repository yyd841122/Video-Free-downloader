# SaveAny 人工收款与手动开通 VIP 操作 SOP

> **产品：** SaveAny 万能视频下载器  
> **阶段：** Beta（Stripe Live / MoR 正式接入前）  
> **文档版本：** 2026-05-28  
> **相关文档：** [monetization-paths.md](./monetization-paths.md) · [stripe-test-mode-validation-report.md](./stripe-test-mode-validation-report.md)

**声明：** 本文档为内部运维 SOP，不构成法律或税务意见。文中 **不记录** API Key、`.env` 内容、支付截图或用户隐私备注。

---

## 1. 目的

本 SOP 用于 **Stripe Live、MoR（Creem / Paddle 等）正式接入之前** 的短期人工收款与 VIP 履约流程。

适用场景包括但不限于：

| 场景 | `reason` 示例 |
|------|----------------|
| 微信收款 | `wechat payment` |
| 支付宝收款 | `alipay payment` |
| PayPal 收款 | `paypal payment` |
| 内测赠送 | `beta gift` |
| 客服补偿 | `support compensation` |
| 手动续费 / 测试开通 | `manual test grant` |

用户通过个人收款码 / PayPal 等付款后，由管理员在服务器 SSH 执行 CLI，按 **注册邮箱** 开通对应套餐 VIP。

---

## 2. 当前能力状态

| 项 | 状态 |
|----|------|
| CLI 工具 | 已上线：`backend/scripts/admin_grant_vip.py` |
| 默认模式 | **dry-run**（不加 `--confirm` 不写库） |
| 真实写入 | 仅 `--confirm` 时创建订单并发放 VIP |
| 人工订单号 | 以 `MAN` 开头（与 Stripe `FVD*` 区分） |
| Account 展示 | 「我的订单」可显示 MAN 订单；会员状态在账户页展示 |
| 审计日志 | `backend/data/audit/manual_grants.jsonl`（**不提交 git**） |
| Stripe Live | **当前不作为主路径** |
| 自动支付 | **当前不接** 微信/支付宝官方商户、MoR 自动回调 |

技术说明：

- VIP 发放复用 `mark_order_paid()`，与 Stripe Test Mode / Webhook 逻辑一致（叠加规则、终身会员规则相同）。
- 订单表 `amount_cents` 使用 **套餐标价**（如月度 ¥19 = `1900` 分）；实际收款金额记在审计字段 `amount_cents_reported`（可选 CLI 参数）。

---

## 3. 操作前检查清单

执行前 **必须** 逐项确认：

1. **用户已注册** — 未注册账号无法开通（CLI 会 `user_not_found`）。
2. **邮箱 = 注册邮箱** — 与用户登录 Account 的邮箱完全一致（大小写不敏感，会自动转小写）。
3. **邮箱无误** — 写错邮箱会给错人开通，无法一键撤销。
4. **套餐确认** — 仅允许：`monthly` | `quarterly` | `yearly` | `lifetime`。
5. **收款方式 / 原因** — `--reason` 使用简短英文或固定短语（见第 1 节表），不写长段隐私。
6. **实收金额（分）** — 与对外标价对照：

   | 套餐 | 标价 | `amount_cents` / `--amount-cents-reported` |
   |------|------|------------------------------------------|
   | monthly | ¥19 | `1900` |
   | quarterly | ¥49 | `4900` |
   | yearly | ¥168 | `16800` |
   | lifetime | ¥399 | `39900` |

7. **`request-id` 唯一** — 同一笔收款只用一个 ID，防止重复 confirm。
8. **先 dry-run，再 confirm** — 禁止跳过预览。

**终身会员注意：** 目标用户已是 lifetime 时，再发 `monthly` / `quarterly` / `yearly` 默认 **失败**；若确需操作须加 `--force`（见 CLI `--help`）。

---

## 4. dry-run 命令模板

在服务器上进入 backend 目录后执行（**不要** 加 `--confirm`）：

```bash
cd /path/to/backend

python scripts/admin_grant_vip.py \
  --email user@example.com \
  --plan monthly \
  --reason "wechat payment" \
  --admin-email support@cozyguidehub.com
```

**说明：**

- 不加 `--confirm` → 默认 dry-run。
- **不写** 数据库、**不写** 审计 JSONL。
- 输出含 `DRY_RUN=yes`、`VIP_BEFORE`、`VIP_AFTER_PREVIEW`、`CONFIRM_REQUIRED=yes`。
- 核对预览无误后再执行第 5 节 confirm。

---

## 5. confirm 命令模板

确认 dry-run 预览正确后：

```bash
python scripts/admin_grant_vip.py \
  --email user@example.com \
  --plan monthly \
  --reason "wechat payment" \
  --admin-email support@cozyguidehub.com \
  --amount-cents-reported 1900 \
  --request-id manual-20260528-001 \
  --confirm
```

**说明：**

- `--amount-cents-reported`：可选；记录 **实际人工收款**（分），不传则审计中为 `null`。
- `--request-id`：confirm 时建议必填；重复 ID 会被拒绝（`duplicate_request_id`）。
- `--confirm`：创建 `MAN*` 订单、发放 VIP、追加审计日志。

成功时 CLI 输出示例字段：

- `MANUAL_VIP_GRANT_STATUS=success`
- `ORDER_NO=MAN...`
- `AUDIT_LOG_WRITTEN=yes`

---

## 6. request-id 规则

**建议格式：**

```
manual-YYYYMMDD-序号
manual-YYYYMMDD-邮箱前缀-plan
manual-20260528-you-163-monthly-001
```

**要求：**

| 规则 | 说明 |
|------|------|
| 一笔收款一个 ID | 同一笔微信/支付宝/PayPal 到账只对应一个 `request-id` |
| 全局唯一 | 已成功写入审计的 `request-id` 不可重复使用 |
| 防双开 | 避免两人对同一付款各执行一次 confirm |

示例（按日 + 序号）：

- `manual-20260528-001`
- `manual-20260528-002`

---

## 7. 操作后检查

confirm 成功后按序检查：

1. CLI：`MANUAL_VIP_GRANT_STATUS=success`
2. CLI：`ORDER_NO` 以 `MAN` 开头
3. CLI：`AUDIT_LOG_WRITTEN=yes`
4. 服务器：查看审计最后一行（见第 8 节）
5. 通知用户：刷新 [Account 页](https://videodown.cozyguidehub.com/account)（或对应前端 `/account`）
6. Account：**会员有效期** / 终身会员文案正确
7. Account：**我的订单** 出现 MAN 订单，状态 **已支付**，金额与套餐一致（如 ¥19）
8. 功能抽测：高清下载、AI 配额等会员权益可用（可选）

---

## 8. 审计日志检查命令

```bash
tail -n 5 backend/data/audit/manual_grants.jsonl
```

**关键字段说明：**

| 字段 | 含义 |
|------|------|
| `admin_email` | 操作管理员邮箱 |
| `target_user_email` | 被开通用户注册邮箱 |
| `plan_code` | 套餐代码 |
| `reason` | 简短原因（收款渠道/补偿类型） |
| `order_no` | MAN 订单号 |
| `amount_cents` | 订单标价（分） |
| `amount_cents_reported` | 实收金额（分，可选） |
| `request_id` | 幂等键（若传入） |
| `vip_expire_at_before` / `vip_expire_at_after` | 开通前后到期时间 |
| `is_lifetime_vip_before` / `is_lifetime_vip_after` | 终身标记 |
| `dry_run` | confirm 记录为 `false` |
| `force` | 是否使用 `--force` |

---

## 9. 误操作处理

**调整工具：** `backend/scripts/admin_adjust_vip.py`（与开通 CLI 分离；审计写入 `manual_vip_adjustments.jsonl`）

| 情况 | 处理 |
|------|------|
| 仅执行了 dry-run | **无需处理**，数据库与审计均未变更 |
| confirm 写错邮箱 | 错号 `revoke-vip`；正确号重新 `admin_grant_vip` |
| 怀疑重复开通 | `list-grants` 查记录；必要时 `rollback-last-manual-grant` |
| 开错套餐 / 需撤销最近一次人工开通 | `rollback-last-manual-grant`（恢复 grant 的 before 状态） |
| 用户退款 / 测试账号恢复 | `revoke-vip`（可选 `--mark-order-refunded`） |
| 需要手改数据库 | **严禁**；只用下方 CLI |

### 查询人工开通记录

```bash
python scripts/admin_adjust_vip.py \
  --action list-grants \
  --email user@example.com \
  --limit 10
```

### 回滚最近一次人工开通（dry-run）

```bash
python scripts/admin_adjust_vip.py \
  --action rollback-last-manual-grant \
  --email user@example.com \
  --reason "refund requested" \
  --admin-email support@cozyguidehub.com \
  --request-id adjust-YYYYMMDD-user-rollback-001 \
  --mark-order-refunded
```

确认后加 `--confirm`。指定订单：`--order-no MAN...`。

### 撤销 VIP（dry-run）

```bash
python scripts/admin_adjust_vip.py \
  --action revoke-vip \
  --email user@example.com \
  --reason "refund completed" \
  --admin-email support@cozyguidehub.com \
  --request-id adjust-YYYYMMDD-user-revoke-001
```

终身会员须加 `--force`。确认后加 `--confirm`。

写操作均须 `--reason`、`--admin-email`、`--request-id`；默认 dry-run，仅 `--confirm` 写库。

---

## 10. 安全限制

1. **仅管理员 SSH** 到生产/预发服务器执行，不向公网暴露 Admin API。
2. **无** 网页后台开通入口（Phase 1）。
3. **不要** 在即时通讯中转发用户付款截图或完整聊天记录。
4. **`reason` 不写** 敏感隐私（身份证号、银行卡号、完整转账备注等）。
5. **不要** 将 `backend/data/audit/` 提交到 git（已在 `.gitignore`）。
6. **不要** 在文档、聊天、审计中写入 `.env`、密钥、Webhook secret。
7. **不要** 对未注册用户开通（CLI 会失败）。
8. **不要** 跳过 dry-run 直接 confirm。

---

## 11. 已验证记录

以下为 Beta 阶段一次 **真实 confirm** 验证（邮箱脱敏）：

| 项 | 记录 |
|----|------|
| 测试账号 | `y***@163.com`（完整邮箱：`you@163.com`） |
| 套餐 | `monthly` |
| 订单号 | `MAN1779926517B209F93D` |
| Account | 会员有效期至 **2026-06-27** |
| 我的订单 | MAN 订单，**已支付**，**¥19** |
| 审计 | `manual_grants.jsonl` 写入成功 |
| **结论** | **人工收款 → CLI 开通 → Account 展示** 链路通过 |

---

## 12. 后续升级（非当前 SOP 范围）

| 方向 | 说明 |
|------|------|
| Admin API | `POST /api/admin/vip/grant` + `ADMIN_EMAILS` 鉴权 |
| Admin Web | `/admin/vip` 搜索用户、开通、查记录 |
| 退款 / 撤销工具 | 误开通回滚、订单状态修正 |
| 订单 UI | Account 区分「人工开通」标签 |
| 导出 | 人工收款与审计 CSV 导出 |
| 自动支付 | MoR（Creem / Lemon Squeezy / Paddle）或国内官方支付接入 |

正式收款上线后，本 SOP 仍可作为 **兜底人工履约** 流程保留。

---

## 附录：常用路径

| 项 | 路径 / 命令 |
|----|-------------|
| CLI | `backend/scripts/admin_grant_vip.py` |
| 服务逻辑 | `backend/app/services/manual_grant_service.py` |
| 审计目录 | `backend/data/audit/`（需存在写权限） |
| 单元测试 | `python scripts/test_admin_grant_vip.py` |

*文档随 CLI 行为变更而更新；以仓库内脚本 `--help` 为准。*
