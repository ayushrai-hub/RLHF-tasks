"""Verifier for path failback report with replay, routing, and recovery invariants."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

REPORT_PATH = Path("/app/output/path_failback_report.json")
SCENARIOS_DIR = Path("/app/environment/data/scenarios")
JOURNAL_DIR = Path("/app/var/failback_journal")
FLAG_DIR = Path("/app/environment/config/failback_flags")
EXPECTED_LABELS = {"s01", "s02", "s03", "s04", "s05", "s06"}


def _sha256_prefix(payload: str, nbytes: int) -> str:
    proc = subprocess.run(
        ["sha256sum"],
        input=payload,
        capture_output=True,
        check=True,
        text=True,
    )
    return proc.stdout.split()[0][: nbytes * 2]


def _spread_index(dataplane: int, affinity: int) -> int:
    return (dataplane & affinity).bit_count()


def _is_subset(affinity: int, dataplane: int) -> bool:
    return (affinity & ~dataplane) == 0


def _mask_hex(mask: int) -> str:
    return format(mask, "x") if mask else "0"


def _load_flush_bump_default() -> int:
    best_depth = 0
    best_order = -1
    if not FLAG_DIR.is_dir():
        return 0
    for path in sorted(FLAG_DIR.glob("*.toml")):
        text = path.read_text(encoding="utf-8")
        order_m = re.search(r"registration_order\s*=\s*(\d+)", text)
        depth_m = re.search(r"completion_depth\s*=\s*(\d+)", text)
        order = int(order_m.group(1)) if order_m else 0
        depth = int(depth_m.group(1)) if depth_m else 0
        if order > best_order:
            best_order = order
            best_depth = depth
    return best_depth


def _load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _segment_kinds(spec: dict[str, Any]) -> list[str]:
    if spec.get("crash_mid"):
        return ["affinity", "dataplane"]
    return ["dataplane"]


def _segment_seq_crc(spec: dict[str, Any]) -> str:
    return _sha256_prefix(",".join(_segment_kinds(spec)), 4)


def _session_token_hex(table_gen: int, dp_hex: str, aff_hex: str) -> str:
    return _sha256_prefix(f"{table_gen}|{dp_hex}|{aff_hex}", 4)


def _digest_hex(
    dp_hex: str,
    aff_hex: str,
    spread: int,
    retransmit: int,
    table_gen: int,
    replay_epoch: int,
    segment_seq_crc: str,
    session_token_hex: str,
) -> str:
    payload = (
        f"{dp_hex}|{aff_hex}|{spread}|{retransmit}|{table_gen}|"
        f"{replay_epoch}|{segment_seq_crc}|{session_token_hex}"
    )
    return _sha256_prefix(payload, 8)


def _retain_stage(stranded: int, dataplane: int, retain_seq: int) -> int:
    if retain_seq <= 0:
        return stranded & dataplane
    shift = retain_seq % 8
    return (stranded >> shift) & dataplane


def _simulate_row(spec: dict[str, Any]) -> dict[str, Any]:
    flush_bump = int(spec.get("flush_bump") or 0) or _load_flush_bump_default()

    dataplane = int(spec["target_path_mask"]) or int(spec["active_path_mask"])
    stranded = int(spec["stranded_path_mask"])
    pre_affinity = stranded & dataplane
    pre_spread = _spread_index(dataplane, pre_affinity)

    replay_epoch = 2 if spec.get("crash_mid") else 0
    retained_affinity = _retain_stage(stranded, dataplane, int(spec.get("retain_seq") or 0))
    post_spread = _spread_index(dataplane, retained_affinity)

    snap_spread = pre_spread if spec.get("failback_early") else post_spread
    even_looking = bool(spec.get("summary_green_view")) or (snap_spread > 0 and snap_spread % 4 == 0)
    filter_hit = bool(spec.get("failback_early")) and (
        even_looking or (snap_spread > 0 and snap_spread % 2 == 0)
    )

    route_dp = int(spec["target_path_mask"]) or int(spec["active_path_mask"])
    routed_affinity = stranded if filter_hit else (stranded & route_dp)

    queue_mask = retained_affinity
    queue_mask &= dataplane
    final_affinity = routed_affinity & queue_mask

    spread_idx = _spread_index(dataplane, final_affinity)
    penalty_spread = pre_spread if spec.get("failback_early") else spread_idx

    retransmit = int(spec["alua_base_ms"])
    if not _is_subset(final_affinity, dataplane):
        retransmit += flush_bump * 7
    if penalty_spread == 0 and spec.get("summary_green_view"):
        retransmit += flush_bump * 3

    dp_hex = _mask_hex(dataplane)
    aff_hex = _mask_hex(final_affinity)
    seq_crc = _segment_seq_crc(spec)
    token = _session_token_hex(int(spec["table_gen"]), dp_hex, aff_hex)

    return {
        "scenario_label": spec["scenario_label"],
        "path_overlap_index": spread_idx,
        "active_path_hex": dp_hex,
        "standby_path_hex": aff_hex,
        "alua_reprobe_ms": retransmit,
        "replay_epoch": replay_epoch,
        "segment_seq_crc": seq_crc,
        "session_token_hex": token,
        "digest_hex": _digest_hex(
            dp_hex,
            aff_hex,
            spread_idx,
            retransmit,
            int(spec["table_gen"]),
            replay_epoch,
            seq_crc,
            token,
        ),
    }


def _rebuild_sweep() -> None:
    subprocess.run(
        [
            "/usr/bin/go",
            "build",
            "-C",
            "/app/environment",
            "-o",
            "/app/bin/pathfb-sweep",
            "/app/environment/cmd/pathfb_sweep",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _run_sweep(scenarios_dir: Path) -> dict[str, Any]:
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()
    _rebuild_sweep()
    subprocess.run(
        [
            "/app/bin/pathfb-sweep",
            "--scenarios-dir",
            str(scenarios_dir),
            "--out",
            str(REPORT_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _rows_by_label(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["scenario_label"]: row for row in report["runs"]}


def _base_specs() -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        spec = _load_scenario(path)
        specs[spec["scenario_label"]] = spec
    return specs


def _write_spec(path: Path, spec: dict[str, Any]) -> None:
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def _scenario_dir_with_injected(extra: dict[str, Any], *, shuffle_names: bool = False) -> Path:
    tmp = Path(tempfile.mkdtemp())
    for idx, src in enumerate(sorted(SCENARIOS_DIR.glob("*.json"))):
        dst_name = src.name
        if shuffle_names:
            dst_name = f"z{idx:02d}_{src.name}"
        shutil.copy2(src, tmp / dst_name)
    out_name = "s07.json" if not shuffle_names else "a00_s07.json"
    _write_spec(tmp / out_name, extra)
    return tmp


def _assert_row_matches(row: dict[str, Any], spec: dict[str, Any]) -> None:
    expected = _simulate_row(spec)
    for key in (
        "path_overlap_index",
        "active_path_hex",
        "standby_path_hex",
        "alua_reprobe_ms",
        "replay_epoch",
        "segment_seq_crc",
        "session_token_hex",
        "digest_hex",
    ):
        assert row[key] == expected[key], f"{spec['scenario_label']} {key}"


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return _run_sweep(SCENARIOS_DIR)


@pytest.fixture(scope="module")
def base_specs() -> dict[str, dict[str, Any]]:
    return _base_specs()


def _s07_spec() -> dict[str, Any]:
    return {
        "scenario_label": "s07",
        "table_gen": 15,
        "crash_mid": True,
        "active_path_mask": 0,
        "target_path_mask": 29,
        "stranded_path_mask": 96,
        "alua_base_ms": 14,
        "flush_bump": 0,
        "failback_early": True,
        "summary_green_view": True,
        "retain_seq": 6,
        "gate_hold": True,
    }


def test_pf01_six_scenario_envelope(report: dict[str, Any]) -> None:
    """Base sweep returns exactly bundled scenario labels once."""
    labels = [row["scenario_label"] for row in report["runs"]]
    assert labels == sorted(EXPECTED_LABELS)


def test_pf02_stage_pipeline_match(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Each bundled row matches independent stage simulation."""
    for label in sorted(EXPECTED_LABELS):
        _assert_row_matches(_rows_by_label(report)[label], base_specs[label])


