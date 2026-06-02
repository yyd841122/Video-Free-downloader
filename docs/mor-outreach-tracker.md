# SaveAny MoR 平台问询与审核跟踪表

> **产品：** SaveAny 万能视频下载器（https://videodown.cozyguidehub.com）  
> **阶段：** Beta Phase（B1 → B2 并行）  
> **文档版本：** 2026-06-02（Agent Run #003 — verified）  
> **最后更新：** 2026-06-02 — SaveAny Beta Operations Tracking Agent（Run #003 核对 Run #002 记录完整）  
> **相关文档：** [mor-application-prep.md](./mor-application-prep.md) · [mor-outreach-message-pack.md](./mor-outreach-message-pack.md) · [beta-current-status-and-next-actions.md](./beta-current-status-and-next-actions.md) · [beta-operations-log.md](./beta-operations-log.md) · [monetization-paths.md](./monetization-paths.md)

**声明：** 本文档为内部运营跟踪，**不记录** API Key、商户号、密钥、个人身份证件或收款码。平台政策以官方回复为准。

---

## 1. 当前目标

| 项 | 说明 |
|----|------|
| MoR 代码 | **不接** — 审核结果明确前不写支付集成 |
| Live Payment | **不接** — Stripe Live 未打通，MoR 亦未接入 |
| 本轮工作 | **问询 + 资料准备** — 判断哪个 MoR 可能接受 SaveAny 类 SaaS / 工具产品 |
| 决策时机 | 收到平台 **明确书面回复** 并完成 Go/No-Go 评估后，再决定是否设计 Webhook 集成 |
| 兜底 | 保留 **人工收款 + MAN 手动开通**（见 [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md)） |

---

## 2. 候选平台跟踪表

> **2026-06-02 Run #003 核对：** MOR-001 Creem 字段与 Run #002 一致 — **human_review_pending** · 问询已发送（dashboard support chat）· **preliminary_go** · 待 human compliance/support。**非正式 Live 通过。**

| ID | 平台 | 官网 / 后台入口 | 当前状态 | 是否已注册账号 | 是否已发送问询 | 发送日期 | 回复日期 | 回复结论 | 是否接受 video utility / AI summary SaaS | 是否需要公司主体 | 是否支持个人开发者 | 是否支持中国开发者 | 提现方式 | 费率 | Webhook 支持 | 风控关注点 | Go / No-Go / Pending | 下一步动作 | 备注 |
|----|------|-----------------|----------|----------------|----------------|----------|----------|----------|------------------------------------------|------------------|--------------------|--------------------|----------|------|--------------|------------|----------------------|------------|------|
| MOR-001 | Creem | https://creem.io | **human_review_pending** | To confirm | **是** | 2026-06-02 | 2026-06-02 | **preliminary_go**, waiting for human compliance/support confirmation | 初步符合（须明确版权/不绕过/不保证全平台） | 否（个人可；local bank 仅企业） | **是** | **是** | 个人：Alipay / UnionPay（单笔上限 50,000 CNY）；企业：local bank transfer | 3.9% + $0.40；最低提现 $50 USD；每月 1 日 / 15 日 | **是**（checkout.completed, payment.succeeded） | 下载类须强调用户版权责任；support 须自有域名邮箱 | **Pending / Preliminary Go** | 等待人工团队回复；随后 KYC / Live Mode review / payout 设置确认 | 发送方式：Creem dashboard support chat / Creemie assistant；chat 状态 Waiting for a teammate |
| MOR-002 | Lemon Squeezy | https://www.lemonsqueezy.com | **ready_to_send** | To confirm | **否** | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 产品类型审核；indie 相对友好 | **Pending** | 人工发送 [mor-outreach-message-pack.md §4](./mor-outreach-message-pack.md)；发送后改 sent + ticket ID | 模板 v2026-06-02 |
| MOR-003 | Paddle | https://www.paddle.com | **ready_to_send** | To confirm | **否** | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 审核较严；下载器类可能需补充 FAQ | **Pending** | 可选：人工发送 [mor-outreach-message-pack.md §5](./mor-outreach-message-pack.md) | Creem/LS 无回复时优先 |
| MOR-004 | Dodo Payments | https://dodopayments.com | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 新平台，案例少；业务类型待核实 | **Pending** | 观察项 — 先看其他平台回复与其他开发者案例 | P2 优先级 |
| MOR-005 | FastSpring | https://fastspring.com | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 企业向审核严；Beta 体量可能不匹配 | **Pending** | 放后面 — 产品更成熟后再联系 | P3 优先级 |

---

## 3. 问询前资料检查清单

发送问询或提交申请前，逐项确认：

| # | 检查项 | 状态 | 位置 / 说明 |
|---|--------|------|-------------|
| 1 | 产品官网可访问 | ☐ 待确认 | https://videodown.cozyguidehub.com — **Agent 未联网实测，发送前人工打开** |
| 2 | Terms of Service | ☐ 待确认 | 站内 Legal 页 — 发送前人工确认 |
| 3 | Privacy Policy | ☐ 待确认 | 站内 Legal 页 — 发送前人工确认 |
| 4 | Refund Policy | ☐ 待确认 | Terms 章节或独立页 — 发送前人工确认 |
| 5 | support 邮箱 | ✅ 已确认 | support@cozyguidehub.com（问询签名用，**勿写收款码**） |
| 6 | 产品功能说明 | ✅ 已确认 | 见 [mor-application-prep.md §3](./mor-application-prep.md) 合规表述包 |
| 7 | 会员价格说明 | ☐ 待确认 | /pricing 页面 SKU 与权益对照 — 发送前人工确认 |
| 8 | 版权合规说明 | ✅ 已确认 | 用户自担版权；个人学习备份用途（邮件包已体现） |
| 9 | 不承诺绕过平台限制 | ✅ 已确认 | 文案与问询邮件中已体现 |
| 10 | 不承诺下载所有内容 | ✅ 已确认 | 受原平台与链接可用性限制 |
| 11 | ASR 未开放说明 | ✅ 已确认 | AI 总结依赖平台字幕或上传 SRT/VTT |
| 12 | 当前人工收款说明 | ✅ 已确认 | Beta 真实付费走线下 + MAN 订单，非站内 Live 扣款 |

