"""Verifier tests for the Rust pinned chunk streaming task."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

APP_DIR = Path("/app")
STREAM_BIN = APP_DIR / "bin" / "streamd"
STREAM_CONFIG = APP_DIR / "config" / "stream.json"
TRACES_DIR = APP_DIR / "data" / "traces"
REPLAY_OUT = APP_DIR / "data" / "replay_out"
CATALOG_PATH = REPLAY_OUT / "catalog.json"
REPLAY_SCRIPT = APP_DIR / "scripts" / "replay-chunks.sh"
SOAK_SCRIPT = APP_DIR / "scripts" / "soak-chunks.sh"
CHUNK_SIZE = 4

CARGO_ENV = {
    **os.environ,
    "PATH": "/usr/local/cargo/bin:/usr/bin:" + os.environ.get("PATH", ""),
}


def fnv8_hex(data: bytes) -> str:
    """FNV-1a 64 low 32 bits as eight lowercase hex digits."""
    h = 0xcbf29ce484222325
    for byte in data:
        h ^= byte
        h = (h * 0x100000001b3) & 0xffffffffffffffff
    return f"{h & 0xffffffff:08x}"


def expected_digest_lines(payload: bytes, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Build contract-correct digest lines for a payload."""
    lines: list[str] = []
    offset = 0
    idx = 0
    while idx + chunk_size <= len(payload):
        chunk = payload[idx : idx + chunk_size]
        lines.append(f"{offset}:{fnv8_hex(chunk)}")
        offset += chunk_size
        idx += chunk_size
    if idx < len(payload):
        lines.append(f"{offset}:{fnv8_hex(payload[idx:])}")
    return lines


def _all_trace_relpaths() -> list[str]:
    """Return relative paths for every trace fixture under /app/data/traces/."""
    return sorted(
        p.relative_to(TRACES_DIR).as_posix()
        for p in TRACES_DIR.rglob("*.trace")
    )


def _expected_catalog_from_disk() -> dict[str, list[str]]:
    """Derive expected digest lines from on-disk trace payloads."""
    return {
        rel: expected_digest_lines((TRACES_DIR / rel).read_bytes())
        for rel in _all_trace_relpaths()
    }


def _run(cmd: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    """Run a command in /app and return the completed process."""
    return subprocess.run(
        cmd,
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=CARGO_ENV,
    )


def _stop_stray_streamd() -> None:
    subprocess.run(
        ["pkill", "-9", "-x", "streamd"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="module")
def _release_build() -> None:
    """Install the release binary once for streamd CLI checks."""
    _stop_stray_streamd()
    result = _run(["make", "release"], timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture(scope="module")
def _catalog(_release_build: None) -> dict[str, list[str]]:
    """Build replay_out/catalog.json once for catalog assertions."""
    if REPLAY_OUT.exists():
        for child in REPLAY_OUT.iterdir():
            if child.is_file():
                child.unlink()
    result = _run(["bash", str(REPLAY_SCRIPT)], timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert CATALOG_PATH.is_file()
    return json.loads(CATALOG_PATH.read_text())


def test_chunk_replay_matches_contract(
    _catalog: dict[str, list[str]],
    _release_build: None,
) -> None:
    """Verify export config, build, probe/replay alignment, catalog, and soak stability."""
    cfg = json.loads(STREAM_CONFIG.read_text())
    assert cfg.get("chunk_size") == 4
    assert cfg.get("digest_width") == 8
    rels = _all_trace_relpaths()
    assert len(rels) >= 8
    assert any(not rel.startswith("qa/") for rel in rels)
    assert sum(1 for rel in rels if rel.startswith("qa/")) >= 5

    result = _run(["cargo", "test", "--workspace", "--locked"], timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    assert STREAM_BIN.exists() and os.access(STREAM_BIN, os.X_OK)

    for rel in rels:
        path = TRACES_DIR / rel
        replay = _run([str(STREAM_BIN), "replay-one", str(path)], timeout=60)
        assert replay.returncode == 0, f"{rel}: {replay.stdout}{replay.stderr}"
        digest_offsets = [
            int(line.split(":")[0])
            for line in replay.stdout.splitlines()
            if line.strip()
        ]
        probe = _run([str(STREAM_BIN), "probe-one", str(path)], timeout=60)
        assert probe.returncode == 0, f"{rel}: {probe.stdout}{probe.stderr}"
        probe_offsets = [
            int(part) for part in probe.stdout.strip().split(",") if part
        ]
        assert probe_offsets == digest_offsets, rel

    assert sorted(_catalog.keys()) == sorted(rels)
    expected = _expected_catalog_from_disk()
    for rel, want in expected.items():
        assert _catalog[rel] == want, rel
        assert expected_digest_lines((TRACES_DIR / rel).read_bytes()) == want

    soak = _run(["bash", str(SOAK_SCRIPT)], timeout=180)
    assert soak.returncode == 0, soak.stdout + soak.stderr
