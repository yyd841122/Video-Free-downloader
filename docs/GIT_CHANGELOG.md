# Git Version Notes

This document records the major Git backup points of the project, so future developers and AI assistants can quickly understand what changed in each version.

## Current Branch

- Main branch: `master`
- Remote repository: `https://github.com/yyd841122/Video-Free-downloader`

## Version Timeline

### Latest - feat: polish download and AI result UI

Polished the main download page and AI result experience:

- Reworked the hero area so parsed results can move into the first viewport faster.
- Added compact parsed-state behavior: hide marketing copy after parsing, restore it when the URL is cleared.
- Rebuilt the result layout as desktop two-column cards with equal height and mobile content-height cards.
- Made Bilibili login guidance contextual: only show the scan-login prompt after parsing a Bilibili link.
- Simplified the Bilibili HD warning copy for normal users.
- Improved summary Markdown presentation, transcript readability, and transcript format downloads.
- Rebuilt the mind map logic around summary-derived semantic branches instead of forced keyword/timeline nodes.
- Added consistent SVG-based mind map rendering and high-quality PNG/SVG downloads.
- Polished AI Q&A into a chat-bubble interface.
- Redesigned the lower marketing area with five feature cards and Free/VIP plan cards.

Validation:

- Frontend production build passed with `npm.cmd run build`.
- Frontend and backend were restarted locally and returned HTTP 200 on `5173` and `/api/health`.

### 3b73ae5 - feat: add AI video summary workflow

Added the first complete AI video understanding workflow:

- Added Deepseek-based AI summary tasks.
- Added platform subtitle extraction and timestamped transcript parsing.
- Added SRT/VTT subtitle upload fallback for videos without extractable platform subtitles.
- Added BibiGPT-style result tabs for summary, transcript, mind map, and AI Q&A.
- Added interactive XMind-like mind map with pan, zoom, fit, and reset controls.
- Added AI Q&A over the generated summary and transcript.
- Fixed YouTube subtitle extraction to avoid downloading all subtitle languages and reduce HTTP 429 risk.
- Added Deepseek malformed JSON repair and fallback summary generation.
- Documented the implementation in `docs/AI_SUMMARY_IMPLEMENTATION.md`.

Validation:

- Backend compile check passed.
- Frontend production build passed.
- YouTube subtitle extraction and AI summary flow were verified with a real public video.

### 5a7d3c0 - feat: add browser extension capture bridge

Added the first browser extension MVP:

- Added `browser-extension/` Chrome/Edge Manifest V3 extension.
- Added media request capture for `m3u8`, `mpd`, `m4s`, `ts`, `mp4`, `webm`, `flv`, and `mov`.
- Added extension popup to start/stop capture, copy JSON, and send capture data to local FastAPI.
- Added backend `/api/extension/captures` API.
- Added in-memory extension capture store.
- Added `docs/EXTENSION_DESIGN.md`.

Purpose:

- Prepare for solving platforms that need browser playback context, such as Bilibili HD, iQIYI, Tencent Video, and similar dynamic playback pages.

### 6e5f3da - feat: add url clear button

Improved frontend URL input usability:

- Added a clear button inside the video URL input area.
- Clicking the button clears the current URL and focuses the input again.
- Added responsive styling for mobile layout.

### b5ffe19 - fix: stabilize douyin downloads

Improved Douyin download reliability:

- Added retry and fallback behavior for Douyin CDN read timeout cases.
- Refreshed media URLs before retrying when needed.
- Improved partial download handling and final file validation.
- Documented Douyin fallback strategy.

### 97e080f - docs: record bilibili quality check

Recorded Bilibili quality investigation:

- Verified Bilibili anonymous mode cannot reliably obtain 1080P.
- Confirmed Referer/User-Agent alone does not solve Bilibili HD access.
- Recorded why Bilibili HD usually needs login state, account permission, or local-helper/plugin mode.

### 291d935 - fix: detect douyin quality variants

Improved Douyin quality detection:

- Avoided displaying false 1080P when the actual downloadable media is only 720P.
- Added real-media probing to compare actual width, height, duration, and file size.
- Grouped and displayed real downloadable quality variants.

### 9514018 - fix: improve platform auth fallbacks

Improved platform warning and authentication fallback behavior:

- Reduced exposure of noisy yt-dlp technical warnings to normal users.
- Added safer handling for platform-specific auth warnings.
- Kept Bilibili login-related guidance where it affects HD availability.

### 0a40331 - fix: support top-level media formats

Fixed cases where a platform returns a top-level media URL without a normal format list:

- Added fallback format synthesis for extractors that return `info.url`.
- Solved cases such as Snapchat where parsing succeeds but no download card was shown.

### c414b58 - feat: polish download feedback

Improved frontend download experience:

- Removed unnecessary backend progress panel from normal user flow.
- Kept the browser download behavior as the main download progress signal.
- Added selected-format feedback and cleaner completion messaging.

### abc1572 - fix: stabilize youtube downloads

Fixed YouTube download issues:

- Configured yt-dlp JavaScript runtime support.
- Added EJS remote component support for YouTube challenge handling.
- Improved retry, timeout, and chunk download settings.
- Ensured YouTube downloads go through backend full download and merge flow.

### 058e897 - feat: build video downloader MVP

Initial MVP implementation:

- Vue + Vite frontend.
- FastAPI backend.
- yt-dlp based video info extraction.
- Server-side download task flow.
- Direct link, redirect, and proxy download modes.
- Basic responsive UI.
- Core API, task store, file download endpoint, and project docs.

## Useful Git Commands

View commit history:

```powershell
git log --oneline --graph --decorate --all
```

View one commit:

```powershell
git show <commit-id>
```

Compare current code with a previous version:

```powershell
git diff <commit-id>..HEAD
```

Temporarily inspect an old version:

```powershell
git checkout <commit-id>
```

Return to the main branch:

```powershell
git checkout master
```

Push all local branches and tags:

```powershell
git push --all origin
git push --tags origin
```

## Notes

- Do not commit cookies, downloaded videos, private tokens, or browser profile data.
- Keep user login state out of Git.
- For large future features, create a new commit after each stable milestone.
- Update this document whenever a meaningful backup point is created.
