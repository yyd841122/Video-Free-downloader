# SaveAny AI 总结 MVP — 能力边界与线上验收清单

Last updated: 2026-05-25

线上地址：https://videodown.cozyguidehub.com  
后端 API：https://api-videodown.cozyguidehub.com

---

## 1. 当前状态摘要

| 项目 | 状态 |
|------|------|
| `AI_SUMMARY_MVP_ENABLED` | `true`（前端已开放 AI 总结入口） |
| `ASR_ENABLED` | `false`（不启用本机 / 外部 ASR） |
| `DEEPSEEK_API_KEY` | 生产环境已配置（具体值不在文档中记录） |
| 有平台字幕 → AI 总结 | 已支持，需按平台样本继续补测 |
| 无平台字幕 → 自动转文字 | **暂未开放** |
| 上传 SRT/VTT → AI 总结 | **已跑通并线上验证** |
| 字幕编码 | UTF-8 / UTF-8 BOM / GBK / GB18030 / VTT 已兼容 |

**服务器现状：** 2C / 4G / 50G，无 GPU。当前不适合在生产环境直接部署 Whisper 或本机 ASR。

**相关 commit（master）：**

- `345deea` — feat(ai): enable subtitle-based summary MVP
- `fc20c99` — feat(ai): enable AI summary MVP flag
- `ce00a1f` — fix(ai): improve no-subtitle summary messaging
- `18b9296` — fix(ai): support common subtitle encodings

---

## 2. 已完成能力

### 2.1 入口与状态

- AI 总结按钮已开放（需登录，受每日配额限制）
- `/api/video/info` 返回字幕状态字段：
  - `has_subtitles`
  - `subtitle_status`（`available` / `unavailable` / `unknown`）
  - `subtitle_languages`
  - `subtitle_source`
- 解析后显示三态字幕提示（已检测到 / 暂未检测到 / 暂无法确认）
- 无字幕时按钮弱化或阻止无意义 API 请求，并显示友好说明
- Douyin / cookies / Fresh cookies / 412 等错误已友好化，不暴露原始 yt-dlp 英文报错
- 无字幕 / cookies 失败时展示 **上传 SRT/VTT** 入口（`SubtitleUploadPanel`）

### 2.2 AI 总结结果 Tab

- **总结摘要** — DeepSeek 结构化总结（one_sentence、outline、key_points、timeline 等）
- **字幕文本** — 带时间戳的 transcript 列表
- **思维导图** — 基于总结生成的 Markdown 导图
- **AI 问答** — 基于字幕 + 总结内容的追问（有轮次配额）

### 2.3 上传字幕路径

- API：`POST /api/ai/summary/subtitle`
- 支持 `.srt`、`.vtt`
- 编码自动识别：`utf-8-sig` → `utf-8` → `gb18030` → `gbk` → `big5`
- 解码失败时返回友好中文错误，不写入乱码 transcript
- 测试脚本：`backend/scripts/test_subtitle_encoding.py`（7/7 通过）

### 2.4 配额与权限（已有）

- 免费用户：每日 AI 总结次数限制（见 `quota_service`）
- VIP 用户：更高每日限额与并发限制
- AI 问答：免费用户每任务轮次限制

---

## 3. 线上已验证结果（2026-05 回归）

| 场景 | 结果 |
|------|------|
| 上传 SRT 字幕 → 触发 AI 总结 | ✅ 成功 |
| 「字幕文本」Tab 中文显示 | ✅ 正常（编码修复后无乱码） |
| 「总结摘要」Tab | ✅ 正常 |
| 「思维导图」Tab | ✅ 正常 |
| GBK / UTF-8 等编码字幕 | ✅ 后端测试通过；线上以实际上传为准 |
| 抖音无字幕 / cookies 类视频 | ✅ 显示友好提示，不暴露 `ERROR: [Douyin] Fresh cookies...` |
| ASR / Whisper | ✅ 保持关闭（`/api/health` → `asr_enabled=false`） |

**修复前已知问题（已关闭）：**

- 上传 GBK 字幕时「字幕文本」Tab 出现 `h AI`、`z?` 等乱码 → 已通过 `decode_subtitle_bytes()` 修复
- AI 总结 MVP 开关未提交导致入口被挡 → 已通过 `mvp.js` 修复
- 无字幕状态提示过于模糊 → 已通过三态文案 + cookies 友好化修复

---

## 4. 当前限制

