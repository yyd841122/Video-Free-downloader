# SaveAny Post Soft Launch 归档与 Beta 阶段路线图

> **产品：** SaveAny 万能视频下载器  
> **线上地址：** https://videodown.cozyguidehub.com  
> **后端 API：** https://api-videodown.cozyguidehub.com  
> **文档版本：** 2026-05-25  
> **相关文档：** [mvp-soft-launch-test-guide.md](./mvp-soft-launch-test-guide.md) · [soft-launch-invite-package.md](./soft-launch-invite-package.md) · [ai-summary-mvp-validation.md](./ai-summary-mvp-validation.md)

---

## 1. Soft Launch 通过结论

**SaveAny MVP 已通过 Soft Launch 内测，可进入 Beta 阶段。**

内测期间核心链路（解析、下载、会员、Stripe Test Mode 支付、AI 总结 MVP、磁盘保护、注册邮箱校验）均已验证可用，未发现阻断扩大测试的 P0 问题。团队可将下一阶段目标定为 **受控扩大 Beta** 与 **真实用户反馈沉淀**，而非立即公开发布或正式收费。

### 当前适合

- **小范围扩大测试**（如 3–5 人 → 10–20 人）
- **收集真实用户反馈**（链接样本、失败案例、文案困惑点）
- **验证下载需求**（多平台、多清晰度、长视频 / 大文件）
- **验证 AI 总结需求**（平台字幕、上传 SRT/VTT、思维导图与问答）
- **继续评估收费路径**（Stripe Live、Creem、MoR 等，文档化决策，不急于上线）

### 当前不适合

- **大规模公开推广**（SEO 放量、广告投放、社群裂变）
- **正式真实收费**（Stripe Live、对外承诺商用扣款）
- **承诺所有平台 100% 可解析**（尤其 YouTube、需 cookies 的场景）
- **承诺无字幕自动转文字**（ASR 未开放）
- **承诺本机 ASR / Whisper**（当前 2C / 4G / 50G 不适合生产 Whisper）

---

## 2. 已验证能力清单

| 模块 | 状态 | 验证要点 |
|------|------|----------|
| **站点与访问** | ✅ | 首页可正常访问；主要路由 HTTP 200 |
| **Auth** | ✅ | 注册 / 登录；邮箱格式校验；占位 / 测试邮箱拦截 |
| **Video parsing** | ✅ | Bilibili / 抖音 / X / mp4 主链路；URL 清洗与粘贴 |
| **Douyin 专项** | ✅ | `v.douyin.com` 分享短链；地址栏 `modal_id` normalize |
| **Download** | ✅ | 720p 免费下载；VIP 1080p+；进度文案；大文件（如 45:55、851.8MB）下载成功且可播放 |
| **Mobile UX** | ✅ | 手机端封面显示已修复 |
| **Membership** | ✅ | VIP 权限、清晰度限制、批量下载（会员） |
| **Payment (Test Mode)** | ✅ | Stripe Checkout → Webhook → paid → VIP；resume checkout；cancel flow |
| **Account** | ✅ | 订单列表、任务记录、权益展示 |
| **AI Summary MVP** | ✅ | 上传 SRT/VTT；摘要 / 字幕文本 / 思维导图 / 问答入口 |
| **Subtitle encoding** | ✅ | UTF-8、UTF-8 BOM、GBK、GB18030、VTT |
| **AI error UX** | ✅ | 无字幕 / Douyin cookies 等友好提示；字幕状态诊断 |
| **Storage guard** | ✅ | downloads >10G 告警；>15G 清理；disk >70% 强制清理；≥85% 紧急保留最近 10 任务目录 |
| **Legal / Support** | ✅ | Terms / Privacy / 退款政策；support@cozyguidehub.com |
| **Docs / Copy** | ✅ | Soft Launch 内测指南、邀请包、前台文案与真实能力一致 |

---

## 3. 当前仍然保留的限制

以下限制 **必须** 在对内对外沟通中写清楚，避免过度承诺。

