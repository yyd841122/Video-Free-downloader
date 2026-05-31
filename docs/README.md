# SaveAny 项目文档索引

本目录沉淀产品、开发、部署与迭代的说明。**以代码为准**；部分英文/早期文档已过时，见 [项目现状与开发路线图.md](./项目现状与开发路线图.md) 的「文档时效」一节。

---

## 优先阅读（按场景）

| 你想做什么 | 读这份 |
|------------|--------|
| 本地跑起来 | [保姆级本地运行指南.md](./保姆级本地运行指南.md) |
| 了解做到哪、还缺什么 | [项目现状与开发路线图.md](./项目现状与开发路线图.md) |
| 买服务器、正式上线 | [生产部署清单.md](./生产部署清单.md) |
| Soft Launch 内测协调 | [mvp-soft-launch-test-guide.md](./mvp-soft-launch-test-guide.md) |
| 邀请内测志愿者、发放内测包 | [soft-launch-invite-package.md](./soft-launch-invite-package.md) |
| Beta 反馈登记与日报 | [beta-feedback-log.md](./beta-feedback-log.md) |
| 平台兼容性样本与回归清单 | [platform-compatibility-samples.md](./platform-compatibility-samples.md) |
| Soft Launch 通过后 Beta 路线 | [post-soft-launch-roadmap.md](./post-soft-launch-roadmap.md) |
| 人工收款 + 手动开通 VIP（SSH CLI） | [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md) |
| 小额人工付费 Beta 邀请与记录表 | [paid-beta-test-plan.md](./paid-beta-test-plan.md) |
| **Beta 当前状态与下一步** | [beta-current-status-and-next-actions.md](./beta-current-status-and-next-actions.md) |
| **MoR 申请与自动收款调研准备** | [mor-application-prep.md](./mor-application-prep.md) |
| **MoR 平台问询与审核跟踪** | [mor-outreach-tracker.md](./mor-outreach-tracker.md) |
| **付费 Beta 反馈与开通跟踪** | [paid-beta-feedback-tracker.md](./paid-beta-feedback-tracker.md) |
| AI 总结 MVP 验收与边界 | [ai-summary-mvp-validation.md](./ai-summary-mvp-validation.md) |
| AI 总结测试样本记录 | [ai-summary-test-samples.md](./ai-summary-test-samples.md) |
| 产品与会员需求背景 | [需求分析.md](./需求分析.md) |
| 早期 API/架构设计（部分已演进） | [方案设计.md](./方案设计.md) / [SOLUTION_DESIGN.md](./SOLUTION_DESIGN.md) |

---

## 文档清单

### 中文（维护中）

| 文件 | 说明 |
|------|------|
| [README.md](./README.md) | 本索引 |
| [项目现状与开发路线图.md](./项目现状与开发路线图.md) | **主交接文档**：已完成功能、缺口、优化项、阶段路线 |
| [保姆级本地运行指南.md](./保姆级本地运行指南.md) | 零基础本地前后端 + Stripe 测试 |
| [生产部署清单.md](./生产部署清单.md) | 腾讯云/Cloudflare、Nginx、Stripe Live、自检 |
| [需求分析.md](./需求分析.md) | 产品需求（部分条目已实现，见路线图对照） |
| [方案设计.md](./方案设计.md) | 中文方案设计（SSE/无库等描述可能过时） |
| [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md) | **人工收款与手动开通 VIP**：dry-run / confirm、request-id、审计与安全 |
| [paid-beta-test-plan.md](./paid-beta-test-plan.md) | **小额付费 Beta**：邀请话术、付费/反馈记录表、扩大测试判断标准 |
| [beta-current-status-and-next-actions.md](./beta-current-status-and-next-actions.md) | **Beta 阶段快照**：已完成能力、限制、优先级、待观察指标与决策树 |
| [mor-application-prep.md](./mor-application-prep.md) | **MoR 调研准备**：候选平台对比、合规表述包、问询模板、Go/No-Go 标准 |
| [mor-outreach-tracker.md](./mor-outreach-tracker.md) | **MoR 问询执行跟踪**：平台审核状态、发送记录、Go/No-Go 决策 |
| [paid-beta-feedback-tracker.md](./paid-beta-feedback-tracker.md) | **付费 Beta 执行跟踪**：用户响应、开通记录、使用反馈、每周复盘 |

