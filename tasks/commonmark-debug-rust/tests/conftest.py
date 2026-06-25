"""Build the Rust crate before any test runs.

The Snorkel-shape `test.sh` invokes pytest directly without a separate build
step, so this session-scoped autouse fixture is responsible for compiling the
agent's edits before any test consumes the binary.
"""
import os
import subprocess

import pytest

TASK = "/app/task_file"


@pytest.fixture(scope="session", autouse=True)
def _build_crate():
    env = os.environ.copy()
    env["PATH"] = "/usr/local/cargo/bin:" + env.get("PATH", "")
    env["CARGO_NET_OFFLINE"] = "true"
    proc = subprocess.run(
        ["cargo", "build", "--release", "--offline"],
        cwd=TASK,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.exit(
            f"cargo build --release failed (rc={proc.returncode}):\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr ---\n{proc.stderr}",
            returncode=1,
        )
