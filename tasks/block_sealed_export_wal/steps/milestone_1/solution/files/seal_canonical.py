"""Canonical byte serialization for integrity seal payloads."""

import json


def canonical_seal_bytes(export: dict) -> bytes:
    metadata = {k: v for k, v in export["metadata"].items() if k != "integrity_seal"}
    body = {
        "metadata": metadata,
        "public": export["public"],
        "manifest_digest": metadata["manifest_digest"],
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
