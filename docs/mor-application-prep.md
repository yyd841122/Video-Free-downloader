# SaveAny MoR 申请与自动收款路径调研准备

> **产品：** SaveAny 万能视频下载器（https://videodown.cozyguidehub.com）  
> **阶段：** Beta Phase（B1 → B2 并行）  
> **文档版本：** 2026-05-31  
> **相关文档：** [monetization-paths.md](./monetization-paths.md) · [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md) · [beta-current-status-and-next-actions.md](./beta-current-status-and-next-actions.md)

**声明：** 本文档为内部调研与申请材料准备，不构成法律、税务或合规意见。文中 **不记录** 任何 API Key、商户号、密钥、个人身份证件或收款码。费率与政策以各平台官网及审核结果为准。

---

## 1. 当前结论

| 项 | 状态 |
|----|------|
| Stripe Live | **未打通** — 站内 Stripe 仅为 Test Mode 技术验证 |
| 当前真实收款 | **人工收款**（微信 / 支付宝 / PayPal 线下）+ 管理员 SSH 执行 `admin_grant_vip.py` → 生成 **MAN** 人工订单 |
| MoR 自动收款 | **中期候选路径**，尚未接入任何 Live 支付 |
| 本文用途 | 调研对比、申请材料准备、平台问询 — **不写 MoR 集成代码** |

**原则：** 在平台审核明确接受业务类型、提现路径可行、Webhook 可自动开通会员之前，**不接入任何 Live 支付**，保留人工收款作为 Beta 兜底。

---

## 2. 候选平台对比

> 以下「中国开发者友好度」「审核风险」等为基于公开信息与同类 SaaS 经验的 **初步判断**；具体政策需注册后确认或联系官方销售 / 支持确认。未联网核实最新条款处已标注「需官方确认」。

| 平台 | 是否 MoR | 适合 SaaS / 数字产品 | 可能是否接受中国开发者 | 是否适合视频下载 + AI 总结工具 | 审核风险 | Webhook 集成成本 | 提现/结算不确定点 | 下一步动作 |
|------|----------|----------------------|------------------------|-------------------------------|----------|------------------|-------------------|------------|
| **Creem** | 是（宣称 MoR，需官网确认） | ⭐⭐⭐⭐ SaaS / AI 工具 | 相对友好（华人社区讨论较多；**需注册后确认**） | 中等 — 需强调用户版权责任、个人学习备份 | 中 — 下载类工具可能被追问用途 | 低–中 — REST + Webhook，与现有订单模型可映射 | 大陆个人无海外公司时的提现、外汇、税务；**需官方确认支持国家** | **优先**：注册 sandbox，发问询邮件（见 §5） |
| **Lemon Squeezy** | 是 | ⭐⭐⭐⭐ 数字产品 / SaaS / 订阅 | 中等 — KYC 必需；部分地区受限，**需官方确认** | 中等 — 类似 Paddle，需合规表述包 | 中 — 对 indie 相对友好但仍可能审查产品类型 | 低–中 — 文档完善，Webhook 事件丰富 | PayPal / 银行到账路径；中国开发者主体要求 **需确认** | **并行优先**：填申请表 + 发问询邮件 |
| **Paddle** | 是（经典 SaaS MoR） | ⭐⭐⭐⭐⭐ | 中等 — 需 KYC；**需官方确认** 大陆个人/个体是否可入驻 | 中–高 — 软件/SaaS 成熟，下载器类可能需补充 FAQ | 中高 — 审核较严但路径清晰 | 中 — Checkout + Webhook，文档成熟 | 分成比例、提现周期、税务代扣范围 **需签约前确认** | 同步准备资料；若 Creem / LS 不顺则推进 |
| **Dodo Payments** | 宣称 MoR | ⭐⭐⭐ 新兴平台 | 待核实 — **需注册后确认** | 待核实 — 视频/下载类是否允许 **需官方确认** | 中–高（新平台，案例少） | 低–中 | 稳定性、争议处理、提现路径均待观察 | P2：观察其他开发者案例后再试 |
| **FastSpring** | 是（偏企业数字商务） | ⭐⭐⭐⭐ 软件许可 / 订阅 | 中等 — 通常面向成熟企业，**需官方确认** | 中 — 更适合成熟 SKU 与合规团队 | 高 — 审核严、流程重 | 中高 — 集成与商务流程较长 | 最低消费、合同门槛；Beta 体量可能不匹配 | P3：产品更成熟后再考虑 |

**参考：** 更完整的变现路径对比见 [monetization-paths.md](./monetization-paths.md)。

---

## 3. SaveAny 合规表述包

用于 MoR 申请、工单或销售邮件中描述产品（英文为主，中文供内部对照）。

### 英文（申请用）

> **SaveAny** is a video utility and AI summary tool for users to process videos they have the right to access and use. It supports video link parsing, format selection, downloads for personal backup and study use, and AI summaries based on available platform subtitles or user-uploaded subtitle files (SRT/VTT). Users are responsible for ensuring they have the rights to download and use the content. SaveAny does not encourage or support copyright infringement. Auto speech-to-text (ASR) for videos without subtitles is **not yet available**. Membership is sold as one-time duration packages (no auto-renewal by default for current Beta SKUs).

### 中文（内部对照）

