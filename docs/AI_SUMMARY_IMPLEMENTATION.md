# AI Video Summary Implementation Notes

Last updated: 2026-05-18

## Goal

Add AI-assisted video understanding on top of the existing yt-dlp download capability.

The confirmed implementation order is:

1. P0: Video summary from URL subtitles/transcript.
2. P0: Timestamped subtitle/transcript display.
3. P1: Mind map visualization.
4. P2: AI Q&A based on video content.

The first production path uses platform subtitles or automatic subtitles extracted by yt-dlp. Videos without subtitles are intentionally deferred; the current product can validate real user demand before adding paid ASR cost.

## Backend Implementation

Added AI summary API routes:

- `POST /api/ai/summary`
- `GET /api/ai/summary/{task_id}`
- `POST /api/ai/summary/subtitle`
- `POST /api/ai/summary/{task_id}/chat`

Added backend modules:

- `backend/app/api/ai.py`
- `backend/app/services/ai_summary_service.py`
- `backend/app/services/ai_task_store.py`

Core flow:

```text
User submits video URL
-> backend creates AI task
-> yt-dlp extracts subtitle metadata
-> backend downloads one preferred subtitle track
-> backend parses SRT/VTT/JSON subtitles into timestamped segments
-> Deepseek generates structured summary JSON
-> transcript.json and summary.json are saved under backend/downloads/{task_id}
-> frontend polls task status and renders result tabs
```

Deepseek configuration is read from `.env`:

```text
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MAX_TOKENS=4096
```

## Subtitle Extraction Strategy

The first version only extracts platform subtitles or automatic subtitles.

Important YouTube fix:

- Do not request `subtitleslangs=["all"]`.
- First read available subtitle metadata.
- Select a preferred single candidate, prioritizing Chinese and English tracks.
- Download one subtitle track at a time.
- Fall back to the next candidate if the first track fails.

This avoids triggering unnecessary subtitle downloads and reduces YouTube `HTTP Error 429: Too Many Requests`.

## Deepseek JSON Robustness

Deepseek can occasionally return malformed JSON even when JSON output is requested.

The backend now handles this safely:

1. Try to parse the original model output.
2. If parsing fails, ask Deepseek to repair the malformed JSON.
3. If repair still fails, generate a safe fallback summary from transcript text.
4. Do not expose raw JSON parse errors to the frontend.

This fixed errors like:

```text
Expecting ',' delimiter: line 55 column 111
```

## Frontend Implementation

Updated files:

- `frontend/src/App.vue`
- `frontend/src/api/client.js`
- `frontend/src/styles/main.css`
- `frontend/src/components/MindMapView.vue`
- `frontend/src/components/SubtitleUploadPanel.vue`
- `frontend/src/components/VideoChatPanel.vue`

AI result tabs:

- Summary
- Transcript
- Mind map
- AI Q&A

The AI summary button is placed next to the download button. The AI progress indicator uses the same compact circular style as download progress.

The result area was redesigned to follow the BibiGPT-style reading layout:

- Compact gray tab strip.
- White active tab.
- Lightweight shadow.
- Article-like summary content.
- Section titles with dividers.
- Highlights with small emoji markers.

## Mind Map

The mind map is rendered by `MindMapView.vue` from the structured summary.

Current capabilities:

- XMind-like branch layout.
- Drag to pan.
- Wheel zoom.
- Toolbar zoom in/out.
- Fit to view.
- Reset view.

The zoom range is now:

```text
20% - 170%
```

The center topic is derived from the video's core summary and keywords instead of simply copying the title.

## No-Subtitle Decision

No-subtitle videos are not converted with ASR in the current version.

Deferred options:

1. User uploads SRT/VTT and then summarizes.
2. Browser extension assists with subtitle capture.
3. Extract audio and call ASR service.

ASR will be evaluated later based on real user demand and cost. This is a product decision, not a technical blocker.

## Validation

Validated locally:

- `python -m compileall app`
- `npm.cmd run build`
- YouTube subtitle 429 fix with `https://www.youtube.com/watch?v=uQbyEv0Z9JM`
- Deepseek malformed JSON repair/fallback path
- Real AI summary task completed with `status=completed`, `progress=100`, and `error=null`

Notes:

- Backend AI tasks are in memory in the MVP. During development, backend reload can lose old task IDs.
- Existing download functionality remains on the original yt-dlp service path.
- No database, queue, vector store, or ASR service was introduced in this milestone.