1. **无 ASR：** 无平台字幕的视频不能自动语音转文字；用户需上传 SRT/VTT，或等待后续 ASR 能力开放。
2. **服务器资源：** 2C / 4G / 无 GPU，不适合本机 Whisper / faster-whisper 跑生产转写。
3. **平台字幕提取：** 依赖 yt-dlp 与各平台开放的字幕/自动字幕 metadata；受登录态、cookies、地区、反爬影响。
4. **Douyin：** 多数视频无开放字幕 metadata；可能出现 `subtitle_status=unknown` 或 cookies 验证失败；已提供上传字幕兜底。
5. **YouTube / Bilibili：** 部分高清或字幕轨道可能需要 cookies / 扫码登录；与下载能力共用同一套 cookies 机制。
6. **任务存储：** AI 任务仍为内存态 + 本地 `backend/downloads/{task_id}` 文件；服务重启后进行中任务丢失，已完成结果可从磁盘恢复（在 retention 窗口内）。
7. **长视频：** 字幕文本有字符上限截断（`MAX_TRANSCRIPT_CHARS`）；ASR 路径虽已实现但当前未启用。

---

## 5. 暂不支持（MVP 边界外）

- 无字幕视频自动 ASR 转文字
- 本机 Whisper / docker-whisper 生产部署
- Groq / OpenAI Whisper / Deepgram / AssemblyAI 等外部 ASR 接入
- 长视频自动语音转写队列
- ASR 单独计费或 VIP 差异化 ASR 配额

---

## 6. 后续路线（建议）

| 阶段 | 目标 |
|------|------|
| **Phase A** | 稳定 AI 总结 MVP：补测有平台字幕的 YouTube / Bilibili / 其他样本 |
| **Phase B** | 收集用户反馈：无字幕占比、上传字幕使用率、总结质量 |
| **Phase C** | 评估外部 ASR API（Groq Whisper、OpenAI 兼容接口等）的成本与国内可达性 |
| **Phase D** | 评估独立 ASR 服务（专用机器或 `ASR_BASE_URL` 网关），与 2C/4G 主站解耦 |
| **Phase E** | 会员权益设计：ASR 次数、时长上限、VIP 专属 |
| **Phase F** | 正式开放「无字幕 → 转写 → 总结」闭环 |

**技术备注：** 代码中已有 `_try_asr_fallback()` 与 `asr_service.py` 骨架，`ASR_ENABLED=false` 时不触发。启用前需单独评估 provider、成本、队列与 2C/4G 限制。

---

## 7. 验收清单

### 7.1 已完成

- [x] AI 总结入口打开（`AI_SUMMARY_MVP_ENABLED=true`）
- [x] 生产 DeepSeek 配置存在（不写 key）
- [x] `/api/video/info` 字幕状态字段可用
- [x] 上传字幕 → AI 总结成功
- [x] 字幕文本 Tab 中文显示正常（含 GBK/UTF-8）
- [x] 总结摘要 Tab 正常
- [x] 思维导图 Tab 正常
- [x] 无字幕 / cookies 提示友好
- [x] 原始 Douyin / yt-dlp 错误不暴露给用户
- [x] ASR 保持关闭（`ASR_ENABLED=false`）
- [x] 字幕编码单元测试 7/7 通过

### 7.2 待办 / 后续

- [ ] 有平台字幕视频（YouTube / Bilibili / 其他）真实样本继续补测
- [ ] ASR provider 选型（外部 API vs 独立 ASR 机器）
- [ ] ASR 成本与单次时长上限评估
- [ ] ASR 权限与计费策略（是否与 VIP 绑定）
- [ ] 长视频 transcript 截断策略产品化说明
- [ ] AI 任务持久化（若用户量上升再评估 SQLite）

---

## 8. 快速 API 参考

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/summary` | 从视频 URL 创建 AI 总结（需登录） |
| GET | `/api/ai/summary/{task_id}` | 轮询状态与结果 |
| POST | `/api/ai/summary/subtitle` | 上传 SRT/VTT 创建总结 |
| POST | `/api/ai/summary/{task_id}/chat` | 基于总结的问答 |
| GET | `/api/health` | 依赖探测（含 `asr_enabled`） |

---

## 9. 相关文档

- 实现细节（部分条目已早于 MVP 开放，以本文为准）：`docs/AI_SUMMARY_IMPLEMENTATION.md`
- AI 开发约定：`docs/AI_CONTEXT.md`
- 本地运行：`docs/保姆级本地运行指南.md`

**维护说明：** 本文档仅记录 MVP 验收与边界；功能变更时请同步更新第 1、3、7 节，勿在文档中写入任何 API key 或 `.env` 内容。
