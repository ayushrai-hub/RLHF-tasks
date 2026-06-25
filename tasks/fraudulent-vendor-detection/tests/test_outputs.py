import json
import os
import subprocess
import tempfile
from pathlib import Path

OUT = Path("/app/output/vendor_audit.json")
ENV_ROOT = Path("/app/environment")
RUNNER = "/app/environment/tools/runner.sh"
CFG_BURST = Path("/app/environment/profiles/burst.json")
CFG_STEADY = Path("/app/environment/profiles/steady.json")
CFG_RELAY = Path("/app/environment/profiles/relay.json")
CFG_SOLO = Path("/app/environment/profiles/solo_stream.json")
CFG_MIXED = Path("/app/environment/profiles/mixed_fleet.json")
CFG_DELAY = Path("/app/environment/profiles/delay_ticks.json")
CFG_SOUTH_RELAY = Path("/app/environment/profiles/south_relay.json")
CFG_CROSS_TICK = Path("/app/environment/profiles/cross_tick.json")
CFG_FAILOVER = Path("/app/environment/profiles/period_failover.json")
ALL_PROFILES = (
    CFG_STEADY,
    CFG_BURST,
    CFG_RELAY,
    CFG_SOLO,
    CFG_MIXED,
    CFG_DELAY,
    CFG_SOUTH_RELAY,
    CFG_CROSS_TICK,
    CFG_FAILOVER,
)
FAILOVER_PROFILES = (CFG_FAILOVER,)
TMP = Path("/tmp/vendor_variants")

NORTH_MANIFEST = [f"u{i:03d}" for i in range(1, 19)]
SOUTH_MANIFEST = [f"s{i:03d}" for i in range(1, 11)]
TICK0_TRIPLE = ("u001", "u002", "u003")
TICK1_TRIPLE = ("u004", "u005", "u006")
SOUTH_TICK0_TRIPLE = ("s001", "s002", "s003")
SOUTH_TICK1_TRIPLE = ("s004", "s005", "s006")
ROW_FIELDS = ("period", "stage", "weight_pts", "bind_slot", "status", "phantom_pts")
NORTH_BURST_REJECTED = frozenset(
    {"u003", "u006", "u009", "u010", "u012", "u015", "u016", "u017", "u018"}
)
SOLO_STAGE0_JOURNEYS = frozenset({"u001", "u004", "u007", "u009", "u011", "u013", "u015", "u017"})
PARITY_SUMMARY_FIELDS = (
    "accepted_count",
    "rejected_count",
    "phantom_event_count",
    "phantom_spend_total",
    "vendor_fingerprint",
)
SUMMARY_FIELDS = PARITY_SUMMARY_FIELDS + (
    "restore_applied_count",
    "replay_periods_count",
    "restore_trim_count",
    "replay_scheduled_count",
)


def _digest(parts: list[str]) -> str:
    script = (
        "import hashlib,sys;"
        "print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"
    )
    payload = "|".join(parts).encode()
    out = subprocess.check_output(["python3", "-c", script], input=payload)
    return out.decode().strip()


_FRESH_BINARY: Path | None = None


def _build_fresh_binary() -> Path:
    """Compile vendorlab from /app/environment into a verifier-only temp path."""
    global _FRESH_BINARY
    fd, raw_path = tempfile.mkstemp(prefix="vendorlab_", suffix="_verify")
    os.close(fd)
    fresh_bin = Path(raw_path)
    env = os.environ.copy()
    env["PATH"] = "/usr/local/go/bin:" + env.get("PATH", "")
    subprocess.check_call(
        [
            "go",
            "build",
            "-trimpath",
            "-ldflags=-s -w",
            "-o",
            str(fresh_bin),
            "./cmd/vendorlab",
        ],
        cwd=str(ENV_ROOT),
        env=env,
    )
    _FRESH_BINARY = fresh_bin
    return fresh_bin


def _documented_runner_literals() -> None:
    subprocess.check_call(
        [RUNNER, "/app/environment/profiles/burst.json", "/app/output/vendor_audit.json"]
    )
    subprocess.check_call(
        [RUNNER, "/app/environment/profiles/steady.json", "/app/output/vendor_audit.json"]
    )


def _run(cfg: Path, out: Path = OUT) -> dict:
    """Run via freshly built Go binary so runner.sh substitution cannot pass."""
    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    bin_path = _FRESH_BINARY if _FRESH_BINARY and _FRESH_BINARY.exists() else _build_fresh_binary()
    subprocess.check_call(
        [str(bin_path), "--config", str(cfg), "--out", str(out)],
    )
    return json.loads(out.read_text())


def _load_cfg(base: Path, **overrides) -> Path:
    obj = json.loads(base.read_text())
    for key, val in overrides.items():
        if key == "flags":
            obj.setdefault("flags", {}).update(val)
        else:
            obj[key] = val
    TMP.mkdir(parents=True, exist_ok=True)
    tag = format(hash(json.dumps(obj, sort_keys=True)) & 0xFFFFFFFF, "08x")
    path = TMP / f"variant_{tag}.json"
    path.write_text(json.dumps(obj, indent=2))
    return path


def _line_map(report: dict) -> dict[str, dict]:
    return {r["invoice_id"]: r for r in report["lines"]}


def _fingerprint(report: dict) -> str:
    return report["summary"]["vendor_fingerprint"]


def _ceiling_map(report: dict) -> dict[str, int]:
    return {row["vendor_id"]: row["vendor_graph_cap"] for row in report["accounts"]}


def _paired_attribution(base: Path = CFG_BURST, **overrides) -> tuple[dict, dict]:
    line_item = _load_cfg(base, view_mode="line_item", **overrides)
    vendor_graph = _load_cfg(base, view_mode="vendor_graph", **overrides)
    return _run(line_item, OUT), _run(vendor_graph, OUT)


