"""Registration email format and placeholder blocklist validation."""

from __future__ import annotations

import re
from typing import Final

MAX_EMAIL_LENGTH: Final[int] = 254

MSG_INVALID_ZH = "请输入有效邮箱地址。"
MSG_INVALID_EN = "Please enter a valid email address."

MSG_PLACEHOLDER_ZH = "请使用真实邮箱注册，测试邮箱或占位邮箱不可用。"
MSG_PLACEHOLDER_EN = "Please use a real email address. Test or placeholder emails are not allowed."

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

BLOCKED_EMAILS: Final[frozenset[str]] = frozenset(
    {
        "test@test.com",
        "abc@abc.com",
        "admin@admin.com",
        "demo@demo.com",
        "fake@fake.com",
        "1@1.com",
        "a@a.com",
        "example@example.com",
    }
)

BLOCKED_DOMAINS: Final[frozenset[str]] = frozenset(
    {
        "example.com",
        "example.net",
        "example.org",
        "test.com",
        "invalid.com",
    }
)


class EmailValidationError(ValueError):
    """Raised when a registration email fails format or blocklist checks."""

    def __init__(self, message_zh: str, message_en: str | None = None) -> None:
        self.message_zh = message_zh
        self.message_en = message_en or message_zh
        super().__init__(message_zh)


def _is_placeholder_email(email_norm: str) -> bool:
    if email_norm in BLOCKED_EMAILS:
        return True
    local, sep, domain = email_norm.partition("@")
    if not sep or not local or not domain:
        return True
    if domain in BLOCKED_DOMAINS:
        return True
    return False


def validate_registration_email(email: str) -> str:
    """Normalize and validate a registration email. Raises EmailValidationError on failure."""
    raw = (email or "").strip()
    if not raw:
        raise EmailValidationError(MSG_INVALID_ZH, MSG_INVALID_EN)
    if len(raw) > MAX_EMAIL_LENGTH:
        raise EmailValidationError(MSG_INVALID_ZH, MSG_INVALID_EN)

    email_norm = raw.lower()
    if not _EMAIL_PATTERN.match(email_norm):
        raise EmailValidationError(MSG_INVALID_ZH, MSG_INVALID_EN)
    if _is_placeholder_email(email_norm):
        raise EmailValidationError(MSG_PLACEHOLDER_ZH, MSG_PLACEHOLDER_EN)
    return email_norm
