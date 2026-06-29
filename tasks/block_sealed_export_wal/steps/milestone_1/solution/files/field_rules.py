"""Low-level field classification helpers used by block_parser."""

from config import ALWAYS_PUBLIC_FIELDS, PUBLIC_OVERRIDE_MARKERS, SECRET_KEYWORD_FRAGMENTS


def field_is_public(field_name: str) -> bool:
    lower = field_name.lower()
    if lower in ALWAYS_PUBLIC_FIELDS:
        return True
    return any(marker in lower for marker in PUBLIC_OVERRIDE_MARKERS)


def field_is_secret(field_name: str) -> bool:
    lower = field_name.lower()
    return any(fragment in lower for fragment in SECRET_KEYWORD_FRAGMENTS)