### 英文 / 历史（参考用）

| 文件 | 说明 |
|------|------|
| [REQUIREMENTS_ANALYSIS.md](./REQUIREMENTS_ANALYSIS.md) | 早期需求英文版 |
| [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) | MVP 计划（**大量未更新**，勿单独采信） |
| [SOLUTION_DESIGN.md](./SOLUTION_DESIGN.md) | 方案设计英文版 |
| [AI_SUMMARY_IMPLEMENTATION.md](./AI_SUMMARY_IMPLEMENTATION.md) | AI 总结实现说明 |
| [AI_CONTEXT.md](./AI_CONTEXT.md) | AI 上下文备忘 |
| [OPERATIONS_AND_TECH_NOTES.md](./OPERATIONS_AND_TECH_NOTES.md) | 运维与技术笔记 |
| [EXTENSION_DESIGN.md](./EXTENSION_DESIGN.md) | 浏览器扩展设计 |
| [T001_HANDOFF_SCAN.md](./T001_HANDOFF_SCAN.md) | 某次扫描交接（**ASR/付费等已过时**） |
| [codex-handoff.md](./codex-handoff.md) | Codex 交接（UI 阶段，**部分过时**） |
| [GIT_CHANGELOG.md](./GIT_CHANGELOG.md) | Git 变更记录 |
| [SEO 优化记录.md](./SEO%20优化记录.md) | 首页 SEO 已做项与未做项 |
| [mvp-soft-launch-test-guide.md](./mvp-soft-launch-test-guide.md) | Soft Launch 内测指南、任务清单、反馈模板 |
| [soft-launch-invite-package.md](./soft-launch-invite-package.md) | Soft Launch 内测邀请包：内测目标、可测功能、限制、测试支付说明、推荐测试流程和反馈模板 |
| [ai-summary-mvp-validation.md](./ai-summary-mvp-validation.md) | AI 总结 MVP 能力边界与验收清单 |
| [ai-summary-test-samples.md](./ai-summary-test-samples.md) | AI 总结测试样本与结果记录模板 |
| [post-soft-launch-roadmap.md](./post-soft-launch-roadmap.md) | Soft Launch 通过归档与 Beta 阶段路线图 |
| [beta-feedback-log.md](./beta-feedback-log.md) | Beta 反馈收集表、等级定义与扩大测试判断标准 |
| [platform-compatibility-samples.md](./platform-compatibility-samples.md) | 平台兼容性样本库与回归测试清单 |

---

## 自测脚本（代码仓库内，非本目录）

| 脚本 | 用途 |
|------|------|
| `backend/scripts/test_billing.py` | 支付/会员/配额 |
| `backend/scripts/admin_grant_vip.py` | 人工开通 VIP（运维 SOP 见 [manual-payment-vip-grant-sop.md](./manual-payment-vip-grant-sop.md)） |
| `backend/scripts/admin_adjust_vip.py` | 人工撤销/调整 VIP（list-grants / rollback / revoke） |
| `backend/scripts/test_admin_grant_vip.py` | 人工开通 VIP 单元测试 |
| `backend/scripts/test_admin_adjust_vip.py` | 人工调整 VIP 单元测试 |
| `backend/scripts/test_history.py` | 任务历史与批量元数据 |
| `backend/scripts/check_production.py` | 生产环境变量自检（不联网） |
| `backend/scripts/smoke_http.py` | HTTP 冒烟 |

---

## 更新约定

- 每完成一个**阶段**（如 P2 批量、E1 合规、上线部署），更新 [项目现状与开发路线图.md](./项目现状与开发路线图.md) 中的表格与日期。
- 部署相关只改 [生产部署清单.md](./生产部署清单.md)；本地环境只改 [保姆级本地运行指南.md](./保姆级本地运行指南.md)。
- 不要重复把「未完成」写进多份文档；以路线图为准，其他文档加链接即可。
