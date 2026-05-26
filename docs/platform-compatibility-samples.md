# SaveAny 平台兼容性样本库

> **产品：** SaveAny 万能视频下载器  
> **测试地址：** https://videodown.cozyguidehub.com  
> **阶段：** Beta Phase B1  
> **文档版本：** 2026-05-25  
> **相关文档：** [post-soft-launch-roadmap.md](./post-soft-launch-roadmap.md) · [beta-feedback-log.md](./beta-feedback-log.md) · [ai-summary-test-samples.md](./ai-summary-test-samples.md)

**注意：** 勿在本文件填写 Cookie、Token、API Key、用户隐私或完整内测联系方式。URL 可脱敏；未知 URL 写「已在线上验证，待补 URL」。

---

## 1. 目标

| 目标 | 说明 |
|------|------|
| 记录真实测试链接 | Beta 志愿者与团队验证过的代表链接 |
| 判断平台支持情况 | 解析 / 下载 / 字幕 / AI 总结 四维状态 |
| 建立回归样本库 | 发版前按清单抽测，防止主链路回归 |
| 支撑优先级决策 | 为 ASR、支付、平台投入提供数据依据 |

---

## 2. 平台分类

| 平台代码 | 说明 |
|----------|------|
| `bilibili` | B 站 BV 链接；常需扫码登录 |
| `douyin` | 抖音分享短链 `v.douyin.com`、地址栏 `modal_id` 等 |
| `x` | X（Twitter）推文视频链接 |
| `tiktok` | TikTok 链接（若志愿者提供） |
| `youtube` | YouTube（部分成功，不保证） |
| `direct_mp4` | 常见 mp4 直链 |
| `unknown` | 无法识别或小众站点 |

---

## 3. 状态定义

### 解析状态（parse）

| 状态 | 含义 |
|------|------|
| `parse_ok` | 解析成功，出现封面与格式列表 |
| `parse_failed` | 解析失败（通用错误） |
| `needs_cookie` | 提示需 cookies / 登录（常见于 YouTube） |
| `unsupported_url` | URL 无法识别或 normalize 失败 |
| `platform_blocked` | 平台风控 / 地区 / IP 限制 |
| `unknown` | 未测或结果不明 |

### 下载状态（download）

| 状态 | 含义 |
|------|------|
| `download_ok` | 选定清晰度后下载成功并可播放 |
| `download_failed` | 下载失败（非大文件专项） |
| `large_file_ok` | 大文件 / 长视频（如 ≥500MB 或 ≥30min）下载成功 |
| `large_file_failed` | 大文件下载失败或中断 |
| `source_interrupted` | 源连接中断（大文件常见） |
| `format_unavailable` | 请求清晰度不可用（如免费用户 1080p） |

### 字幕 / AI 状态

| 状态 | 含义 |
|------|------|
| `subtitle_available` | 检测到平台字幕 |
| `subtitle_unavailable` | 明确无平台字幕 |
| `subtitle_unknown` | 字幕状态暂无法确认 |
| `upload_subtitle_ok` | 上传 SRT/VTT 后可用 |
| `ai_summary_ok` | AI 总结成功（摘要/导图/问答） |
| `ai_summary_failed` | AI 总结失败（含 cookies 类） |
| `friendly_hint_ok` | 无字幕/cookies 错误已友好提示（未 Raw 报错） |
| `asr_not_available` | 无字幕自动转写未开放（预期行为） |

---

## 4. 样本表

> ID 格式建议：`S-001`、`S-002` …  
> 「加入回归」填 `yes` / `no` / `candidate`

