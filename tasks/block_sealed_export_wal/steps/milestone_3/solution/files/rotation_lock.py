"""Advisory rotation lock with stale recovery."""

import json
import os
import time

from config import ROTATION_LOCK_STALE_SEC, ROTATION_LOCK_SUFFIX


def lock_path(export_path: str) -> str:
    return export_path + ROTATION_LOCK_SUFFIX


def acquire_rotation_lock(export_path: str) -> bool:
    path = lock_path(export_path)
    if os.path.exists(path):
        return False
    with open(path, "w") as f:
        json.dump({"pid": os.getpid(), "started_at": time.time()}, f)
    return True


def release_rotation_lock(export_path: str) -> None:
    path = lock_path(export_path)
    if os.path.exists(path):
        os.remove(path)


def recover_stale_rotation_lock(export_path: str) -> None:
    path = lock_path(export_path)
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            data = json.load(f)
        started = float(data.get("started_at", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        os.remove(path)
        return
    if time.time() - started > ROTATION_LOCK_STALE_SEC:
        os.remove(path)
