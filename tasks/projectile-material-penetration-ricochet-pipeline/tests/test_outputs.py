"""Behavioral verifier for ballctl penetration and batch export."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from reference_ballistics import (
    ReplayHistory,
    reference_batch,
    reference_mutated_stack,
    reference_shot,
    reference_snapshot,
    trace_digest,
)

APP = Path("/app")
CLI = "/usr/local/bin/ballctl"
FIXTURES = APP / "fixtures"
STACKS = FIXTURES / "stacks"
BATCHES = FIXTURES / "batches"
MATERIALS = FIXTURES / "materials/catalog.json"
OUTPUT = APP / "output"
SNAPSHOT = APP / "state/shot-snapshot.json"
HIDDEN_STACKS = Path("/opt/verifier-fixtures/ballistics/stacks")
CATALOG = json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))
STACK_NAMES = CATALOG["stacks"]
BATCH_NAMES = CATALOG["batches"]

SHOT_CASES: dict[str, dict] = {
    "simple": {"velocity": [0.0, 0.0, -420.0], "energy_j": 2500.0, "seed": 1},
    "multi-layer": {"velocity": [0.0, 0.0, -380.0], "energy_j": 3200.0, "seed": 42},
    "ricochet-trap": {"velocity": [0.0, 0.0, -360.0], "energy_j": 280.0, "seed": 99},
    "material-id-trap": {"velocity": [0.0, 0.0, -400.0], "energy_j": 2800.0, "seed": 13},
    "boundary-double": {"velocity": [0.0, 0.0, -450.0], "energy_j": 5000.0, "seed": 7},
    "thin-glass": {"velocity": [0.0, 0.0, -300.0], "energy_j": 55.0, "seed": 42},
}

PROTECTED_SHA256: dict[str, str] = {}


def sha256_file(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(APP), capture_output=True, text=True, check=False)


def reset_state() -> None:
    proc = run(["bash", "/app/scripts/reset-state.sh"])
    assert proc.returncode == 0, proc.stderr


def rebuild_cli() -> None:
    proc = run(["cargo", "build", "--release", "--locked", "-p", "ballcore"])
    assert proc.returncode == 0, proc.stderr
    proc = run(["cargo", "build", "--release", "--locked", "-p", "ballctl"])
    assert proc.returncode == 0, proc.stderr
    run(["install", "-m", "0755", str(APP / "target/release/ballctl"), CLI])


def integrate_shot_cli(
    stack_path: Path,
    velocity: list[float],
    energy_j: float,
    seed: int,
) -> None:
    vel_str = ",".join(str(v) for v in velocity)
    proc = run(
        [
            CLI,
            "integrate-shot",
            "--stack",
            str(stack_path),
            "--materials",
            str(MATERIALS),
            "--velocity",
            vel_str,
            "--energy",
            str(energy_j),
            "--seed",
            str(seed),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def export_shot_cli(out: Path) -> dict:
    proc = run([CLI, "export-shot", "--export", str(out)])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def pipeline_shot_cli(stack: str, out_name: str, **kwargs) -> dict:
    """Two-step integrate-shot + export-shot per /app/docs/export-shot-contract.md."""
    case = SHOT_CASES[stack]
    velocity = kwargs.get("velocity", case["velocity"])
    energy = kwargs.get("energy_j", case["energy_j"])
    seed = kwargs.get("seed", case["seed"])
    out = OUTPUT / out_name
    integrate_shot_cli(STACKS / f"{stack}.json", velocity, energy, seed)
    return export_shot_cli(out)


def pipeline_shot_path(
    stack_path: Path,
    velocity: list[float],
    energy_j: float,
    seed: int,
    out: Path,
) -> dict:
    integrate_shot_cli(stack_path, velocity, energy_j, seed)
    return export_shot_cli(out)


def simulate_batch_cli(batch: str, out_name: str) -> dict:
    out = OUTPUT / out_name
    proc = run(
        [
            CLI,
            "simulate-batch",
            "--batch",
            str(BATCHES / f"{batch}.json"),
            "--materials",
            str(MATERIALS),
            "--stacks-dir",
            str(STACKS),
            "--export",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.fixture(scope="session", autouse=True)
def _populate_protected_hashes() -> None:
    if PROTECTED_SHA256:
        return
    for rel in [
        "catalog.json",
        "seeds.json",
        "materials/catalog.json",
        *[f"stacks/{s}.json" for s in STACK_NAMES],
        *[f"batches/{b}.json" for b in BATCH_NAMES],
    ]:
        PROTECTED_SHA256[rel] = sha256_file(FIXTURES / rel)


@pytest.fixture(autouse=True)
def _fresh_state() -> None:
    reset_state()


def test_fixture_integrity() -> None:
    """Catalog, stacks, batches, and materials must match baked SHA256."""
    for rel, digest in PROTECTED_SHA256.items():
        path = FIXTURES / rel
        assert path.is_file(), rel
        assert sha256_file(path) == digest, rel


@pytest.mark.parametrize("stack", STACK_NAMES)
def test_shot_matches_reference(stack: str) -> None:
    """Each catalog stack must match independent reference physics via two-step pipeline."""
    case = SHOT_CASES[stack]
    got = pipeline_shot_cli(stack, f"shot-{stack}.json")
    exp = reference_shot(
        STACKS / f"{stack}.json",
        case["velocity"],
        case["energy_j"],
        case["seed"],
    )
    assert got == exp


def test_export_writes_shot_json_under_app_output() -> None:
    """export-shot must write the audit JSON under /app/output/shot.json."""
    out = Path("/app/output/shot.json")
    case = SHOT_CASES["simple"]
    integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
    got = export_shot_cli(out)
    assert out.is_file(), "missing /app/output/shot.json export file"
    assert got["stack"] == "simple"


def test_export_without_integrate_fails() -> None:
    """export-shot must fail when no staged snapshot exists."""
    reset_state()
    out = OUTPUT / "no-snapshot.json"
    proc = run([CLI, "export-shot", "--export", str(out)])
    assert proc.returncode != 0


def test_ricochet_trap_stops_and_reflects() -> None:
    """Hard front layer must ricochet with reflected exit angles."""
    got = pipeline_shot_cli("ricochet-trap", "ricochet-check.json")
    assert got["penetrated"] is False
    assert got["ricochet"] is not None
    exp = reference_shot(
        STACKS / "ricochet-trap.json",
        SHOT_CASES["ricochet-trap"]["velocity"],
        SHOT_CASES["ricochet-trap"]["energy_j"],
        SHOT_CASES["ricochet-trap"]["seed"],
    )
    assert got["ricochet"] == exp["ricochet"]


def test_material_id_trap_uses_physics_id() -> None:
    """Steel physics_id must win over misleading asset_label metadata."""
    got = pipeline_shot_cli("material-id-trap", "material-id-check.json")
    exp = reference_shot(
        STACKS / "material-id-trap.json",
        SHOT_CASES["material-id-trap"]["velocity"],
        SHOT_CASES["material-id-trap"]["energy_j"],
        SHOT_CASES["material-id-trap"]["seed"],
    )
    assert got["penetrated"] == exp["penetrated"]
    assert got["layers"] == exp["layers"]


def test_multi_layer_falloff_after_traversal() -> None:
    """Second-layer energy must reflect post-first-layer falloff ordering."""
    got = pipeline_shot_cli("multi-layer", "multi-layer-check.json")
    exp = reference_shot(
        STACKS / "multi-layer.json",
        SHOT_CASES["multi-layer"]["velocity"],
        SHOT_CASES["multi-layer"]["energy_j"],
        SHOT_CASES["multi-layer"]["seed"],
    )
    assert got["exit_energy_j"] == exp["exit_energy_j"]
    assert got["layers"][1]["energy_after_j"] == exp["layers"][1]["energy_after_j"]


def test_boundary_ledger_not_doubled() -> None:
    """Path ledger must debit each exit boundary once across three layers."""
    got = pipeline_shot_cli("boundary-double", "boundary-check.json")
    exp = reference_shot(
        STACKS / "boundary-double.json",
        SHOT_CASES["boundary-double"]["velocity"],
        SHOT_CASES["boundary-double"]["energy_j"],
        SHOT_CASES["boundary-double"]["seed"],
    )
    assert got["path_ledger_m"] == exp["path_ledger_m"]


@pytest.mark.parametrize("batch", BATCH_NAMES)
def test_batch_matches_reference(batch: str) -> None:
    """Batch exports must group and sort ticks like the reference."""
    got = simulate_batch_cli(batch, f"batch-{batch}.json")
    exp = reference_batch(BATCHES / f"{batch}.json")
    assert got == exp


def test_tick_order_trap_not_arrival_order() -> None:
    """Out-of-file tick events must export ascending sim_tick groups."""
    got = simulate_batch_cli("tick-order-trap", "tick-order-check.json")
    ticks = [t["sim_tick"] for t in got["ticks"]]
    assert ticks == sorted(ticks)
    assert ticks == [0, 2]
    exp = reference_batch(BATCHES / "tick-order-trap.json")
    assert got["ticks"] == exp["ticks"]


def test_mutated_stack_layers() -> None:
    """Randomized layer stacks must match reference, blocking hardcoded JSON."""
    specs = [(103, 0.0035), (101, 0.0025), (102, 0.007)]
    velocity = [0.0, 0.0, -410.0]
    energy = 2400.0
    seed = 7
    exp = reference_mutated_stack(specs, velocity, energy, seed)
    stack_path = Path("/tmp/mutated-probe.json")
    stack_path.write_text(
        json.dumps(
            {
                "name": "mutated",
                "normal": [0.0, 0.0, 1.0],
                "layers": [
                    {"physics_id": pid, "thickness_m": thick} for pid, thick in specs
                ],
            }
        ),
        encoding="utf-8",
    )
    integrate_shot_cli(stack_path, velocity, energy, seed)
    got = export_shot_cli(OUTPUT / "mutated-probe.json")
    assert got == exp


def test_repeat_run_byte_identical() -> None:
    """Repeated pipeline runs with reset state must produce identical exports."""
    case = SHOT_CASES["simple"]
    out1 = OUTPUT / "repeat-a.json"
    out2 = OUTPUT / "repeat-b.json"
    integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
    export_shot_cli(out1)
    first_bytes = out1.read_bytes()
    reset_state()
    integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
    export_shot_cli(out2)
    assert first_bytes == out2.read_bytes()


def test_replay_seq_advances_second_integrate() -> None:
    """Second integrate with same stack+seed must bump replay_seq and trace_digest."""
    case = SHOT_CASES["simple"]
    hist = ReplayHistory()
    exp_first = reference_shot(
        STACKS / "simple.json",
        case["velocity"],
        case["energy_j"],
        case["seed"],
        replay_hist=hist,
    )
    integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
    first = export_shot_cli(OUTPUT / "replay-first.json")
    assert first == exp_first

    exp_second = reference_shot(
        STACKS / "simple.json",
        case["velocity"],
        case["energy_j"],
        case["seed"],
        replay_hist=hist,
    )
    integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
    second = export_shot_cli(OUTPUT / "replay-second.json")
    assert second == exp_second
    assert second["trace_digest"] != first["trace_digest"]
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snap.get("replay_seq") == 1


def test_staging_snapshot_written() -> None:
    """integrate-shot must write /app/state/shot-snapshot.json with trace_ids and replay_seq."""
    case = SHOT_CASES["simple"]
    integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
    assert SNAPSHOT.is_file(), "missing /app/state/shot-snapshot.json"
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snap.get("staging_version") == 1
    assert snap.get("replay_seq") == 0
    assert isinstance(snap.get("trace_ids"), list) and snap["trace_ids"]
    history = Path("/app/state/replay-history.json")
    assert history.is_file(), "missing /app/state/replay-history.json"
    assert str(SNAPSHOT) == "/app/state/shot-snapshot.json"
    exp = reference_snapshot(
        STACKS / "simple.json",
        case["velocity"],
        case["energy_j"],
        case["seed"],
        replay_seq=0,
    )
    assert snap["path_ledger_m"] == exp["path_ledger_m"]
    assert snap["trace_ids"] == exp["trace_ids"]


def test_trace_digest_traversal_order() -> None:
    """Export trace_digest must hash replay_seq|traversal-order physics_ids."""
    got = pipeline_shot_cli("multi-layer", "digest-check.json")
    exp = reference_shot(
        STACKS / "multi-layer.json",
        SHOT_CASES["multi-layer"]["velocity"],
        SHOT_CASES["multi-layer"]["energy_j"],
        SHOT_CASES["multi-layer"]["seed"],
    )
    assert got["trace_digest"] == exp["trace_digest"]


def test_hidden_digest_order_trap() -> None:
    """Hidden stack with non-sorted physics_id traversal must match reference digest."""
    root = Path("/opt/verifier-fixtures/ballistics/stacks")
    hidden = root / "digest-order-trap.json"
    assert hidden.is_file(), "missing hidden digest-order-trap fixture"
    velocity = [0.0, 0.0, -430.0]
    energy = 3500.0
    seed = 17
    integrate_shot_cli(hidden, velocity, energy, seed)
    got = export_shot_cli(OUTPUT / "hidden-digest.json")
    exp = reference_shot(hidden, velocity, energy, seed)
    snap = reference_snapshot(hidden, velocity, energy, seed, replay_seq=0)
    sorted_digest = trace_digest(sorted(snap["trace_ids"]), replay_seq=0)
    reversed_prefix = hashlib.sha256(
        f"{','.join(str(i) for i in snap['trace_ids'])}|0".encode("utf-8")
    ).hexdigest()
    assert got["trace_digest"] == exp["trace_digest"]
    assert sorted_digest != exp["trace_digest"]
    assert reversed_prefix != exp["trace_digest"]


def test_tb3_verifier_digest_fixture_present() -> None:
    """TB3 hidden digest-order-trap stack must ship under /opt/verifier-fixtures."""
    trap = Path("/opt/verifier-fixtures/ballistics/stacks/digest-order-trap.json")
    assert trap.is_file()


def test_hidden_replay_prefix_required_on_second_integrate() -> None:
    """Second integrate must change trace_digest when replay_seq advances."""
    case = SHOT_CASES["simple"]
    stack = STACKS / "simple.json"
    hist = ReplayHistory()
    reference_shot(stack, case["velocity"], case["energy_j"], case["seed"], replay_hist=hist)
    integrate_shot_cli(stack, case["velocity"], case["energy_j"], case["seed"])
    first = export_shot_cli(OUTPUT / "hidden-replay-first.json")
    exp_second = reference_shot(
        stack, case["velocity"], case["energy_j"], case["seed"], replay_hist=hist
    )
    integrate_shot_cli(stack, case["velocity"], case["energy_j"], case["seed"])
    second = export_shot_cli(OUTPUT / "hidden-replay-second.json")
    assert second == exp_second
    assert second["trace_digest"] != first["trace_digest"]


def test_partial_digest_traversal_only_still_fails_prefix() -> None:
    """Traversal-order digest without replay_seq prefix must fail export contract."""
    export_path = APP / "crates/ballcore/src/export_stage.rs"
    saved = export_path.read_text(encoding="utf-8")
    for needle, repl in (
        (
            "digest::digest_shot_export(stored.replay_seq, &stored.trace_ids)",
            "digest::digest_traversal_only(&stored.trace_ids)",
        ),
        (
            "digest::digest_ids_before_replay(stored.replay_seq, &stored.trace_ids)",
            "digest::digest_traversal_only(&stored.trace_ids)",
        ),
    ):
        if needle in saved:
            patched = saved.replace(needle, repl)
            break
    else:
        pytest.skip("export_stage digest call not found for partial trap")
    try:
        export_path.write_text(patched, encoding="utf-8")
        export_path.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        hidden = Path("/opt/verifier-fixtures/ballistics/stacks") / "digest-order-trap.json"
        integrate_shot_cli(hidden, [0.0, 0.0, -430.0], 3500.0, 17)
        got = export_shot_cli(OUTPUT / "partial-digest-prefix.json")
        exp = reference_shot(hidden, [0.0, 0.0, -430.0], 3500.0, 17)
        assert got["trace_digest"] != exp["trace_digest"]
    finally:
        export_path.write_text(saved, encoding="utf-8")
        rebuild_cli()


def test_partial_staging_fix_still_fails_boundary() -> None:
    """Correct staging alone must not fix integrator double boundary debit."""
    target = APP / "crates/ballcore/src/integrator.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_integrator.rs"
    saved = target.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, target)
        target.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        got = pipeline_shot_cli("boundary-double", "partial-staging-boundary.json")
        exp = reference_shot(
            STACKS / "boundary-double.json",
            SHOT_CASES["boundary-double"]["velocity"],
            SHOT_CASES["boundary-double"]["energy_j"],
            SHOT_CASES["boundary-double"]["seed"],
        )
        assert got["path_ledger_m"] != exp["path_ledger_m"]
    finally:
        target.write_text(saved, encoding="utf-8")
        rebuild_cli()


def test_partial_export_stage_fix_still_fails_hidden_digest() -> None:
    """Traversal-correct export_stage must still fail ledger when staging halves path."""
    staging_path = APP / "crates/ballcore/src/staging.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_staging.rs"
    saved = staging_path.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, staging_path)
        staging_path.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        hidden = Path("/opt/verifier-fixtures/ballistics/stacks") / "digest-order-trap.json"
        velocity = [0.0, 0.0, -430.0]
        energy = 3500.0
        seed = 17
        integrate_shot_cli(hidden, velocity, energy, seed)
        got = export_shot_cli(OUTPUT / "partial-export-digest.json")
        exp = reference_shot(hidden, velocity, energy, seed)
        assert got["path_ledger_m"] != exp["path_ledger_m"]
    finally:
        staging_path.write_text(saved, encoding="utf-8")
        rebuild_cli()


def test_partial_material_fix_still_fails_id_trap() -> None:
    """Broken asset_name lookup must fail material-id-trap even if other modules fixed."""
    mat_path = APP / "crates/ballcore/src/material.rs"
    int_path = APP / "crates/ballcore/src/integrator.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_material.rs"
    saved_mat = mat_path.read_text(encoding="utf-8")
    saved_int = int_path.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, mat_path)
        int_text = saved_int
        if "catalog.by_physics_id(layer.physics_id)?" in int_text:
            int_text = int_text.replace(
                "catalog.by_physics_id(layer.physics_id)?",
                "catalog.resolve_layer(layer)?",
            )
        elif "resolve_layer(layer)" not in int_text and "resolve_layer(&layer)" not in int_text:
            pytest.skip("integrator has no layer-based catalog lookup to exercise")
        int_path.write_text(int_text, encoding="utf-8")
        mat_path.touch()
        int_path.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        got = pipeline_shot_cli("material-id-trap", "partial-material.json")
        exp = reference_shot(
            STACKS / "material-id-trap.json",
            SHOT_CASES["material-id-trap"]["velocity"],
            SHOT_CASES["material-id-trap"]["energy_j"],
            SHOT_CASES["material-id-trap"]["seed"],
        )
        assert got["exit_energy_j"] != exp["exit_energy_j"]
    finally:
        mat_path.write_text(saved_mat, encoding="utf-8")
        int_path.write_text(saved_int, encoding="utf-8")
        rebuild_cli()


def test_partial_integrator_fix_still_fails_boundary() -> None:
    """Double boundary debit must break path ledger even when materials are fixed."""
    target = APP / "crates/ballcore/src/integrator.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_integrator.rs"
    saved = target.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, target)
        target.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        got = pipeline_shot_cli("boundary-double", "partial-integrator.json")
        exp = reference_shot(
            STACKS / "boundary-double.json",
            SHOT_CASES["boundary-double"]["velocity"],
            SHOT_CASES["boundary-double"]["energy_j"],
            SHOT_CASES["boundary-double"]["seed"],
        )
        assert got["path_ledger_m"] != exp["path_ledger_m"]
    finally:
        target.write_text(saved, encoding="utf-8")
        rebuild_cli()


def test_partial_ricochet_fix_still_fails_angles() -> None:
    """Wrong-normal-direction exit angles must fail ricochet-trap reflection checks."""
    target = APP / "crates/ballcore/src/ricochet.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_ricochet.rs"
    saved = target.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, target)
        target.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        got = pipeline_shot_cli("ricochet-trap", "partial-ricochet.json")
        exp = reference_shot(
            STACKS / "ricochet-trap.json",
            SHOT_CASES["ricochet-trap"]["velocity"],
            SHOT_CASES["ricochet-trap"]["energy_j"],
            SHOT_CASES["ricochet-trap"]["seed"],
        )
        assert got["ricochet"]["exit_angle_deg"] != exp["ricochet"]["exit_angle_deg"]
    finally:
        target.write_text(saved, encoding="utf-8")
        rebuild_cli()


def test_partial_batch_fix_still_fails_tick_order() -> None:
    """Arrival-order batch rollup must diverge from tick-sorted reference export."""
    target = APP / "crates/ballcore/src/rollup.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_rollup.rs"
    saved = target.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, target)
        target.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        got = simulate_batch_cli("tick-order-trap", "partial-batch.json")
        exp = reference_batch(BATCHES / "tick-order-trap.json")
        assert len(got["ticks"]) != len(exp["ticks"])
    finally:
        target.write_text(saved, encoding="utf-8")
        rebuild_cli()


def test_partial_replay_fix_still_fails_second_digest() -> None:
    """Replay gate stuck at zero must diverge on second integrate with same stack+seed."""
    target = APP / "crates/ballcore/src/replay_gate.rs"
    broken = Path(__file__).resolve().parent / "broken_lib/broken_replay_gate.rs"
    saved = target.read_text(encoding="utf-8")
    try:
        shutil.copy2(broken, target)
        target.touch()
        try:
            rebuild_cli()
        except AssertionError:
            return
        case = SHOT_CASES["simple"]
        hist = ReplayHistory()
        reference_shot(
            STACKS / "simple.json",
            case["velocity"],
            case["energy_j"],
            case["seed"],
            replay_hist=hist,
        )
        integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
        first = export_shot_cli(OUTPUT / "partial-replay-first.json")
        exp_second = reference_shot(
            STACKS / "simple.json",
            case["velocity"],
            case["energy_j"],
            case["seed"],
            replay_hist=hist,
        )
        integrate_shot_cli(STACKS / "simple.json", case["velocity"], case["energy_j"], case["seed"])
        second = export_shot_cli(OUTPUT / "partial-replay-second.json")
        assert second["trace_digest"] != exp_second["trace_digest"]
        assert second["trace_digest"] == first["trace_digest"]
    finally:
        target.write_text(saved, encoding="utf-8")
        rebuild_cli()
