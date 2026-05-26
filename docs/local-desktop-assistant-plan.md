# SaveAny Local Desktop Assistant — 可行性与架构设计

> **产品：** SaveAny 万能视频下载器  
> **文档类型：** 可行性分析 + 架构设计（**本轮不写代码**）  
> **文档版本：** 2026-05-25  
> **相关文档：** [post-soft-launch-roadmap.md](./post-soft-launch-roadmap.md) · [monetization-paths.md](./monetization-paths.md) · [ai-summary-mvp-validation.md](./ai-summary-mvp-validation.md)

---

## 1. 产品定位

### SaveAny Web 与 Desktop 的关系

| 产品 | 定位 | 核心职责 |
|------|------|----------|
| **SaveAny Web** | 在线入口、账号与会员中枢 | 注册登录、会员/订单（Test Mode → 未来正式支付）、轻量解析与下载（受服务器资源限制）、**AI 总结 MVP**（字幕 / 上传 SRT/VTT）、帮助文档、Beta 反馈 |
| **SaveAny Local Desktop Assistant** | 会员配套 **本地执行引擎** | 本地 yt-dlp 解析、本地下载与 ffmpeg 合并、**本地 cookies / 扫码登录态**、本地文件管理、**本地 ASR**（可选）、将 transcript 上传云端做 AI 总结或本地保存 |

**一句话：** Web 负责「身份、权益、云端 AI、合规文案」；Desktop 负责「重计算、大文件、平台登录态、隐私敏感数据留在本机」。

**用户旅程（目标态）：**

1. 在 Web 注册 / 购买会员（或人工/MoR 开通）。
2. 下载并安装 Windows EXE，使用同一 SaveAny 账号登录。
3. 桌面端校验会员与功能包（下载 / 本地 ASR / 云端 AI 额度）。
4. 粘贴链接 → 本地解析下载 →（可选）本地转写 → 一键提交 transcript 至云端 AI 总结。

**不替代 Web：** Desktop 不是「离线版网站」，而是 **增强型下载与转写工作站**，与 Web 账号体系绑定。

---

## 2. 为什么需要本地端

| 痛点（Web / 服务器） | 本地端如何解决 |
|----------------------|----------------|
| **YouTube** cookies、bot 验证、服务器 IP 风控 | 用户本机 Chrome/Edge cookies；不经过 SaveAny 服务器 |
| **Bilibili** 扫码登录态、SESSDATA 敏感 | 本地浏览器或本地 cookies 导入；**不上传** 到云端 |
| **抖音** 风控、短链与 modal_id 虽可服务器解析，大文件占带宽 | 本地下载，不占 50G 服务器磁盘与出口带宽 |
| **大文件 / 长视频**（如 800MB+） | 服务器 2C/4G 压力大；本地磁盘与家庭宽带更合适 |
| **ASR / Whisper** 生产不适合 2C/4G 无 GPU 服务器 | 用户 PC 可能带 GPU；或 CPU 慢速本地转写 |
| **cookies 隐私与安全** | 服务器存 cookies 有泄露、合规与信任成本；本地仅存用户机器 |
| **并发与成本** | 10–20 人 Beta 可接受；规模化后服务器下载不可持续 |

**结论：** 本地端不是「可做可不做」，而是 SaveAny 在 **平台风控、大文件、ASR、隐私** 四条线上的自然延伸；与 Web Beta **并行规划**，不阻塞当前 Web Beta，但应在路线图中占位。

---

## 3. MVP 功能范围（分阶段）

### V0.1 — 最小可演示（CLI 亦可）

| 能力 | 说明 |
|------|------|
| Windows EXE（或安装包） | 单平台优先，Win10/11 x64 |
| 登录 SaveAny 账号 | JWT / token 存本地加密配置 |
| 检查会员权限 | 拉取 license：是否可本地下载 |
| 粘贴链接 | 单 URL |
| yt-dlp 本地调用 | 复用与后端相近的 normalize 逻辑（后续抽共享库或复制） |
| 下载到用户选择目录 | 进度、日志 |
| ffmpeg 合并 | 打包进安装目录或检测系统 PATH |
| UI | 日志窗口 + 打开下载目录 |

**不含：** cookies、ASR、自动更新。

### V0.2 — 平台登录态（隐私核心）

