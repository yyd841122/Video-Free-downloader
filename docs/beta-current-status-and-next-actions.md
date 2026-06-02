# SaveAny Beta 当前状态与下一步执行记录

> **产品：** SaveAny 万能视频下载器  
> **线上：** https://videodown.cozyguidehub.com  
> **文档版本：** 2026-06-02（Agent Run #002）  
> **最后 Agent 同步：** 2026-06-02 — Creem preliminary_go, human_review_pending · LS/Paddle ready_to_send  
> **相关文档：** [paid-beta-test-plan.md](./paid-beta-test-plan.md) · [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md) · [mor-application-prep.md](./mor-application-prep.md) · [beta-feedback-log.md](./beta-feedback-log.md)

---

## 1. 当前阶段

| 项 | 说明 |
|----|------|
| 阶段名称 | **Beta Phase** |
| 子阶段 | **B1**（受控扩大测试 + 小额人工付费验证）与 **B2**（体验优化）**并行推进** |
| 性质 | **不是** 公开发布 / 正式商业化阶段 |
| 收款 | Test Mode 技术验证 + **人工收款** 为当前唯一真实收入路径 |

---

## 2. 已完成能力

| 能力 | 状态 | 备注 |
|------|------|------|
| Web MVP | ✅ | 注册 / 登录；Bilibili / 抖音 / X / mp4 解析；720p / 1080p 下载 |
| 大文件验证 | ✅ | 长视频 45:55 / 851.8MB 已验证 |
| AI Summary MVP | ✅ | SRT/VTT 上传；摘要 / 思维导图 / 问答；字幕编码兼容已修复 |
| ASR | ❌ 关闭 | 定价与文案均不承诺 ASR |
| Stripe Test Mode | ✅ 技术链路 | Checkout → Webhook → VIP；**非正式扣款** |
| 人工 VIP 开通 | ✅ | `admin_grant_vip.py` 已部署验证；MAN 订单 + audit log |
| 人工 VIP 调整 | ✅ | `admin_adjust_vip.py`（list-grants / rollback / revoke）已部署验证 |
| Account / Pricing Beta 文案 | ✅ | MAN vs Test Mode、人工开通说明、权益边界（commit 7980b5c） |
| P0 空白页热修复 | ✅ | i18n 邮箱 `@` 转义；`/pricing`、`/account` 恢复（commit 10eff50） |

---

## 3. 当前真实限制

| 限制 | 影响 |
|------|------|
| **Stripe Live 未打通** | 站内「购买」按钮走 Test Mode，不能描述为正式自动收款 |
| **MoR 未接入** | 无国际信用卡 Live 扣款；Creem **preliminary_go / human_review_pending** — **非正式 Live 批准** |
| **ASR 关闭** | 无字幕视频须上传 SRT/VTT 才能 AI 总结 |
| **人工收款无法规模化** | 依赖管理员核对付款 + SSH 开通；适合 5–20 人 Beta |
| **平台解析受原平台限制** | 登录 / cookies、地区、清晰度上限等因平台而异 |
| **无 Admin Web** | 运维仅 SSH CLI，无浏览器管理后台 |

---

## 4. 当前最高优先级（本轮 P0/P1）

| 优先级 | 工作项 | 状态 |
|--------|--------|------|
| P0 | **MoR 调研 — Creem 人工审核待回复** | preliminary_go；human_review_pending；**不接 webhook / Live** |
| P0 | **MoR 备选 — Lemon Squeezy / Paddle** | **ready_to_send**；Creem No-Go 或 Pending 过久时再发 |
| P0 | **付费 Beta 扩展（10–20 人）** | 槽位已建；邀请话术见 paid-beta-test-plan §4；**待人工私聊** |
| P0 | **i18n `@` 规范检查**（vue-i18n 邮箱转义） | 2026-05-31 巡检通过 |
| P0 | **Beta 收款文案巡检**（Pricing / Account / Payment） | 2026-05-31 巡检通过 |
| — | **不做** Desktop 客户端 | 范围外 |
| — | **不做** ASR 开放 | 范围外 |
| — | **不做** Admin Web / Admin API | 范围外 |

