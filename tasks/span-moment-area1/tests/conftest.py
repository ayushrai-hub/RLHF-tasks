"""Session fixtures for beam envelope verifier."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path("/app")
APP = ROOT / "environment"
BIN = APP / "bin" / "beam-envelope"


@pytest.fixture(autouse=True)
def isolate_disk_cache() -> None:
    """Each test starts without a warm on-disk envelope cache."""
    cache = Path("/tmp/beam_envelope_cache.tsv")
    if cache.exists():
        cache.unlink()


@pytest.fixture(scope="session", autouse=True)
def clear_disk_cache() -> None:
    """Start each verifier session without a warm cross-run envelope cache."""
    cache = Path("/tmp/beam_envelope_cache.tsv")
    if cache.exists():
        cache.unlink()


@pytest.fixture(scope="session")
def built_bin() -> None:
    """Build beam-envelope from current application sources."""
    subprocess.run(
        ["bash", "/app/environment/scripts/build.sh"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert BIN.is_file()
