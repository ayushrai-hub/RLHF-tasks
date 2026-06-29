"""Export metadata assembly for the encrypt pipeline."""

from config import EXPORT_SCHEMA_VERSION, STAGING_FINGERPRINT_METADATA_KEY


def build_export_metadata(
    block_type: str,
    key_version: int = 1,
    manifest_digest: str = "",
    staging_fingerprint: str = "",
) -> dict:
    return {
        "block_type": block_type,
        "key_version": key_version,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "manifest_digest": manifest_digest,
        STAGING_FINGERPRINT_METADATA_KEY: staging_fingerprint,
    }