def _assert_summary_equal(left: dict, right: dict) -> None:
    for key in PARITY_SUMMARY_FIELDS:
        assert left["summary"][key] == right["summary"][key]


def _assert_line_rows_equal(left: dict, right: dict) -> None:
    left_rows, right_rows = _line_map(left), _line_map(right)
    assert left_rows.keys() == right_rows.keys()
    for uid in left_rows:
        for key in ROW_FIELDS:
            assert left_rows[uid][key] == right_rows[uid][key], f"{uid}.{key}"


def _assert_tick_snapshots_equal(left: dict, right: dict) -> None:
    assert len(left["ticks"]) == len(right["ticks"])
    for left_tick, right_tick in zip(left["ticks"], right["ticks"]):
        assert left_tick["period_index"] == right_tick["period_index"]
        assert left_tick["stage_digest"] == right_tick["stage_digest"]
        assert left_tick["vendor_snaps"] == right_tick["vendor_snaps"]


def _assert_full_schedule_parity(left: dict, right: dict) -> None:
    assert _fingerprint(left) == _fingerprint(right)
    _assert_summary_equal(left, right)
    _assert_line_rows_equal(left, right)
    _assert_tick_snapshots_equal(left, right)


def _assert_zero_drift(report: dict) -> None:
    assert report["summary"]["phantom_event_count"] == 0
    assert report["summary"]["phantom_spend_total"] == 0


def _recompute_vendor_fingerprint(report: dict) -> str:
    parts = [
        f"{row['invoice_id']}:{row['bind_slot']}"
        for row in sorted(report["lines"], key=lambda r: r["invoice_id"])
        if row["status"] == "accepted"
    ]
    return _digest(parts)


def _recompute_tick_digest(tick_row: dict) -> str:
    parts = sorted(
        f"{snap['vendor_id']}:{snap['committed_pts']}:{snap['pending_pts']}"
        for snap in tick_row["vendor_snaps"]
    )
    return _digest(parts)


def _assert_summary_consistency(report: dict) -> None:
    summ = report["summary"]
    rows = report["lines"]
    accepted = [r for r in rows if r["status"] == "accepted"]
    rejected = [r for r in rows if r["status"] == "rejected"]
    assert summ["accepted_count"] == len(accepted)
    assert summ["rejected_count"] == len(rejected)
    overage_events = sum(1 for r in accepted if r["phantom_pts"] > 0)
    leaked = sum(r["phantom_pts"] for r in accepted)
    assert summ["phantom_event_count"] == overage_events
    assert summ["phantom_spend_total"] == leaked
    slots = [r["bind_slot"] for r in accepted]
    assert len(slots) == len(set(slots))
    assert all(s >= 0 for s in slots)
    for r in rejected:
        assert r["bind_slot"] == -1
        assert r["phantom_pts"] == 0


def _assert_bind_slot_apply_order(report: dict) -> None:
    accepted = [r for r in report["lines"] if r["status"] == "accepted"]
    by_apply = sorted(accepted, key=lambda r: (r["period"], r["stage"], r["invoice_id"]))
    slots = [r["bind_slot"] for r in by_apply]
    assert slots == sorted(slots)
    assert len(slots) == len(set(slots))


def _assert_tick_snaps_within_ceiling(report: dict) -> None:
    ceilings = _ceiling_map(report)
    for tick_row in report["ticks"]:
        for snap in tick_row["vendor_snaps"]:
            total = snap["committed_pts"] + snap["pending_pts"]
            assert total <= ceilings[snap["vendor_id"]]


def _assert_triple_rejection(report: dict, triple: tuple[str, str, str]) -> None:
    rows = _line_map(report)
    assert rows[triple[0]]["status"] == "accepted"
    assert rows[triple[1]]["status"] == "accepted"
    assert rows[triple[2]]["status"] == "rejected"
    assert rows[triple[2]]["bind_slot"] == -1


def _assert_config_roundtrip(report: dict, cfg: Path) -> None:
    expected = json.loads(cfg.read_text())
    assert report["config_id"] == expected["config_id"]
    assert report["seed"] == expected["seed"]
    assert report["panel_id"] == expected["panel_id"]
    assert report["stage_width"] == expected["stage_width"]
    assert report["max_period"] == expected["max_period"]
    assert report["view_mode"] == expected["view_mode"]
    for key, val in expected["flags"].items():
        assert report["flags"][key] is val


def _assert_phantom_bounded(report: dict) -> None:
    for row in report["lines"]:
        if row["status"] == "accepted":
            assert 0 <= row["phantom_pts"] <= row["weight_pts"]
        else:
            assert row["phantom_pts"] == 0


def _assert_period_index_span(report: dict) -> None:
    expected_len = report["max_period"] + 1
    assert len(report["ticks"]) == expected_len
    for i, tick_row in enumerate(report["ticks"]):
        assert tick_row["period_index"] == i


def _assert_account_budgets_match_fixture(report: dict) -> None:
    ceilings = _ceiling_map(report)
    for row in report["accounts"]:
        assert ceilings[row["vendor_id"]] == row["vendor_graph_cap"]


def _assert_vendor_graph_invariants(report: dict, cfg: Path) -> None:
    _assert_zero_drift(report)
    _assert_summary_consistency(report)
    _assert_phantom_bounded(report)
    _assert_period_index_span(report)
    _assert_config_roundtrip(report, cfg)
    _assert_account_budgets_match_fixture(report)
    assert report["summary"]["vendor_fingerprint"] == _recompute_vendor_fingerprint(report)
    for tick_row in report["ticks"]:
        assert tick_row["stage_digest"] == _recompute_tick_digest(tick_row)
    _assert_tick_snaps_within_ceiling(report)
    _assert_lines_sorted(report)
    _assert_vendor_snaps_sorted(report)
    _assert_committed_pts_monotonic(report)
    _assert_bind_slot_sequence(report)


