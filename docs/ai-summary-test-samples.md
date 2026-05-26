# SaveAny AI 总结 — 测试样本记录模板

Last updated: 2026-05-25

用途：记录 AI 总结 MVP 回归测试样本，便于判断「有没有字幕」「能不能直接总结」「是否需要上传 SRT/VTT」。

**注意：** 不要在本文件中填写 cookie、token、API key、用户隐私信息。

相关文档：`docs/ai-summary-mvp-validation.md`

---

## 1. 样本分类

| 分类 | 说明 | 预期 `subtitle_status` |
|------|------|------------------------|
| 有平台字幕 | YouTube / Bilibili 等带 manual 或 automatic captions | `available` |
| 无平台字幕 | 平台 metadata 明确无字幕轨道 | `unavailable` |
| 状态 unknown | 平台未返回字幕 metadata（常见于 Douyin） | `unknown` |
| 上传 SRT/VTT | 不走 `/api/video/info` 字幕检测，直接上传 | N/A |
| 需 cookies / 登录 | 解析或 AI 总结需平台验证 | `unknown` 或 AI 失败友好提示 |

---

## 2. 有字幕视频样本

| # | URL | 平台 | subtitle_status | subtitle_source | subtitle_languages | AI 总结结果 | 备注 |
|---|-----|------|-----------------|-----------------|-------------------|-------------|------|
| 1 | _(待填)_ | YouTube | available | automatic | en | _(待测)_ | 英文自动字幕 |
| 2 | _(待填)_ | YouTube | available | manual | zh-Hans | _(待测)_ | 中文人工字幕 |
| 3 | _(待填)_ | Bilibili | available | automatic | zh-CN | _(待测)_ | 需观察是否需登录 |
| 4 | _(待填)_ | _(其他)_ | available | manual | _(待填)_ | _(待测)_ | |

**页面预期：**

- 主文案：`字幕状态：已检测到字幕，可使用 AI 总结。`
- 明细：字幕检测 / 语言 / 来源 / 可直接点击 AI 总结

---

## 3. 无字幕视频样本

| # | URL | 平台 | subtitle_status | subtitle_source | subtitle_languages | AI 总结结果 | 备注 |
|---|-----|------|-----------------|-----------------|-------------------|-------------|------|
| 1 | _(待填)_ | Douyin | unavailable | none | _(空)_ | 不发起 API / 提示上传 | |
| 2 | _(待填)_ | _(其他)_ | unavailable | none | _(空)_ | _(待测)_ | |

**页面预期：**

- 主文案：`字幕状态：暂未检测到字幕…`
- 明细：建议上传 SRT/VTT
- 显示 `SubtitleUploadPanel`

---

## 4. unknown 字幕状态样本

| # | URL | 平台 | subtitle_status | subtitle_source | subtitle_languages | AI 总结结果 | 备注 |
|---|-----|------|-----------------|-----------------|-------------------|-------------|------|
| 1 | _(待填)_ | Douyin | unknown | unknown | _(空)_ | 可尝试 AI 总结 | metadata 未暴露 |
| 2 | _(待填)_ | _(其他)_ | unknown | unknown | _(空)_ | _(待测)_ | |

**页面预期：**

- 主文案：`字幕状态：暂无法确认…`
- 明细：可尝试 AI 总结提取平台字幕
- AI 按钮可点击

---

## 5. 上传 SRT/VTT 样本

| # | 文件 | 编码 | 关联视频 URL | AI 总结结果 | 字幕文本 Tab | 备注 |
|---|------|------|--------------|-------------|--------------|------|
| 1 | sample.srt | UTF-8 | _(可选)_ | completed | 中文正常 | |
| 2 | sample.srt | GBK | _(可选)_ | completed | 中文正常 | 编码修复回归 |
| 3 | sample.srt | UTF-8 BOM | _(可选)_ | completed | 中文正常 | |
| 4 | sample.vtt | UTF-8 | _(可选)_ | completed | 中文正常 | |

**API：** `POST /api/ai/summary/subtitle`

---

## 6. 需 cookies / 登录验证样本

| # | URL | 平台 | subtitle_status | AI 总结点击结果 | 用户可见文案 | 备注 |
|---|-----|------|-----------------|-----------------|--------------|------|
| 1 | _(待填)_ | Douyin | unknown | failed / no_transcript | 友好提示 + 上传入口 | 不应出现 Fresh cookies 原文 |
| 2 | _(待填)_ | YouTube 会员/年龄限制 | unknown | _(待测)_ | _(待测)_ | 可选 cookies |
| 3 | _(待填)_ | Bilibili 高清/字幕 | unknown | _(待测)_ | _(待测)_ | 可选扫码登录 |

---

## 7. 回归检查项（每次填样本时勾选）

- [ ] 解析后字幕诊断区块显示主文案 + 明细
- [ ] `available` 显示语言 / 来源（若有）
- [ ] `unavailable` 显示上传建议且不误点 API
- [ ] `unknown` 允许尝试 AI 总结
- [ ] 上传字幕后 transcript 中文正常
- [ ] 总结摘要 / 思维导图 / 问答正常
- [ ] ASR 仍关闭（`/api/health` → `asr_enabled=false`）
- [ ] 无 cookie / token 写入本文档

---

## 8. 本地开发诊断行

开发模式（`npm run dev`）下，字幕诊断区块底部会显示一行技术摘要，例如：

```text
诊断：status=available · source=automatic · languages=zh,en
```

生产构建默认不显示该行。
