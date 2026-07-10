#!/usr/bin/env python3
"""Driver for the interval tree calendar service."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8080"


def _post(path, body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=10)
    return r.status_code, r.json() if r.content else {}


def _get(path):
    r = requests.get(f"{BASE}{path}", timeout=10)
    return r.status_code, r.json() if r.content else {}


def _delete(path):
    r = requests.delete(f"{BASE}{path}", timeout=10)
    return r.status_code, r.json() if r.content else {}


def run(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    ops_log = []

    events = [
        {"name": "meeting_a", "start_ms": 1000, "end_ms": 3000, "metadata": {"room": "A"}},
        {"name": "meeting_b", "start_ms": 2000, "end_ms": 4000, "metadata": {"room": "B"}},
        {"name": "meeting_c", "start_ms": 500,  "end_ms": 1500, "metadata": {"room": "C"}},
        {"name": "all_day",   "start_ms": 0,    "end_ms": 86400000, "metadata": {}},
        {"name": "future",    "start_ms": 9000, "end_ms": 10000, "metadata": {}},
    ]
    for ev in events:
        sc, body = _post("/events", ev)
        ops_log.append({"op": "add_event", "name": ev["name"], "status": sc, "response": body})

    sc, stab = _get("/stab?at=1500")
    ops_log.append({"op": "stab", "at": 1500, "status": sc})
    (outdir / "stab_result.json").write_text(json.dumps(stab, indent=2))

    sc, overlap = _get("/overlap?start=1000&end=2000")
    ops_log.append({"op": "overlap", "status": sc})
    (outdir / "overlap_result.json").write_text(json.dumps(overlap, indent=2))

    sc, stats = _get("/stats")
    ops_log.append({"op": "stats", "status": sc})
    (outdir / "stats_snapshot.json").write_text(json.dumps(stats, indent=2))

    sc, del_body = _delete("/events/1")
    ops_log.append({"op": "delete", "id": 1, "status": sc})

    (outdir / "ops_log.ndjson").open("w").writelines(
        json.dumps(e) + "\n" for e in ops_log
    )
    print(f"driver: {len(ops_log)} operations")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", type=Path)
    args = ap.parse_args()
    return run(args.outdir)


if __name__ == "__main__":
    sys.exit(main())
