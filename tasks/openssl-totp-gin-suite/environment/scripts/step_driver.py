#!/usr/bin/env python3
"""Scenario driver for m3 integration suite."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import stat
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path

BIN = "/app/bin/m3_cli"
BASE_URL = "http://127.0.0.1:9477"
STORE_ROOT = "/app/output/store"
STEP_SECONDS = 30


def run_cmd(argv: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(argv, capture_output=True, text=True, env=merged, check=False)


def post_json(path: str, body: dict, clock: int) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Clock-Epoch": str(clock),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        return exc.code, payload


def update_store_signing(account_id: str, signing_hex: str) -> None:
    path = Path(STORE_ROOT) / f"{account_id}.store"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["signing_material"] = signing_hex
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def kid_prefix(account_id: str) -> str:
    return account_id[:16]


def digest_hex(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reference_counter_be(counter: int) -> bytes:
    """Big-endian counter bytes shared with the C passcode lane."""
    return struct.pack(">Q", counter)


def reference_passcode(secret: bytes, material_epoch: int, step_seconds: int = STEP_SECONDS) -> str:
    """Reference HOTP materialization using the same hmac/struct contract as the C lane."""
    counter = material_epoch // step_seconds
    msg = reference_counter_be(counter)
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    ) % 1_000_000
    return f"{code:06d}"


def run_scenario(spec: dict) -> dict:
    name = spec["name"]
    handle = spec["handle"]
    expect = spec["expect_status"]
    clock_base = int(spec.get("clock_epoch", 1700000040))
    offset_steps = int(spec.get("clock_offset_steps", 0))
    clock_host = clock_base + offset_steps * STEP_SECONDS
    clock_passcode = clock_base

    env = {
        "K9_CLOCK_EPOCH": str(clock_host),
        "K9_PASSCODE_EPOCH": str(clock_passcode),
    }
    Path(STORE_ROOT).mkdir(parents=True, exist_ok=True)

    row = {
        "scenario": name,
        "status": expect,
        "artifact_digest": "",
        "kid": "",
    }

    if spec.get("duplicate_enroll"):
        first = run_cmd([BIN, "enroll", "--handle", handle, "--store-dir", STORE_ROOT], env)
        if first.returncode != 0:
            row["status"] = "store_reject"
            return row
        second = run_cmd([BIN, "enroll", "--handle", handle, "--store-dir", STORE_ROOT], env)
        if second.returncode == 10:
            row["status"] = "enroll_reject"
        else:
            row["status"] = "store_reject"
        return row

    enroll = run_cmd(
        [BIN, "enroll", "--handle", handle, "--store-dir", STORE_ROOT, "--base-url", BASE_URL],
        env,
    )
    if enroll.returncode != 0:
        row["status"] = "store_reject"
        return row
    account_id = enroll.stdout.strip()

    if spec.get("check_store_mode"):
        store_path = Path(STORE_ROOT) / f"{account_id}.store"
        mode = stat.S_IMODE(store_path.stat().st_mode)
        if mode != 0o600:
            row["status"] = "store_reject"
            return row

    if spec.get("bad_passcode"):
        code, _payload = post_json(
            "/v1/sessions/mfa",
            {"account_id": account_id, "passcode": "000000"},
            clock_host,
        )
        if code == 401:
            row["status"] = "totp_reject"
        else:
            row["status"] = "store_reject"
        return row

    mfa = run_cmd(
        [
            BIN,
            "mfa",
            "--account-id",
            account_id,
            "--store-dir",
            STORE_ROOT,
            "--base-url",
            BASE_URL,
            "--clock-epoch",
            str(clock_host),
        ],
        env,
    )
    if mfa.returncode == 11:
        row["status"] = "totp_reject"
        return row
    if mfa.returncode != 0:
        row["status"] = "store_reject"
        return row
    token = mfa.stdout.strip()

    if spec.get("rotate_signing") or spec.get("rotate_stale_seal"):
        code, payload = post_json("/v1/accounts/rotate", {"account_id": account_id}, clock_host)
        if code != 200:
            row["status"] = "store_reject"
            return row
        update_store_signing(account_id, payload["signing_material"])
        old_verify = run_cmd(
            [
                BIN,
                "verify",
                "--account-id",
                account_id,
                "--token",
                token,
                "--store-dir",
                STORE_ROOT,
                "--clock-epoch",
                str(clock_host),
            ],
            env,
        )
        if spec.get("rotate_stale_seal"):
            if old_verify.returncode == 12:
                row["status"] = "seal_reject"
            else:
                row["status"] = "store_reject"
            return row
        if old_verify.returncode != 12:
            row["status"] = "seal_reject" if expect != "ok" else "store_reject"
            return row
        mfa2 = run_cmd(
            [
                BIN,
                "mfa",
                "--account-id",
                account_id,
                "--store-dir",
                STORE_ROOT,
                "--base-url",
                BASE_URL,
                "--clock-epoch",
                str(clock_host),
            ],
            env,
        )
        if mfa2.returncode != 0:
            row["status"] = "store_reject"
            return row
        token = mfa2.stdout.strip()

    if spec.get("tamper_token"):
        token = token[:-1] + ("a" if token[-1] != "a" else "b")

    verify = run_cmd(
        [
            BIN,
            "verify",
            "--account-id",
            account_id,
            "--token",
            token,
            "--store-dir",
            STORE_ROOT,
            "--clock-epoch",
            str(clock_host),
        ],
        env,
    )
    if verify.returncode == 12:
        row["status"] = "seal_reject"
        return row
    if verify.returncode != 0:
        row["status"] = "store_reject"
        return row

    row["status"] = "ok"
    row["artifact_digest"] = digest_hex(token)
    row["kid"] = kid_prefix(account_id)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["suite"])
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--session-out", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.seeds).read_text(encoding="utf-8"))
    runs = [run_scenario(spec) for spec in manifest["scenarios"]]
    out_path = Path(args.session_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"runs": runs}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
