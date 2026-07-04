#!/usr/bin/env python3
"""Independent expected values for ledger transparency verification."""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

APP = Path("/app")
LEDGER = APP / "data/ledger_fixture.csv"
SEED = APP / "data/ceremony_seed.bin"
NOTICE = APP / "data/key_rotation_notice.json"
ADDENDUM = APP / "docs/ceremony_minutes_addendum.md"

CHAIN_ROOT = "40efdcdcd6d3b93d1524760eb8363d52003f4f71ca5b9990e65731f59efd9d73"


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


def parse_row(line: str) -> list[str]:
    return next(csv.reader([line]))


def canonicalize_csv_row(line: str) -> str:
    seq, tenant, amount, memo, posted_at, signer, _sig = parse_row(line)
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


def load_fixture_rows() -> list[list[str]]:
    return [parse_row(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def expected_ceremony_rules() -> dict:
    notice = json.loads(NOTICE.read_text())
    return {
        "signing": {
            "separator": "|",
            "fields": ["seq", "tenant", "amount_cents", "memo", "posted_at", "signer"],
            "memo_empty_literal": "(empty)",
            "memo_normalization": ["trim", "collapse_whitespace", "nfc"],
            "amount_format": "decimal_integer_no_leading_zeros",
            "posted_at_format": "utc_iso8601_z",
        },
        "keys": {
            "primary_key_id": notice["primary_key_id"],
            "primary_effective": notice["primary_effective"],
            "legacy_key_id": notice["legacy_key_id"],
            "legacy_valid_before": notice["legacy_valid_before"],
            "primary_public_key_path": "/app/data/keys/ledger-key-v2.pub.pem",
            "legacy_public_key_path": "/app/data/keys/ledger-key-v1.pub.pem",
        },
        "bootstrap": {
            "signer": notice["bootstrap_signer"],
            "algorithm": "hmac-sha256",
            "seed_path": notice["bootstrap_seed_path"],
            "valid_until": notice["bootstrap_valid_until"],
        },
        "chain": {
            "genesis": "ledger-genesis-v3",
            "row_digest": "sha256(canonical|signature_hex)",
            "link": "sha256(prev_digest|row_digest)",
        },
        "receipts": {
            "prefix": "rcpt-HBR-",
            "seq_width": 4,
        },
        "authoritative_docs": [
            "/app/docs/ceremony_minutes_addendum.md",
            "/app/data/key_rotation_notice.json",
        ],
    }


def expected_canonical_samples() -> dict[str, str]:
    rows = load_fixture_rows()
    return {row[0]: canonicalize_csv_row(",".join(row)) for row in rows}


def compute_chain_root() -> str:
    state = hashlib.sha256(b"ledger-genesis-v3").hexdigest()
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        row = parse_row(line)
        canonical = canonicalize_csv_row(line)
        row_digest = hashlib.sha256(f"{canonical}|{row[6]}".encode()).hexdigest()
        state = hashlib.sha256(f"{state}|{row_digest}".encode()).hexdigest()
    return state


def receipt_id_for(seq: str) -> str:
    return f"rcpt-HBR-{seq.zfill(4)}"


def forged_rows() -> list[tuple[str, bool]]:
    rows = load_fixture_rows()
    valid_line = ",".join(rows[0])
    tampered_amount = valid_line.replace(",12500,", ",12501,", 1)
    wrong_sig = valid_line.rsplit(",", 1)[0] + ",deadbeef"
    late_base = "9,archive-south,0,late bootstrap,2026-03-16T08:00:00Z,legacy-bootstrap"
    late_canon = canonicalize_csv_row(f"{late_base},000000")
    late_sig = hmac.new(SEED.read_bytes(), late_canon.encode(), hashlib.sha256).hexdigest()
    late_bootstrap = f"{late_base},{late_sig}"
    return [
        (tampered_amount, False),
        (wrong_sig, False),
        (late_bootstrap, False),
        (valid_line, True),
    ]
