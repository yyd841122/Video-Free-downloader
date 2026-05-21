# SEO 优化记录

> 记录 SaveAny（万能视频下载总结器）前端 SEO 审计与逐轮落地的工作沉淀。本文与 `鱼厂 SEO 优化工作流.md`、`GEO优化入门指南.md` 配合使用。

---

## 1. 背景与目标

- **目标**：让用户在全网各搜索引擎（Google / 百度 / Bing / 360 / 搜狗）优先看到 SaveAny 产品内容。
- **正式域名（暂定）**：`videodown.cozyguidehub.com`。
- **品牌名（待最终确认）**：当前对外统一使用 `SaveAny`；中文长名「万能视频下载（总结）器」仅在文档与文案副标题里出现。
- **执行节奏**：分阶段、零业务风险落地，每一阶段只动 SEO 静态资产与语义层级，不改动任何业务逻辑、API 路由或 Vue 状态逻辑。

---

## 2. 审计结论摘要

使用 `seo-audit` skill 完整审计了：抓取性、索引性、技术 SEO、On-Page、Content Quality、合规与品牌一致性、AI 搜索可见性（llms.txt）。

**总体评分**：约 4 / 10 — 有 SEO 意识但存在 P0 级硬阻断。

**Top 5 紧急问题**

1. 全站使用占位域名 `saveany.example.com`，所有 canonical / og:url / sitemap / robots / JSON-LD 都指向不存在的域 — 等同于自我抑制收录。
2. Vue 3 SPA + 客户端渲染（CSR），HTML 源码只有 `<div id="app"></div>`，百度 / 360 / 搜狗几乎抓不到正文。
3. 单页架构，没有按页面模板划分 TDK，长尾流量战场（YouTube 下载 / Bilibili 下载 / AI 视频总结 等）完全放弃。
4. 同一页面出现两个 `<h1>`（Hero 区 1 个 + AI 摘要面板的 `sr-only` 1 个），违反 H1 唯一性。
5. 缺 `og:image`、Twitter Card 还是 `summary`、`index.html` 没有 `<link rel="icon">`。

完整发现按 `Technical / On-Page / Content` 三类共记录约 20 条，每条都标记了 Impact（High/Medium/Low）、Evidence（具体文件与行号）、Fix、Priority。

---

## 3. 本次（A 节奏）已落地的零风险修复

### 3.1 改动文件清单

| 文件 | 改动 |
|---|---|
| `frontend/index.html` | 替换域名为 `videodown.cozyguidehub.com`；新增 `X-UA-Compatible` / `format-detection`；新增 `<link rel="icon" type="image/svg+xml" href="/favicon.svg">`；`WebApplication` JSON-LD 补 `inLanguage: zh-CN`；新增独立 `Organization` JSON-LD 块；body 末尾加 `<noscript>` 兜底正文；标记 og:image / twitter:image 的 TODO 占位 |
| `frontend/src/App.vue` | AI 摘要面板内多余的 `<h1 class="sr-only">` 改为 `<h2 class="sr-only">`（视觉零变化，仅修语义层级，消除多 H1） |
| `frontend/public/robots.txt` | 增加 `Disallow: /api/` 与 `Disallow: /downloads/`；Sitemap 指向新域名 |
| `frontend/public/sitemap.xml` | `<loc>` 替换为新域名 |
| `frontend/public/llms.txt` | Home / Sitemap 链接替换为新域名 |
| `frontend/public/favicon.svg`（新增） | SaveAny 品牌色播放按钮 favicon，与 `App.vue` Header 品牌图标一致 |

### 3.2 设计取舍记录

- **OG 图未启用**：未提供 1200×630 PNG 之前，刻意不引用 `og:image` / `twitter:image`，避免社交分享出现破图。HTML 留有 `TODO(SEO)` 注释指引未来切换为 `summary_large_image`。
- **未做 SSR / 预渲染**：保持 SPA 架构，先用 `<noscript>` 兜底文案给百度 / 360 / 搜狗这类不跑 JS 的爬虫一份基础语义。后续是否上 `vite-ssg` 或 Nuxt 待用户拍板。
- **未引入 vue-router 与落地页**：长尾落地页方案（YouTube 下载页 / Bilibili 下载页 / AI 视频总结页 等）已规划但暂不落地，避免本轮范围扩散。
- **未改 H1 文案**：Hero 区的 `<h1>万能视频下载器，一键保存</h1>` 没有动；要换文案需要先确定最终品牌名定调。
- **未改 sitemap URL 列表**：只有首页一个 URL；扩展依赖落地页路由先就位。
- **`MindMapView.vue` 的本地改动**：是思维导图导出字体自适应优化，**不属于本次 SEO 工作**，未纳入 SEO commit。
- **`.agents/` 与 `skills-lock.json`**：是安装 `seo-audit` skill 留下的本地产物，是否进库由项目策略决定，未主动加入 SEO commit。

