"""Shared subprocess and HTTP helpers for ABAC framed-wire verifier tests."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from gen_abwf_fixtures import fixture_root

INGEST_BIN = Path("/app/bin/abac-ingest")
EXPORT_BIN = Path("/app/bin/abac-export")
SERVE_BIN = Path("/app/bin/abac-serve")
PUBLIC_SAMPLE = Path("/app/data/sample-policy.abwf")
PROFILE_PATH = Path("/app/config/abac-policy-profile.json")

ABAC_GOOD_BATCH = "good_correct_crc.abwf"
ABAC_BAD_CRC_BATCH = "bad_crc.abwf"
ABAC_OOO_BATCH = "out_of_order_eval_seq.abwf"
ABAC_MISSING_ATTR_BATCH = "missing_clearance.abwf"
ABAC_DUP_SEQ_BATCH = "duplicate_eval_seq.abwf"
ABAC_DENY_TRAP_BATCH = "deny_only_after_permit.abwf"

ABAC_ENV = {
    "PATH": "/app/bin:/opt/scala3/bin:" + os.environ.get("PATH", ""),
}


def abac_wire_batch(name: str) -> Path:
    return fixture_root() / name


def abac_cli_ingest(db: Path, batch: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(INGEST_BIN), "--db", str(db), "--batch", str(batch)],
        capture_output=True,
        text=True,
        check=False,
        env=ABAC_ENV,
        timeout=30,
    )


def abac_cli_export(db: Path, out: Path, tenant: str = "TEN") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(EXPORT_BIN), "--db", str(db), "--tenant", tenant, "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
        env=ABAC_ENV,
        timeout=30,
    )


def abac_parse_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@contextlib.contextmanager
def start_abac_http(db: Path, port: int):
    proc = subprocess.Popen(
        [str(SERVE_BIN), "--db", str(db), "--listen", f"127.0.0.1:{port}"],
        env=ABAC_ENV,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("abac-serve failed to start")
    try:
        yield port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def http_get_json(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"error": body}