| 限制项 | 说明 |
|--------|------|
| **Stripe Test Mode** | 当前为测试环境内测支付验证，**不是真实收费**；Live Mode / Creem 等后续评估 |
| **真实收费未开放** | 正式商用扣款、发票、退款 SLA 等未按生产商用标准上线 |
| **ASR 未开放** | `ASR_ENABLED=false`；无字幕视频 **不能** 自动语音转文字 |
| **本机 Whisper** | 服务器 2C / 4G / 50G / 无 GPU，**不适合** 本机生产 Whisper |
| **平台字幕不稳定** | 部分视频无平台字幕或提取失败，需上传 SRT/VTT |
| **平台验证 / cookies** | 抖音 / Bilibili / YouTube 部分视频受 cookies、登录验证、地区或 IP 风控影响 |
| **YouTube** | 仅部分链接可能成功；不保证稳定 |
| **下载源稳定性** | 大文件 / 长视频仍受平台源、网络中断影响；非 100% 成功率 |
| **服务器规格** | 2C / 4G / 50G，不适合高并发与本机重算力任务 |
| **磁盘** | 已有磁盘保护，但极端并发大文件仍可能触发空间紧张 |

---

## 4. Beta 阶段推荐路线

### Phase B1：扩大 Beta 测试

**目标**

- 内测规模：**3–5 人 → 10–20 人**
- 收集 **真实链接样本** 与 **失败案例**
- 建立 **平台兼容性** 认知（哪些稳、哪些偶发、哪些必败）

**任务**

- 新建 **反馈收集表 / 文档**（统一模板：链接、平台、步骤、截图、是否可复现）
- 按 **P0 / P1 / P2** 分类问题（参考 [mvp-soft-launch-test-guide.md](./mvp-soft-launch-test-guide.md) 分级规则）
- 维护 **平台样本库**（B 站 / 抖音 / X / mp4 / YouTube 代表链接与结果，可脱敏）
- 复用 [soft-launch-invite-package.md](./soft-launch-invite-package.md) 邀请话术并迭代

**产出物建议**

- `docs/beta-feedback-log.md`（或表格）
- `docs/platform-compatibility-samples.md`（扩展现有 [ai-summary-test-samples.md](./ai-summary-test-samples.md) 思路）

---

### Phase B2：产品体验优化

**目标**

- 降低新用户困惑与失败挫败感
- 提升 Account、任务记录、移动端的可理解性

**任务**

- 注册 / 登录流程与错误提示（邮箱、密码、网络）
- 解析 / 下载 / AI 失败时的 **就近、可行动** 提示
- **Account**：失败任务原因、重试引导、订单与 VIP 状态一目了然
- **任务记录**：下载与 AI 任务筛选、状态说明
- **移动端**：间距、按钮、长文案折行、封面与进度条细节

**注意**

- 不改变已验证核心链路行为，以 UX 小步迭代为主

---

### Phase B3：收款方案决策

**目标**

- 在 **不立即开启真实收费** 的前提下，完成路径调研与风险评估

**调研方向**

| 方案 | 关注点 |
|------|--------|
| **Stripe Live** | 商户资质、Webhook、测试到 Live 切换清单、退款与争议 |
| **Creem** | 与现有 Stripe Test 闭环的差异、集成成本 |
| **Paddle / Lemon Squeezy / MoR** | 税务、跨境、国内用户支付体验 |
| **国内收款** | 支付宝 / 微信直连或聚合；合规与主体 |

**任务**

- 编写 **真实收费路径调研文档**（利弊、成本、上线 checklist）
- 明确 **公告节奏**：Test Mode → Beta → 正式收费前的用户告知

**原则**

- Beta 阶段继续 **Stripe Test Mode** 或维持「内测不正式扣款」口径，直至决策完成并验收

---

### Phase B4：ASR 方案评估

**目标**

- 为「无字幕自动转文字」找到 **可上线、可计费、可运维** 的方案

**约束**

- **不用本机 Whisper**（资源与稳定性不足）
- 评估 **外部 ASR API**（按分钟 / 按次计费）
- 评估 **会员次数限制** 与 **长视频切片** 策略
- 评估失败降级（仍引导上传 SRT/VTT）

**任务**

- ASR 供应商对比（价格、中文效果、延迟、隐私）
- 与 AI 总结 MVP 的衔接设计（仅文档，本轮不改代码）
- 成本模型：2C/4G 服务器 + API 调用费 vs 会员定价

