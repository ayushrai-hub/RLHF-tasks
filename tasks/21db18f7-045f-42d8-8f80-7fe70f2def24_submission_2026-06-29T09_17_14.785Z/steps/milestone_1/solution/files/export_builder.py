"""Build encrypted export JSON from a staged block artifact."""

import json

from aes_crypto import encrypt_secrets
from block_parser import extract_public_fields, extract_secret_fields
from export_metadata import build_export_metadata
from integrity_seal import compute_integrity_seal
from replay_journal import initialize_journal
from secret_manifest import compute_manifest_digest
from staging_lineage import read_fingerprint_sidecar


def build_encrypted_export(staging_path: str, key: bytes, output_path: str) -> int:
    with open(staging_path) as f:
        staging = json.load(f)

    block_type = staging["block_type"]
    fields = staging["fields"]
    secrets = extract_secret_fields(fields)
    public = extract_public_fields(fields)
    key_version = 1
    manifest_digest = compute_manifest_digest(sorted(secrets.keys()))
    staging_fingerprint = read_fingerprint_sidecar(staging_path)
    if not staging_fingerprint:
        raise ValueError(f"Missing staging fingerprint sidecar for {staging_path!r}")

    export = {
        "metadata": build_export_metadata(
            block_type,
            key_version=key_version,
            manifest_digest=manifest_digest,
            staging_fingerprint=staging_fingerprint,
        ),
        "public": public,
        "secrets": encrypt_secrets(secrets, key, block_type, key_version),
    }
    export["metadata"]["integrity_seal"] = compute_integrity_seal(export, key)

    with open(output_path, "w") as f:
        json.dump(export, f, indent=2)

    initialize_journal(output_path, key_version)

    return len(secrets)
