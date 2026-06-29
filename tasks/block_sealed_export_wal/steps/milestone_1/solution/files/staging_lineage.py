"""Canonical staging artifact fingerprinting for the encrypt pipeline."""

import hashlib
import json
from pathlib import Path

from config import STAGING_FINGERPRINT_SUFFIX


def canonical_staging_bytes(staging: dict) -> bytes:
    return json.dumps(staging, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_staging_fingerprint(staging: dict) -> str:
    return hashlib.sha256(canonical_staging_bytes(staging)).hexdigest()


def fingerprint_sidecar_path(staging_path: str) -> str:
    return staging_path + STAGING_FINGERPRINT_SUFFIX


def write_fingerprint_sidecar(staging_path: str, staging: dict) -> None:
    digest = compute_staging_fingerprint(staging)
    Path(fingerprint_sidecar_path(staging_path)).write_text(digest + "\n", encoding="utf-8")


def read_fingerprint_sidecar(staging_path: str) -> str:
    path = Path(fingerprint_sidecar_path(staging_path))
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()
