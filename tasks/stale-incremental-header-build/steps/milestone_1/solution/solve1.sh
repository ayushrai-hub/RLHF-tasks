#!/bin/bash
set -euo pipefail

/app/environment/bin/trace_host /app/environment/data/run_plan.json

python3 <<'PY'
import json
import struct
import subprocess
import time
from pathlib import Path

TRACE = Path("/app/output/rebuild_trace.json")
HDR = Path("/app/environment/var/gen/version_slot.h")
PLAN = Path("/app/environment/data/run_plan.json")
DELTA = Path("/app/output/quick_full_delta.json")
RING_AUDIT = Path("/app/output/slot_ring_audit.json")
JOURNAL = Path("/app/output/journal_surfaces.json")
RING_BIN = Path("/app/environment/var/slots/gen_ring.bin")
COMPILE_LOG = Path("/app/environment/var/stats/compile.log")


def rows_for(doc, plan_id):
    return [r for r in doc["rows"] if r["plan_id"] == plan_id]


def live_hdr_gen():
    st = HDR.stat()
    return int((int(st.st_mtime) ^ st.st_size) & 0xFFFFFFFF)


def read_ring():
    if not RING_BIN.is_file():
        return []
    data = RING_BIN.read_bytes()
    if len(data) < 4:
        return []
    n = struct.unpack_from("<i", data, 0)[0]
    live = live_hdr_gen()
    entries = []
    off = 4
    for _ in range(n):
        blob = data[off : off + 256].split(b"\0", 1)[0].decode()
        off += 256
        gen = struct.unpack_from("<I", data, off)[0]
        off += 4
        entries.append(
            {
                "blob_path": blob,
                "stored_gen": gen,
                "live_gen": live,
                "gen_aligned": gen == live,
            }
        )
    return entries


doc = json.loads(TRACE.read_text(encoding="utf-8"))
plans = []
for plan in json.loads(PLAN.read_text(encoding="utf-8"))["plans"]:
    pid = plan["plan_id"]
    bad = [
        r["target"]
        for r in rows_for(doc, pid)
        if r["fast_digest_hex"] != r["pristine_digest_hex"]
    ]
    if bad:
        plans.append({"plan_id": pid, "targets": bad})
DELTA.write_text(
    json.dumps(
        {"mismatch_count": len(plans), "plans_with_mismatch": plans},
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

COMPILE_LOG.unlink(missing_ok=True)
subprocess.run(["/app/environment/bin/bld_host", "--pristine", "cap_r1"], check=True)
time.sleep(1)
subprocess.run(["/app/environment/bin/bld_host", "cap_r2"], check=True)

entries = read_ring()
RING_AUDIT.write_text(
    json.dumps(
        {
            "entries": entries,
            "any_stale_gen": any(not e["gen_aligned"] for e in entries),
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

saw_skip = False
if COMPILE_LOG.is_file():
    for line in COMPILE_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] == "skip" and "app_v1/main.c" in parts[1]:
            saw_skip = True
JOURNAL.write_text(
    json.dumps(
        {
            "surfaces": [
                {
                    "source_rel": "app_v1/main.c",
                    "last_action_skip": saw_skip,
                }
            ]
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
