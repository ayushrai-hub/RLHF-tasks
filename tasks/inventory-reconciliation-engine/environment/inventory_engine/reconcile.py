from __future__ import annotations

import hashlib
import json
from pathlib import Path

from inventory_engine.constants import GENERATED_FROM
from inventory_engine.emit import write_snapshot
from inventory_engine.engine import InventoryEngine
from inventory_engine.loader import load_events


def run_reconciliation(events_path: Path, output_path: Path) -> None:
    raw_events, line_count, malformed = load_events(events_path)
    engine = InventoryEngine()
    engine.process([{"payload": event.payload, "line_index": event.line_index} for event in raw_events])

    rejections = sorted(engine.rejections, key=lambda row: (row["priority_rank"], row["event_id"]))
    snapshot = {
        "generated_from": GENERATED_FROM,
        "event_line_count": line_count,
        "parsed_count": len(raw_events),
        "malformed_line_count": malformed,
        "processed_count": len(raw_events) - engine.skipped_idempotent_count,
        "applied_count": engine.applied_count,
        "rejected_count": engine.rejected_count,
        "skipped_idempotent_count": engine.skipped_idempotent_count,
        "rejections": rejections,
        "inventory": engine.inventory_rows(),
    }
    body = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    snapshot["snapshot_digest"] = hashlib.sha256(body).hexdigest()
    write_snapshot(output_path, snapshot)
