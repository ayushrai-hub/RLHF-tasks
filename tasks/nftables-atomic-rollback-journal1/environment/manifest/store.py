"""Manifest epoch store stub."""

import hashlib
import json
import tomllib


def digest_payload(payload: dict) -> str:
    """Return a lowercase hex digest for compact JSON payloads."""
    data = json.dumps(payload, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def load_profile_toml(path: str) -> dict:
    with open(path, "rb") as handle:
        return tomllib.load(handle)