def test_pf03_crash_fragment_epoch(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Crash-mid scenarios replay both fragment kinds and report epoch two."""
    for label in ("s02", "s04"):
        row = _rows_by_label(report)[label]
        expected = _simulate_row(base_specs[label])
        assert row["replay_epoch"] == expected["replay_epoch"] == 2


def test_pf04_retain_partial_overlap(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Retain-sequence transform still preserves subset overlap contract."""
    _assert_row_matches(_rows_by_label(report)["s06"], base_specs["s06"])


def test_pf05_gate_hold_live_spread(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Gate-hold scenarios compute live overlap from final routed masks."""
    _assert_row_matches(_rows_by_label(report)["s05"], base_specs["s05"])


def test_pf06_failback_early_penalty_spread(base_specs: dict[str, dict[str, Any]]) -> None:
    """Injected scenario verifies failback_early penalty spread semantics."""
    injected = _s07_spec()
    scenarios_dir = _scenario_dir_with_injected(injected)
    try:
        rep = _run_sweep(scenarios_dir)
    finally:
        shutil.rmtree(scenarios_dir, ignore_errors=True)
    row = _rows_by_label(rep)["s07"]
    expected = _simulate_row(injected)
    assert row["alua_reprobe_ms"] == expected["alua_reprobe_ms"]
    assert row["path_overlap_index"] == expected["path_overlap_index"]


def test_pf07_triple_sweep_stable() -> None:
    """Three consecutive sweeps must produce identical digest rows."""
    reports = [_run_sweep(SCENARIOS_DIR), _run_sweep(SCENARIOS_DIR), _run_sweep(SCENARIOS_DIR)]
    for label in EXPECTED_LABELS:
        digests = [_rows_by_label(rep)[label]["digest_hex"] for rep in reports]
        assert digests[0] == digests[1] == digests[2]


def test_pf08_segment_crc_crash_kinds(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Crash-mid rows share the same segment-kind CRC fingerprint."""
    expected = _segment_seq_crc(base_specs["s02"])
    assert expected == _segment_seq_crc(base_specs["s04"])
    assert _rows_by_label(report)["s02"]["segment_seq_crc"] == expected
    assert _rows_by_label(report)["s04"]["segment_seq_crc"] == expected


def test_pf09_changed_input_order_invariant(base_specs: dict[str, dict[str, Any]]) -> None:
    """Shuffled fixture filenames cannot change per-label row semantics."""
    injected = _s07_spec()
    scenarios_dir = _scenario_dir_with_injected(injected, shuffle_names=True)
    try:
        rep = _run_sweep(scenarios_dir)
    finally:
        shutil.rmtree(scenarios_dir, ignore_errors=True)
    rows = _rows_by_label(rep)
    for label, spec in {**base_specs, "s07": injected}.items():
        _assert_row_matches(rows[label], spec)


def test_pf10_session_token_distinct(report: dict[str, Any]) -> None:
    """Session tokens should vary across materially different rows."""
    tokens = {label: _rows_by_label(report)[label]["session_token_hex"] for label in EXPECTED_LABELS}
    assert len(set(tokens.values())) >= 4


def test_pf11_cross_pack_subset_invariant(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Each row keeps standby subset and overlap consistency together."""
    for label in sorted(EXPECTED_LABELS):
        row = _rows_by_label(report)[label]
        expected = _simulate_row(base_specs[label])
        assert _is_subset(int(row["standby_path_hex"], 16), int(row["active_path_hex"], 16))
        assert row["path_overlap_index"] == expected["path_overlap_index"]


def test_pf12_crash_mid_target_path_mask(report: dict[str, Any], base_specs: dict[str, dict[str, Any]]) -> None:
    """Crash-mid path mask converges to target dataplane mask semantics."""
    _assert_row_matches(_rows_by_label(report)["s04"], base_specs["s04"])


def test_pf13_stale_tail_ignored() -> None:
    """Injected stale tail must not affect crash-mid replay epoch or digest."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    tail_path = JOURNAL_DIR / "s02.tail"
    tail_path.write_text(json.dumps({"replay_epoch": 99}), encoding="utf-8")
    try:
        rep = _run_sweep(SCENARIOS_DIR)
        row = _rows_by_label(rep)["s02"]
        expected = _simulate_row(_base_specs()["s02"])
        assert row["replay_epoch"] == expected["replay_epoch"]
        assert row["digest_hex"] == expected["digest_hex"]
    finally:
        tail_path.unlink(missing_ok=True)


def test_pf14_rebuild_idempotent_after_source_touch() -> None:
    """Rebuild-and-rerun stays idempotent when sources are unchanged."""
    first = _run_sweep(SCENARIOS_DIR)
    digest_a = {row["scenario_label"]: row["digest_hex"] for row in first["runs"]}
    second = _run_sweep(SCENARIOS_DIR)
    digest_b = {row["scenario_label"]: row["digest_hex"] for row in second["runs"]}
    assert digest_a == digest_b


def test_pf15_flush_bump_from_flag_registration() -> None:
    """Zero flush_bump uses highest registration_order completion depth."""
    injected = _s07_spec()
    scenarios_dir = _scenario_dir_with_injected(injected)
    try:
        rep = _run_sweep(scenarios_dir)
    finally:
        shutil.rmtree(scenarios_dir, ignore_errors=True)
    expected_bump = _load_flush_bump_default()
    assert expected_bump > 0
    row = _rows_by_label(rep)["s07"]
    expected = _simulate_row(injected)
    assert row["alua_reprobe_ms"] == expected["alua_reprobe_ms"]


def test_pf16_digest_recompute_consistency(report: dict[str, Any]) -> None:
    """Every emitted digest must recompute from published row fields."""
    for row in report["runs"]:
        recomputed = _digest_hex(
            row["active_path_hex"],
            row["standby_path_hex"],
            int(row["path_overlap_index"]),
            int(row["alua_reprobe_ms"]),
            int(_base_specs()[row["scenario_label"]]["table_gen"]),
            int(row["replay_epoch"]),
            row["segment_seq_crc"],
            row["session_token_hex"],
        )
        assert row["digest_hex"] == recomputed
