# SaveAny Helper

Chrome/Edge Manifest V3 extension for local media request capture.

## What it does

- Lets the user manually start capture on the current video tab.
- Records likely media requests such as `m3u8`, `mpd`, `m4s`, `ts`, `mp4`, `webm`.
- Captures safe request headers by default: `User-Agent`, `Referer`, `Origin`, `Range`, `Accept`, `Accept-Language`.
- Sends captured results to the local FastAPI service at `http://127.0.0.1:8000/api/extension/captures`.
- Does not capture `Cookie` or `Authorization` unless the user explicitly enables the sensitive-header checkbox.

## Local install

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable developer mode.
3. Click "Load unpacked".
4. Select this `browser-extension` directory.

## Current scope

This is the first bridge version. It captures browser-side playback requests but does not yet convert them into download tasks.