def _assert_lines_sorted(report: dict) -> None:
    invoice_ids = [row["invoice_id"] for row in report["lines"]]
    assert invoice_ids == sorted(invoice_ids)


def _assert_vendor_snaps_sorted(report: dict) -> None:
    for tick_row in report["ticks"]:
        vendor_ids = [snap["vendor_id"] for snap in tick_row["vendor_snaps"]]
        assert vendor_ids == sorted(vendor_ids)


def _assert_committed_pts_monotonic(report: dict) -> None:
    vendors = {row["vendor_id"] for row in report["accounts"]}
    for vendor_id in vendors:
        last_committed = -1
        for tick_row in report["ticks"]:
            snap = next(s for s in tick_row["vendor_snaps"] if s["vendor_id"] == vendor_id)
            assert snap["committed_pts"] >= last_committed
            last_committed = snap["committed_pts"]


def _assert_bind_slot_sequence(report: dict) -> None:
    accepted = [r for r in report["lines"] if r["status"] == "accepted"]
    if not accepted:
        return
    by_apply = sorted(accepted, key=lambda r: (r["period"], r["stage"], r["invoice_id"]))
    slots = [r["bind_slot"] for r in by_apply]
    assert slots[0] == 1
    assert slots == list(range(1, len(slots) + 1))


def _manifest_invoices_up_to_period(panel_id: str, max_period: int) -> set[str]:
    fixture = json.loads(
        (ENV_ROOT / "fixtures" / f"corpus_{panel_id}.json").read_text()
    )
    return {
        row["invoice_id"]
        for row in fixture["lines"]
        if row["period"] <= max_period
    }


def _vendor_snap_at(report: dict, period_index: int, vendor_id: str) -> dict:
    tick_row = report["ticks"][period_index]
    return next(s for s in tick_row["vendor_snaps"] if s["vendor_id"] == vendor_id)


def _trajectory_at(report: dict, period_index: int) -> dict[str, tuple[int, int]]:
    tick_row = report["ticks"][period_index]
    return {
        snap["vendor_id"]: (snap["committed_pts"], snap["pending_pts"])
        for snap in tick_row["vendor_snaps"]
    }


NORTH_BURST_COMMITTED_BY_PERIOD: tuple[dict[str, int], ...] = (
    {"vendor-acme": 800, "vendor-beta": 0},
    {"vendor-acme": 800, "vendor-beta": 400},
    {"vendor-acme": 950, "vendor-beta": 450},
    {"vendor-acme": 950, "vendor-beta": 450},
    {"vendor-acme": 1000, "vendor-beta": 450},
    {"vendor-acme": 1000, "vendor-beta": 500},
    {"vendor-acme": 1000, "vendor-beta": 500},
    {"vendor-acme": 1000, "vendor-beta": 500},
)
NORTH_TRIPLE_PERIOD_REJECTED = {0: "u003", 1: "u006"}
SOUTH_MIXED_REJECTED = frozenset({"s003", "s006", "s010"})
SOUTH_MIXED_COMMITTED_BY_PERIOD: tuple[dict[str, int], ...] = (
    {"vendor-delta": 600, "gamma-pallet": 0},
    {"vendor-delta": 600, "gamma-pallet": 300},
    {"vendor-delta": 700, "gamma-pallet": 340},
    {"vendor-delta": 780, "gamma-pallet": 340},
)


def _recompute_checkpoint_state_digest(committed: dict[str, int]) -> str:
    parts = sorted(f"{vendor_id}:{pts}" for vendor_id, pts in committed.items())
    return _digest(parts)


def _assert_checkpoint_integrity(ckpt_path: Path, prefix_report: dict | None = None) -> dict:
    payload = json.loads(ckpt_path.read_text())
    assert payload["state_digest"] == _recompute_checkpoint_state_digest(payload["committed_pts"])
    assert payload["last_period_index"] >= 0
    assert payload["next_bind_slot"] >= 1
    assert payload["rejected_count"] >= 0
    assert isinstance(payload["lines"], list)
    assert isinstance(payload["ticks"], list)
    assert len(payload["ticks"]) == payload["last_period_index"] + 1
    for tick_row in payload["ticks"]:
        assert tick_row["stage_digest"] == _recompute_tick_digest(tick_row)
    last_tick = payload["ticks"][payload["last_period_index"]]
    for snap in last_tick["vendor_snaps"]:
        assert payload["committed_pts"][snap["vendor_id"]] == snap["committed_pts"]
        assert payload["pending_pts"][snap["vendor_id"]] == snap["pending_pts"]
    if prefix_report is not None:
        assert payload["rejected_count"] == prefix_report["summary"]["rejected_count"]
        assert {row["invoice_id"] for row in payload["lines"]} <= set(_line_map(prefix_report))
    return payload


def _audit_bytes(cfg: Path) -> tuple[bytes, bytes]:
    first_out = TMP / "det_first.json"
    second_out = TMP / "det_second.json"
    _run(cfg, first_out)
    first = first_out.read_bytes()
    _run(cfg, second_out)
    second = second_out.read_bytes()
    return first, second


def _period_accepted_weight(report: dict, period: int, vendor_id: str) -> int:
    return sum(
        row["weight_pts"]
        for row in report["lines"]
        if row["period"] == period
        and row["vendor_id"] == vendor_id
        and row["status"] == "accepted"
    )