**模板版本：** [mor-outreach-message-pack.md](./mor-outreach-message-pack.md)（2026-06-02）；通用参考 [mor-application-prep.md §5](./mor-application-prep.md)

---

## 4. 问询邮件 / 工单发送记录

| 日期 | 平台 | 联系方式 | 使用模板版本 | 是否发送 | 附带资料 | 对方 ticket id | 对方回复摘要 | 需要补充的信息 | 当前状态 | 操作时间戳 |
|------|------|----------|--------------|----------|----------|----------------|--------------|----------------|----------|------------|
| 2026-06-02 | Creem | Creem dashboard support chat / Creemie assistant | mor-outreach-message-pack §3 v2026-06-02 | **是** | 官网链接；合规边界说明 | —（chat 无 ticket id） | 初步符合 SaaS 类别；须明确版权/不绕过/不保证全平台；支持 individual + China merchants；Alipay/UnionPay payout；webhook 支持；**已转人工** Waiting for a teammate | human compliance/support final confirmation；Creem public support settings 配置 support@cozyguidehub.com | **human_review_pending** | 2026-06-02 Agent #002；#003 verified |
| 2026-06-02 | Lemon Squeezy | LS seller support（To confirm 具体入口） | mor-outreach-message-pack §4 v2026-06-02 | **否** | 官网链接 | — | — | — | **ready_to_send** | 2026-06-02 Agent #001 |
| 2026-06-02 | Paddle | Paddle vendor support（To confirm 具体入口） | mor-outreach-message-pack §5 v2026-06-02 | **否** | 官网链接 | — | — | — | **ready_to_send** | 2026-06-02 Agent #001 |
| — | Dodo Payments | To confirm | mor-application-prep §5 | 否 | — | — | — | — | Pending | — |
| — | FastSpring | To confirm | mor-application-prep §5 | 否 | — | — | — | — | Pending | — |

> **发送后必填：** 将对应行「是否发送」改为 **是**，「当前状态」改为 **sent** 或 **等待回复**，填写 **ticket id** 与 **发送日期**；同步更新 §2 对应平台行。

---

## 5. Go / No-Go 决策记录

| 日期 | 平台 | 判断 | 主要原因 | 风险 | 下一步 | 决策人 |
|------|------|------|----------|------|--------|--------|
| 2026-06-02 | Creem | **Pending / Preliminary Go** | AI/assistant 初步回复符合 SaaS 类别；已转人工 compliance/support；**非正式 Live 批准** | 下载类合规文案须持续一致；KYC 与 payout 账号须同一人 | 等待人工最终确认 → KYC / Live Mode review / payout 设置 | To confirm |
| 2026-06-02 | Lemon Squeezy | **Pending** | 问询未发送，无平台回复 | To confirm | 人工发送 §4 后等待回复 | To confirm |
| 2026-06-02 | Paddle | **Pending** | 问询未发送（可选） | To confirm | Creem/LS Pending 过久时发送 §5 | To confirm |

> 判断取值：**Go** / **No-Go** / **Pending**。仅在收到平台明确回复并完成 §3 清单后改为 Go/No-Go。

**Go 参考标准**（详见 [mor-application-prep.md §6](./mor-application-prep.md)）：

- 平台明确支持该类 SaaS
- 商户审核材料可准备
- 提现路径可行
- Webhook 可驱动会员自动开通
- 费率可接受

**No-Go 参考标准：**

- 明确拒绝 video downloader 类目
- 要求当前无法提供的主体 / 税务资料
- 提现不可行或风控要求过高

---

## 6. 当前推荐动作

| 优先级 | 动作 | 说明 | 状态 |
|--------|------|------|------|
| 1 | **等待 Creem 人工回复** | human_review_pending；勿写 webhook 代码或启用 Live | **进行中** |
| 2 | 发送 **Lemon Squeezy** 问询（Creem No-Go 或 Pending 过久时） | 复制 [mor-outreach-message-pack.md](./mor-outreach-message-pack.md) §4 | ready_to_send |
| 3 | **Paddle** 备选 | 复制 message pack §5；Creem No-Go 时优先 | ready_to_send |
| 4 | **Dodo Payments** 作观察项 | 不优先投入；观察社区案例与其他平台结论 | Pending |
| 5 | **FastSpring** 放后面 | Beta 体量与审核成本不匹配，产品成熟后再联系 | Pending |
| 6 | **不写支付代码** | 直至 Creem **Live approval 明确** 且 §5 出现正式 **Go** | 进行中 |

---

*每收到平台回复或完成一次问询，更新 §2、§4、§5 并注明日期；操作日志见 [beta-operations-log.md](./beta-operations-log.md)。*
