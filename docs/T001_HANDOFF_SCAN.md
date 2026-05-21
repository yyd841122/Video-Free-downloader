# T001 接手扫描报告

扫描时间：2026-05-20
扫描人：Claude Code（智谱模型）
扫描范围：E:/Video-Free-downloader-claude-test（只读）

---

## 状态总览

```
T001_STATUS=done
CURRENT_DIRECTORY=/e/Video-Free-downloader-claude-test
IS_TEST_DIRECTORY=yes
BRANCH=master
WORKTREE_STATUS=clean
```

## 基本信息

| 项目 | 值 |
|---|---|
| 当前目录 | `/e/Video-Free-downloader-claude-test` |
| 是否测试目录 | **YES** |
| 分支 | `master` |
| 工作树状态 | **clean**（无未提交改动） |
| 远端同步 | **已同步**，无未 push 提交 |
| 最新提交 | `9235552 feat: polish download and AI result UI` |
| 远端地址 | `https://github.com/yyd841122/Video-Free-downloader.git` |

## 最新提交记录

```
9235552 feat: polish download and AI result UI        ← 最新
3b73ae5 feat: add AI video summary workflow
5a7d3c0 feat: add browser extension capture bridge
6e5f3da feat: add url clear button
b5ffe19 fix: stabilize douyin downloads
97e080f docs: record bilibili quality check
291d935 fix: detect douyin quality variants
9514018 fix: improve platform auth fallbacks
0a40331 fix: support top-level media formats
c414b58 feat: polish download feedback
abc1572 fix: stabilize youtube downloads
058e897 feat: build video downloader MVP              ← 初始
```

## 项目结构摘要

```
E:/Video-Free-downloader-claude-test/
├── .codex-research/              # Codex 研究：bili_downloader whl + 源码
├── .env                          # 环境变量（已 gitignore）
├── .gitignore
├── .research/                    # 竞品研究
├── README.md
├── docs/                         # 9+ 个文档文件（含 codex-handoff.md、GIT_CHANGELOG.md）
├── browser-extension/            # Chrome/Edge Manifest V3 扩展 MVP
│   ├── manifest.json
│   ├── background.js
│   ├── popup.html / popup.js / popup.css
│   └── README.md
├── frontend/                     # Vue 3 + Vite
│   ├── index.html                # 仅基础 title + description
│   ├── package.json              # Vue 3.5 + Vite 6（无额外 UI 框架）
│   ├── vite.config.js            # 代理 /api → 127.0.0.1:8000
│   └── src/
│       ├── App.vue               # 主单文件组件（41KB）
│       ├── main.js
│       ├── api/client.js
│       ├── components/
│       │   ├── MindMapView.vue
│       │   ├── SubtitleUploadPanel.vue
│       │   └── VideoChatPanel.vue
│       └── styles/
│           └── main.css          # 全局样式（33KB）
├── backend/                      # FastAPI + yt-dlp
│   ├── requirements.txt          # 7 个依赖
│   ├── downloads/                # 5.1GB 测试下载文件
│   └── app/
│       ├── main.py
│       ├── core/config.py
│       ├── models/schemas.py
│       ├── api/
│       │   ├── ai.py             # AI 总结 API
│       │   ├── auth.py           # Bilibili 登录
│       │   ├── direct.py         # 直链
│       │   ├── extension.py      # 扩展桥接
│       │   ├── files.py          # 文件下载
│       │   ├── health.py
│       │   ├── tasks.py          # 下载任务
│       │   └── video.py          # 视频解析
│       ├── services/
│       │   ├── ytdlp_service.py  # 下载核心（33KB）
│       │   ├── ai_summary_service.py  # AI 总结核心（25KB）
│       │   ├── ai_task_store.py  # 内存态 AI 任务
│       │   ├── task_store.py     # 内存态下载任务
│       │   ├── bilibili_auth_store.py
│       │   ├── direct_link_store.py
│       │   └── extension_capture_store.py
│       └── utils/
└── tmp/
```