| 能力 | 说明 |
|------|------|
| 读取 Chrome / Edge cookies | 仅本机，用户确认授权 |
| Bilibili / YouTube 登录态 | 本地扫码回调或 cookies 文件导入 |
| **明确不上传 cookies 到 SaveAny 服务器** | UI 与隐私政策一致 |
| 抖音 / X | 视 yt-dlp 与本机网络情况 |

### V0.3 — 本地 ASR + 云端 AI 衔接

| 能力 | 说明 |
|------|------|
| 本地音频提取 | ffmpeg 抽音频 |
| 本地 ASR | whisper.cpp tiny/base（CPU）或 faster-whisper（可选 GPU） |
| 输出 txt / srt | 用户可编辑 |
| 上传 transcript | 调用云端 `POST /api/ai/summary/from-transcript`（草案） |
| 或仅本地保存 | 不消耗云端 AI 额度 |

### V0.4 — 产品化

| 能力 | 说明 |
|------|------|
| 授权系统 | 设备绑定、心跳、吊销 |
| 离线授权缓存 | 短期离线可用（带过期） |
| 自动更新 | 差分或安装包；代码签名降低误报 |
| 错误日志导出 | 脱敏后用户自愿上传排障 |

---

## 4. 技术选型

### 4.1 候选对比

| 维度 | Python + PyInstaller | Electron | Tauri | Flutter Desktop | Rust + Python sidecar |
|------|----------------------|----------|-------|-----------------|------------------------|
| **开发速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **复用现有 Python** | ⭐⭐⭐⭐⭐（yt-dlp 服务逻辑） | ⭐（需重写或子进程） | ⭐⭐（sidecar） | ⭐ | ⭐⭐⭐⭐ sidecar |
| **yt-dlp 集成** | 原生子进程/库 | 子进程 | 子进程 | 子进程 | 子进程 |
| **ffmpeg 集成** | 打包二进制 | 打包 | 打包 | 打包 | 打包 |
| **Whisper 集成** | whisper.cpp / faster-whisper 成熟 | 间接 | 间接 | 较弱 | 可绑 C++ |
| **EXE 体积** | 80–200MB+（含依赖） | 150MB+ | 较小前端+sidecar | 中等 | 中等 |
| **Windows 兼容** | 好（注意 VC 运行库） | 好 | 好 | 好 | 好 |
| **自动更新** | 需自建（如 zip + 脚本） | electron-updater 成熟 | tauri-updater | 一般 | 需自建 |
| **杀毒误报** | 中–高（PyInstaller 常见） | 中 | 较低 | 中 | 低–中 |
| **UI 现代感** | 需 PyQt / CustomTkinter 等 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 取决于前端 |

### 4.2 推荐结论

| 阶段 | 推荐栈 |
|------|--------|
| **第一版（D0–D2）** | **Python 3.11+ + PyInstaller** + 轻量 GUI（CustomTkinter 或 PySide6） |
| **子进程** | 内置 `yt-dlp`、`ffmpeg` 静态路径 |
| **后续（D5+）** | 若 UI/更新/体积成为瓶颈，评估 **Tauri 2 + Python sidecar**（Rust 壳 + 现有 Python 引擎） |

**理由：** 与现有 `backend/app/services/ytdlp_service.py`、脚本生态一致，最快验证「本地下载闭环」；Electron 过重且难复用 Python；Flutter 对 Whisper 生态弱。

---

## 5. 本地 ASR 方案

| 方案 | CPU | GPU | 模型体积 | 中文 | 长视频 | 资源占用 | 建议阶段 |
|------|-----|-----|----------|------|--------|----------|----------|
| **whisper.cpp** | ⭐⭐⭐⭐ | 可选 CUDA/Metal | tiny ~75MB, base ~150MB | 可用 base | 需切片 | 中 | **V0.3 首选 CPU** |
| **faster-whisper** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 类似 | 好 | 切片成熟 | 中高 | V0.4+ 有 NVIDIA 时 |
| **OpenAI Whisper 原版** | 慢 | 可用 | 大 | 好 | 切片 | 高 | 不推荐打包进 EXE |
| **外部 ASR API** | 低本地 | — | — | 好 | 好 | 依赖网络 | 与 Web 类似，非 Desktop 差异化 |
| **云端 ASR** | — | — | — | — | — | 占服务器成本 | Web 已关闭；Desktop 不优先 |

