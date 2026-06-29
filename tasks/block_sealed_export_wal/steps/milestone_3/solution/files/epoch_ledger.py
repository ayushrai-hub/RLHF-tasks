"""Epoch ledger sidecar tracking committed rotation state."""

import json
import time

from config import EPOCH_SUFFIX


def epoch_path(export_path: str) -> str:
    return export_path + EPOCH_SUFFIX


def load_epoch(export_path: str) -> dict:
    path = epoch_path(export_path)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"key_version": 0, "manifest_digest": "", "committed_at": 0}


def commit_epoch(export_path: str, key_version: int, manifest_digest: str) -> None:
    ledger = {
        "key_version": key_version,
        "manifest_digest": manifest_digest,
        "committed_at": int(time.time()),
    }
    with open(epoch_path(export_path), "w") as f:
        json.dump(ledger, f, indent=2)