## 核心文件 — SEO/GEO 阶段禁止修改

| 文件 | 说明 | 原因 |
|---|---|---|
| `backend/app/services/ytdlp_service.py` | 下载核心 | 稳定，不碰 |
| `backend/app/services/ai_summary_service.py` | AI 总结核心 | 稳定，不碰 |
| `backend/app/services/ai_task_store.py` | AI 任务存储 | 内存态，不碰 |
| `backend/app/services/task_store.py` | 下载任务存储 | 内存态，不碰 |
| `backend/app/services/bilibili_auth_store.py` | B 站登录态 | 稳定，不碰 |
| `backend/app/api/ai.py` | AI API 路由 | 稳定，不碰 |
| `backend/app/api/video.py` | 视频 API 路由 | 稳定，不碰 |
| `backend/app/api/direct.py` | 直链 API 路由 | 稳定，不碰 |
| `backend/app/api/auth.py` | 登录 API 路由 | 稳定，不碰 |
| `backend/app/core/config.py` | 后端配置 | 仅在需要时加 SEO 相关配置 |
| `frontend/src/components/MindMapView.vue` | 思维导图 | 稳定，不碰 |
| `frontend/src/components/VideoChatPanel.vue` | AI 问答 | 稳定，不碰 |
| `frontend/src/components/SubtitleUploadPanel.vue` | 字幕上传 | 稳定，不碰 |
| `frontend/src/api/client.js` | API 客户端 | 稳定，不碰 |

## 未完成 / 半完成 / 风险项

### 1. VIP / 免费版 / ¥9.9 套餐 → 纯 UI 营销

**确认结果：只是前端静态文案，无任何后端能力。**

- `App.vue:1084-1120` 包含免费版/VIP 套餐卡片，文案含"每日 5 次免费下载"、"¥9.9/月"、"无限次下载"、"4K/8K"
- 没有用户系统、支付、额度、订单、VIP 权限控制
- "开通 VIP" 按钮（`App.vue:666`）是 `<button>` 无 `@click` 事件
- **风险**：SEO 阶段需要决定这些文案是保留、软化为 coming soon、还是移除

### 2. 无字幕 ASR → 未实现

**确认结果：完全未实现。**

- 后端无任何 Whisper/ASR/Speech-to-Text 代码
- 前端 `App.vue:859` 仅有一条提示文案："后续可接入音频转写"
- `ai_summary_service.py` 中遇到无字幕视频直接抛 `NoTranscriptError`

### 3. AI 任务 + 下载任务 → 纯内存态

**确认结果：所有任务存储都是内存态。**

- `task_store.py` 和 `ai_task_store.py` 使用 Python dict + threading.Lock
- 后端重启后所有 task_id 丢失
- 有 `TASK_RETENTION_SECONDS = 6 小时` 的过期清理（仅清理内存记录）

### 4. 下载文件自动清理 → 不完整

**确认结果：内存记录有 6 小时过期，但磁盘文件未自动清理。**

- `backend/downloads/` 当前累积 **5.1GB / 55+ 个任务目录**
- 有 3 个测试视频文件（各 ~2.8MB）+ 1 个测试缩略图
- 没有定时清理磁盘文件的后台任务

### 5. Bilibili 高清 → 依赖登录态

**确认结果：已确认无法稳定获取 1080P+。**

- `docs/` 中已有 Bilibili 质量调查文档
- 匿名模式无法可靠获取 1080P
- 需要用户扫码登录 + 账号权限

### 6. 浏览器扩展 → MVP

**确认结果：基础功能可用，非生产级。**

- Manifest V3，仅 `background.js` + `popup`
- 后端只有一个 `/api/extension/captures` 端点
- 内存态 capture store

### 7. `.codex-research` 和 `.research` 目录

