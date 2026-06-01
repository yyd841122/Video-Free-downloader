# SaveAny MoR 问询邮件包（可直接复制发送）

> **产品：** SaveAny 万能视频下载器  
> **文档版本：** 2026-05-31  
> **相关文档：** [mor-application-prep.md](./mor-application-prep.md) · [mor-outreach-tracker.md](./mor-outreach-tracker.md)

---

## 1. 使用说明

| 项 | 说明 |
|----|------|
| 用途 | 提交给 MoR 平台 **客服、销售或审核团队** 的 pre-sales / compliance 问询 |
| 发送前 | 请自行补充 **[Your name]**、联系方式、账号信息（如已注册） |
| 不包含 | API Key、商户密钥、身份证、银行账号、税务编号、个人收款码 |
| 性质 | **仅用于问询**，不代表正式申请已通过或已签约 |
| 发送后 | 在 [mor-outreach-tracker.md](./mor-outreach-tracker.md) 回填记录（见 §7） |
| 代码 | 当前 **不接** MoR Webhook、Stripe Live 或任何 Live 支付集成 |

**模板版本 ID：** `mor-outreach-message-pack` v2026-05-31

---

## 2. 通用英文问询模板

**Subject:** Pre-sales inquiry — SaveAny (video utility + AI summary SaaS, Beta)

```
Hello,

I am evaluating Merchant of Record services for SaveAny, a web-based video utility and AI summary tool currently in Beta.

Website: https://videodown.cozyguidehub.com
Support: support@cozyguidehub.com

Product type
- Video utility + AI summary SaaS for personal backup and study use
- Stage: Beta (controlled testing, not public launch)

Planned membership model
- One-time duration packages: monthly, quarterly, yearly, and lifetime options
- No auto-renewal by default in current Beta SKUs

Current features
- Video link parsing and format selection
- Downloads for personal backup and study (users must have rights to the content)
- AI summaries, mind maps, and Q&A based on platform subtitles or user-uploaded SRT/VTT files
- Auto speech-to-text (ASR) for videos without subtitles is NOT yet offered

Compliance boundaries
- Users are responsible for ensuring they have the rights to download and use content
- We do not encourage or support copyright infringement
- We do not promise to bypass platform restrictions or DRM
- We do not guarantee that all videos or platforms are supported (availability depends on the source platform and link)

Current payments
- No live in-app charges today
- Beta uses manual payment fallback for real users; Stripe Test Mode on-site is for technical validation only

Questions
1. Is this product category acceptable under your MoR program (video utility / productivity SaaS with the compliance framing above)?
2. Can individual developers apply, and are China-based developers supported? What entity types are required?
3. What payout methods, timelines, and fees apply under your MoR model?
4. Do you support webhooks for paid orders so we can activate membership automatically?
5. What documents are required for merchant review (Terms, Privacy, Refund Policy, etc.)?
6. Are there additional compliance requirements or prohibited use cases we should know about?
7. What is a typical review timeline?

Thank you,
[Your name]
SaveAny — support@cozyguidehub.com
```

---

## 3. Creem 专用版本

**适用：** Creem support / contact form（语气简洁）

**Subject:** Beta SaaS inquiry — SaveAny video utility + AI summaries

```
Hi Creem team,

I'm evaluating Creem as MoR for SaveAny (https://videodown.cozyguidehub.com) — a Beta-stage video utility + AI summary SaaS.

What we do:
- Parse video links, let users pick formats, download for personal backup/study
- AI summary / mind map / Q&A from platform subtitles or uploaded SRT/VTT (no ASR yet)
- Sell membership duration packs (monthly / quarterly / yearly / lifetime), one-time payment, no default auto-renewal

What we don't promise:
- Users must have rights to content; no infringement support
- No bypassing platform limits; not all platforms/videos guaranteed

We're in Beta with manual payments only — no live checkout yet. Stripe Test on our site is dev validation only.

Could you confirm:
1) Whether SaveAny fits your acceptable SaaS categories?
2) Individual vs company onboarding, and China-based developers?
3) Payout options and typical fees?
4) Webhook support for paid orders → membership activation?
5) Docs needed for review and expected timeline?

Thanks,
[Your name]
support@cozyguidehub.com
```

---

## 4. Lemon Squeezy 专用版本

**适用：** Lemon Squeezy support / seller inquiry（强调 SaaS / digital product）

**Subject:** Merchant inquiry — SaveAny digital SaaS (video utility + AI summaries, Beta)

```
Hello Lemon Squeezy team,

I am preparing to sell memberships for SaveAny, a B2C web SaaS product in Beta, and would like to confirm merchant eligibility before integration.

Product overview
- Type: Digital SaaS — video utility with AI summary features
- URL: https://videodown.cozyguidehub.com
- Support: support@cozyguidehub.com

SaveAny helps registered users:
- Parse supported video links and select download formats for personal backup and study
- Generate AI summaries, mind maps, and Q&A from available platform subtitles or user-uploaded SRT/VTT subtitle files
- Auto transcription (ASR) is not offered at this time

Commercial model
- Membership duration products: monthly, quarterly, yearly, and lifetime (one-time payment; current Beta SKUs do not use auto-renewal by default)

Compliance
- Terms of Service and Privacy Policy are published on our site
- Users are responsible for lawful use and content rights
- We do not market circumvention of third-party platform restrictions
- Platform and video availability vary by source; we do not guarantee universal download support

Current stage
- Beta with manual payment processing for paying users
- On-site Stripe is Test Mode for engineering validation only — not live revenue

Please advise:
1. Whether this SaaS category is acceptable for Lemon Squeezy MoR
2. Supported seller entity types (individual vs company) and any restrictions for China-based developers
3. Payout methods, settlement timing, and fee structure
4. Webhook / API events for order paid to automate membership provisioning
5. Required compliance documents and typical approval timeline
6. Any product-specific restrictions for video or AI tools

Thank you,
[Your name]
SaveAny
support@cozyguidehub.com
```

