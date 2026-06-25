#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/app}

cat <<'EOF' > "$APP_DIR/referral_processor.py"
from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_referral_events(referrers: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = deepcopy(referrers)
    by_code = {row.get("referralData", {}).get("referralCode", "").strip(): row for row in rows}
    for event in events:
        code = str(event.get("referralCode", "") or "").strip()
        if not code or code not in by_code:
            continue
        referred_user_id = str(event.get("referredUserId", "") or "").strip()
        if not referred_user_id:
            continue
        row = by_code[code]
        if referred_user_id == str(row.get("userId", "") or "").strip():
            continue
        if event.get("eventType") not in {"signup", "signin"}:
            continue
        data = row.setdefault("referralData", {})
        referred_users = data.setdefault("referredUsers", [])
        if referred_user_id in referred_users:
            continue
        referred_users.append(referred_user_id)
        data["referralCount"] = int(data.get("referralCount", 0) or 0) + 1
    return rows


def build_report(referrers: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for row in sorted(apply_referral_events(referrers, events), key=lambda item: item["userId"]):
        rows.append({
            "userId": row["userId"],
            "referralCount": row["referralData"].get("referralCount", 0),
            "referredUsers": sorted(row["referralData"].get("referredUsers", [])),
        })
    return {"records": rows}
EOF

python3 "$APP_DIR/reconcile.py"
