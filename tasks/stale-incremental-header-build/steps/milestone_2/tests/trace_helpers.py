"""Shared helpers for milestone 2 verifier tests."""

from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

TRACE_OUT = Path("/app/output/rebuild_trace.json")
PLAN = Path("/app/environment/data/run_plan.json")
COMPILE_LOG = Path("/app/environment/var/stats/compile.log")
GEN_HDR = Path("/app/environment/var/gen/version_slot.h")
MAIN_OBJ = Path("/app/environment/var/objs/app_v1/main.o")
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


def parse_compile_log() -> list[tuple[str, str, str]]:
    if not COMPILE_LOG.is_file():
        return []
    rows: list[tuple[str, str, str]] = []
    for line in COMPILE_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def count_actions(action: str, mode: str | None = None) -> int:
    total = 0
    for act, _src, m in parse_compile_log():
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


def assert_matrix_law(doc: dict, plan_id: str) -> None:
    expected = plan_cap_value(plan_id)
    rows = rows_for(doc, plan_id)
    assert rows, f"no rows for {plan_id}"
    for row in rows:
        assert row["fast_digest_hex"] == row["pristine_digest_hex"]
        assert row["capability_tag"] == expected


def unchanged_matches_header_bump_app_v1(doc: dict) -> None:
    control_rows = rows_for(doc, "unchanged_control")
    bump_rows = rows_for(doc, "header_bump")
    assert control_rows, "unchanged_control must emit rows"
    assert bump_rows, "header_bump must emit rows"
    control = control_rows[0]
    bump_v1 = next(r for r in bump_rows if r["target"] == "app_v1")
    assert control["fast_digest_hex"] == bump_v1["fast_digest_hex"]
    assert control["pristine_digest_hex"] == bump_v1["pristine_digest_hex"]


def triple_incremental_only_reuse() -> None:
    run_bld("--pristine", "cap_r2")
    run_bld("cap_r2")
    for _ in range(3):
        clear_compile_log()
        run_bld("--incremental-only")
        assert count_actions("compile", "fast") == 0
        assert count_actions("skip", "fast") >= 1


def header_bump_compiles_main() -> None:
    run_bld("--pristine", "cap_r1")
    clear_compile_log()
    run_bld("cap_r2")
    compiles = [
        src for act, src, mode in parse_compile_log() if act == "compile" and mode == "fast"
    ]
    assert any("app_v1/main.c" in s for s in compiles)
    obj_st = MAIN_OBJ.stat()
    hdr_st = GEN_HDR.stat()
    assert obj_st.st_mtime_ns >= hdr_st.st_mtime_ns


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


def header_bump_ring_recovered() -> None:
    run_bld("--pristine", "cap_r1")
    run_bld("cap_r2")
    after = read_ring_entries()
    assert after, "ring must record link blobs after cap-bump rebuild"
    assert ring_gens_aligned(), "all ring entries must share the same generation tag"
    doc = run_trace()
    for row in rows_for(doc, "header_bump"):
        assert row["fast_digest_hex"] == row["pristine_digest_hex"]
