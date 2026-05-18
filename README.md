# 全能视频下载网站 MVP

Vue + Vite + FastAPI + yt-dlp 的轻量视频下载网站。

## 功能

- 视频信息解析
- 服务端下载并提供文件链接
- 真实媒体直链解析
- 直链重定向与代理下载
- 下载进度展示
- 移动端适配

## 合规说明

本项目仅用于学习、技术研究和个人合法内容备份。请尊重版权，不要下载、传播未授权内容，不要尝试绕过 DRM、付费墙或平台访问限制。使用第三方平台时请遵守对应平台条款，并注意账号风控风险。

## 启动

后端：

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

## 项目文档

- [需求分析文档](docs/REQUIREMENTS_ANALYSIS.md)
- [方案设计文档](docs/SOLUTION_DESIGN.md)
- [AI 协作上下文](docs/AI_CONTEXT.md)
- [MVP 开发方案](docs/DEVELOPMENT_PLAN.md)
- [操作与技术方案记录](docs/OPERATIONS_AND_TECH_NOTES.md)
- [Git 版本修改记录](docs/GIT_CHANGELOG.md)