def _assert_period_accepted_weight_within_caps(report: dict) -> None:
    ceilings = _ceiling_map(report)
    periods = {row["period"] for row in report["lines"]}
    vendors = {row["vendor_id"] for row in report["accounts"]}
    for period in periods:
        for vendor_id in vendors:
            spent = _period_accepted_weight(report, period, vendor_id)
            assert spent <= ceilings[vendor_id]


def _assert_pending_within_remaining_cap(report: dict) -> None:
    ceilings = _ceiling_map(report)
    for tick_row in report["ticks"]:
        for snap in tick_row["vendor_snaps"]:
            remaining = ceilings[snap["vendor_id"]] - snap["committed_pts"]
            assert snap["pending_pts"] <= remaining


def _assert_committed_trajectory_table(
    report: dict, table: tuple[dict[str, int], ...]
) -> None:
    assert len(report["ticks"]) >= len(table)
    for period_index, expected in enumerate(table):
        traj = _trajectory_at(report, period_index)
        for vendor_id, committed_pts in expected.items():
            assert traj[vendor_id][0] == committed_pts, (
                f"period {period_index} {vendor_id}: "
                f"got {traj[vendor_id][0]} expected {committed_pts}"
            )
            assert traj[vendor_id][1] == 0


def _run_prefix_checkpoint(prefix_period: int, ckpt_path: Path) -> dict:
    cfg = _load_cfg(
        CFG_BURST,
        view_mode="vendor_graph",
        max_period=prefix_period,
        checkpoint_out=str(ckpt_path),
    )
    return _run(cfg, OUT)


def test_entrypoint_prefix_ledger_emit():
    """Documented runner succeeds and prefix burst runs emit warm ledger checkpoints."""
    _documented_runner_literals()
    ckpt = TMP / "entrypoint_prefix.ckpt"
    prefix = _run_prefix_checkpoint(2, ckpt)
    assert ckpt.is_file()
    payload = json.loads(ckpt.read_text())
    assert payload["last_period_index"] == 2
    assert payload["state_digest"]
    assert prefix["summary"]["phantom_spend_total"] == 0


def test_audit_shape_and_fields():
    """Audit JSON parses and exposes documented top-level and nested fields."""
    r = _run(CFG_STEADY, OUT)
    required = {
        "config_id",
        "seed",
        "view_mode",
        "panel_id",
        "stage_width",
        "max_period",
        "flags",
        "accounts",
        "lines",
        "summary",
        "ticks",
    }
    assert required <= set(r.keys())
    rec = r["lines"][0]
    for key in (
        "invoice_id",
        "vendor_id",
        "period",
        "stage",
        "weight_pts",
        "bind_slot",
        "status",
        "phantom_pts",
    ):
        assert key in rec
    summ = r["summary"]
    for key in SUMMARY_FIELDS:
        assert key in summ
    period = r["ticks"][0]
    assert "period_index" in period
    assert "stage_digest" in period
    assert "vendor_snaps" in period


def test_prefix_ledger_replay_identical():
    """Repeated prefix burst runs with checkpoint_out produce byte-identical ledger files."""
    ckpt_a = TMP / "replay_a.ckpt"
    ckpt_b = TMP / "replay_b.ckpt"
    _run_prefix_checkpoint(2, ckpt_a)
    _run_prefix_checkpoint(2, ckpt_b)
    assert ckpt_a.read_bytes() == ckpt_b.read_bytes()


def test_primary_schedule_parity():
    """Dashboard and vendor_graph views agree on burst profile when enforcement is correct."""
    line_item, vendor_graph = _paired_attribution(CFG_BURST)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(line_item)
    _assert_zero_drift(vendor_graph)


def test_relay_schedule_parity():
    """Alternate seed keeps line_item and vendor_graph attribution aligned."""
    line_item, vendor_graph = _paired_attribution(CFG_RELAY)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)


def test_warm_continuation_matches_cold_burst():
    """Warm checkpoint continuation across a prefix window matches one cold burst audit."""
    ckpt = TMP / "warm_prefix.ckpt"
    _run_prefix_checkpoint(2, ckpt)
    cold = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    warm_cfg = _load_cfg(
        CFG_BURST,
        view_mode="vendor_graph",
        warm_checkpoint=str(ckpt),
    )
    warm = _run(warm_cfg, OUT)
    assert warm["lines"] == cold["lines"]
    assert warm["ticks"] == cold["ticks"]
    assert warm["summary"] == cold["summary"]


def test_row_tally_consistency():
    """Summary tallies match row-level accepted, rejected, and ghost counts."""
    report = _run(CFG_STEADY, OUT)
    _assert_summary_consistency(report)


def test_single_width_geometry():
    """Single-stage vendor_graph geometry stays within vendor caps."""
    line_item, vendor_graph = _paired_attribution(CFG_SOLO)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)


def test_mixed_fleet_manifest():
    """South panel manifest enforces caps under vendor_graph view."""
    line_item, vendor_graph = _paired_attribution(CFG_MIXED)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)
    rows = _line_map(vendor_graph)
    assert rows["s003"]["status"] == "rejected"


def test_delay_ticks_profile():
    """Extended period window preserves parity and zero drift."""
    line_item, vendor_graph = _paired_attribution(CFG_DELAY)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)


