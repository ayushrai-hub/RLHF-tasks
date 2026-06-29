"""Export lineage checks before rotation."""

from config import STAGING_FINGERPRINT_METADATA_KEY
from exceptions import ExportParseError
from secret_manifest import compute_manifest_digest


def assert_export_lineage(export: dict) -> None:
    metadata = export.get("metadata")
    if not isinstance(metadata, dict):
        raise ExportParseError("Export metadata must be a mapping")
    fingerprint = metadata.get(STAGING_FINGERPRINT_METADATA_KEY)
    if not fingerprint:
        raise ExportParseError(
            f"Export metadata missing required key: {STAGING_FINGERPRINT_METADATA_KEY!r}"
        )
    manifest = metadata.get("manifest_digest")
    if not manifest:
        raise ExportParseError("Export metadata missing manifest_digest")
    secret_keys = sorted(export.get("secrets", {}).keys())
    expected_manifest = compute_manifest_digest(secret_keys)
    if manifest != expected_manifest:
        raise ExportParseError("manifest_digest does not match encrypted secret paths")
