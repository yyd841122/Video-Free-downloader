"""Tests for registration email validation (no real mail)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.email_validation import (  # noqa: E402
    EmailValidationError,
    MSG_INVALID_ZH,
    MSG_PLACEHOLDER_ZH,
    validate_registration_email,
)


def expect_pass(email: str) -> None:
    result = validate_registration_email(email)
    assert "@" in result
    assert result == result.lower()


def expect_fail(email: str, *, contains: str) -> None:
    try:
        validate_registration_email(email)
    except EmailValidationError as exc:
        if contains not in exc.message_zh:
            raise AssertionError(f"expected {contains!r} in {exc.message_zh!r} for {email!r}") from exc
        return
    raise AssertionError(f"expected failure for {email!r}")


def test_valid_gmail() -> None:
    expect_pass("user.name@gmail.com")


def test_valid_gmail_plus() -> None:
    expect_pass("user+test@gmail.com")


def test_valid_qq() -> None:
    expect_pass("user@qq.com")


def test_invalid_no_at() -> None:
    expect_fail("not-an-email", contains=MSG_INVALID_ZH)


def test_blocked_test_test() -> None:
    expect_fail("test@test.com", contains=MSG_PLACEHOLDER_ZH)


def test_blocked_example_domain() -> None:
    expect_fail("someone@example.com", contains=MSG_PLACEHOLDER_ZH)


def main() -> int:
    tests = [
        test_valid_gmail,
        test_valid_gmail_plus,
        test_valid_qq,
        test_invalid_no_at,
        test_blocked_test_test,
        test_blocked_example_domain,
    ]
    passed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"PASS {name}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {name}: {exc}")
    print(f"\n{passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
