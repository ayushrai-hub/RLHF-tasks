"""Rotation replay journal sidecar for monotonic commit sequencing."""

import json

from config import JOURNAL_SUFFIX


def journal_path(export_path: str) -> str:
    return export_path + JOURNAL_SUFFIX


def load_journal(export_path: str) -> dict:
    path = journal_path(export_path)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"rotation_seq": 0, "last_key_version": 0}


def initialize_journal(export_path: str, key_version: int) -> None:
    journal = {"rotation_seq": 0, "last_key_version": key_version}
    with open(journal_path(export_path), "w") as f:
        json.dump(journal, f, indent=2)


def record_rotation_commit(export_path: str, key_version: int) -> None:
    journal = load_journal(export_path)
    journal["rotation_seq"] = int(journal.get("rotation_seq", 0)) + 1
    journal["last_key_version"] = key_version
    with open(journal_path(export_path), "w") as f:
        json.dump(journal, f, indent=2)
