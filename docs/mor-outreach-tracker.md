# SaveAny MoR 平台问询与审核跟踪表

> **产品：** SaveAny 万能视频下载器（https://videodown.cozyguidehub.com）  
> **阶段：** Beta Phase（B1 → B2 并行）  
> **文档版本：** 2026-05-31  
> **相关文档：** [mor-application-prep.md](./mor-application-prep.md) · [beta-current-status-and-next-actions.md](./beta-current-status-and-next-actions.md) · [monetization-paths.md](./monetization-paths.md)

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

> 初始状态均为 **Pending / To confirm**，待实际问询后更新。勿将「待确认」当作已批准。

| ID | 平台 | 官网 / 后台入口 | 当前状态 | 是否已注册账号 | 是否已发送问询 | 发送日期 | 回复日期 | 回复结论 | 是否接受 video utility / AI summary SaaS | 是否需要公司主体 | 是否支持个人开发者 | 是否支持中国开发者 | 提现方式 | 费率 | Webhook 支持 | 风控关注点 | Go / No-Go / Pending | 下一步动作 | 备注 |
|----|------|-----------------|----------|----------------|----------------|----------|----------|----------|------------------------------------------|------------------|--------------------|--------------------|----------|------|--------------|------------|----------------------|------------|------|
| MOR-001 | Creem | https://creem.io | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 下载类工具可能被追问；需强调用户版权责任 | **Pending** | 优先注册并发送 [mor-application-prep.md §5](./mor-application-prep.md) 问询邮件 | 华人社区讨论较多，优先调研 |
| MOR-002 | Lemon Squeezy | https://www.lemonsqueezy.com | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 产品类型审核；indie 相对友好 | **Pending** | 与 Creem 并行发送问询 | 文档与 Webhook 较完善 |
| MOR-003 | Paddle | https://www.paddle.com | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 审核较严；下载器类可能需补充 FAQ | **Pending** | 准备资料；Creem / LS 不顺则推进 | 经典 SaaS MoR，作备选 |
| MOR-004 | Dodo Payments | https://dodopayments.com | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 新平台，案例少；业务类型待核实 | **Pending** | 观察项 — 先看其他平台回复与其他开发者案例 | P2 优先级 |
| MOR-005 | FastSpring | https://fastspring.com | Pending | To confirm | 否 | — | — | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | To confirm | 企业向审核严；Beta 体量可能不匹配 | **Pending** | 放后面 — 产品更成熟后再联系 | P3 优先级 |

---

## 3. 问询前资料检查清单

发送问询或提交申请前，逐项确认：

| # | 检查项 | 状态 | 位置 / 说明 |
|---|--------|------|-------------|
| 1 | 产品官网可访问 | ☐ 待确认 | https://videodown.cozyguidehub.com |
| 2 | Terms of Service | ☐ 待确认 | 站内 Legal 页 |
| 3 | Privacy Policy | ☐ 待确认 | 站内 Legal 页 |
| 4 | Refund Policy | ☐ 待确认 | Terms 章节或独立页 |
| 5 | support 邮箱 | ☐ 待确认 | support@cozyguidehub.com（问询签名用，**勿写收款码**） |
| 6 | 产品功能说明 | ☐ 待确认 | 见 [mor-application-prep.md §3](./mor-application-prep.md) 合规表述包 |
| 7 | 会员价格说明 | ☐ 待确认 | /pricing 页面 SKU 与权益对照 |
| 8 | 版权合规说明 | ☐ 待确认 | 用户自担版权；个人学习备份用途 |
| 9 | 不承诺绕过平台限制 | ☐ 待确认 | 文案与问询邮件中已体现 |
| 10 | 不承诺下载所有内容 | ☐ 待确认 | 受原平台与链接可用性限制 |
| 11 | ASR 未开放说明 | ☐ 待确认 | AI 总结依赖平台字幕或上传 SRT/VTT |
| 12 | 当前人工收款说明 | ☐ 待确认 | Beta 真实付费走线下 + MAN 订单，非站内 Live 扣款 |

**模板版本：** [mor-application-prep.md §5](./mor-application-prep.md)（2026-05-31）

---

## 4. 问询邮件 / 工单发送记录

| 日期 | 平台 | 联系方式 | 使用模板版本 | 是否发送 | 附带资料 | 对方回复摘要 | 需要补充的信息 | 当前状态 |
|------|------|----------|--------------|----------|----------|--------------|----------------|----------|
| — | Creem | To confirm | mor-application-prep §5 | 否 | — | — | — | 待发送 |
| — | Lemon Squeezy | To confirm | mor-application-prep §5 | 否 | — | — | — | 待发送 |
| — | Paddle | To confirm | mor-application-prep §5 | 否 | — | — | — | 待发送 |
| — | Dodo Payments | To confirm | mor-application-prep §5 | 否 | — | — | — | 待发送 |
| — | FastSpring | To confirm | mor-application-prep §5 | 否 | — | — | — | 待发送 |

> 每发送一条问询，新增一行并更新 §2 对应平台行。

---

## 5. Go / No-Go 决策记录

| 日期 | 平台 | 判断 | 主要原因 | 风险 | 下一步 | 决策人 |
|------|------|------|----------|------|--------|--------|
| — | — | — | — | — | — | — |

> 判断取值：**Go** / **No-Go** / **Pending**。仅在收到平台明确回复并完成 §3 清单后填写。

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

| 优先级 | 动作 | 说明 |
|--------|------|------|
| 1 | 问询 **Creem**、**Lemon Squeezy** | 并行发送 §5 模板邮件；更新 §2、§4 |
| 2 | **Paddle** 作为备选 | 同步准备申请资料；前两者 No-Go 或 Pending 过久时推进 |
| 3 | **Dodo Payments** 作观察项 | 不优先投入；观察社区案例与其他平台结论 |
| 4 | **FastSpring** 放后面 | Beta 体量与审核成本不匹配，产品成熟后再联系 |
| 5 | **不写支付代码** | 直至 §5 出现至少一个 **Go** 且提现 / Webhook 书面确认 |

---

*每收到平台回复或完成一次问询，更新 §2、§4、§5 并注明日期。*