- `.codex-research/`：包含 `bili_downloader-1.0.2-py3-none-any.whl`（96KB）+ 源码
- `.research/`：包含竞品研究
- `.research/` 已在 `.gitignore` 中，`.codex-research/` **未在 `.gitignore` 中**

### 8. 其他发现

- `frontend/dist/` 已被 `.gitignore` 排除，但实际存在构建产物（index.html + assets）
- `frontend/server.err.log`、`frontend/server.out.log`、`frontend/vite.err.log`、`frontend/vite.out.log` 等日志文件存在于 frontend 根目录，**未被 gitignore 排除**
- `backend/app/utils/` 目录存在但未检查内容

## SEO/GEO 基线评估

| 检查项 | 当前状态 | 评分 |
|---|---|---|
| `<title>` | `SaveAny - 万能视频下载器` | 有，但不够 SEO 友好 |
| `<meta name="description">` | `SaveAny 万能视频下载器，支持服务端下载与直链代理模式。` | 有，但面向开发者，非用户 |
| `<meta name="keywords">` | 不存在 | 0 |
| `lang` 属性 | `lang="zh-CN"` | 有 |
| `robots.txt` | **不存在**（`frontend/public/` 目录不存在） | 0 |
| `sitemap.xml` | **不存在** | 0 |
| `canonical` | 不存在 | 0 |
| Open Graph (og:) | 不存在 | 0 |
| Twitter Card | 不存在 | 0 |
| JSON-LD (结构化数据) | 不存在 | 0 |
| FAQ Schema | 不存在 | 0 |
| HowTo Schema | 不存在 | 0 |
| `llms.txt` | **不存在** | 0 |
| 语义化 HTML | 基本没有（SPA，`<div>` 为主） | 弱 |
| `<h1>` / heading 层级 | 未检查，需确认 | 待查 |
| SSR / 预渲染 | 不存在（纯 SPA） | 0 |

**SEO 基线总分：约 10/100**

## 进入 SEO/GEO 前必须向用户确认的问题

### P0 — 决策级问题

1. **VIP/套餐文案处理**：底部"免费版/VIP ¥9.9"区域目前是纯营销 UI，无后端能力。SEO 上线时：
   - (a) 保留原样，搜索引擎收录后用户看到 VIP 功能但无法使用
   - (b) 改为 "Coming Soon" 或去掉价格/次数等具体承诺
   - (c) 完全移除套餐区域，等支付系统就绪再加

2. **部署方式**：当前是纯 SPA（Vue + Vite），无 SSR。SEO 效果严重受限。选择方案：
   - (a) 保持 SPA，通过 Prerender / 预渲染静态 HTML 解决
   - (b) 迁移到 Nuxt / SSR 方案（改动大）
   - (c) 用 Vite SSG (vite-ssg) 做静态生成

3. **目标用户和市场**：
   - 主要面向中文用户还是全球用户？
   - 目标域名和部署平台是什么？（影响 sitemap、canonical、OG 配置）

4. **SEO 目标关键词**：是否有关键词规划？例如"视频下载"、"在线视频下载"、"免费视频下载器"等。

### P1 — 技术级问题

5. **GEO (Generative Engine Optimization) 优先级**：`llms.txt`、AI 友好的结构化内容需要多大投入？是否和传统 SEO 同步进行？

6. **FAQ / HowTo 内容**：是否有现成的 FAQ 内容？还是需要生成？

7. **`frontend/public/` 目录**：需要创建这个目录并放入 `robots.txt`、`llms.txt` 等静态文件吗？

8. **`backend/downloads/` 清理**：5.1GB 测试下载文件是否需要清理？SEO 阶段不影响，但占用磁盘空间。

9. **日志文件**：`frontend/*.log` 文件是否需要加入 `.gitignore`？

10. **`.codex-research/` 目录**：是否需要加入 `.gitignore`？它包含 whl 文件，不应提交到远端。

## 推荐下一步

等待用户回答 P0 级问题后，再开始制定 SEO/GEO 实施计划。
