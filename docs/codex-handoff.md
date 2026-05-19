# Codex Project Handoff

Last updated: 2026-05-19

## 1. 项目名称

万能视频下载器 / Video-Free-downloader

## 2. 当前项目目标

在已有 yt-dlp 视频下载能力基础上，扩展 AI 视频理解能力，让用户可以通过视频 URL 提取字幕/转录，调用 Deepseek 生成总结摘要，并继续查看字幕、思维导图和基于视频内容的 AI 问答。

当前产品方向：

- 优先服务有平台字幕或自动字幕的视频。
- 无字幕视频的 ASR 音频转文字方案已经讨论并沉淀，但暂时不实现，等上线后根据真实用户需求和成本再决定。

## 3. 当前已完成的工作

已完成并已提交推送的大功能提交：

- Commit: `3b73ae5 feat: add AI video summary workflow`
- Branch: `master`
- Remote: `origin/master`

已完成内容：

- P0：AI 视频总结。
  - `POST /api/ai/summary`
  - `GET /api/ai/summary/{task_id}`
  - 基于 yt-dlp 提取平台字幕/自动字幕。
  - 调用 Deepseek 生成结构化总结。
- P0：字幕/转录展示。
  - 展示带时间戳的字幕片段。
  - 支持复制全文。
- P0 增强：上传 SRT/VTT 字幕后继续总结。
  - `POST /api/ai/summary/subtitle`
- P1：思维导图。
  - `MindMapView.vue`
  - 支持拖动画布、滚轮缩放、放大/缩小、适配、重置。
  - 缩放范围目前为 20% - 170%。
- P2：AI 问答。
  - `POST /api/ai/summary/{task_id}/chat`
  - 基于总结和字幕上下文回答问题。
- YouTube 字幕 429 修复。
  - 不再一次性下载全部字幕语言。
  - 先读取字幕元数据，再按优先级下载单个候选字幕。
- Deepseek JSON 容错。
  - Deepseek 返回坏 JSON 时会尝试修复。
  - 修复失败时生成兜底总结。
  - 不再直接把 JSON 解析错误暴露给前端。
- BibiGPT 风格的 AI 结果区。
  - 紧凑灰底 Tab。
  - 白色激活 Tab。
  - 文章式总结排版。
  - 摘要、字幕、思维导图、AI 问答四个 Tab。
- 文档沉淀：
  - `docs/AI_SUMMARY_IMPLEMENTATION.md`
  - `docs/GIT_CHANGELOG.md`
  - `docs/SOLUTION_DESIGN.md`
  - `docs/AI_CONTEXT.md`

最近已验证过：

- 后端：`python -m compileall app`
- 前端：`npm.cmd run build`
- YouTube 测试视频：`https://www.youtube.com/watch?v=uQbyEv0Z9JM`
- Deepseek malformed JSON 修复/兜底路径

## 4. 当前正在进行的任务

当前处于下载页与 AI 结果区 UI 验收打磨阶段，已完成一轮较大的界面重构和体验优化，准备提交为新的稳定点。

本轮已完成但尚未推送的改动：

- 首页与结果区布局：
  - Hero 区域改为解析后自动紧凑，仅保留输入框和必要提示。
  - 清空网址后恢复完整品牌标题、说明和示例入口。
  - 下载结果区改为左右双卡片，桌面端左右等高，移动端按内容高度收起。
  - 移动端去除下载卡片底部多余空白。
- Bilibili 登录提示：
  - `解析不到 1080P？扫码登录 Bilibili` 不再常驻显示。
  - 仅在用户输入 Bilibili / b23.tv 链接并点击解析后显示。
  - Bilibili 高清缺失提示文案改为更面向用户的短句。
- AI 总结与字幕：
  - 总结 Tab 改为更优雅的文档式 Markdown 展示。
  - 字幕列表改为更易读的时间轴文本样式。
  - 字幕下载合并为“下载”下拉菜单，支持 TXT/SRT/VTT/MD/JSON。
- 思维导图：
  - 生成逻辑改为根据总结内容组织语义树，不再硬塞关键词、时间轴或学习建议节点。
  - 改为纯 SVG 渲染，页面展示与 PNG/SVG 导出共用同一套布局数据。
  - 支持高清 PNG 与 SVG 下载。
  - 优化多链路布局、线条观感、末端节点换行和重复节点问题。
