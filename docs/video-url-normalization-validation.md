# SaveAny 抖音 modal_id URL Normalize 验收报告

本文档记录抖音地址栏 `modal_id` 链接的 URL normalize 修复及生产环境验收结果，供后续运维与回归参考。

---

## 1. 验收概要

| 项 | 内容 |
|---|---|
| 验收日期 | 2026-05-25 |
| 关联 commit | `0610161`（modal_id 识别）；`2f3d87f`（normalize 目标修正为 share URL） |
| 前端 | `https://videodown.cozyguidehub.com`（Cloudflare Pages） |
| 后端 API | `https://api-videodown.cozyguidehub.com` |
| 验收结论 | **通过** — 地址栏 `jingxuan?modal_id=` 链接可解析并下载 |

---

## 2. 背景与根因

### 2.1 用户场景

用户从抖音网页地址栏复制链接，例如：

```text
https://www.douyin.com/jingxuan?modal_id=7643509713572777266
```

其中 `modal_id` 为真实视频 ID；页面路径 `jingxuan` 为精选页，视频以弹窗形式展示。

### 2.2 中间方案为何失败

首轮修复将 `modal_id` normalize 为：

```text
https://www.douyin.com/video/{modal_id}
```

线上 normalize 已生效，但解析仍失败，报错类似：

```text
抖音页面未返回可解析的视频数据，请稍后重试。
```

排查结论：

1. 当前环境 yt-dlp 对 `douyin.com/video/{id}` 常返回 `Fresh cookies are needed`，无法直接拿到 info。
2. `www.douyin.com/video/{id}` 桌面页 **不含** `window._ROUTER_DATA`。
3. 项目 Douyin 可用兜底为 `extract_douyin_share_info()`，依赖分享页 HTML 中的 `_ROUTER_DATA`。
4. 因此 `/video/{id}` 不是适合当前提取链路的 normalize 目标。

### 2.3 正确 normalize 目标

`modal_id` 应 normalize 为抖音分享页 URL：

```text
https://www.iesdouyin.com/share/video/{modal_id}/
```

该页面包含 `_ROUTER_DATA`，与 `v.douyin.com` 短链、`m.douyin.com/share/video/{id}` 走同一兜底路径。

---

## 3. Normalize 规则（当前生产）

| 输入类型 | 示例 | normalize 结果 |
|---|---|---|
| 地址栏 modal_id | `https://www.douyin.com/jingxuan?modal_id=7643509713572777266` | `https://www.iesdouyin.com/share/video/7643509713572777266/` |
| 分享短链 | `https://v.douyin.com/RkYdrHyJWek/` | **保持不变** |
| 已有 `/video/{id}` 直链 | `https://www.douyin.com/video/7643509713572777266` | **保持不变**（不强制转 share URL） |
| 非数字 modal_id | `?modal_id=abc123` | **不转换**，走原有 Douyin normalize |

前后端共用逻辑：

- 前端：`frontend/src/utils/urlNormalize.js`
- 后端：`backend/app/utils/url_normalize.py`
- 测试：`backend/scripts/test_url_normalize.py`

---

## 4. 生产验收用例

### 4.1 主用例：地址栏 modal_id

| 步骤 | 结果 |
|---|---|
| 输入 `https://www.douyin.com/jingxuan?modal_id=7643509713572777266` | ✅ |
| 前端/后端 normalize 为 `https://www.iesdouyin.com/share/video/7643509713572777266/` | ✅ |
| 解析出视频卡片（标题、封面、时长、清晰度） | ✅ |
| 下载完成 | ✅ |

### 4.2 回归：分享短链

| 输入 | 结果 |
|---|---|
| `https://v.douyin.com/...` 整段分享文案或短链 | ✅ 仍可用，逻辑未破坏 |

### 4.3 页面与 Console

| 检查项 | 结果 |
|---|---|
| 首页无白屏 | ✅ |
| 无 `Invalid linked format` | ✅ |
| Console 仅浏览器插件类 warning（如 `runtime.lastError: The message port closed before a response was received`） | ✅ 非 SaveAny fatal error |

---

## 5. 限制与后续

- Douyin 兜底仍依赖分享页输出 `window._ROUTER_DATA`；若抖音改版页面结构，需同步更新 `extract_douyin_share_info`。
- `www.douyin.com/video/{id}` 直链未在本轮强制改写；在无 cookies 环境下仍可能解析失败，用户可改用分享短链。
- 本文档不记录任何用户隐私、Cookie 内容或 API 密钥。

---

## 6. 本地回归命令

```powershell
cd frontend
npm run build

cd ../backend
python -m compileall app
python scripts/test_url_normalize.py
```

---

*本文档仅记录 URL normalize 与 Douyin 解析验收，不构成对外产品承诺。*
