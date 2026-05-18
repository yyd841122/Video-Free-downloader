# 方案设计文档

## 1. 总体架构

项目采用前后端分离架构。

```text
Vue + Vite 前端
    |
    | HTTP / JSON
    v
FastAPI 后端
    |
    | Python API
    v
yt-dlp
    |
    +--> 服务端下载到 backend/downloads
    |
    +--> 解析真实媒体直链
```

MVP 阶段不使用数据库，后端通过内存保存任务状态和直链 token。文件存储在本地 `backend/downloads` 目录。

## 2. 技术选型

### 2.1 前端

使用 Vue 3 + Vite。

原因：

- 上手简单
- 前后端分离清晰
- 适合快速构建控制台类页面
- 后续可平滑接入 Pinia、Vue Router、组件库

### 2.2 后端

使用 FastAPI。

原因：

- Python 技术栈，便于直接封装 yt-dlp
- 接口声明清晰
- Pydantic 模型适合沉淀 API 契约
- 本地开发和部署都轻量

### 2.3 下载核心

使用 yt-dlp 的 Python API，不解析命令行 stdout。

核心封装点：

- `extract_info`：解析视频信息
- `download_video_task`：服务端下载任务
- `extract_direct_link`：解析真实媒体链接
- `progress_hook`：更新下载进度
- `normalize_formats`：清洗格式列表给前端

## 3. 当前目录结构

```text
E:\Video-Free-downloader
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ direct.py
│  │  │  ├─ files.py
│  │  │  ├─ health.py
│  │  │  ├─ tasks.py
│  │  │  └─ video.py
│  │  ├─ core/
│  │  │  └─ config.py
│  │  ├─ models/
│  │  │  └─ schemas.py
│  │  ├─ services/
│  │  │  ├─ direct_link_store.py
│  │  │  ├─ task_store.py
│  │  │  └─ ytdlp_service.py
│  │  └─ main.py
│  ├─ downloads/
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  │  └─ client.js
│  │  ├─ styles/
│  │  │  └─ main.css
│  │  ├─ App.vue
│  │  └─ main.js
│  ├─ index.html
│  ├─ package.json
│  └─ vite.config.js
└─ docs/
```

## 4. 后端模块设计

### 4.1 API 层

`app/api/video.py`

- `POST /api/video/info`
- `POST /api/video/download`
- `POST /api/video/direct`

`app/api/tasks.py`

- `GET /api/tasks/{task_id}`

`app/api/files.py`

- `GET /api/files/{task_id}`

`app/api/direct.py`

- `GET /api/redirect/{token}`
- `GET /api/proxy/{token}`

`app/api/health.py`

- `GET /api/health`

### 4.2 服务层

`ytdlp_service.py`

负责与 yt-dlp 交互，是下载能力的核心边界。后续新增 cookies、代理、播放列表、字幕处理时，应优先扩展这里，而不是把 yt-dlp 逻辑散落到 API 层。

`task_store.py`

MVP 使用内存字典保存任务状态。后续接数据库时，可以把这个模块替换为数据库实现，并尽量保持 API 层调用方式不变。

`direct_link_store.py`

MVP 使用内存字典保存短期直链 token。后续可以替换为 Redis 或数据库。

## 5. 前端模块设计

### 5.1 页面结构

当前前端集中在 `App.vue`：

- 顶部导航
- 下载控制台
- 视频解析结果卡片
- 任务进度卡片
- 直链结果卡片
- 能力卖点区
- 合规提示区

MVP 阶段保持单页面，减少路由和状态管理复杂度。

### 5.2 API 封装

`src/api/client.js` 封装所有后端请求：

- `getVideoInfo`
- `createDownloadTask`
- `getTask`
- `createDirectLink`

后续新增接口时，应先在这里补方法，再由组件调用。

### 5.3 UI 风格

参考 `https://ai.codefather.cn/painting` 的轻商业风格：

- 白底
- 蓝色主按钮
- 顶部轻导航
- 大输入控制台
- 圆角卡片
- 清晰的卖点卡片
- 移动端优先保证可用

当前项目视觉方向：

- 主色：`#1777ff`
- 深色文字：`#0f172a`
- 背景：白色到浅蓝灰
- 卡片：白色、轻边框、柔和阴影

## 6. 下载流程设计

### 6.1 服务端下载

```text
前端提交 URL、format、with_subtitle
-> POST /api/video/download
-> task_store 创建任务
-> FastAPI BackgroundTasks 执行 download_video_task
-> yt-dlp progress_hook 更新任务状态
-> 前端轮询 GET /api/tasks/{task_id}
-> 完成后前端展示 /api/files/{task_id}
```

当前实现适合 MVP。后续如果要支持大量并发，应该替换为真正任务队列，例如 Celery、RQ、Dramatiq 或 Arq。

### 6.2 直链模式

```text
前端提交 URL、format
-> POST /api/video/direct
-> yt-dlp extract_info(download=False)
-> 找到可用媒体 URL
-> direct_link_store 生成短期 token
-> 返回 redirect_url 和 proxy_url
```

重定向适合真实媒体链接可直接访问的场景。

代理适合需要后端附带 headers 的场景，但 MVP 代理还没有做流量限制和并发保护，线上部署前必须补齐。

## 7. 数据模型

### 7.1 VideoInfoResponse

用于前端展示解析结果：

- title
- webpage_url
- thumbnail
- duration
- uploader
- extractor
- formats

### 7.2 TaskStatusResponse

用于展示服务端下载进度：

- task_id
- status
- progress
- speed
- eta
- filename
- download_url
- error