**建议：**

- **V0.1–V0.2：** 不做 ASR，降低首版复杂度。
- **V0.3：** `whisper.cpp` **tiny 或 base**，CPU 默认可用；长视频 **按 5–10 分钟切片**；进度条 + 可取消。
- **后续：** 检测 NVIDIA → 可选 faster-whisper；无 GPU 仍走 cpp。

**用户体验：** 明确标注「本地转写耗时与电脑性能相关」；会员可设 **每月本地 ASR 时长上限**（授权层控制，非无限）。

---

## 6. 授权与收费设计

### 6.1 权益维度（建议拆分）

| 权益 | 免费版 | 月卡 | 年卡 | 永久本地版 |
|------|--------|------|------|------------|
| Web 720p 下载 | ✔ | ✔ | ✔ | ✔ |
| Web VIP 高清 | — | ✔ | ✔ | 可选绑定 |
| **Desktop 本地下载** | 限量/试用 | ✔ | ✔ | ✔ |
| **Desktop 本地 ASR** | — / 试用分钟 | 配额 | 更高配额 | 配额（**非无限**） |
| **云端 AI 总结** | 低额度 | 中 | 高 | **单独额度包**，永久版不无限送 |
| **设备数** | 1 | 2 | 3 | 3–5（可配置） |
| **离线授权缓存** | 24h | 72h | 7d | 7d |

### 6.2 原则

- **永久本地版** 卖的是 **软件授权 + 本地下载/ASR 能力**，**不应** 无限赠送云端 AI token（避免成本击穿）。
- Desktop 与 Web VIP **可捆绑销售**，也可 **Desktop -addon** 单独定价。
- 授权文件含：`user_id`、`plan`、`features[]`、`expire_at`、`device_id`、`signature`（服务器私钥签，客户端公钥验）。

### 6.3 离线缓存

- 心跳成功时刷新本地 license 缓存（如 7 天滑动）。
- 超期未心跳 → 降级为只读/禁止新下载，已下载文件不受影响。

---

## 7. 云端 API 设计草案（仅草案，本轮不改代码）

