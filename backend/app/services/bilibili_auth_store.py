from __future__ import annotations

import base64
import io
import secrets
import time
from dataclasses import dataclass, field

import qrcode
import requests


@dataclass
class BiliAuthSession:
    session_id: str
    qrcode_key: str
    login_url: str
    request_session: requests.Session
    created_at: float = field(default_factory=time.time)
    cookies_text: str | None = None
    is_logged_in: bool = False
    message: str = "等待扫码"


class BiliAuthStore:
    def __init__(self) -> None:
        self._sessions: dict[str, BiliAuthSession] = {}

    def _new_requests_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
            }
        )
        return session

    def create(self) -> tuple[BiliAuthSession, str]:
        self.cleanup()
        request_session = self._new_requests_session()
        response = request_session.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        auth = BiliAuthSession(
            session_id=secrets.token_urlsafe(18),
            qrcode_key=data["qrcode_key"],
            login_url=data["url"],
            request_session=request_session,
        )
        self._sessions[auth.session_id] = auth
        return auth, self._make_qr_data_uri(auth.login_url)

    def poll(self, session_id: str) -> BiliAuthSession | None:
        auth = self._sessions.get(session_id)
        if not auth:
            return None
        if auth.is_logged_in:
            return auth
        response = auth.request_session.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": auth.qrcode_key},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        code = data.get("code")
        messages = {
            0: "登录成功",
            86038: "二维码已失效，请重新生成",
            86090: "已扫码，请在手机上确认",
            86101: "等待扫码",
        }
        auth.message = messages.get(code, data.get("message") or "等待扫码")
        if code == 0:
            auth.is_logged_in = True
            auth.cookies_text = self._cookies_to_netscape(auth.request_session.cookies)
        return auth

    def get_cookies(self, session_id: str | None) -> str | None:
        if not session_id:
            return None
        auth = self._sessions.get(session_id)
        if not auth or not auth.is_logged_in:
            return None
        return auth.cookies_text

    def cleanup(self) -> None:
        now = time.time()
        expired = [
            session_id
            for session_id, auth in self._sessions.items()
            if now - auth.created_at > 60 * 60 * 4
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)

    def _make_qr_data_uri(self, content: str) -> str:
        image = qrcode.make(content)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _cookies_to_netscape(self, cookies: requests.cookies.RequestsCookieJar) -> str:
        lines = ["# Netscape HTTP Cookie File"]
        for cookie in cookies:
            domain = cookie.domain or ".bilibili.com"
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            path = cookie.path or "/"
            secure = "TRUE" if cookie.secure else "FALSE"
            expires = int(cookie.expires or 2147483647)
            lines.append(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}")
        return "\n".join(lines) + "\n"


bili_auth_store = BiliAuthStore()
