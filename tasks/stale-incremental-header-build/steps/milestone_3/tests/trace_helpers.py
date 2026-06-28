"""Shared helpers for milestone 3 verifier tests."""

from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

TRACE_OUT = Path("/app/output/rebuild_trace.json")
PLAN = Path("/app/environment/data/run_plan.json")
COMPILE_LOG = Path("/app/environment/var/stats/compile.log")
RING_BIN = Path("/app/environment/var/slots/gen_ring.bin")


def run_trace() -> dict:
    TRACE_OUT.unlink(missing_ok=True)
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert TRACE_OUT.is_file(), "rebuild_trace.json missing"
    return json.loads(TRACE_OUT.read_text(encoding="utf-8"))


def rows_for(doc: dict, plan_id: str) -> list[dict]:
    return [r for r in doc.get("rows", []) if r.get("plan_id") == plan_id]


def plan_cap_value(plan_id: str) -> str:
    doc = json.loads(PLAN.read_text(encoding="utf-8"))
    for plan in doc["plans"]:
        if plan["plan_id"] == plan_id:
            return plan["cap_value"]
    raise KeyError(plan_id)


def clear_compile_log() -> None:
    COMPILE_LOG.unlink(missing_ok=True)


def count_actions(action: str, mode: str | None = None) -> int:
    if not COMPILE_LOG.is_file():
        return 0
    total = 0
    for line in COMPILE_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        act, _src, m = parts
        if act != action:
            continue
        if mode is not None and m != mode:
            continue
        total += 1
    return total


def run_bld(*args: str) -> None:
    proc = subprocess.run(
        ["/app/environment/bin/bld_host", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def cap_rollback_manual_ring_stable() -> None:
    run_bld("--pristine", "cap_r2")
    run_bld("cap_r3")
    run_bld("cap_r2")
    assert ring_gens_homogeneous(), "ring tags must stay aligned through rollback sequence"
    doc = run_trace()
    expected = plan_cap_value("cap_rollback")
    for row in rows_for(doc, "cap_rollback"):
        assert row["fast_digest_hex"] == row["pristine_digest_hex"]
        assert row["capability_tag"] == expected


def same_second_incremental_chain() -> None:
    run_bld("--pristine", "cap_r3")
    run_bld("cap_r3")
    subprocess.run(
        ["/app/environment/scripts/touch_same_sec.sh", "/app/environment"],
        check=True,
    )
    run_bld("cap_r3")
    clear_compile_log()
    run_bld("--incremental-only")
    assert count_actions("compile", "fast") == 0
    assert count_actions("skip", "fast") >= 1
    first = run_trace()
    clear_compile_log()
    run_bld("--incremental-only")
    assert count_actions("compile", "fast") == 0
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    second = json.loads(TRACE_OUT.read_text(encoding="utf-8"))
    assert second == first


def trace_bytes_stable() -> None:
    run_trace()
    first = TRACE_OUT.read_bytes()
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    second = TRACE_OUT.read_bytes()
    assert first == second


def read_ring_entries() -> list[tuple[str, int]]:
    if not RING_BIN.is_file():
        return []
    data = RING_BIN.read_bytes()
    if len(data) < 4:
        return []
    (n,) = struct.unpack_from("<i", data, 0)
    if n < 0 or n > 8:
        return []
    entries: list[tuple[str, int]] = []
    off = 4
    for _ in range(n):
        blob = data[off : off + 256].split(b"\0", 1)[0].decode("utf-8", errors="replace")
        off += 256
        (gen,) = struct.unpack_from("<I", data, off)
        off += 4
        entries.append((blob, gen))
    return entries


def ring_gens_homogeneous() -> bool:
    entries = read_ring_entries()
    if not entries:
        return True
    gens = {gen for _blob, gen in entries}
    return len(gens) == 1


def ring_gens_aligned() -> bool:
    """All ring entries carry the same generation tag."""
    return ring_gens_homogeneous()


def triple_incremental_stable() -> None:
    run_bld("--pristine", "cap_r2")
    run_bld("cap_r2")
    run_bld("cap_r3")
    run_bld("cap_r2")
    clear_compile_log()
    run_bld("--incremental-only")
    assert count_actions("compile", "fast") == 0
    after = read_ring_entries()
    assert after, "ring must record link blobs after cap cycles"
    assert ring_gens_homogeneous(), "all ring entries must share the same generation tag"
    assert ring_gens_aligned()
    doc = run_trace()
    for plan_id in ("header_bump", "cap_rollback", "same_second_seq"):
        for row in rows_for(doc, plan_id):
            assert row["fast_digest_hex"] == row["pristine_digest_hex"]


def trace_stable_after_incremental_only() -> None:
    first = run_trace()
    run_bld("--incremental-only")
    proc = subprocess.run(
        ["/app/environment/bin/trace_host", str(PLAN)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    second = json.loads(TRACE_OUT.read_text(encoding="utf-8"))
    assert second == first
