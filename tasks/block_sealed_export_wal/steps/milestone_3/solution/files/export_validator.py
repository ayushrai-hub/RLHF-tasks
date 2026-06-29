"""Validate encrypted export files before rotation or persistence."""

from config import EXPORT_SCHEMA_VERSION, STAGING_FINGERPRINT_METADATA_KEY
from exceptions import ExportParseError

_REQUIRED_TOP_LEVEL = ("metadata", "public", "secrets")
_REQUIRED_METADATA = (
    "block_type",
    "key_version",
    "schema_version",
    "manifest_digest",
    "integrity_seal",
    STAGING_FINGERPRINT_METADATA_KEY,
)


def validate_export(export: dict) -> None:
    if not all(k in export for k in _REQUIRED_TOP_LEVEL):
        raise ExportParseError(
            f"Export is missing required top-level keys: {_REQUIRED_TOP_LEVEL}"
        )
    metadata = export["metadata"]
    if not all(k in metadata for k in _REQUIRED_METADATA):
        raise ExportParseError(
            f"Export metadata missing required keys: {_REQUIRED_METADATA}"
        )
    if metadata["schema_version"] != EXPORT_SCHEMA_VERSION:
        raise ExportParseError(
            f"Invalid schema_version {metadata['schema_version']!r}; "
            f"expected {EXPORT_SCHEMA_VERSION!r}"
        )