def test_beta_fleet_crosscheck():
    """North manifest ids are complete and period-zero triple rejects the third stage."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    assert set(_line_map(report)) == set(NORTH_MANIFEST)
    _assert_triple_rejection(report, TICK0_TRIPLE)


def _run_failover_continuous_pair(cfg: Path = CFG_FAILOVER) -> tuple[dict, dict]:
    continuous = _load_cfg(cfg, run_mode="", view_mode="vendor_graph")
    failover = _load_cfg(cfg, view_mode="vendor_graph")
    return _run(continuous, OUT), _run(failover, OUT)


def _assert_tick_snaps_within_ceiling_for_tick(report: dict, period_index: int) -> None:
    ceilings = _ceiling_map(report)
    tick_row = report["ticks"][period_index]
    for snap in tick_row["vendor_snaps"]:
        total = snap["committed_pts"] + snap["pending_pts"]
        assert total <= ceilings[snap["vendor_id"]]


def test_period_failover_matches_continuous_vendor_graph():
    """Period failover replay path reproduces the uninterrupted vendor_graph audit."""
    continuous, failover = _run_failover_continuous_pair()
    _assert_zero_drift(continuous)
    _assert_zero_drift(failover)
    assert continuous["lines"] == failover["lines"]
    assert continuous["ticks"] == failover["ticks"]
    _assert_summary_equal(continuous, failover)


def test_failover_restore_replay_counters_exercised():
    """Failover profile applies restore and replays staged periods before continuing."""
    report = _run(_load_cfg(CFG_FAILOVER, view_mode="vendor_graph"), OUT)
    summ = report["summary"]
    assert summ["restore_applied_count"] == 1
    assert summ["replay_scheduled_count"] >= 1
    assert summ["replay_periods_count"] >= 1
    assert summ["replay_periods_count"] <= summ["replay_scheduled_count"]
    _assert_zero_drift(report)


def test_failover_audit_matches_burst_vendor_graph():
    """Failover north burst geometry matches the primary burst vendor_graph audit."""
    burst = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    failover = _run(_load_cfg(CFG_FAILOVER, view_mode="vendor_graph"), OUT)
    assert burst["lines"] == failover["lines"]
    assert burst["summary"]["vendor_fingerprint"] == failover["summary"]["vendor_fingerprint"]
    _assert_zero_drift(burst)


def test_burst_accepted_bind_slot_map_exact():
    """North burst accepted invoices keep monotonic bind slots without leaking slot maps."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    _assert_bind_slot_sequence(report)
    _assert_bind_slot_apply_order(report)
    rows = _line_map(report)
    rejected = {jid for jid, row in rows.items() if row["status"] == "rejected"}
    assert rejected == NORTH_BURST_REJECTED
    assert report["summary"]["accepted_count"] + report["summary"]["rejected_count"] == len(
        NORTH_MANIFEST
    )


def test_burst_committed_trajectory_periods_zero_through_three():
    """North burst committed weight stays within caps and monotonic through period three."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    _assert_committed_pts_monotonic(report)
    for period_index in range(4):
        _assert_tick_snaps_within_ceiling_for_tick(report, period_index)


def test_south_manifest_complete():
    """Mixed panel run includes every south invoice id once."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    assert set(_line_map(report)) == set(SOUTH_MANIFEST)


def test_vendor_fingerprint_recomputed():
    """Summary vendor_fingerprint matches the documented SHA-256 pair digest."""
    for cfg in (CFG_BURST, CFG_RELAY, CFG_MIXED):
        report = _run(_load_cfg(cfg, view_mode="vendor_graph"), OUT)
        assert report["summary"]["vendor_fingerprint"] == _recompute_vendor_fingerprint(report)


def test_tick_snapshot_hash_chain():
    """Each period stage_digest matches recomputed account snapshot triples."""
    report = _run(_load_cfg(CFG_RELAY, view_mode="vendor_graph"), OUT)
    for tick_row in report["ticks"]:
        assert tick_row["stage_digest"] == _recompute_tick_digest(tick_row)


def test_relay_view_parity():
    """Relay profile keeps per-period stage_digest and vendor_snaps aligned across modes."""
    line_item, vendor_graph = _paired_attribution(CFG_RELAY)
    _assert_tick_snapshots_equal(line_item, vendor_graph)


def test_beta_tote_tick1_rejection():
    """North period-one triple rejects the third vendor-beta stage under vendor_graph attribution."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(report)
    _assert_triple_rejection(report, TICK1_TRIPLE)


def test_gamma_pallet_tick1_rejection():
    """South period-one triple rejects the third gamma-pallet stage under vendor_graph attribution."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(report)
    _assert_triple_rejection(report, SOUTH_TICK1_TRIPLE)


def test_deferred_boundary_off_schedule_parity():
    """Burst profile with deferred_rollout disabled still matches line_item and vendor_graph modes."""
    line_item, vendor_graph = _paired_attribution(CFG_BURST, flags={"deferred_rollout": False})
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)


def test_bind_slot_apply_order_monotonic():
    """Accepted bind_slot values increase in documented apply order."""
    report = _run(_load_cfg(CFG_CROSS_TICK, view_mode="vendor_graph"), OUT)
    _assert_bind_slot_apply_order(report)


def test_tick_rows_within_ceiling():
    """Period snapshots never exceed vendor caps on bundled vendor_graph profiles."""
    for cfg in (CFG_BURST, CFG_RELAY, CFG_MIXED, CFG_SOUTH_RELAY, CFG_CROSS_TICK):
        report = _run(_load_cfg(cfg, view_mode="vendor_graph"), OUT)
        _assert_tick_snaps_within_ceiling(report)


def test_delay_width_filter_geometry():
    """Reduced stage_width excludes high-stage lines while preserving schedule parity."""
    line_item, vendor_graph = _paired_attribution(CFG_DELAY)
    rows = _line_map(vendor_graph)
    assert "u003" not in rows
    assert rows["u002"]["status"] == "accepted"
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)


def test_south_relay_schedule_parity():
    """Alternate south seed keeps line_item and vendor_graph attribution aligned."""
    line_item, vendor_graph = _paired_attribution(CFG_SOUTH_RELAY)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)
    assert set(_line_map(vendor_graph)) == set(SOUTH_MANIFEST)


