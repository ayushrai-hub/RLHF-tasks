#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 <<'PY'
import json
from pathlib import Path

notice = json.loads(Path("/app/data/key_rotation_notice.json").read_text())
out = {
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
        "/app/docs/api_overview.md",
    ],
}
Path("/app/output").mkdir(parents=True, exist_ok=True)
Path("/app/output/ceremony_rules.json").write_text(json.dumps(out, indent=2) + "\n")
PY
