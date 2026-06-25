#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/app}

cat <<'EOF' > "$APP_DIR/scheduler.py"
from __future__ import annotations

from typing import Any


def schedule_messages(polls: list[dict[str, Any]], candidates: list[int], messages: list[str], config: dict[str, Any]) -> dict[str, Any]:
    min_gap = int(config.get("minimumIntervalSec", 10) or 10)
    grace_window = int(config.get("graceWindowSec", 60) or 60)
    deliveries = []
    last_sent_at: int | None = None
    message_index = 0
    for tick in candidates:
        poll = next((item for item in polls if item["startsAtSec"] <= tick <= item["endsAtSec"] + grace_window), None)
        if not poll:
            continue
        if last_sent_at is not None and tick - last_sent_at < min_gap:
            continue
        deliveries.append({
            "pollId": poll["pollId"],
            "sentAtSec": tick,
            "message": messages[message_index % len(messages)],
        })
        last_sent_at = tick
        message_index += 1
    return {"deliveries": deliveries}
EOF

python3 "$APP_DIR/reconcile.py"