def test_cross_tick_schedule_parity():
    """Short north window rejects both period-zero and period-one triples with mode parity."""
    line_item, vendor_graph = _paired_attribution(CFG_CROSS_TICK)
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)
    _assert_triple_rejection(vendor_graph, TICK0_TRIPLE)
    _assert_triple_rejection(vendor_graph, TICK1_TRIPLE)


def test_matrix_all_bundled_configs_parity():
    """Every operations.md profile keeps full line_item/vendor_graph parity with zero drift."""
    for cfg in ALL_PROFILES:
        line_item, vendor_graph = _paired_attribution(cfg)
        _assert_full_schedule_parity(line_item, vendor_graph)
        _assert_zero_drift(line_item)
        _assert_zero_drift(vendor_graph)


def test_matrix_vendor_graph_invariants_all_configs():
    """Cohort runs across the full profile matrix satisfy digest, tally, and cap rules."""
    for cfg in ALL_PROFILES:
        variant = _load_cfg(cfg, view_mode="vendor_graph")
        report = _run(variant, OUT)
        _assert_vendor_graph_invariants(report, variant)


def test_vendor_graph_period_end_pending_pts_zero():
    """Cohort deferred runs clear pending_pts on every completed period tick snapshot."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    for tick_row in report["ticks"]:
        for snap in tick_row["vendor_snaps"]:
            assert snap["pending_pts"] == 0


def test_south_tick0_triple_rejection():
    """South period-zero triple rejects the third vendor-delta stage under vendor_graph attribution."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(report)
    _assert_triple_rejection(report, SOUTH_TICK0_TRIPLE)


def test_acme_tick0_accept_pair_reject_third():
    """North period-zero keeps two 400-cent accepts and rejects the third 400-cent line."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    rows = _line_map(report)
    assert rows["u001"]["weight_pts"] == 400 and rows["u001"]["phantom_pts"] == 0
    assert rows["u002"]["weight_pts"] == 400 and rows["u002"]["phantom_pts"] == 0
    assert rows["u003"]["status"] == "rejected"
    assert rows["u003"]["phantom_pts"] == 0


def test_line_item_burst_isolated_control():
    """Dashboard-only burst run stays clean without relying on vendor_graph mode in the profile file."""
    report = _run(_load_cfg(CFG_BURST, view_mode="line_item"), OUT)
    _assert_zero_drift(report)
    _assert_triple_rejection(report, TICK0_TRIPLE)
    assert set(_line_map(report)) == set(NORTH_MANIFEST)


def test_cross_fleet_north_south_zero_drift():
    """North burst and south mixed vendor_graph runs both keep ghost tallies at zero."""
    north = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    south = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(north)
    _assert_zero_drift(south)
    assert set(_line_map(north)) == set(NORTH_MANIFEST)
    assert set(_line_map(south)) == set(SOUTH_MANIFEST)


def test_bind_slots_match_apply_order_all_configs():
    """Accepted bind_slot ordering holds on every bundled vendor_graph profile."""
    for cfg in ALL_PROFILES:
        report = _run(_load_cfg(cfg, view_mode="vendor_graph"), OUT)
        _assert_bind_slot_apply_order(report)


def test_south_relay_tick0_triple_rejection():
    """South relay seed rejects the period-zero triple on the south fleet."""
    report = _run(_load_cfg(CFG_SOUTH_RELAY, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(report)
    _assert_triple_rejection(report, SOUTH_TICK0_TRIPLE)


def test_committed_pts_monotonic_burst_vendor_graph():
    """North burst vendor_graph snapshots keep non-decreasing committed_pts per vendor across periods."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    _assert_committed_pts_monotonic(report)
    acme = _vendor_snap_at(report, 0, "vendor-acme")
    assert acme["committed_pts"] == 800
    assert acme["pending_pts"] == 0


def test_period_tick_hash_varies_on_burst():
    """Period tick hashes differ across periods that carry invoice activity on burst vendor_graph runs."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    digests = [row["stage_digest"] for row in report["ticks"][:4]]
    assert len(set(digests)) > 1


def test_seed_metamorphic_fingerprint_differs():
    """Short max_period windows change fingerprints while keeping zero ghost tallies."""
    full = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    short = _run(_load_cfg(CFG_CROSS_TICK, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(full)
    _assert_zero_drift(short)
    assert _fingerprint(full) != _fingerprint(short)
    line_item, vendor_graph = _paired_attribution(CFG_CROSS_TICK)
    _assert_full_schedule_parity(line_item, vendor_graph)


def test_cross_tick_manifest_truncation():
    """Short max_period window includes only manifest invoices through the configured period."""
    report = _run(_load_cfg(CFG_CROSS_TICK, view_mode="vendor_graph"), OUT)
    expected = _manifest_invoices_up_to_period("north", 2)
    assert set(_line_map(report)) == expected
    assert report["summary"]["rejected_count"] == 2


def test_solo_stage_width_one_geometry():
    """Single-stage width keeps only stage-zero invoices and drops higher-stage rows."""
    report = _run(_load_cfg(CFG_SOLO, view_mode="vendor_graph"), OUT)
    rows = set(_line_map(report))
    assert rows == SOLO_STAGE0_JOURNEYS
    assert "u002" not in rows and "u003" not in rows
    _assert_zero_drift(report)


def test_triple_flag_disable_combo_parity():
    """Burst with all rollout flags disabled still matches line_item and vendor_graph rows."""
    line_item, vendor_graph = _paired_attribution(
        CFG_BURST,
        flags={
            "deferred_rollout": False,
            "strict_stage_sort": False,
            "track_exposure": False,
        },
    )
    _assert_full_schedule_parity(line_item, vendor_graph)
    _assert_zero_drift(vendor_graph)


def test_south_relay_matches_mixed_fingerprint():
    """South relay and mixed south profiles share geometry and produce identical vendor_graph fingerprints."""
    relay = _run(_load_cfg(CFG_SOUTH_RELAY, view_mode="vendor_graph"), OUT)
    mixed = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    _assert_zero_drift(relay)
    _assert_zero_drift(mixed)
    assert _fingerprint(relay) == _fingerprint(mixed)
    assert set(_line_map(relay)) == set(_line_map(mixed)) == set(SOUTH_MANIFEST)


def test_burst_exact_rejection_tally():
    """North burst vendor_graph run rejects the documented nine-invoice id set with zero ghost tallies."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    rejected = {r["invoice_id"] for r in report["lines"] if r["status"] == "rejected"}
    assert rejected == NORTH_BURST_REJECTED
    assert report["summary"]["accepted_count"] == len(NORTH_MANIFEST) - len(NORTH_BURST_REJECTED)
    assert report["summary"]["rejected_count"] == len(NORTH_BURST_REJECTED)
    accepted_weight = sum(r["weight_pts"] for r in report["lines"] if r["status"] == "accepted")
    assert accepted_weight == 1500


