"""Shared helpers for milestone 1 verifier tests."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
from pathlib import Path

TRACE_OUT = Path("/app/output/rebuild_trace.json")
PLAN = Path("/app/environment/data/run_plan.json")
GEN_HDR = Path("/app/environment/var/gen/version_slot.h")
MAIN_OBJ = Path("/app/environment/var/objs/app_v1/main.o")
ENV = Path("/app/environment")
DELTA = Path("/app/output/quick_full_delta.json")
RING_AUDIT = Path("/app/output/slot_ring_audit.json")
JOURNAL_SURF = Path("/app/output/journal_surfaces.json")
RING_BIN = Path("/app/environment/var/slots/gen_ring.bin")
COMPILE_LOG = Path("/app/environment/var/stats/compile.log")

FIX_FRONTIER_SHA256: dict[str, str] = {}


def _load_fix_frontier() -> None:
    global FIX_FRONTIER_SHA256
    if FIX_FRONTIER_SHA256:
        return
    rels = [
        "host/bld_core.c",
        "host/bld_host.c",
        "p2/slot_lane.c",
        "p2/slot_shadow.c",
        "q4/edge_scan.c",
        "q4/edge_shadow.c",
        "w7/stamp_lane.c",
        "w7/stamp_shadow.c",
        "k9/cache_ring.c",
    ]
    FIX_FRONTIER_SHA256 = {
        rel: hashlib.sha256((ENV / rel).read_bytes()).hexdigest() for rel in rels
    }


_load_fix_frontier()


def run_trace() -> dict:
    assert TRACE_OUT.is_file(), "agent must produce rebuild_trace.json before verifier rerun"
    agent_trace = json.loads(TRACE_OUT.read_text(encoding="utf-8"))
    TRACE_OUT.unlink(missing_ok=True)
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert TRACE_OUT.is_file(), "rebuild_trace.json missing after verifier trace"
    live = json.loads(TRACE_OUT.read_text(encoding="utf-8"))
    assert agent_trace == live, "agent trace must match live trace_host output"
    return live


def rows_for(doc: dict, plan_id: str) -> list[dict]:
    return [r for r in doc.get("rows", []) if r.get("plan_id") == plan_id]


def reproduce_header_bump_cap() -> None:
    import time

    proc = subprocess.run(
        ["/app/environment/bin/bld_host", "--pristine", "cap_r1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    time.sleep(1)
    proc = subprocess.run(
        ["/app/environment/bin/bld_host", "cap_r2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def live_hdr_gen() -> int:
    st = GEN_HDR.stat()
    return int((int(st.st_mtime) ^ st.st_size) & 0xFFFFFFFF)


def read_ring_entries() -> list[dict]:
    if not RING_BIN.is_file():
        return []
    data = RING_BIN.read_bytes()
    if len(data) < 4:
        return []
    (n,) = struct.unpack_from("<i", data, 0)
    if n < 0 or n > 8:
        return []
    entries: list[dict] = []
    off = 4
    live = live_hdr_gen()
    for _ in range(n):
        blob = data[off : off + 256].split(b"\0", 1)[0].decode("utf-8", errors="replace")
        off += 256
        (gen,) = struct.unpack_from("<I", data, off)
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


def expected_quick_full_delta(doc: dict) -> dict:
    plans: list[dict] = []
    for plan in json.loads(PLAN.read_text(encoding="utf-8"))["plans"]:
        pid = plan["plan_id"]
        bad_targets = [
            r["target"]
            for r in rows_for(doc, pid)
            if r["fast_digest_hex"] != r["pristine_digest_hex"]
        ]
        if bad_targets:
            plans.append({"plan_id": pid, "targets": bad_targets})
    return {"mismatch_count": len(plans), "plans_with_mismatch": plans}


def expected_ring_audit() -> dict:
    RING_BIN.unlink(missing_ok=True)
    reproduce_header_bump_cap()
    entries = read_ring_entries()
    any_stale = any(not e["gen_aligned"] for e in entries) if entries else False
    return {"entries": entries, "any_stale_gen": any_stale}


def journal_tail_skip(src_rel: str) -> bool:
    if not COMPILE_LOG.is_file():
        return False
    saw = False
    for line in COMPILE_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        action, src, _mode = parts
        if action == "skip" and src_rel in src:
            saw = True
    return saw


def expected_journal_surfaces() -> dict:
    RING_BIN.unlink(missing_ok=True)
    COMPILE_LOG.unlink(missing_ok=True)
    reproduce_header_bump_cap()
    return {
        "surfaces": [
            {
                "source_rel": "app_v1/main.c",
                "last_action_skip": journal_tail_skip("app_v1/main.c"),
            }
        ]
    }


def assert_fix_frontier_unchanged() -> None:
    for rel, want in FIX_FRONTIER_SHA256.items():
        path = ENV / rel
        assert path.is_file(), f"missing env file {rel}"
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        assert got == want, f"environment source modified during diagnosis: {rel}"


def expected_broken_plan_ids() -> set[str]:
    TRACE_OUT.unlink(missing_ok=True)
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    live = json.loads(TRACE_OUT.read_text(encoding="utf-8"))
    delta = expected_quick_full_delta(live)
    return {entry["plan_id"] for entry in delta["plans_with_mismatch"]}


def ring_covers_both_targets(entries: list[dict]) -> bool:
    blobs = {entry["blob_path"] for entry in entries}
    has_v1 = any("app_v1" in blob for blob in blobs)
    has_v2 = any("app_v2" in blob for blob in blobs)
    return has_v1 and has_v2


def delta_matches_fresh_trace(delta_path: Path) -> bool:
    TRACE_OUT.unlink(missing_ok=True)
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    live = json.loads(TRACE_OUT.read_text(encoding="utf-8"))
    agent_doc = json.loads(delta_path.read_text(encoding="utf-8"))
    return agent_doc == expected_quick_full_delta(live)
