"""Write-ahead log persistence helpers for key rotation."""

import hashlib
import json


def wal_path(export_path: str) -> str:
    return export_path + ".wal"


def load_wal(wal_path: str) -> dict:
    try:
        with open(wal_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"entries": []}


def save_wal(wal_path: str, wal: dict) -> None:
    with open(wal_path, "w") as f:
        json.dump(wal, f, indent=2)


def build_pending_entry(export_path: str, old_key: bytes, new_key: bytes) -> dict:
    return {
        "export_path": export_path,
        "old_key_hash": hashlib.sha256(old_key).hexdigest(),
        "new_key_hash": hashlib.sha256(new_key).hexdigest(),
        "status": "pending",
    }