def test_period_zero_acme_weight_accounting():
    """Period-zero vendor-acme accepted weight points sum to 800 with zero ghost points."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    rows = [r for r in report["lines"] if r["vendor_id"] == "vendor-acme" and r["period"] == 0]
    accepted = [r for r in rows if r["status"] == "accepted"]
    assert sum(r["weight_pts"] for r in accepted) == 800
    assert all(r["phantom_pts"] == 0 for r in accepted)
    assert len(accepted) == 2


def test_sequential_vendor_graph_runs_isolated():
    """Back-to-back burst and steady vendor_graph runs do not cross-contaminate manifests or tallies."""
    burst = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    steady = _run(_load_cfg(CFG_STEADY, view_mode="line_item"), OUT)
    _assert_zero_drift(burst)
    _assert_zero_drift(steady)
    assert set(_line_map(burst)) == set(NORTH_MANIFEST)
    assert _line_map(steady)["u003"]["status"] == "rejected"


def test_warm_checkpoint_lines_prefix_preserved():
    """Warm continuation preserves prefix invoice rows from the checkpoint ledger verbatim."""
    ckpt = TMP / "lines_prefix.ckpt"
    prefix = _run_prefix_checkpoint(1, ckpt)
    warm = _run(
        _load_cfg(CFG_BURST, view_mode="vendor_graph", warm_checkpoint=str(ckpt)),
        OUT,
    )
    prefix_ids = {row["invoice_id"] for row in prefix["lines"]}
    for row in warm["lines"]:
        if row["invoice_id"] in prefix_ids:
            assert row == _line_map(prefix)[row["invoice_id"]]


def test_checkpoint_state_digest_matches_committed_map():
    """Prefix ledger state_digest recomputes from sorted vendor:committed_pts pairs."""
    ckpt = TMP / "digest_integrity.ckpt"
    prefix = _run_prefix_checkpoint(2, ckpt)
    payload = _assert_checkpoint_integrity(ckpt, prefix)
    assert payload["last_period_index"] == 2
    _assert_committed_trajectory_table(prefix, NORTH_BURST_COMMITTED_BY_PERIOD[:3])


def test_checkpoint_ticks_and_rejected_tally_match_prefix_audit():
    """Warm ledger ticks and rejected_count mirror the prefix burst audit through the boundary."""
    ckpt = TMP / "ticks_tally.ckpt"
    prefix = _run_prefix_checkpoint(3, ckpt)
    payload = _assert_checkpoint_integrity(ckpt, prefix)
    assert payload["ticks"] == prefix["ticks"]
    assert payload["rejected_count"] == prefix["summary"]["rejected_count"]


def test_vendor_beta_committed_after_period_one_is_four_hundred():
    """North burst vendor-beta committed_pts is 400 after period one with zero pending."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    beta = _vendor_snap_at(report, 1, "vendor-beta")
    assert beta["committed_pts"] == 400
    assert beta["pending_pts"] == 0
    assert _period_accepted_weight(report, 1, "vendor-beta") == 400


def test_vendor_delta_period_zero_committed_six_hundred():
    """South mixed period-zero vendor-delta committed_pts is 600 after the triple rejection."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    delta = _vendor_snap_at(report, 0, "vendor-delta")
    assert delta["committed_pts"] == 600
    assert delta["pending_pts"] == 0
    _assert_triple_rejection(report, SOUTH_TICK0_TRIPLE)


def test_gamma_pallet_period_one_committed_three_hundred():
    """South mixed period-one gamma-pallet committed_pts is 300 with the third stage rejected."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    gamma = _vendor_snap_at(report, 1, "gamma-pallet")
    assert gamma["committed_pts"] == 300
    assert gamma["pending_pts"] == 0
    _assert_triple_rejection(report, SOUTH_TICK1_TRIPLE)


def test_burst_north_committed_trajectory_period_table():
    """North burst vendor_graph committed_pts follows the documented eight-period trajectory."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    _assert_committed_trajectory_table(report, NORTH_BURST_COMMITTED_BY_PERIOD)
    acme = _vendor_snap_at(report, 4, "vendor-acme")
    assert acme["committed_pts"] == 1000


def test_south_mixed_committed_trajectory_period_table():
    """South mixed vendor_graph committed_pts follows the documented four-period trajectory."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    _assert_committed_trajectory_table(report, SOUTH_MIXED_COMMITTED_BY_PERIOD)