SaveAny 仅供用户处理其有权访问和使用的视频内容，用于个人学习、备份和整理。支持链接解析、清晰度选择、下载，以及基于平台可提取字幕或用户上传 SRT/VTT 的 AI 总结。用户须自行确保对内容拥有合法使用权；产品不鼓励也不支持侵权用途。无字幕视频的 ASR 自动转文字 **暂未开放**。当前 Beta 会员为一次性时长套餐（非默认自动续费）。

### 建议一并提供的链接

- 产品：https://videodown.cozyguidehub.com  
- Terms of Service / Privacy Policy（站内 Legal 页）  
- Refund Policy（如有独立页或 Terms 章节）  
- 支持邮箱：support@cozyguidehub.com（**不要在本文档中嵌入个人收款信息**）

---

## 4. 风险说明

| 风险 | 说明与应对 |
|------|------------|
| 产品类型敏感 | 视频下载 / 多平台解析类工具可能被支付平台归类为高风险；申请时 **如实描述**，强调个人学习备份与用户自担版权责任 |
| 版权与合规 | 必须提供 Terms / Privacy / Refund Policy；文案中 **不承诺** 绕过平台限制、下载所有平台、或规避 DRM |
| 功能边界 | **不承诺** ASR 已开放；AI 总结能力以「平台字幕或上传字幕」为准 |
| 开发者主体 | 大陆个人无海外公司时，多数 MoR 的 KYC、提现、外汇与税务仍需自行处理 — 申请前先问清 **支持的国家/主体类型** |
| 密钥安全 | Webhook 与 API 密钥仅存放在服务端环境变量；**不得** 写入仓库或本文档 |

---

## 5. 问询邮件 / 工单模板（英文）

**Subject:** Pre-sales inquiry — SaaS video utility + AI summary tool (SaveAny)

```
Hello [Platform] team,

I am preparing a digital SaaS product called SaveAny (https://videodown.cozyguidehub.com) and would like to confirm whether your Merchant of Record service is a fit before we invest in integration.

Product summary:
- SaveAny helps users parse video links, choose formats, and download videos they have the right to access for personal backup and study.
- AI features generate summaries, mind maps, and Q&A from platform subtitles or user-uploaded SRT/VTT files.
- Auto transcription (ASR) for videos without subtitles is not yet offered.
- We sell one-time membership duration packages (not auto-renewal by default in our current Beta).

Business model:
- B2C web SaaS, subscription-style duration packages (monthly / yearly / lifetime SKUs planned).
- Users must comply with our Terms; they are responsible for copyright and lawful use.

Questions:
1. Do you accept SaaS tools in the video utility / productivity category with the compliance framing above?
2. Which countries/regions and business entity types (individual vs company) can onboard as a seller?
3. What are payout methods, timelines, fees, and tax handling (VAT/sales tax) under your MoR model?
4. Do you support webhooks for order paid / subscription events so we can activate membership automatically?
5. Are there prohibited use cases we should be aware of (e.g., video downloaders, AI tools)?
6. Typical review timeline and required materials for merchant approval?

We are currently in Beta with manual payment fallback and Stripe Test Mode for technical validation only — no live in-app charges yet.

Thank you,
[Your name]
SaveAny / support@cozyguidehub.com
```

**使用说明：** 将 `[Platform]` 替换为 Creem、Lemon Squeezy、Paddle 等；勿在邮件中附带密钥、身份证件或收款码。

---

## 6. Go / No-Go 判断标准

### Go（可进入 sandbox 集成设计阶段）

- [ ] 平台 **明确书面确认** 接受该类 SaaS（或给出可接受的合规表述条件）
- [ ] 商户审核材料可在当前阶段准备完成
- [ ] 提现路径可行（到账方式、周期、手续费可接受）
- [ ] Webhook 支持「支付成功 → 自动开通会员时长」
- [ ] 费率与固定成本在当前 Beta 阶段可承受
- [ ] Terms / Privacy / Refund 已就绪且与产品描述一致

### No-Go（暂停或换平台）

- [ ] 平台 **明确拒绝** video downloader / 类似工具类目
- [ ] 要求当前无法提供的公司 / 税务主体（如必须海外 C-Corp 且无法注册）
- [ ] 提现不可行或周期/限额不适合 SaaS 现金流
- [ ] 风控要求过高（如强制移除核心功能、过度用户审查）
- [ ] 费用（分成 + 固定月费）超过当前阶段可承受范围
- [ ] Webhook 能力不足，无法可靠驱动现有 VIP / 订单模型

---

## 7. 推荐下一步

| 顺序 | 动作 | 说明 |
|------|------|------|
| 1 | 向 **Creem**、**Lemon Squeezy** 发送 §5 问询邮件或提交 pre-sales 表单 | 优先确认业务类型与主体要求 |
| 2 | 同步准备 **Paddle** 申请资料 | Creem / LS 若不顺则切换 |
| 3 | **保留人工收款** + `admin_grant_vip.py` 作为 Beta 兜底 | 见 [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md) |
| 4 | **不立即写 MoR 集成代码** | 避免审核未过时的无效开发 |
| 5 | 平台 Go 决策后，再设计 Webhook → 订单表 → VIP 发放 | 复用现有 Stripe Test Mode 验收过的订单与会员模型 |

**技术备忘（本轮不做）：** 订单表未来可增加 `payment_provider` 字段；Webhook 幂等与对账流程参考 [stripe-test-mode-validation-report.md](./stripe-test-mode-validation-report.md)。

---

*本文档随平台回复与 Beta 反馈更新；政策以各服务商官网为准。*