---

### Phase B5：公开发布准备

**目标**

- 在 **真实收费 + ASR 决策完成** 且 **Beta 反馈可接受** 后，再考虑公开推广

**任务**

- SEO 落地页与关键词（下载器、平台名、使用场景）
- 使用教程（B 站扫码、抖音链接粘贴、字幕上传总结）
- FAQ（付费、退款、AI 边界、不支持场景）
- 用户反馈入口（邮箱、表单、社群）
- 发布渠道规划（博客、朋友圈、垂直社群）—— **非当前紧急项**

---

## 5. 下一步推荐任务（优先级）

### P0（Beta 开局优先）

| # | 任务 | 说明 |
|---|------|------|
| 1 | **新建反馈收集表 / 文档** | 统一内测与 Beta 反馈格式，便于汇总 P0/P1 |
| 2 | **新建平台兼容性样本库** | 按平台记录链接类型、解析 / 下载 / AI 结果 |
| 3 | **整理 Beta 测试邀请话术** | 在 [soft-launch-invite-package.md](./soft-launch-invite-package.md) 基础上扩至 10–20 人 |
| 4 | **Account 失败任务提示优化** | 失败原因可读、可行动（前端文案 / 展示，单独立项） |
| 5 | **真实收费路径调研文档** | Stripe Live / Creem / MoR 对比与上线 checklist |

### P1（Beta 中期）

| # | 任务 |
|---|------|
| 1 | 邮箱验证流程（注册确认 / 验证码） |
| 2 | 忘记密码 |
| 3 | AI 总结历史详情页优化 |
| 4 | 下载历史与磁盘清理可视化（用户可感知保留策略） |
| 5 | 移动端样式微调 |

### P2（Beta 后期 / 公开发布前）

| # | 任务 |
|---|------|
| 1 | ASR 自动转文字（外部 API 方案落地） |
| 2 | SEO 增长与内容矩阵 |
| 3 | 多语言扩展 |
| 4 | 外部支付替代方案落地 |
| 5 | 公共 API 或浏览器插件 |

---

## 6. 里程碑与时间建议（参考）

| 阶段 | 建议周期 | 退出标准 |
|------|----------|----------|
| B1 扩大 Beta | 2–4 周 | 样本库 ≥30 条；P0=0；P1 有清单 |
| B2 体验优化 | 与 B1 并行，2–3 周 | Top 5 困惑点关闭或文档化 |
| B3 收款决策 | 2 周调研 + 评审 | 书面方案与 Go/No-Go |
| B4 ASR 评估 | 2–3 周 | 供应商 + 成本 + 限额方案 |
| B5 公开发布 | 决策后 2–4 周准备 | Live 收费或明确 Beta 延期公告 |

*以上为规划参考，非对外承诺日期。*

---

## 7. 相关文档索引

| 文档 | 用途 |
|------|------|
| [mvp-soft-launch-test-guide.md](./mvp-soft-launch-test-guide.md) | 内测任务清单、Bug 分级 |
| [soft-launch-invite-package.md](./soft-launch-invite-package.md) | 内测邀请包与反馈模板 |
| [ai-summary-mvp-validation.md](./ai-summary-mvp-validation.md) | AI MVP 边界与验收 |
| [ai-summary-test-samples.md](./ai-summary-test-samples.md) | AI 测试样本模板 |
| [stripe-test-mode-validation-report.md](./stripe-test-mode-validation-report.md) | Stripe Test Mode 验收 |
| [payment-live-mode-dry-run-plan.md](./payment-live-mode-dry-run-plan.md) | Live 切换铺垫（勿单独采信时间表） |

---

## 8. 推荐下一个 Cursor 任务

```
NEXT_RECOMMENDED_TASK=SaveAny P0：Beta 反馈收集表与平台兼容性样本库
```

建议在该任务中 **仅新增 docs**（反馈日志模板 + 平台样本库），延续 Soft Launch 文档风格，仍不改核心业务逻辑。

---

*本文档为 Soft Launch 通过后的内部规划归档，不构成对外产品承诺或收费时间表。*