---

## 5. 待观察指标

| 指标 | 观察方式 | 当前 |
|------|----------|------|
| 有多少人 **愿意付费** | 邀请话术回复、咨询邮件 | **0 / 目标 10–20**（2026-06-02 批次启动，待联系） |
| 是否有人 **实际支付**（人工通道） | MAN 订单 + 收款记录 | **0** — Pending |
| **人工开通** 流程是否顺畅 | 开通耗时、用户是否收到权益 | 工具已就绪，待样本 |
| 用户是否理解 **Test Mode vs 人工收款** | 反馈、误付投诉 | 文案已加强，待观察 |
| 用户最看重 **下载 / 高清 / 批量 / AI 总结** 哪一项 | Beta 反馈表 | To confirm |
| MoR 平台回复 | mor-outreach-tracker §4 | **Creem 初步回复已收** — human_review_pending；LS/Paddle ready_to_send |

记录模板见 [paid-beta-test-plan.md](./paid-beta-test-plan.md)、[paid-beta-feedback-tracker.md](./paid-beta-feedback-tracker.md)、[beta-feedback-log.md](./beta-feedback-log.md)、[beta-operations-log.md](./beta-operations-log.md)。

---

## 6. 下一步推荐（决策树）

```
MoR（Creem）
├── human_review_pending（preliminary_go）
│   ├── 人工确认 Go → KYC / Live Mode / payout 设置（仍不写 webhook 直至 Live approval）
│   ├── 要求改合规文案 → 先改网站再提交 Live review
│   └── No-Go → 发送 Lemon Squeezy / Paddle 问询
付费意愿反馈
├── 1–3 人愿意付费且流程顺畅
│   └── 维持 10–20 人受控 Beta
├── 用户不理解支付 / 误以为 Test Mode 已扣款
│   └── 继续优化 Pricing / Account / Payment 文案
└── 长期无人愿意付费
    └── 回到需求验证（功能优先级、定价、目标用户）
```

| 场景 | 推荐动作 |
|------|----------|
| Creem human_review_pending | **1.** 等 Creem 人工回复 **2.** 若 Go → KYC / Live Mode / payout **3.** 若要求改文案 → 先改网站 **4.** 若 No-Go → 发 LS/Paddle **5.** **不接 webhook 直至 Live approval 明确** |
| Lemon Squeezy / Paddle | **ready_to_send** — Creem No-Go 或 Pending 过久时人工发送 message pack §4/§5 |
| 有 1–3 笔真实人工付费 | 维持 10–20 人 cohort；更新 [paid-beta-feedback-tracker.md](./paid-beta-feedback-tracker.md) |
| 用户混淆 Test / Live | 强化页面说明；客服统一话术（support@cozyguidehub.com） |
| Creem / Lemon Squeezy 回复积极 | Creem 已 preliminary_go；**暂不写生产 Webhook** 直至 **Live approval 明确** |
| MoR 全部 No-Go | 评估国内个体户 + 支付宝/微信（中长期）；短期维持人工收款 |
| 解析 / AI 失败率高 | 优化失败任务指引；平台兼容性回归（见 [platform-compatibility-samples.md](./platform-compatibility-samples.md)） |

---

## 7. 近期 Git 里程碑（供交接）

| Commit | 说明 |
|--------|------|
| `7980b5c` | Account/Pricing Beta 收款与 MAN 订单文案 |
| `10eff50` | P0：i18n 邮箱 `@` 转义；修复 /pricing 与 /account 空白页 |
| `ba455ad` | admin_adjust_vip.py 手动 VIP 调整 CLI |

---

## 8. 明确不在本轮范围

- Stripe Live 接入  
- MoR 生产代码与 Webhook（**含 Creem webhook — Live approval 前不接**）  
- ASR 启用  
- Desktop 项目  
- Admin Web / 公网 Admin API  
- 真实 VIP 开通 / 撤销操作（仅文档与文案）  
- 修改生产数据库  

---

*本文档随 Beta 反馈与 MoR 调研进展更新；以代码与线上行为为准。*
