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

## 12. Bilibili Referer 与登录态结论

已用同一个 Bilibili 链接做过对比验证：

- 默认 yt-dlp 无 cookies 解析，只能拿到 360P/480P。
- 补充 `User-Agent`、`Referer`、`Origin` 后，仍然只能拿到 360P/480P。
- 因此 Bilibili 1080P 缺失不是 Referer 单独导致，核心仍然是登录态、账号权限、会员权限或平台风控策略。

当前实现：

- 后端会为所有请求补充桌面浏览器 `User-Agent` 和中文 `Accept-Language`，减少平台误判。
- Bilibili 链接会额外补充 `Referer` 和 `Origin`，提高无登录解析的兼容性。
- Bilibili 扫码登录成功后，前端只保存后端返回的 `auth_session_id` 到 `localStorage`。
- 页面刷新后会自动用 `auth_session_id` 查询后端会话；如果后端内存里的 cookies 仍有效，就自动恢复登录态。
- 前端不保存 cookies，cookies 仍只保存在后端内存会话中。

限制：

- 后端重启后，内存会话会丢失，需要重新扫码。
- 当前 Bilibili 登录会话清理周期为 4 小时。
- 是否能解析或下载 1080P 仍取决于 Bilibili 账号自身权限和目标视频权限。

### 12.2 Bilibili 清晰度一致性检查

已对 `https://www.bilibili.com/video/BV1cq5q6CEu3` 做过对照检查：

- 项目 API 无 cookies 解析结果只返回 360P/480P。
- yt-dlp 原始 `formats` 同样只返回 360P/480P，不存在项目过滤导致的高清缺失。
- 对 `30032` 格式做 `ffprobe` 探测：
  - yt-dlp 标记：`852x480`
  - 实际媒体流：`852x480`
  - yt-dlp 估算大小约 `24.2MB`
  - 实际媒体流大小约 `24.2MB`

结论：

- Bilibili 当前没有发现 Douyin 那种“页面 metadata 标高清，但默认播放地址实际较低清”的问题。
- Bilibili 格式列表来自 yt-dlp 对平台播放接口的真实返回，不是项目根据页面 metadata 合成。
- 无 cookies 时高清缺失仍然是权限/登录态问题，不是清晰度探测或前端展示问题。

### 12.1 Bilibili 扫码入口交互

前端只保留一个轻量入口：

- 按钮文案：`解析不到 1080P？扫码登录 Bilibili`
- 用户点击后立即调用 `/api/bilibili/qrcode` 生成二维码。
- 不再额外展示“生成登录二维码”二次按钮。
- 不在主界面展示浏览器 cookies、手动 cookies 输入等高级兜底项，避免普通用户困惑。

底层仍保留 `cookies`、`browser_cookies`、`auth_session_id` 三种能力，后续可在调试页或管理员页重新暴露。

## 13. Douyin Fresh Cookies 兜底解析

问题现象：

```text
ERROR: [Douyin] <aweme_id>: Fresh cookies (not necessarily logged in) are needed
```

原因：

- 当前 yt-dlp 的 Douyin extractor 会优先请求 `https://www.douyin.com/aweme/v1/web/aweme/detail/`。
- 部分短链或视频在无新鲜匿名 cookies 时，该接口只返回空 JSON。
- yt-dlp 会判断为需要 fresh cookies，但这类 cookies 不一定需要登录，只是平台风控需要的匿名会话。

当前实现：

- 正常情况下仍优先使用 yt-dlp 原生解析。
- 只有 Douyin 链接遇到 `Fresh cookies` 错误时，才启用项目内兜底解析。
- 兜底解析会请求抖音分享页或短链跳转后的页面，读取页面中的 `window._ROUTER_DATA`。
- 从 `videoInfoRes.item_list[0]` 提取：
  - `desc` 作为标题
  - `author.nickname` 作为作者
  - `video.cover.url_list[0]` 作为封面
  - `video.play_addr.url_list[0]` 作为媒体地址
- 注意：`video.play_addr.url_list[0]` 通常是 `playwm` 分享播放地址，可能只有 720P；不能把页面里的 `video.width` / `video.height` 直接当成可下载文件清晰度。
- 后端会从 `play_addr` 中提取 `video_id`，再尝试构造抖音 `play` 接口的多档地址：
  - `ratio=1080p`
  - `ratio=720p`
  - `ratio=540p`
  - `ratio=origin`
- 每个候选地址都会用 `ffprobe` 探测真实媒体流，优先使用探测结果：
  - 实际 `width` / `height` 作为最终展示清晰度
  - 实际 `duration` 作为时长
  - 实际 `size` 作为文件大小
- 相同高度的候选会去重，按高度和文件大小降序展示。
- 如果 `ffprobe` 不可用或所有候选探测失败，才回退到页面中的 `play_addr` 和 `video.width` / `video.height` / `duration`。
- 后端合成前端可展示的格式：
  - `format_id=douyin_1080p` / `douyin_720p` / `douyin_576p` 等
  - `ext=mp4`
  - `vcodec=h264`
  - `acodec=aac`
  - `resolution=widthxheight`

下载策略：

- 如果用户选择 `douyin_share`，或 Douyin 无 cookies 下载时，后端直接使用兜底媒体地址流式下载。
- 下载时使用移动端 UA 和 Referer，避免把错误页保存成假 mp4。
- 下载完成后校验文件大小，文件过小会判定为异常。
- `extract_info` 兜底成功后清空原始英文 warning，避免页面继续展示 `Fresh cookies` 技术报错。

验证方式：

```powershell
python -m compileall app
npm.cmd run build
```

真实链接验证：

```powershell
POST http://127.0.0.1:8000/api/video/info
{
  "url": "https://v.douyin.com/SFpd4CeGZhk"
}
```

成功标准：

- `extractor=Douyin`
- 能展示封面和真实媒体清晰度，例如 `1920x1080`、`1280x720`
- `warnings` 为空
- 下载得到的文件能被 `ffprobe` 识别为 `mov,mp4,m4a,3gp,3g2,mj2`

限制：

- 兜底能力依赖抖音分享页当前仍输出 `window._ROUTER_DATA`。
- 若抖音后续改版页面结构，需要同步更新 `extract_douyin_share_info`。
- 该兜底只在 Douyin fresh-cookie 场景启用，不改变其他平台解析策略。
