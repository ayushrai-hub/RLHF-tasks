#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/files/ledger_verify.c" /app/native/ledger_verify.c
make -C /app/native -B
cp "$SCRIPT_DIR/files/transparency_cli.rb" /app/service/transparency_cli.rb

python3 <<'PY'
import csv
import hashlib
import hmac
import json
import subprocess
import time
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path("/app/data/ledger_fixture.csv")
SEED = Path("/app/data/ceremony_seed.bin")


def normalize_memo(raw: str) -> str:
    text = " ".join(raw.strip().split())
    text = unicodedata.normalize("NFC", text)
    return text if text else "(empty)"


def normalize_amount(raw: str) -> str:
    return str(int(raw))


def normalize_posted_at(raw: str) -> str:
    if raw.endswith("Z"):
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonicalize(line: str) -> str:
    seq, tenant, amount, memo, posted_at, signer, _sig = next(csv.reader([line]))
    return "|".join(
        [
            seq,
            tenant,
            normalize_amount(amount),
            normalize_memo(memo),
            normalize_posted_at(posted_at),
            signer,
        ]
    )


rows = [line.strip() for line in LEDGER.read_text().splitlines() if line.strip()]

proc = subprocess.Popen(
    ["ruby", "/app/scripts/start_transparency_server.rb"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)


def wait_server():
    for _ in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:9292/ledger/root", timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise SystemExit("server failed to start")


def post_validate(csv_row: str) -> bool:
    req = urllib.request.Request(
        "http://127.0.0.1:9292/ledger/validate",
        data=json.dumps({"csv_row": csv_row}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["valid"]


wait_server()

with urllib.request.urlopen("http://127.0.0.1:9292/ledger/root") as resp:
    chain_root = json.loads(resp.read())["root"]

receipts = []
for row in rows:
    seq = row.split(",", 1)[0]
    with urllib.request.urlopen(f"http://127.0.0.1:9292/receipts/{seq}") as resp:
        body = json.loads(resp.read())
    receipts.append({"seq": seq, "receipt_id": body["receipt_id"]})

late_base = "9,archive-south,0,late bootstrap,2026-03-16T08:00:00Z,legacy-bootstrap"
late_sig = hmac.new(SEED.read_bytes(), canonicalize(f"{late_base},000000").encode(), hashlib.sha256).hexdigest()
forged_rows = [
    (rows[0].replace(",12500,", ",12501,", 1), False),
    (rows[0].rsplit(",", 1)[0] + ",deadbeef", False),
    (f"{late_base},{late_sig}", False),
    (rows[0], True),
]
forged_results = [{"csv_row": row, "valid": post_validate(row)} for row, _expected in forged_rows]

report = {
    "chain_root": chain_root,
    "receipts": receipts,
    "forged_results": forged_results,
}
Path("/app/output").mkdir(parents=True, exist_ok=True)
Path("/app/output/validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
proc.terminate()
proc.wait(timeout=5)
PY
