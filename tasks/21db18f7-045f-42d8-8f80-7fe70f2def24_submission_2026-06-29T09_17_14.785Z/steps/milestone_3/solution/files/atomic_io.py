"""Atomic filesystem helpers for rotation."""

import json
import os


def atomic_write_json(path: str, data: dict) -> None:
    tmp_out = path + ".tmp"
    try:
        with open(tmp_out, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_out, path)
    finally:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