### 7.3 DirectLinkResponse

用于展示直链模式结果：

- title
- format_id
- ext
- direct_url
- redirect_url
- proxy_url
- expires_in

## 8. 扩展设计

### 8.1 数据库扩展

推荐新增表：

- users
- download_tasks
- direct_links
- files
- subscriptions
- usage_records

MVP 的 `task_store` 和 `direct_link_store` 是未来数据库层的替换边界。

### 8.2 批量下载

推荐设计：

- 前端允许一行一个链接
- 后端创建 batch_id
- 每个链接生成独立 task_id
- 前端展示批量进度和单项错误

不要让一个任务内部吞掉所有链接，否则失败恢复和重试会比较困难。

### 8.3 字幕和翻译

推荐流程：

```text
yt-dlp 下载字幕
-> 标准化为 vtt/srt
-> 前端预览
-> 调用翻译服务
-> 生成双语字幕文件
```

### 8.4 AI 总结

推荐优先使用字幕作为输入：

```text
字幕文本
-> 分段清洗
-> 摘要模型
-> 输出要点、时间轴、金句、行动项
```

如果没有字幕，再考虑音频提取和 ASR。

#### 8.4.1 P0 已确认实现方案

AI 视频总结按“平台字幕优先”实现，不在第一版引入音频 ASR：

```text
用户提交视频 URL
-> POST /api/ai/summary 创建 AI 总结任务
-> yt-dlp 只提取平台字幕/自动字幕，不下载完整视频
-> 解析 SRT/VTT 为带时间戳的 transcript_segments
-> 调用 Deepseek 生成结构化总结 JSON
-> 保存 transcript.json 和 summary.json 到 backend/downloads/{task_id}
-> 前端轮询 GET /api/ai/summary/{task_id} 展示进度、字幕和总结
```

默认模型使用 `deepseek-v4-flash`，通过 `.env` 配置：

```text
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MAX_TOKENS=4096
```

P0 输出包括：

- 一句话总结
- 章节大纲
- 核心要点
- 时间轴
- 关键词
- 字幕/转录文本展示

无字幕时任务返回 `no_transcript`，前端提示后续可接入音频转写或上传字幕文件。

#### 8.4.2 后续扩展

- P1：基于 P0 的结构化总结生成思维导图。
- P2：基于字幕和总结内容做 AI 问答。
- 无字幕增强：优先支持上传 SRT/VTT，其次浏览器插件辅助捕获字幕，最后再接入音频提取 + ASR。

#### 8.4.2.1 上传字幕增强

当平台没有开放字幕或当前登录态无法提取字幕时，前端在 `no_transcript` 状态下提供 SRT/VTT 上传入口：

```text
用户上传 SRT/VTT
-> POST /api/ai/summary/subtitle multipart/form-data
-> 后端保存到 backend/downloads/{task_id}/uploaded.{srt|vtt}
-> 解析字幕并调用 Deepseek 总结
-> 复用 P0/P1/P2 的总结、思维导图和问答展示
```

该能力需要 FastAPI 文件上传依赖 `python-multipart`。上传文件大小由 `SUBTITLE_UPLOAD_MAX_BYTES` 控制，默认 2MB。

#### 8.4.3 P1 思维导图实现方案

思维导图不新增后端接口，直接复用 P0 的结构化总结结果：

```text
summary.json
-> title / one_sentence 作为中心主题
-> outline / key_points / timeline / keywords / learning_suggestions 作为分支
-> 前端 MindMapView 组件渲染为可扫读的知识结构
```

第一版使用 Vue 3 单文件组件和 CSS 实现，不引入额外图形库，避免影响现有构建体积和下载功能。后续如果需要拖拽、缩放、导出图片，再考虑接入专门的 mindmap/canvas 库。

#### 8.4.4 P2 AI 问答实现方案

AI 问答基于已完成的 P0 总结任务，不重新解析视频：

```text
用户在总结结果中提问
-> POST /api/ai/summary/{task_id}/chat
-> 后端读取内存中的 summary、transcript_segments
-> 拼接结构化摘要、截断后的字幕上下文和最近对话历史
-> 调用 Deepseek Chat Completions
-> 返回 answer 和回答中出现的时间戳 references
```

第一版不引入向量库或数据库，适合中短视频和本地 MVP。长视频后续可把字幕切片并做检索增强，避免把整段字幕塞进模型上下文。

### 8.5 付费能力

推荐把付费和下载能力解耦：

- 用户额度
- 每日任务数
- 最大文件大小
- 并发数
- 文件保留时长
- 高级能力开关

## 9. 线上部署前必须补齐

- 下载并发限制
- 代理并发限制
- 最大文件大小
- 最大下载时长
- 文件清理任务
- 请求频率限制
- 更严格的 URL 校验
- 日志脱敏
- ffmpeg 可用性检测
- 错误码规范
- CORS 白名单改为真实域名

## 10. AI 开发约定

后续让 AI 修改项目时，建议先提供：

- `docs/REQUIREMENTS_ANALYSIS.md`
- `docs/SOLUTION_DESIGN.md`
- `docs/AI_CONTEXT.md`
- 具体要改的功能点

AI 修改原则：

- 优先复用现有模块
- yt-dlp 逻辑集中在 `ytdlp_service.py`
- API 入参和响应先写入 `schemas.py`
- 前端请求先写入 `src/api/client.js`
- MVP 不随意引入数据库、队列或大型组件库
- 涉及下载、代理、cookies、付费能力时必须补安全和合规说明
