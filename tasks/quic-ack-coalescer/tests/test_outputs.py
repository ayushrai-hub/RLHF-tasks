"""Verifier for the qack QUIC ACK coalescer.

Builds /app/cmd/qack from clean, runs the binary, and asserts every documented
rule lands on the canonical output. Re-runs the binary to confirm byte-level
idempotency, swaps to an alt fixture, mutates the input dynamically, and
checks the source tree is what the spec requires.
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

APP = Path("/app")
BIN = APP / "bin" / "qack"
DATA = APP / "ack_trove"
OUT = APP / "output"
DOCS = APP / "quic_atrium"
ALT = Path("/tests/fixtures/alt_ack_trove")

EXPECTED_DATA_DIGEST = "997d5a531d122432d0fd3bc129a6b96726b88cbd48f86a39e7f7a4718c6dc0e0"
EXPECTED_ALT_DIGEST = "d24adcf8af2cd2239d9430ba6e7643bb7109bff67264857f4a56a3602fe9c056"

ALL_VERDICTS = {
    "ACK_COALESCED",
    "ACK_DELIVERED",
    "ACK_REORDERED",
    "BAD_SPACE",
    "BUDGET_EXCEEDED",
    "RESET_VOID",
    "TYPE_INVALID",
}


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    files = []
    for r, _, fs in os.walk(str(root)):
        for f in fs:
            p = os.path.join(r, f)
            rel = os.path.relpath(p, str(root))
            files.append((rel, p))
    files.sort()
    for rel, p in files:
        h.update(rel.encode())
        h.update(b"\x00")
        with open(p, "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
        h.update(b"\x00")
    return h.hexdigest()


def _build():
    if BIN.exists():
        BIN.unlink()
    res = subprocess.run(
        ["make", "build"],
        cwd=str(APP),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert res.returncode == 0, f"make build failed: {res.stderr}"
    assert BIN.exists(), "make build did not produce /app/bin/qack"


def _run(data_dir: Path = DATA, out_dir: Path = OUT):
    env = os.environ.copy()
    env["QACK_DATA_DIR"] = str(data_dir)
    env["QACK_OUT_DIR"] = str(out_dir)
    if out_dir.exists():
        for child in out_dir.iterdir():
            try:
                child.unlink()
            except IsADirectoryError:
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(
        [str(BIN)],
        cwd=str(APP),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert res.returncode == 0, f"binary failed: stderr={res.stderr}"
    assert res.stdout == "", f"binary emitted unexpected stdout: {res.stdout!r}"
    return res


def _report(out_dir: Path = OUT):
    return json.loads((out_dir / "report.json").read_text())


_PRE_HASH = None
_POST_HASH = None


def setup_module(_module):
    global _PRE_HASH, _POST_HASH
    _PRE_HASH = tree_digest(DATA)
    _build()
    _run()
    _POST_HASH = tree_digest(DATA)


# ===== Anti-cheat (A1–A7) =====


def test_a1_input_data_digest():
    """A1: input tree digest matches baked constant (catches tampered fixtures)."""
    assert tree_digest(DATA) == EXPECTED_DATA_DIGEST


def test_a3_input_immutability():
    """A3: /app/ack_trove unchanged across the binary run."""
    assert _PRE_HASH == _POST_HASH
    assert tree_digest(DATA) == EXPECTED_DATA_DIGEST


def test_a4_dynamic_mutation_appended_row_changes_output():
    """A4: appending a new accepted frame moves the summary counters and digest."""
    baseline = _report()
    shard = DATA / "frames_a.ndjson"
    snap = shard.read_bytes()
    extra = (
        '{"conn_id":"C2","pn_space":"INITIAL","ack_ts_ms":1717459299999,'
        '"packet_number":999,"largest_acked":998,"ack_delay_us":10,'
        '"ecn_ct0":0,"ecn_ct1":0,"ecn_ce":0,"ack_eliciting":true,'
        '"shard_seq":777}\n'
    )
    try:
        shard.write_bytes(snap + extra.encode())
        _run()
        mutated = _report()
        assert mutated["summary"]["total"] == baseline["summary"]["total"] + 1
        assert mutated["report_digest"] != baseline["report_digest"]
        c2 = next(b for b in mutated["by_conn"] if b["conn_id"] == "C2")
        assert c2["events_count"] == 12
    finally:
        shard.write_bytes(snap)
        _run()


def test_a5_alt_fixture_produces_different_digest_and_direction():
    """A5: alt fixture exercises FORWARD direction and matches a baked digest constant."""
    assert tree_digest(ALT) == EXPECTED_ALT_DIGEST
    alt_out = Path("/tmp/qack-alt-out")
    if alt_out.exists():
        shutil.rmtree(alt_out)
    alt_out.mkdir(parents=True)
    _run(data_dir=ALT, out_dir=alt_out)
    alt = json.loads((alt_out / "report.json").read_text())
    assert alt["summary"]["hamilton_direction"] == "FORWARD"
    assert alt["summary"]["total"] == 8
    primary = _report()
    assert alt["report_digest"] != primary["report_digest"]
    # Restore the primary output.
    _run()


def test_a6_elf_magic_bytes():
    """A6: produced binary starts with the ELF magic."""
    assert BIN.exists()
    with open(BIN, "rb") as fh:
        head = fh.read(4)
    assert head == b"\x7fELF"


def test_a7_main_go_present_nonempty():
    """A7: cmd/qack/main.go must exist and be > 0 bytes (smuggled binary rejected)."""
    main_go = APP / "cmd" / "qack" / "main.go"
    assert main_go.exists()
    assert main_go.stat().st_size > 0


def test_a_source_presence_strict_int_stdlib():
    """A: source-presence sweep — required Go stdlib imports appear anywhere under /app/**.*go."""
    seen = []
    for r, _, fs in os.walk(str(APP)):
        if "/bin" in r:
            continue
        for f in fs:
            if f.endswith(".go"):
                seen.append(Path(r) / f)
    blob = "\n".join(p.read_text() for p in seen)
    assert "encoding/json" in blob
    assert "crypto/sha256" in blob
    assert "encoding/hex" in blob
    assert blob.count("func ") >= 8


# ===== Determinism (B1–B5) =====


def test_b1_idempotent_byte_diff():
    """B1: re-running the binary produces byte-identical output."""
    _run()
    first = (OUT / "report.json").read_bytes()
    _run()
    second = (OUT / "report.json").read_bytes()
    assert first == second


def test_b2_output_directory_exclusivity():
    """B2: /app/output contains exactly one file."""
    listed = sorted(p.name for p in OUT.iterdir())
    assert listed == ["report.json"], listed


def test_b3_stale_file_removal():
    """B3: a stale file in /app/output is cleaned up by the binary."""
    stale = OUT / "stale.txt"
    stale.write_text("debris")
    _run()
    assert not stale.exists()
    listed = sorted(p.name for p in OUT.iterdir())
    assert listed == ["report.json"]


def test_b4_build_from_clean():
    """B4: rebuild from scratch reproduces the same report digest."""
    baseline = _report()["report_digest"]
    _build()
    _run()
    assert _report()["report_digest"] == baseline


def test_b5_gomod_mode_marker_present():
    """B5: GOFLAGS=-mod=mod is set in the image so module mode is forced."""
    assert "-mod=mod" in os.environ.get("GOFLAGS", "")


# ===== Output-shape pins (C1, C6, C7, C8, C10, C11, C12) =====


def test_c1_trailing_newline_exactly_one():
    """C1: file ends with exactly one trailing newline."""
    raw = (OUT / "report.json").read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_c6_closed_enum_summary_by_verdict_all_keys_present():
    """C6: summary.by_verdict carries every closed-enum verdict key including zero counts."""
    r = _report()
    assert set(r["summary"]["by_verdict"].keys()) == ALL_VERDICTS


def test_c6_closed_enum_per_conn_all_keys_present():
    """C6: every by_conn block carries every closed-enum verdict key."""
    r = _report()
    for blk in r["by_conn"]:
        assert set(blk["by_verdict"].keys()) == ALL_VERDICTS, blk["conn_id"]


def test_c7_summary_total_matches_events_array():
    """C7: summary.total equals len(events)."""
    r = _report()
    assert r["summary"]["total"] == len(r["events"])


def test_c7_by_conn_sum_matches_summary():
    """C7: per-verdict summary equals sum of per-conn counts."""
    r = _report()
    for v in ALL_VERDICTS:
        s = sum(blk["by_verdict"][v] for blk in r["by_conn"])
        assert r["summary"]["by_verdict"][v] == s, v


def test_c8_event_record_key_set_exact():
    """C8: each event has the exact expected key set in declared order."""
    expected = [
        "conn_id",
        "pn_space",
        "ack_ts_ms",
        "packet_number",
        "largest_acked",
        "ack_delay_us",
        "ecn_ct0",
        "ecn_ct1",
        "ecn_ce",
        "ack_eliciting",
        "shard_seq",
        "anchor",
        "verdict",
    ]
    r = json.loads(
        (OUT / "report.json").read_text(),
        object_pairs_hook=lambda pairs: pairs,
    )
    # Find events array key
    top = dict(r)
    events = top["events"]
    assert isinstance(events, list)
    for ev in events:
        keys = [k for k, _ in ev]
        assert keys == expected, keys


def test_c11_events_sort_numeric_suffix_then_ack_ts():
    """C11: events sort key 1 is numeric-suffix(conn_id) so C2 precedes C10/C11."""
    r = _report()
    seen = []
    for ev in r["events"]:
        seen.append(ev["conn_id"])
    # First the run of C2 rows, then C9, then C10, then C11. Plain lex would
    # interleave C10 ahead of C2.
    first_idx = {c: seen.index(c) for c in set(seen)}
    assert first_idx["C2"] < first_idx["C9"]
    assert first_idx["C9"] < first_idx["C10"]
    assert first_idx["C10"] < first_idx["C11"]


def test_c11_by_conn_numeric_suffix_order():
    """C11: by_conn ordered by numeric-suffix(conn_id)."""
    r = _report()
    order = [b["conn_id"] for b in r["by_conn"]]
    assert order == ["C2", "C9", "C10", "C11"]


def test_c12_self_binding_digest_self_consistent():
    """C12: report_digest is sha256 over canonical bytes with digest field blanked."""
    raw_text = (OUT / "report.json").read_text()
    parsed = json.loads(raw_text)
    digest_field = parsed["report_digest"]
    # Recompute by emitting the same canonical form with digest blanked.
    blanked = dict(parsed)
    blanked["report_digest"] = ""
    # Recreate the canonical 2-space JSON, no HTML escape, no trailing newline.
    canon = json.dumps(blanked, indent=2, ensure_ascii=False)
    # Go's encoder uses ": " and ",\n" identically; this matches.
    recomputed = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    assert digest_field == recomputed


# ===== Hardness levers =====


def test_anchor_uses_larger_packet_number_on_tie():
    """F4.5: among C10 events at ack_ts=1717459206000, the LARGER pn wins anchor."""
    r = _report()
    c10 = [ev for ev in r["events"] if ev["conn_id"] == "C10" and ev["ack_ts_ms"] == 1717459206000]
    assert len(c10) == 2
    anchor = [ev for ev in c10 if ev["anchor"]]
    nonanc = [ev for ev in c10 if not ev["anchor"]]
    assert len(anchor) == 1
    assert anchor[0]["packet_number"] == 501
    assert nonanc[0]["packet_number"] == 500
    assert nonanc[0]["verdict"] == "ACK_COALESCED"


def test_window_boundary_coalesced_at_200ms_for_standard():
    """F3.2 right-inclusive coalesce: C2 STANDARD row at delta=200 is COALESCED."""
    r = _report()
    pn102 = next(ev for ev in r["events"] if ev["packet_number"] == 102 and ev["conn_id"] == "C2")
    assert pn102["verdict"] == "ACK_COALESCED"


def test_window_boundary_reordered_at_201ms_for_standard():
    """F3.2 left-exclusive reorder: C2 STANDARD row at delta=201 is REORDERED."""
    r = _report()
    pn103 = next(ev for ev in r["events"] if ev["packet_number"] == 103 and ev["conn_id"] == "C2")
    assert pn103["verdict"] == "ACK_REORDERED"


def test_window_right_boundary_reordered_at_500ms_for_standard():
    """F3.2 right-inclusive reorder: C2 STANDARD row at delta=500 is REORDERED."""
    r = _report()
    pn104 = next(ev for ev in r["events"] if ev["packet_number"] == 104 and ev["conn_id"] == "C2")
    assert pn104["verdict"] == "ACK_REORDERED"


def test_window_beyond_reorder_is_delivered():
    """C2 STANDARD row at delta=501 is ACK_DELIVERED (out of both windows)."""
    r = _report()
    pn105 = next(ev for ev in r["events"] if ev["packet_number"] == 105 and ev["conn_id"] == "C2")
    assert pn105["verdict"] == "ACK_DELIVERED"


def test_critical_tier_halves_coalesce_window():
    """F4.6: CRITICAL tier coalesce_ms is 100, so C9 delta=100 IS COALESCED."""
    r = _report()
    pn301 = next(ev for ev in r["events"] if ev["packet_number"] == 301 and ev["conn_id"] == "C9")
    assert pn301["verdict"] == "ACK_COALESCED"
    pn302 = next(ev for ev in r["events"] if ev["packet_number"] == 302 and ev["conn_id"] == "C9")
    assert pn302["verdict"] == "ACK_REORDERED"


def test_type_invalid_float_ack_ts_zeros_numerics():
    """F2.4: float ack_ts_ms trips strict-int rejection, zeros all numerics."""
    r = _report()
    invalid_c10 = [
        ev for ev in r["events"] if ev["conn_id"] == "C10" and ev["verdict"] == "TYPE_INVALID"
    ]
    assert len(invalid_c10) == 1
    inv = invalid_c10[0]
    for k in ("ack_ts_ms", "packet_number", "largest_acked", "ack_delay_us",
              "ecn_ct0", "ecn_ct1", "ecn_ce"):
        assert inv[k] == 0, k
    assert inv["ack_eliciting"] is False
    assert inv["shard_seq"] == 20


def test_type_invalid_int_ack_eliciting_is_rejected():
    """F4.7: ack_eliciting=1 (int, not bool) routes to TYPE_INVALID."""
    r = _report()
    invalid_c2 = [
        ev for ev in r["events"] if ev["conn_id"] == "C2" and ev["verdict"] == "TYPE_INVALID"
    ]
    assert len(invalid_c2) == 1
    assert invalid_c2[0]["shard_seq"] == 21


def test_bad_space_verdict():
    """Closed pn_space enum: ZERORTT → BAD_SPACE."""
    r = _report()
    bad = [ev for ev in r["events"] if ev["verdict"] == "BAD_SPACE"]
    assert len(bad) == 1
    assert bad[0]["pn_space"] == "ZERORTT"
    assert bad[0]["conn_id"] == "C11"


def test_reset_void_via_validated_marker():
    """F5.7: validated RESET_RANGE marker voids pn in [target_low, target_high]."""
    r = _report()
    voided = sorted(
        ev["packet_number"]
        for ev in r["events"]
        if ev["verdict"] == "RESET_VOID"
    )
    assert voided == [600, 605]
    # pn=606 falls outside the range → still becomes the bucket anchor.
    pn606 = next(ev for ev in r["events"] if ev["packet_number"] == 606)
    assert pn606["verdict"] == "ACK_DELIVERED"
    assert pn606["anchor"] is True


def test_marker_with_invalid_hmac_does_nothing():
    """F4.4: a marker whose hmac8 mismatches is silently dropped (C2 pn=100 stays accepted)."""
    r = _report()
    pn100 = next(ev for ev in r["events"] if ev["packet_number"] == 100 and ev["conn_id"] == "C2")
    assert pn100["verdict"] == "ACK_DELIVERED"
    assert pn100["anchor"] is True


def test_marker_with_wrong_source_does_nothing():
    """F4.4: marker.source != 'control_plane' → silently dropped (C9 pn=300 stays anchored)."""
    r = _report()
    pn300 = next(ev for ev in r["events"] if ev["packet_number"] == 300 and ev["conn_id"] == "C9")
    assert pn300["verdict"] == "ACK_DELIVERED"
    assert pn300["anchor"] is True


def test_cross_cycle_cascade_budget_exceeded():
    """F5.6: C2 day-1 ACCEPTED count=8 triggers BUDGET_EXCEEDED on day-2 earliest event."""
    r = _report()
    budget = [ev for ev in r["events"] if ev["verdict"] == "BUDGET_EXCEEDED"]
    assert len(budget) == 1
    assert budget[0]["conn_id"] == "C2"
    assert budget[0]["packet_number"] == 200
    assert budget[0]["anchor"] is False


def test_hamilton_direction_default_reverse():
    """ORIGINAL: REVERSE by default when no registered conn carries urgent=true."""
    r = _report()
    assert r["summary"]["hamilton_direction"] == "REVERSE"


def test_hamilton_basis_points_sum_to_10000():
    """Hamilton conservation: basis_points sum to exactly 10000 when total weight > 0."""
    r = _report()
    assert sum(s["basis_points"] for s in r["hamilton"]) == 10000


def test_hamilton_exact_distribution():
    """Hamilton exact values for the primary fixture."""
    r = _report()
    got = {s["conn_id"]: (s["weight"], s["basis_points"]) for s in r["hamilton"]}
    assert got["C2"] == (9, 5000)
    assert got["C9"] == (5, 2778)
    assert got["C10"] == (3, 1667)
    assert got["C11"] == (1, 555)


def test_hamilton_direction_flips_forward_when_urgent_on_alt():
    """ORIGINAL: any registered urgent=true flips Hamilton to FORWARD on alt fixture."""
    alt_out = Path("/tmp/qack-alt-direction")
    if alt_out.exists():
        shutil.rmtree(alt_out)
    alt_out.mkdir(parents=True)
    _run(data_dir=ALT, out_dir=alt_out)
    alt = json.loads((alt_out / "report.json").read_text())
    assert alt["summary"]["hamilton_direction"] == "FORWARD"
    got = {s["conn_id"]: s["basis_points"] for s in alt["hamilton"]}
    # D1 wins the +1 leftover under FORWARD numeric-suffix tiebreak (D1 < D3 < D7).
    assert got["D1"] == 1667
    assert got["D3"] == 3333
    assert got["D7"] == 5000
    _run()


def test_tier_synonym_case_insensitive():
    """F9.4: tier 'standard' / 'bulk' / 'CRITICAL' all canonicalize."""
    r = _report()
    tiers = {b["conn_id"]: b["tier"] for b in r["by_conn"]}
    assert tiers["C2"] == "STANDARD"
    assert tiers["C9"] == "CRITICAL"
    assert tiers["C10"] == "BULK"
    assert tiers["C11"] == "STANDARD"


def test_summary_by_verdict_exact_counts():
    """Exact summary counts for the primary fixture."""
    r = _report()
    assert r["summary"]["by_verdict"] == {
        "ACK_COALESCED": 5,
        "ACK_DELIVERED": 7,
        "ACK_REORDERED": 6,
        "BAD_SPACE": 1,
        "BUDGET_EXCEEDED": 1,
        "RESET_VOID": 2,
        "TYPE_INVALID": 2,
    }


def test_summary_total_and_registered():
    """summary.total and registered_connections match the primary fixture."""
    r = _report()
    assert r["summary"]["total"] == 24
    assert r["summary"]["registered_connections"] == 4
    assert r["summary"]["budget_threshold"] == 8
    assert r["summary"]["policy_version"] == "2026.06.07"


def test_sample_harness_byte_matches_expected():
    """The shipped sample harness byte-matches the golden run under the workshop."""
    sample_dir = DOCS / "ack_workshop" / "coalescer_seed"
    expected_path = DOCS / "ack_workshop" / "golden_run.json"
    out_dir = Path("/tmp/qack-sample-test")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    _run(data_dir=sample_dir, out_dir=out_dir)
    got = (out_dir / "report.json").read_bytes()
    expected = expected_path.read_bytes()
    assert got == expected
    _run()


def test_no_html_escapes_in_output():
    """C3: no HTML escapes in the canonical output."""
    raw = (OUT / "report.json").read_text()
    assert "\\u003c" not in raw
    assert "\\u003e" not in raw
    assert "\\u0026" not in raw


def test_no_python_files_in_app():
    """Allowed-language enforcement: no .py files exist under /app."""
    for r, _, fs in os.walk(str(APP)):
        for f in fs:
            assert not f.endswith(".py"), f"{r}/{f}"


def test_anchor_per_bucket_at_most_one():
    """Every (conn, pn_space, utc_day) bucket has at most one anchor=true row."""
    r = _report()
    seen = {}
    for ev in r["events"]:
        if ev["verdict"] in {"TYPE_INVALID", "BAD_SPACE", "RESET_VOID", "BUDGET_EXCEEDED"}:
            continue
        if not ev["anchor"]:
            continue
        day = ev["ack_ts_ms"] // 86400000
        key = (ev["conn_id"], ev["pn_space"], day)
        assert key not in seen, key
        seen[key] = ev


def test_no_banned_scaffold_files():
    """No CLAUDE.md / AGENTS.md / skills.md scaffolding artifacts under /app or environment paths."""
    banned = {"CLAUDE.md", "AGENTS.md", "skills.md", "SKILLS.md", "BUGS.md", "TODO.md", "FIXME.md", "HINTS.md"}
    for r, _, fs in os.walk(str(APP)):
        for f in fs:
            assert f not in banned, f"{r}/{f}"


def test_per_conn_accepted_count_matches_hamilton_weight():
    """Conservation: hamilton weight per conn matches accepted in by_conn."""
    r = _report()
    by_conn_acc = {b["conn_id"]: b["accepted"] for b in r["by_conn"]}
    for s in r["hamilton"]:
        assert by_conn_acc[s["conn_id"]] == s["weight"], s["conn_id"]