- AI 问答：
  - 改成聊天气泡样式。
  - 去掉顶部说明区和消息前的“你 / AI”标签。
  - 用户消息右侧蓝色气泡，回答左侧浅灰气泡。
- 底部广告与套餐区：
  - “为什么选择 SaveAny”改成 5 张功能卡。
  - 套餐区改成免费版 / VIP 高级版双卡片设计。
  - 移除旧的平台标签和安全说明散列区域。

本轮改动涉及：

- `frontend/src/App.vue`
- `frontend/src/styles/main.css`
- `frontend/src/components/MindMapView.vue`
- `frontend/src/components/VideoChatPanel.vue`
- `backend/app/services/ytdlp_service.py`
- `docs/codex-handoff.md`
- `docs/GIT_CHANGELOG.md`

## 5. 当前未完成的问题

产品/功能层面未完成：

- 无字幕视频的 ASR 音频转文字暂不实现。
- AI 总结任务仍为内存态，后端重启或热更新后旧 task_id 会丢失。
- 没有数据库持久化任务历史。
- 没有用户系统、额度、计费、支付。
- 没有 Deepseek 成本控制、每日次数限制、超长视频限制。
- 没有自动文件清理机制，`backend/downloads/{task_id}` 会继续累积。
- 没有正式线上部署安全配置，如真实 CORS 白名单、请求频率限制、并发限制、日志脱敏。
- AI 总结 UI 仍处于用户人工验收阶段，最终视觉效果待用户确认。

技术/验证层面待确认：

- 本轮 UI 打磨将提交到本地 git，但尚未推送远端。
- 当前前后端服务最近一次已启动：
  - 前端：`http://127.0.0.1:5173`
  - 后端：`http://127.0.0.1:8000`
- 当前 `.env` 中的 Deepseek Key 是否仍有效：待确认，不要读取或输出密钥。
- `docs/AI_CONTEXT.md` 等部分历史中文文档在终端输出中可能出现乱码，但项目文件本身是否需要统一编码整理：待确认。

## 6. 下一步应该执行的任务

建议下一步顺序：

1. 用户继续验收当前 UI 效果，重点检查：
   - 桌面端左右卡片等高。
   - 移动端下载卡片无多余空白。
   - Bilibili 登录提示只在解析 B 站链接后显示。
   - 思维导图页面展示和导出一致性。
2. 如用户确认通过，可再决定是否 `git push` 当前提交。
3. 进入可上线能力补齐：
   - 文件自动清理机制。
   - AI 任务持久化。
   - 用户额度/成本控制。
   - 更友好的错误提示。
   - 正式部署配置。

如果继续做功能，建议优先：

1. 文件清理机制。
2. AI 任务持久化。
3. 用户额度与成本控制。
4. 无字幕 ASR 方案只在用户重新确认后再实施。

## 7. 关键文件路径