以下接口供 Desktop 客户端调用；路径前缀建议 `/api/desktop/` 与现有 `/api/users` 隔离。

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/api/desktop/login` | 邮箱+密码或 refresh token → `access_token` + `refresh_token` |
| `GET` | `/api/desktop/license` | 返回当前用户 Desktop 权益、配额、过期时间、功能开关 |
| `POST` | `/api/desktop/device/activate` | 绑定 `device_id`（硬件指纹哈希）、设备名；校验设备数上限 |
| `POST` | `/api/desktop/device/heartbeat` | 续期离线缓存；上报版本号（可选匿名统计） |
| `DELETE` | `/api/desktop/device/{id}` | 用户解绑设备 |
| `GET` | `/api/account/me` | 复用现有用户信息（昵称、VIP 状态） |
| `POST` | `/api/ai/summary/from-transcript` | 上传 transcript 文本或 SRT 内容 → 异步 AI 总结任务（与 Web AI MVP 对齐） |
| `GET` | `/api/ai/summary/{task_id}` | 轮询总结结果 |

**安全草案：**

- Desktop 使用独立 `client_id` + 较长 refresh token。
- License 响应 **服务器签名**（JWT 或自定义 JSON + HMAC）。
- **无** cookies 上传接口。

---

## 8. 隐私与安全

| 原则 | 说明 |
|------|------|
| **cookies 仅存本机** | 读取浏览器 profiles 或用户导入文件；进程内存用后清理 |
| **不上传 cookies** | 网络层无 cookies 字段；隐私政策与用户首次授权弹窗明确 |
| **本地日志脱敏** | 日志中屏蔽 Cookie 头、SESSDATA、token；导出前二次确认 |
| **上传云端内容** | 仅 **transcript / 用户主动提交的 SRT** 及 AI 总结请求元数据 |
| **版权免责** | 用户自行承担下载内容合法性；软件内与 Terms 一致 |
| **设备指纹** | 仅用于授权绑定，告知用户用途；提供解绑 |
| **传输** | HTTPS only；证书固定可选（V0.4） |

---

## 9. 法律与平台风险

| 风险类型 | 说明 | 缓解 |
|----------|------|------|
| **版权** | 下载工具可能被指鼓励侵权 | Terms 强调个人合理使用；不提供盗版源；投诉通道 |
| **平台 ToS** | YouTube/B 站等禁止未经授权下载 | 用户自担；产品不宣称「破解」 |
| **cookies 读取** | 可能触及浏览器数据使用边界 | 明示授权；本地处理；参考同类工具做法 |
| **软件分发** | 无签名 EXE 易被 SmartScreen 拦截 | 代码签名证书；开源部分组件说明 |
| **杀毒误报** | PyInstaller 打包常见误报 | 签名 + 厂商申诉 + 官网直链 |
| **跨境数据** | transcript 上传云端 | 隐私政策说明存储地；最小化上传 |

---

## 10. 推荐实施路线

| 阶段 | 名称 | 交付物 | 依赖 |
|------|------|--------|------|
| **D0** | 文档与原型设计 | 本文档、线框图、API 草案评审 | 无 |
| **D1** | CLI 原型 | `saveany-local download <url>` 可调通 yt-dlp+ffmpeg | 新仓库或 monorepo 子目录 |
| **D2** | Windows GUI MVP | V0.1 EXE、登录、会员检查、下载 | D1 |
| **D3** | 会员授权 | license API、设备绑定、心跳 | 后端小改（另任务） |
| **D4** | cookies 支持 | V0.2 本机 cookies / 扫码 | D2 |
| **D5** | 本地 ASR | V0.3 whisper.cpp | D2 |
| **D6** | 正式发布 | 签名、更新、文档、与 Web 捆绑销售 | D3–D5 + [monetization-paths.md](./monetization-paths.md) |

**与 Web Beta 并行：** D0–D1 可由 1 人兼职，**不阻塞** Web Beta B1/B2；D3 需后端排期时与「手动开通 VIP」等合并规划。

---

## 11. 是否值得做 — 明确判断

| 问题 | 判断 |
|------|------|
| **是否值得做？** | **值得**，作为 SaveAny 差异化与成本结构优化的战略方向；非立即替代 Web。 |
| **什么时候做？** | **Web Beta 稳定后**（连续无 P0、付费路径有结论）启动 **D1 CLI**；**2–3 个月内** 出 V0.1 EXE 内测。 |
| **是否新建仓库？** | **建议新建** `SaveAny-Desktop` 或 monorepo `packages/desktop`，与 Web 仓库解耦发布周期；共享 `url_normalize` 等可抽 **git submodule / 小型 shared 包**。 |
| **第一版最小目标？** | **V0.1：** 会员登录 + 本地 yt-dlp 下载 + ffmpeg 合并 + 打开文件夹；**不做** cookies 与 ASR。 |
| **是否阻塞当前 Web Beta？** | **不阻塞。** Web 继续 Beta、反馈表、变现调研；Desktop 走 D0/D1 文档与原型即可。 |

---

## 12. 架构示意（逻辑）

```text
┌─────────────────────────────────────────────────────────────┐
│                 SaveAny Cloud (现有 Web API)                 │
│  Auth · VIP/License · Orders · AI Summary (transcript in)   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS (no cookies)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           SaveAny Local Desktop Assistant (Windows)          │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐ │
│  │   GUI   │  │ License  │  │ yt-dlp  │  │   ffmpeg     │ │
│  │         │  │  Cache   │  │ worker  │  │   merge      │ │
│  └─────────┘  └──────────┘  └─────────┘  └──────────────┘ │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │ Cookies Reader  │  │ whisper.cpp / faster-whisper (D5)│  │
│  │ (local only)    │  └──────────────────────────────────┘  │
│  └─────────────────┘                                         │
│  User Download Folder · Local SRT/TXT · Logs (redacted)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. 下一步推荐任务

```
NEXT_RECOMMENDED_TASK=SaveAny P0：后台手动开通 VIP 工具设计
```

（优先完成 Web Beta 变现与人工开通闭环；Desktop D1 CLI 可与该任务 **并行** 由不同人推进。）

Desktop 专属后续任务示例：

- `SaveAny P1：Desktop CLI 原型（yt-dlp + ffmpeg）`
- `SaveAny P1：Desktop License API 详细设计`

---

*本文档为架构与可行性研究，不代表已立项或对外承诺发布时间。*
