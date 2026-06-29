"""Low-level field classification helpers used by block_parser."""

from config import ALWAYS_PUBLIC_FIELDS, PUBLIC_OVERRIDE_MARKERS, SECRET_KEYWORD_FRAGMENTS


def field_is_public(field_name: str) -> bool:
    """Return True when a dot-path should be treated as public."""
    lower = field_name.lower()
    if lower in ALWAYS_PUBLIC_FIELDS:
        return True
    return lower in PUBLIC_OVERRIDE_MARKERS


def field_is_secret(field_name: str) -> bool:
    """Return True when a dot-path should be treated as secret."""
    lower = field_name.lower()
    return lower in SECRET_KEYWORD_FRAGMENTS
