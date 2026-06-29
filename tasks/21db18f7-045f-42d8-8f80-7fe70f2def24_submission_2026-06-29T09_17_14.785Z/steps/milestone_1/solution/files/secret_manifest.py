"""Canonical digest of encrypted secret field paths."""

import hashlib


def compute_manifest_digest(secret_paths: list[str]) -> str:
    canonical = "\n".join(sorted(secret_paths))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
