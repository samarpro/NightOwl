"""Telegram webhook verification helpers."""

from __future__ import annotations

from hmac import compare_digest


def verify_telegram_secret(secret_header: str | None, expected_secret: str) -> bool:
    if not expected_secret:
        return True
    if not secret_header:
        return False
    return compare_digest(secret_header, expected_secret)