后端：

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/models/schemas.py`
- `backend/app/api/ai.py`
- `backend/app/api/video.py`
- `backend/app/api/tasks.py`
- `backend/app/api/files.py`
- `backend/app/services/ai_summary_service.py`
- `backend/app/services/ai_task_store.py`
- `backend/app/services/ytdlp_service.py`
- `backend/app/services/task_store.py`
- `backend/requirements.txt`

前端：

- `frontend/src/App.vue`
- `frontend/src/api/client.js`
- `frontend/src/styles/main.css`
- `frontend/src/components/MindMapView.vue`
- `frontend/src/components/SubtitleUploadPanel.vue`
- `frontend/src/components/VideoChatPanel.vue`
- `frontend/package.json`

文档：

- `docs/codex-handoff.md`
- `docs/AI_SUMMARY_IMPLEMENTATION.md`
- `docs/SOLUTION_DESIGN.md`
- `docs/AI_CONTEXT.md`
- `docs/GIT_CHANGELOG.md`
- `docs/REQUIREMENTS_ANALYSIS.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/OPERATIONS_AND_TECH_NOTES.md`

浏览器扩展：

- `browser-extension/manifest.json`
- `browser-extension/background.js`
- `browser-extension/popup.js`
- `docs/EXTENSION_DESIGN.md`

## 8. 当前不能做的事情

除非用户明确要求，否则不要做：

- 不要继续实现无字幕 ASR。
- 不要绕过 DRM、付费墙、登录权限或平台访问限制。
- 不要默认保存、输出或提交用户 cookies。
- 不要读取、输出或提交 `.env` 中的密钥。
- 不要随意引入数据库、队列、向量库或大型前端依赖。
- 不要重构下载主链路，除非明确是修复下载问题。
- 不要删除下载文件、缓存文件或用户数据，除非用户明确授权。
- 不要执行 `git reset --hard`、`git checkout --`、批量删除等危险命令。
- 不要在用户未要求时 git commit / git push。

## 9. 当前必须遵守的限制

项目限制：

- 继续保持现有 Vue 3 + Vite + FastAPI + yt-dlp 架构。
- yt-dlp 相关逻辑优先集中在 `backend/app/services/ytdlp_service.py` 或专门 service 中，不要散落到 API 层。
- 新增后端 API 时，先补 `schemas.py`，再补 service，再补 API route。
- 新增前端 API 调用时，先补 `frontend/src/api/client.js`。
- 不破坏已有视频解析和下载能力。
- 当前 MVP 不默认引入数据库。
- 当前 AI 总结优先使用平台字幕/自动字幕。
- 无字幕 ASR 只有在用户再次确认后才能进入实施。

用户要求：

- 如果有不明确内容，先找用户人工确认。
- 涉及新技术文档或库用法时，必须通过 Context7 和联网搜索确认最新文档，不要使用过时代码。
- UI 调整需要贴近用户截图和参考网站，尤其是 BibiGPT 风格。
- 修改后应自主运行必要测试或构建验证。

当前交接任务限制：

- 不要读取或输出 `.env` 密钥。
- 不要删除下载文件、缓存文件或用户数据，除非用户明确授权。
- 不要 `git push`，除非用户明确要求。

## 10. 新对话继续时应该读取哪些文件

新对话开始后建议按顺序读取：

1. `docs/codex-handoff.md`
2. `docs/AI_SUMMARY_IMPLEMENTATION.md`
3. `docs/SOLUTION_DESIGN.md`
4. `docs/GIT_CHANGELOG.md`
5. `frontend/src/App.vue`
6. `frontend/src/styles/main.css`
7. `frontend/src/components/VideoChatPanel.vue`
8. `frontend/src/components/MindMapView.vue`
9. `frontend/src/api/client.js`
10. `backend/app/api/ai.py`
11. `backend/app/services/ai_summary_service.py`
12. `backend/app/models/schemas.py`

然后执行只读检查：

```powershell
git status --short --untracked-files=all
git log --oneline -5
```

如果要继续 UI 验收，优先查看当前未提交 diff：

```powershell
git diff -- frontend/src/styles/main.css frontend/src/components/VideoChatPanel.vue docs/codex-handoff.md
```

## 11. 给新 Codex 对话使用的启动提示词

```text
你现在接手 E:\Video-Free-downloader 项目。请先阅读 docs/codex-handoff.md、docs/AI_SUMMARY_IMPLEMENTATION.md、docs/SOLUTION_DESIGN.md、docs/GIT_CHANGELOG.md，然后执行 git status --short --untracked-files=all。

当前项目是“万能视频下载器”，技术栈为 Vue 3 + Vite + FastAPI + yt-dlp。已完成视频下载主链路和 AI 视频总结功能：字幕提取、Deepseek 总结、字幕展示、思维导图、AI 问答。最新大功能提交为 3b73ae5；之后已继续完成一轮首页、下载卡、AI 结果区、字幕下载、思维导图、Bilibili 提示和底部广告区 UI 打磨，并已准备本地提交。

请不要重新实现已完成内容。继续工作前先确认当前分支状态和最近提交。任何不明确的产品决策都先问我。涉及新技术文档或库用法时必须通过 Context7 和联网搜索确认最新文档。不要读取或输出 .env 密钥，不要删除文件，不要 push，除非我明确要求。
```