---

## 5. Paddle 专用版本

**适用：** Paddle sales / vendor support（语气正式，强调合规与政策页）

**Subject:** Vendor pre-qualification — SaveAny SaaS (video utility + AI summaries)

```
Dear Paddle team,

I am writing to pre-qualify SaveAny for Paddle's Merchant of Record services before we invest in integration.

Company / product
- Product name: SaveAny
- Website: https://videodown.cozyguidehub.com
- Category: B2C SaaS — video utility and AI-assisted summarization for lawful personal use
- Contact: support@cozyguidehub.com

Product description
SaveAny is a web application that allows users to process videos they have the right to access and use. Features include link parsing, format selection, downloads for personal backup and study, and AI-generated summaries based on available platform subtitles or user-uploaded SRT/VTT files. Automatic speech-to-text for videos without subtitles is not currently offered.

Pricing model
- Digital membership duration packages: monthly, quarterly, yearly, and lifetime options
- One-time payment model for current Beta SKUs (no default auto-renewal)

Compliance and policies
- Terms of Service, Privacy Policy, and refund terms are available on our website
- Users must agree to terms stating they are responsible for copyright and lawful use
- We do not promote copyright infringement, circumvention of platform technical measures, or unauthorized access to content
- We do not represent that all platforms, videos, or formats are supported

Current go-to-market status
- Private Beta; no live Paddle or other MoR checkout connected
- Real Beta payments are processed manually offline; on-site Stripe remains Test Mode for technical validation only

We respectfully request confirmation on:
1. Eligibility of this SaaS category under Paddle's acceptable use and risk policies
2. Required business entity type (individual, sole proprietor, company) and support for China-based developers
3. Supported payout instruments, currencies, and indicative fee schedule
4. Webhook capabilities to notify our backend on successful payment for membership activation
5. Complete list of onboarding documents and expected review duration
6. Any additional compliance steps for video-related productivity tools

Thank you for your guidance.

Sincerely,
[Your name]
SaveAny
support@cozyguidehub.com
```

---

## 6. 中文辅助说明（发送前自检）

| 检查项 | 说明 |
|--------|------|
| 主体类型 | 表单若要求 Company / Individual，按你 **实际可提供** 的主体填写；无法提供时不要虚构 |
| 证件资料 | 仅通过平台 **官方安全渠道** 提交；**不要** 把证件号、银行信息写进本仓库文档 |
| 网站 URL | 确认 https://videodown.cozyguidehub.com 可访问，Legal 页可打开 |
| Terms / Privacy / Refund | Paddle 问询尤其需要；发送前打开站内页面确认内容与产品描述一致 |
| 表述边界 | **避免**「任意视频下载」「破解」「绕过会员」等表述；使用「用户有权访问的内容」「个人学习备份」 |
| ASR | 明确说明 **未开放**，避免审核误解 |
| 付款现状 | 可说明 Beta 人工收款 + 站内 Test Mode 非正式扣款，**不要** 声称已接入 Live MoR |
| 复制发送 | 替换 `[Your name]`；Creem / LS 表单若无 Subject 字段，将 Subject 内容并入正文首行 |

---

## 7. 发送后记录格式

发送成功后，更新 [mor-outreach-tracker.md](./mor-outreach-tracker.md)：

### §2 候选平台跟踪表 — 更新字段

| 字段 | 填写示例 |
|------|----------|
| 当前状态 | `sent`（仅在实际发送后） |
| 是否已发送问询 | `是` |
| 发送日期 | `2026-06-01` |
| 下一步动作 | 等待回复；收到后更新回复结论 |

### §4 问询邮件 / 工单发送记录 — 新增一行

| 字段 | 说明 |
|------|------|
| 日期 | 实际发送日期 |
| 平台 | Creem / Lemon Squeezy / Paddle |
| 联系方式 | 如 `support@…`、官网表单、后台 ticket |
| 使用模板版本 | `mor-outreach-message-pack` §3 / §4 / §5（2026-05-31） |
| 是否发送 | `是` |
| 附带资料 | 如「官网链接、Terms/Privacy URL」；**不写** 证件或密钥 |
| 对方 ticket id | 平台返回的工单号（如有） |
| 回复摘要 | 收到回复后填写要点；**不编造** |
| 需要补充的信息 | 平台要求的补充材料 |
| 当前状态 | `等待回复` / `已回复` / `需补充资料` |

**注意：** 本任务仅将跟踪表标为 `ready_to_send`。用户 **实际发送后** 再将状态改为 `sent` 并填写 §4。

---

*模板随产品阶段更新；政策以各 MoR 平台官方回复为准。*
