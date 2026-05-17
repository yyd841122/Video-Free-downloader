# 操作与技术方案记录

## 1. 当前 MVP 能力

当前项目已经跑通一个前后端分离的视频下载 MVP：

- Vue + Vite 前端
- FastAPI 后端
- yt-dlp 下载核心
- 单链接解析
- 视频封面展示
- 可下载清晰度/格式展示
- 点击立即下载后自动保存到本地
- Bilibili 扫码登录获取高清解析能力
- 浏览器登录态读取作为备用方案
- 手动 cookies 输入作为兜底方案

## 2. 启动方式

后端：

```powershell
cd E:\Video-Free-downloader\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd E:\Video-Free-downloader\frontend
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173/
```

## 3. 核心接口

### 健康检查

```http
GET /api/health
```

### 视频解析

```http
POST /api/video/info
```

请求字段：

- `url`：视频地址
- `auth_session_id`：Bilibili 扫码登录会话，可选
- `browser_cookies`：读取本机浏览器登录态，可选
- `cookies`：手动 cookies 文本，可选

### 创建下载任务

```http
POST /api/video/download
```

请求字段：

- `url`
- `format`
- `with_subtitle`
- `auth_session_id`
- `browser_cookies`
- `cookies`

### 查询任务

```http
GET /api/tasks/{task_id}
```

### 下载文件

```http
GET /api/files/{task_id}
```

### Bilibili 扫码登录

```http
POST /api/auth/bilibili/qrcode
GET /api/auth/bilibili/qrcode/{session_id}
```

流程：

```text
前端生成二维码
-> 用户用 Bilibili App 扫码确认
-> 后端轮询登录状态
-> 登录成功后后端在内存中保存本次会话 cookies
-> 解析和下载请求携带 auth_session_id
-> 后端自动把登录态交给 yt-dlp
```

## 4. 高清解析问题结论

### 4.1 问题现象

同一个 Bilibili 视频，在未登录状态下只能解析出：

- 480P
- 360P

解析不到：

- 720P
- 1080P
- 1080P 高码率
- 4K

### 4.2 根因

本地直接执行 yt-dlp 可复现：

```powershell
python -m yt_dlp -F https://www.bilibili.com/video/BV1cq5q6CEu3
```

yt-dlp 会提示：

```text
Format(s) 4K 超高清, 1080P 高码率, 1080P 高清, 720P 准高清 are missing;
you have to become a premium member to download them.
Use --cookies-from-browser or --cookies for the authentication.
```

结论：

- 不是 yt-dlp 不能解析高清
- 也不是格式列表前端展示问题
- 是后端没有拿到登录态时，Bilibili 接口不会返回高清流

### 4.3 已尝试方案

#### 读取本机浏览器登录态

yt-dlp 支持：

```powershell
python -m yt_dlp --cookies-from-browser chrome -F <url>
```

但本机测试遇到：

```text
Chrome: Could not copy Chrome cookie database
Edge: Failed to decrypt with DPAPI
```

常见原因：

- 浏览器正在运行，Cookie 数据库被锁
- Windows DPAPI 解密受限
- 浏览器配置和运行用户不一致

#### Bilibili WBI 接口

参考 `bili-downloader`，验证过：

- `x/player/wbi/playurl`
- `fnval=4048`
- `fourk=1`
- WBI 签名

游客态请求同样只返回 480P/360P，高清仍依赖登录态或会员权限。

### 4.4 最终 MVP 方案

实现 Bilibili 扫码登录：

- 不要求用户手动复制 cookies
- 不依赖浏览器 Cookie 数据库
- 登录态只保存在后端内存
- 当前运行期间有效
- 解析和下载自动复用同一登录态

这是当前最适合作为本地学习项目的方案。

## 5. 格式选择与下载策略

### 5.1 前端展示

前端只展示真实视频清晰度，不展示：

- audio only
- 自动匹配
- 虚拟最佳质量

格式列表按清晰度聚合，每个清晰度只展示一个推荐格式。

### 5.2 下载传参

如果视频格式没有音频轨，前端传给后端：

```text
{video_format_id}+bestaudio/{video_format_id}
```

例如：

```text
30032+bestaudio/30032
```

yt-dlp 会下载指定视频轨，并合并最佳音频轨。

### 5.3 自动保存

用户点击 `立即下载` 后：

```text
创建后端下载任务
-> 前端轮询任务状态
-> 任务完成后自动触发 /api/files/{task_id}
-> 浏览器开始保存文件
```

页面不再展示下载进度条。

## 6. 重要文件

后端：

- `backend/app/main.py`
- `backend/app/api/video.py`
- `backend/app/api/auth.py`
- `backend/app/services/ytdlp_service.py`
- `backend/app/services/bilibili_auth_store.py`
- `backend/app/services/task_store.py`
- `backend/app/models/schemas.py`

前端：

- `frontend/src/App.vue`
- `frontend/src/api/client.js`
- `frontend/src/styles/main.css`

文档：

