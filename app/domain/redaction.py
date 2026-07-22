from __future__ import annotations

import re

from pydantic import BaseModel


class RedactionResult(BaseModel):
    text: str
    counts: dict[str, int]


class Redactor:
    _PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
        ("id_card", re.compile(r"(?<!\d)\d{17}[\dXx](?![\dXx])"), "[REDACTED_ID_CARD]"),
        ("phone", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[REDACTED_PHONE]"),
        (
            "email",
            re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9_.-])"),
            "[REDACTED_EMAIL]",
        ),
    )

    def redact(self, text: str) -> RedactionResult:
        redacted = text
        counts: dict[str, int] = {}
        for category, pattern, replacement in self._PATTERNS:
            redacted, count = pattern.subn(replacement, redacted)
            counts[category] = count
        return RedactionResult(text=redacted, counts=counts)