| ID | 日期 | 平台 | URL | 视频标题 | 时长 | 最大文件大小 | 解析 | 下载 | 字幕/AI | 移动端 | 错误信息（摘要） | 回归 | 备注 |
|----|------|------|-----|----------|------|--------------|------|------|---------|--------|----------------|------|------|
| S-001 | 2026-05-25 | douyin | _(已验证，待补 URL)_ | 西游记相关长视频 | 45:55 | ~851.8MB | parse_ok | large_file_ok | subtitle_unknown / ai_summary_pending | ok | — | yes | Soft Launch 生产验证：下载成功、可播放 |
| S-002 | 2026-05-25 | douyin | _(jingxuan?modal_id=…，待补)_ | _(待填)_ | _(待填)_ | _(待填)_ | parse_ok | download_ok | _(待填)_ | ok | — | yes | modal_id normalize 已验收 |
| S-003 | 2026-05-25 | douyin | _(v.douyin.com 短链，待补)_ | _(待填)_ | _(待填)_ | _(待填)_ | parse_ok | download_ok | _(待填)_ | ok | — | yes | 分享短链回归 |
| S-004 | 2026-05-25 | douyin | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | parse_ok | download_ok | subtitle_unavailable / friendly_hint_ok | _(待填)_ | 无字幕友好提示 | yes | 无字幕 / cookies 类 UX |
| S-005 | 2026-05-25 | _(任意)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(N/A)_ | _(N/A)_ | upload_subtitle_ok / ai_summary_ok | _(待填)_ | — | yes | 上传 SRT/VTT；UTF-8/GBK/VTT 编码 |
| S-006 | 2026-05-25 | bilibili | _(待填)_ | Codex 相关 / 测试视频 | _(待填)_ | _(待填)_ | parse_ok | _(待填)_ | subtitle_unavailable / pending | _(待填)_ | — | candidate | 需扫码；AI 待 Beta 补测 |
| S-007 | 2026-05-25 | direct_mp4 | _(sample-5s 等，待补)_ | sample | ~5s | 小文件 | parse_ok | download_ok | asr_not_available | _(待填)_ | — | yes | 直链冒烟 |
| S-008 | _(待填)_ | x | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | candidate | 去 `?s=20` 等 query |
| S-009 | _(待填)_ | youtube | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | no | 不保证；随手测 |
| S-010 | _(待填)_ | bilibili | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | _(待填)_ | subtitle_available / ai_summary_ok | _(待填)_ | — | candidate | 有字幕 AI 回归 |

---

## 5. 已知样本说明（Soft Launch 归档）

以下能力已在 Soft Launch 验证，URL 由 Beta 阶段补全即可：

| 场景 | 平台 | 结论 |
|------|------|------|
| 长视频大文件 | 抖音 | 45:55 / ~851.8MB → `large_file_ok`，播放正常 |
| 地址栏 modal_id | 抖音 | normalize → `parse_ok` / `download_ok` |
| 分享短链 | 抖音 | `v.douyin.com` → `parse_ok` |
| 无字幕 / cookies | 抖音等 | `friendly_hint_ok`，引导上传 SRT/VTT |
| 上传字幕总结 | 全平台 | `upload_subtitle_ok` / `ai_summary_ok` |
| B 站 Codex 类 | Bilibili | 字幕待 Beta 补测；可能 `subtitle_unavailable` |
| 5s 样本 mp4 | direct_mp4 | `download_ok` |
| 手机封面 | 多平台 | 移动端封面显示已修复 |

---

## 6. 回归测试清单

发版或扩大 Beta 前，建议至少抽测以下项（勾选记录日期与结果）：

### 解析与下载

- [ ] 抖音分享短链 `v.douyin.com`
- [ ] 抖音地址栏 `jingxuan?modal_id=`（normalize）
- [ ] Bilibili BV 链接（含扫码登录）
- [ ] X 链接（含 `?s=20` 清洗）
- [ ] direct mp4 小文件（如 sample-5s）
- [ ] 大文件 **800MB+** 或 **40min+**（参考 S-001）
- [ ] 免费 720p 下载
- [ ] VIP 1080p 下载（Stripe Test Mode 开通后）

### 体验与 AI

- [ ] 手机端封面显示
- [ ] 上传 SRT/VTT → AI 总结成功
- [ ] 无字幕视频 → 友好提示 + 上传引导（非 Raw cookies 报错）
- [ ] 字幕状态诊断文案可读
- [ ] 会员高清权限与格式列表提示

### 账号与支付（Test Mode）

- [ ] 注册真实邮箱 / 拦截 test@test.com
- [ ] Stripe Test Mode 开通 VIP → Account 订单已支付
- [ ] resume checkout / 取消流程（可选）

### 运维

- [ ] `python scripts/check_downloads_storage.py` 状态正常（服务器）
- [ ] 无 P0 反馈未关闭（见 [beta-feedback-log.md](./beta-feedback-log.md)）

---

## 7. 与 AI 样本文档的关系

| 文档 | 侧重 |
|------|------|
| 本文档 | **全平台** 解析 / 下载 / 移动端 / 大文件 |
| [ai-summary-test-samples.md](./ai-summary-test-samples.md) | **AI 总结** 字幕检测、上传编码、问答 |

同一链接可同时记入两表，ID 互引即可（如 `S-005` ↔ AI 表 #5）。

---

*样本库随 Beta 迭代更新；对外宣传请勿引用未验证 URL 或成功率承诺。*
