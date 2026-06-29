"""String normalization helpers for supplier feeds."""

from __future__ import annotations


def normalize_token(raw: str) -> str:
    return raw.strip().upper()
