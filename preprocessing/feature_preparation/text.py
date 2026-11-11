"""Lightweight bug report text cleanup before vectorization."""

from __future__ import annotations

import html
import re


_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def clean_report_text(value: object) -> str:
    """Decode HTML entities, remove markup, and normalize whitespace."""
    text = html.unescape(str(value or ""))
    text = _TAG.sub(" ", text)
    return _SPACE.sub(" ", text).strip()
