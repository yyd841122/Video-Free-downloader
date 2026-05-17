# AI 协作上下文

这份文档用于给后续 AI 快速理解项目，减少重复解释。

## 1. 项目一句话

这是一个 Vue + Vite + FastAPI + yt-dlp 的全能视频下载网站 MVP，支持服务端下载和直链重定向/代理下载两种模式。

## 2. 当前实现状态

已实现：

- 前端 Vue 单页面
- FastAPI 后端
- yt-dlp 信息解析
- 服务端下载任务
- 下载进度轮询
- 下载完成文件接口
- 直链解析
- 直链重定向
- 直链代理
- 移动端响应式布局
- 合规和风险提示

未实现：

- 登录注册
- 数据库
- 支付
- 用户额度
- 批量任务
- 任务历史
- AI 总结
- 字幕翻译
- 文件自动清理
- 线上级限流

## 3. 重要文件

- 后端入口：`backend/app/main.py`
- API 路由：`backend/app/api/`
- 请求响应模型：`backend/app/models/schemas.py`
- yt-dlp 封装：`backend/app/services/ytdlp_service.py`
- 下载任务内存状态：`backend/app/services/task_store.py`
- 直链 token 内存状态：`backend/app/services/direct_link_store.py`
- 前端主页面：`frontend/src/App.vue`
- 前端 API 请求：`frontend/src/api/client.js`
- 前端样式：`frontend/src/styles/main.css`
- 需求分析：`docs/REQUIREMENTS_ANALYSIS.md`
- 方案设计：`docs/SOLUTION_DESIGN.md`
- MVP 计划：`docs/DEVELOPMENT_PLAN.md`

## 4. 当前 API

```http
GET /api/health
POST /api/video/info
POST /api/video/download
POST /api/video/direct
GET /api/tasks/{task_id}
GET /api/files/{task_id}
GET /api/redirect/{token}
GET /api/proxy/{token}
```

## 5. 本地启动

后端：

```powershell
cd E:\Video-Free-downloader\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd E:\Video-Free-downloader\frontend
npm run dev
```

访问：

```text
http://127.0.0.1:5173/
```

## 6. 设计约束

### 6.1 不要轻易改的边界

- 不要把 yt-dlp 调用散落到 API 层
- 不要在 MVP 阶段强行加入数据库
- 不要把下载文件放到项目任意目录
- 不要移除版权和风险提示
- 不要默认保存用户 cookies
- 不要承诺绕过 DRM、付费墙或登录限制

### 6.2 新增后端能力时

推荐顺序：

1. 在 `schemas.py` 增加请求/响应模型
2. 在 `services/` 增加或扩展服务逻辑
3. 在 `api/` 增加路由
4. 更新 `docs/SOLUTION_DESIGN.md`
5. 增加最小可验证测试

### 6.3 新增前端能力时

推荐顺序：

1. 在 `src/api/client.js` 增加请求方法
2. 在 `App.vue` 或新组件中接入
3. 在 `main.css` 中复用现有视觉 token
4. 验证桌面和 390px 手机宽度

## 7. 后续任务建议

### 最近一轮适合做

- 文件自动清理
- 最大文件大小限制
- 下载任务超时
- 更友好的错误提示
- ffmpeg 检测提示
- 批量链接输入

### 中期适合做

- SQLite 持久化任务
- 登录注册
- 下载历史
- 字幕下载和预览
- 音频提取

### 后期适合做

- 会员额度
- 支付
- AI 总结
- 字幕翻译
- 云存储

## 8. 测试参考

已用公开小 MP4 验证过基础链路：

```text
https://samplelib.com/lib/preview/mp4/sample-5s.mp4
```

验证过：

- `/api/video/info`
- `/api/video/direct`
- `/api/video/download`
- `/api/tasks/{task_id}`
- `/api/files/{task_id}`
- `/api/proxy/{token}`

## 9. 给 AI 的推荐提示词

后续可以这样发起任务：

```text
请先阅读 docs/REQUIREMENTS_ANALYSIS.md、docs/SOLUTION_DESIGN.md、docs/AI_CONTEXT.md。
在不破坏现有 MVP 的前提下，实现 [具体功能]。
要求：保持 yt-dlp 逻辑集中在 services/ytdlp_service.py，更新必要文档，并完成本地测试。
```