def test_period_intra_accepted_weight_within_vendor_caps():
    """Per-period accepted weight never exceeds any vendor cap on burst and mixed panels."""
    for cfg in (CFG_BURST, CFG_MIXED, CFG_RELAY, CFG_SOUTH_RELAY):
        report = _run(_load_cfg(cfg, view_mode="vendor_graph"), OUT)
        _assert_period_accepted_weight_within_caps(report)
        _assert_zero_drift(report)


def test_pending_exposure_never_exceeds_remaining_cap():
    """Every period snapshot keeps pending_pts within the vendor cap minus committed_pts."""
    for cfg in ALL_PROFILES:
        report = _run(_load_cfg(cfg, view_mode="vendor_graph"), OUT)
        _assert_pending_within_remaining_cap(report)


def test_warm_prefix_stage_digests_match_cold_burst_prefix():
    """Warm checkpoint ticks through the prefix window match cold burst ticks at the same indices."""
    ckpt = TMP / "digest_prefix.ckpt"
    prefix = _run_prefix_checkpoint(3, ckpt)
    cold = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    warm = _run(
        _load_cfg(CFG_BURST, view_mode="vendor_graph", warm_checkpoint=str(ckpt)),
        OUT,
    )
    for period_index in range(prefix["max_period"] + 1):
        assert warm["ticks"][period_index] == cold["ticks"][period_index]
    assert warm["ticks"][:4] == cold["ticks"][:4]


def test_north_burst_triple_period_rejections_are_stage_two():
    """North burst period-zero and period-one rejections are the third triple stage with no bind slot."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    rows = _line_map(report)
    for period, invoice_id in NORTH_TRIPLE_PERIOD_REJECTED.items():
        row = rows[invoice_id]
        assert row["period"] == period
        assert row["stage"] == rows[TICK0_TRIPLE[2]]["stage"]
        assert row["status"] == "rejected"
        assert row["bind_slot"] == -1
        assert row["phantom_pts"] == 0


def test_south_mixed_accepted_weight_total_eleven_twenty():
    """South mixed vendor_graph accepted invoice weight sums to 1120 with three documented rejections."""
    report = _run(_load_cfg(CFG_MIXED, view_mode="vendor_graph"), OUT)
    rejected = {r["invoice_id"] for r in report["lines"] if r["status"] == "rejected"}
    assert rejected == SOUTH_MIXED_REJECTED
    accepted_weight = sum(r["weight_pts"] for r in report["lines"] if r["status"] == "accepted")
    assert accepted_weight == 1120
    assert report["summary"]["accepted_count"] == 7


def test_acme_cap_saturation_rejection_periods_four_through_seven():
    """North burst rejects late-period vendor-acme rows once committed_pts reaches the 1000 cap."""
    report = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    rows = _line_map(report)
    assert rows["u011"]["status"] == "accepted"
    assert rows["u012"]["status"] == "rejected"
    assert rows["u015"]["status"] == "rejected"
    assert rows["u017"]["status"] == "rejected"
    _assert_committed_trajectory_table(report, NORTH_BURST_COMMITTED_BY_PERIOD)


def test_matrix_vendor_graph_pending_cleared_all_profiles():
    """Every bundled vendor_graph profile clears pending_pts on all completed period ticks."""
    for cfg in ALL_PROFILES:
        report = _run(_load_cfg(cfg, view_mode="vendor_graph"), OUT)
        for tick_row in report["ticks"]:
            for snap in tick_row["vendor_snaps"]:
                assert snap["pending_pts"] == 0, f"{cfg.name} period {tick_row['period_index']}"


def test_prefix_checkpoint_lines_are_sorted_and_echo_prefix_audit():
    """Checkpoint ledger lines stay sorted by invoice_id and match the prefix audit row map."""
    ckpt = TMP / "lines_sorted.ckpt"
    prefix = _run_prefix_checkpoint(2, ckpt)
    payload = _assert_checkpoint_integrity(ckpt, prefix)
    invoice_ids = [row["invoice_id"] for row in payload["lines"]]
    assert invoice_ids == sorted(invoice_ids)
    for row in payload["lines"]:
        assert row == _line_map(prefix)[row["invoice_id"]]


def test_failover_replay_counters_match_scheduled_window():
    """Failover replay_periods_count equals replay_scheduled_count on a correct run."""
    report = _run(_load_cfg(CFG_FAILOVER, view_mode="vendor_graph"), OUT)
    summ = report["summary"]
    assert summ["restore_applied_count"] == 1
    assert summ["replay_scheduled_count"] >= 1
    assert summ["replay_periods_count"] >= 1
    assert summ["replay_periods_count"] == summ["replay_scheduled_count"]
    _assert_zero_drift(report)


def test_warm_checkpoint_fingerprint_matches_cold_through_period_three():
    """Warm continuation through period three matches cold burst vendor_fingerprint and stage digests."""
    ckpt = TMP / "warm_fp_p3.ckpt"
    _run_prefix_checkpoint(3, ckpt)
    cold = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    warm = _run(
        _load_cfg(CFG_BURST, view_mode="vendor_graph", warm_checkpoint=str(ckpt)),
        OUT,
    )
    assert _fingerprint(warm) == _fingerprint(cold)
    for period_index in range(4):
        assert warm["ticks"][period_index] == cold["ticks"][period_index]


def test_failover_and_burst_share_post_restore_vendor_trajectory():
    """Period-4 failover matches burst committed_pts from period four onward."""
    burst = _run(_load_cfg(CFG_BURST, view_mode="vendor_graph"), OUT)
    failover = _run(_load_cfg(CFG_FAILOVER, view_mode="vendor_graph"), OUT)
    for period_index in range(4, 8):
        assert _trajectory_at(burst, period_index) == _trajectory_at(failover, period_index)