- `docs/REQUIREMENTS_ANALYSIS.md`
- `docs/SOLUTION_DESIGN.md`
- `docs/AI_CONTEXT.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/OPERATIONS_AND_TECH_NOTES.md`

## 7. 后续扩展建议

### P1

- Bilibili 扫码登录状态持久化
- 登录会话手动退出
- 文件自动清理
- 下载失败重试
- 更清晰的错误码和用户提示

### P2

- 批量下载
- 下载历史
- 任务队列
- SQLite 持久化
- 用户系统

### P3

- AI 视频总结
- 字幕下载和翻译
- 会员额度
- 支付能力

## 8. 注意事项

- 不要把 cookies 写入 git
- 不要长期保存用户登录态，除非后续明确设计安全方案
- 不要绕过 DRM、付费墙或平台权限限制
- Bilibili 高清能力取决于账号权限
- 线上部署前必须加并发限制、文件大小限制、任务超时和清理任务

## 9. YouTube JS Runtime 配置

新版 yt-dlp 的 YouTube 提取器需要 JavaScript runtime 来处理播放器签名和 n challenge。

本项目在 `backend/app/services/ytdlp_service.py` 中统一配置：

```python
{
    "js_runtimes": {"node": {"path": ".../node.exe"}},
    "remote_components": ["ejs:github"],
}
```

实现要点：

- 默认使用本机 `node`，通过 `shutil.which("node")` 自动查找路径。
- 可用环境变量 `YTDLP_JS_RUNTIME` 切换到 `deno`、`bun`、`quickjs`。
- 可用环境变量 `YTDLP_JS_RUNTIME_PATH` 指定运行时完整路径。
- `remote_components=["ejs:github"]` 允许 yt-dlp 获取官方推荐的 EJS challenge solver，避免 YouTube 解析时缺少格式或下载失败。
- 这份配置必须同时作用于解析、下载和直链提取三条链路，不能只配置某一个接口。

验证命令：

```powershell
python -m compileall app
npm.cmd run build
```

本地 API 验证：

```powershell
POST http://127.0.0.1:8000/api/video/info
{
  "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
}
```

成功标准：

- `extractor` 返回 `Youtube`
- `warnings` 为空
- 可创建下载任务并最终返回 `status=completed`

### 9.1 下载策略

YouTube 和部分平台会同时返回两类格式：

- 音视频合一：一个媒体地址里同时包含视频和音频。
- 音视频分离：高清视频轨和音频轨分开，需要 yt-dlp 下载后用 ffmpeg 合并。

MVP 当前策略：

- 用户点击下载统一走 `/api/video/download`，由后端 yt-dlp 完整下载、合并、校验成品文件后，再通过 `/api/files/{task_id}` 交给浏览器保存。
- 不在前端下载流程里直接保存 YouTube 直链或代理流，避免浏览器把失败响应、中间流或不可播放片段当成 mp4 保存。
- 前端在同一清晰度下优先选择更高质量的视频轨；如果该格式没有音频，传参为 `{video_format_id}+bestaudio/{video_format_id}`，由 yt-dlp 合并最佳音频。
- 后端下载配置保留 `socket_timeout`、`retries`、`fragment_retries`、`http_chunk_size`，降低 `googlevideo` 读超时导致的失败概率。
- 浏览器下载图标显示的是最终成品文件从本地服务传给浏览器的进度；YouTube 拉取和合并阶段以后端任务状态为准。

## 10. 平台 Warning 展示策略

yt-dlp 会输出很多偏工程侧的 warning，例如：

- TikTok impersonation 依赖提示
- YouTube EJS / JS runtime 兼容性提示
- `If you encounter errors... install dependencies` 这类预防性提示

产品侧不要把这些英文技术提示原样暴露给用户。

当前策略：

- 如果已经解析出可下载视频格式，非阻塞技术 warning 会被隐藏。
- 如果 warning 可能导致格式缺失，会转换成中文兼容性提示。
- 如果确实没有解析出格式，才展示需要补充依赖、登录态或环境配置的可行动提示。
- Bilibili 高清缺失仍保留中文提示，因为它通常和登录态、会员权限、cookies 直接相关。

## 11. 顶层媒体 URL 兜底格式

部分平台，例如 Snapchat Spotlight，yt-dlp 可以解析出标题、封面、时长和顶层媒体地址，但不会提供常规的 `formats` 列表，或者 `formats` 里只有前端不应展示的辅助资源。

处理策略：

- 后端 `normalize_formats` 会先读取 `info["formats"]`。
- 如果没有任何可展示的视频格式，但顶层 `info["url"]` 存在，则合成一个兜底格式：
  - `format_id=best`
  - `ext` 默认取 yt-dlp 返回值，缺省为 `mp4`
  - `resolution` 由 `width` / `height` 或 `height` 推导
  - `filesize` / `filesize_approx` 尽量保留
  - `vcodec` / `acodec` 缺省为 `unknown`
- 前端把常见视频扩展名 `mp4/webm/mkv/mov/flv` 识别为可下载视频，即使编码信息未知，也会展示下载卡片。

这样可以避免“解析成功但清晰度区域为空、无法点击下载”的体验问题。