---

## 4. 验证方法

1. **页面外观零变化**：启动 `npm run dev`，访问 `http://localhost:5173/`，所有现有功能（解析 / 下载 / AI 总结 / 思维导图 / Bilibili 扫码登录）应当与改动前一致。
2. **查看页面源代码**：右键 → 查看页面源代码，确认：
   - 3 段 JSON-LD（WebApplication / Organization / FAQPage）都存在
   - canonical / og:url 已经是 `https://videodown.cozyguidehub.com/`
   - `<noscript>` 区块完整
3. **禁用 JS 复测**：DevTools → Settings → Debugger → Disable JavaScript → 刷新，应看到 `<noscript>` 渲染出的中文兜底页（H1 + 平台列表 + 使用提示）。这就是百度 / 360 看到的内容。
4. **静态资产可达性**：
   - `http://localhost:5173/favicon.svg` 返回 200 + SVG 内容
   - `http://localhost:5173/robots.txt` 返回 200 + 含新域名 Sitemap 行
   - `http://localhost:5173/sitemap.xml` 返回 200 + `<loc>` 为新域名

---

## 5. 后续待办（按优先级）

### P0 — 剩余关键阻断

- [ ] 渲染策略决策：仅 `<noscript>` 兜底是否够用？要不要再上 `vite-ssg` 做构建期预渲染（不动 Vue 代码、不动 API、纯构建链增强）。

### P1 — 高影响改造

- [ ] OG 图：制作 1200×630 品牌 PNG（< 5MB），放到 `frontend/public/og-cover.png`，启用 `og:image` / `twitter:image` 并将 `twitter:card` 升级为 `summary_large_image`。
- [ ] 长尾落地页：引入 `vue-router`，规划 6–8 个长尾落地页（YouTube / Bilibili / 抖音 / TikTok / Twitter-X 下载，AI 视频总结，字幕提取，FAQ / About），每页独立 TDK 与 `<title>` / `<meta>` 切换。
- [ ] H1 / H2 / H3 文案：在不破坏视觉的前提下让主标题与小节标题覆盖关键词。
- [ ] Footer / 「关于我们」：展示合规与联系信息，提升 E-E-A-T Trustworthiness。
- [ ] JSON-LD 进阶：补 `SoftwareApplication`、`screenshot`、`publisher/author`、`aggregateRating`（如有评分数据）。

### P2 — 持续优化

- [ ] 内链系统：FAQ / 特性区里的关键词做成指向落地页的内链。
- [ ] 撰写产品博客 / 教程 / 平台兼容性详情页。
- [ ] Google Search Console / 百度站长平台 / Bing Webmaster 提交。
- [ ] Core Web Vitals & PageSpeed 复测（markmap、AI 面板考虑路由懒加载）。
- [ ] 决策是否做多语言（英文版） → 走完整 hreflang 规范（自指 / 双向 / `x-default`）。
- [ ] `vite.config.js` 中暴露 `VITE_SITE_ORIGIN` / `VITE_SITE_NAME`，让 SEO 资产不再硬编码域名。

---

## 6. 关键决策记录

| 决策项 | 当前选择 | 备注 |
|---|---|---|
| 正式域名 | `videodown.cozyguidehub.com` | 用户在 A 节奏阶段给定 |
| 节奏 | A 节奏（最稳） | 仅做零业务风险的 F-1 ~ F-6 |
| 品牌名 | 暂用 `SaveAny`（英文）+ 副标题中文 | 等用户最终拍板 |
| 渲染策略 | SPA + `<noscript>` 兜底 | SSR / 预渲染待决策 |
| OG 图 | 暂不启用 | 等 PNG 资产 |
| 落地页路由 | 不引入 | 等用户允许扩 URL |
| 多语言 | 不做 hreflang | 等是否做英文版决策 |

---

## 7. 参考资料

- `鱼厂 SEO 优化工作流.md` — 鱼皮团队的 SEO 工作流（TDK 规范、Meta 标签清单、结构化标签、检查清单）。
- `GEO优化入门指南.md` — Generative Engine Optimization 入门，面向 AI 搜索的可见性。
- `seo-audit` skill — 安装于 `.agents/skills/seo-audit/`，提供本次审计的框架。
