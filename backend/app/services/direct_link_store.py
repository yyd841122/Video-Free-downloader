from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from app.core.config import DIRECT_LINK_TTL_SECONDS


@dataclass
class DirectLink:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    title: str | None = None
    expires_at: float = field(default_factory=lambda: time.time() + DIRECT_LINK_TTL_SECONDS)


class DirectLinkStore:
    def __init__(self) -> None:
        self._links: dict[str, DirectLink] = {}

    def create(self, link: DirectLink) -> str:
        self.cleanup()
        token = secrets.token_urlsafe(24)
        self._links[token] = link
        return token

    def get(self, token: str) -> DirectLink | None:
        link = self._links.get(token)
        if not link:
            return None
        if link.expires_at < time.time():
            self._links.pop(token, None)
            return None
        return link

    def cleanup(self) -> None:
        now = time.time()
        expired = [token for token, link in self._links.items() if link.expires_at < now]
        for token in expired:
            self._links.pop(token, None)


direct_link_store = DirectLinkStore()
