"""Session-scoped lifecycle: stop, reset state, start the service."""
import os
import subprocess

import pytest


def _maybe_run(path: str) -> int:
    if not os.path.exists(path):
        return 0
    return subprocess.run(["bash", path], capture_output=True).returncode


@pytest.fixture(scope="session", autouse=True)
def live_service():
    """Reset and restart the service before each milestone's tests."""
    _maybe_run("/app/scripts/stop_service.sh")
    for d in ("/app/data", "/app/output", "/app/logs"):
        subprocess.run(["rm", "-rf", d], check=False)
        os.makedirs(d, exist_ok=True)
    for s in ("/app/scripts/start_service.sh",):
        if os.path.exists(s):
            r = subprocess.run(["bash", s], capture_output=True, text=True)
            if r.returncode != 0:
                pytest.fail(f"failed to start service via {s}: {r.stderr}", pytrace=False)
            break
    for d in ("/app/scripts/run_driver.sh",):
        if os.path.exists(d):
            subprocess.run(["bash", d, "/app/output"], capture_output=True, check=False)
    yield
    for s in ("/app/scripts/stop_service.sh",):
        if os.path.exists(s):
            subprocess.run(["bash", s], capture_output=True, check=False)
