from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ENV = Path("/app/environment")
OUTPUT = Path("/app/output/r7_matrix_record.json")
STATE = ENV / "state/mp_lane.json"
BUILD_CTL = ENV / "target" / "release" / "ctl_r7"
BUILD_CHAIN = ENV / "target" / "release" / "chain_ref"
VERIFIER_DIR = Path("/opt/verifier")
CTL_BIN = VERIFIER_DIR / "ctl_r7"
CHAIN_BIN = VERIFIER_DIR / "chain_ref"

ALL_SLUGS = (
    "mp_control",
    "mp_north",
    "mp_south",
    "mp_west",
    "mp_east",
    "mp_tandem",
    "mp_echo",
)


def rebuild_desk_from_source() -> None:
    subprocess.run(
        ["cargo", "build", "--release", "--locked"],
        cwd=ENV,
        check=True,
        env=os.environ.copy(),
        timeout=600,
    )


def assert_elf_executable(path: Path) -> None:
    header = path.read_bytes()[:4]
    assert header == b"\x7fELF", f"{path} is not a compiled ELF binary"
    assert os.access(path, os.X_OK), f"{path} is not executable"


def stage_release_binaries() -> None:
    rebuild_desk_from_source()
    assert BUILD_CTL.is_file(), "release ctl_r7 missing after cargo build"
    assert BUILD_CHAIN.is_file(), "release chain_ref missing after cargo build"
    assert_elf_executable(BUILD_CTL)
    assert_elf_executable(BUILD_CHAIN)
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUILD_CTL, CTL_BIN)
    shutil.copy2(BUILD_CHAIN, CHAIN_BIN)
    os.chmod(CTL_BIN, 0o755)
    os.chmod(CHAIN_BIN, 0o755)
    assert_elf_executable(CTL_BIN)
    assert_elf_executable(CHAIN_BIN)


@pytest.fixture(scope="session", autouse=True)
def rebuilt_release_desk() -> None:
    stage_release_binaries()


def clear_lane_state() -> None:
    if STATE.exists():
        STATE.unlink()


def run_slug(slug: str) -> None:
    subprocess.run(
        [str(CTL_BIN), "--scenario", slug],
        check=True,
        capture_output=True,
        text=True,
    )


def run_slug_sequence(slugs: list[str], *, keep_state: bool = True) -> dict:
    if not keep_state:
        clear_lane_state()
    for slug in slugs:
        run_slug(slug)
    return read_record()


def read_record() -> dict:
    return json.loads(OUTPUT.read_text())


def chain_hex(rows: list[dict]) -> str:
    payload = json.dumps(rows)
    result = subprocess.run(
        [str(CHAIN_BIN)],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def load_lane_state() -> dict:
    if not STATE.exists():
        return {"by_slug": {}, "wal_obs": [], "active_slug": ""}
    return json.loads(STATE.read_text())


def committed_gen(slug: str) -> int:
    state = load_lane_state()
    entry = state.get("by_slug", {}).get(slug, {})
    return int(entry.get("committed_gen", 0))


def load_segment_cells(segment: str) -> dict[str, str]:
    cells: dict[str, str] = {}
    for line in (ENV / "fixtures" / "sidecars" / f"{segment}.seg").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key.startswith("ent_"):
            cells[key] = val.strip()
    return cells


def load_checkpoint_markers(checkpoint: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    text = (ENV / "data/checkpoints" / f"cp_blob_{checkpoint}.bin").read_text()
    for line in text.splitlines():
        if line.startswith("marker_"):
            ent = line.split("=", 1)[0].removeprefix("marker_")
            markers[ent] = line.split("=", 1)[1].strip()
    return markers


def load_segment_branch(segment: str) -> str:
    for line in (ENV / "fixtures" / "sidecars" / f"{segment}.seg").read_text().splitlines():
        if line.startswith("branch="):
            return line.split("=", 1)[1].strip()
    return ""


def load_case(slug: str) -> dict:
    return json.loads((ENV / "data/cases" / f"case_{slug}.json").read_text())


def load_case_segment(slug: str) -> str:
    return load_case(slug)["segment"]


def load_case_entities(slug: str) -> list[str]:
    return load_case(slug)["entities"]


def isolated_slug_bytes(slug: str) -> bytes:
    clear_lane_state()
    run_slug(slug)
    return OUTPUT.read_bytes()


def assert_rows_match_segment(record: dict, slug: str) -> None:
    cells = load_segment_cells(load_case_segment(slug))
    for row in record["rows"]:
        assert row["book_cell"] == cells[row["entity"]]
        assert not row["book_cell"].endswith("_cache_stale")


def assert_markers_match_checkpoint(record: dict, slug: str) -> None:
    case = load_case(slug)
    expected = load_checkpoint_markers(case["checkpoint"])
    assert len(record["rows"]) == len(expected)
    for row in record["rows"]:
        assert row["marker"] == expected[row["entity"]]
        assert row["wave"] == 2
        assert not row["marker"].startswith("compact_wave_")
        assert not row["marker"].startswith("rk_")


def assert_no_wal_replay_bleed(record: dict) -> None:
    wal_rows = [item for item in record["observations"] if item.get("phase") == "wal_replay"]
    assert not wal_rows, "wal_replay observations must not appear in final export"


def test_kp_h0_release_build_is_rust_binary():
    """Desk must be produced by a release cargo build, not a script substitute."""
    stage_release_binaries()
    assert CTL_BIN.is_file()
    assert CHAIN_BIN.is_file()
    assert_elf_executable(CTL_BIN)
    assert_elf_executable(CHAIN_BIN)


def test_kp_h1_delete_rerender():
    """Output must be regenerated by ctl_r7 after the stale matrix record is removed."""
    clear_lane_state()
    if OUTPUT.exists():
        OUTPUT.unlink()
    run_slug("mp_control")
    assert OUTPUT.exists()
    record = read_record()
    assert record["scenario"] == "mp_control"
    assert_rows_match_segment(record, "mp_control")


def test_kp_h2_six_slug_marathon_isolated():
    """Six-slug marathon ending on tandem must match an isolated tandem export."""
    marathon = [
        "mp_north",
        "mp_south",
        "mp_west",
        "mp_east",
        "mp_control",
        "mp_tandem",
    ]
    run_slug_sequence(marathon)
    chained = OUTPUT.read_bytes()
    isolated = isolated_slug_bytes("mp_tandem")
    assert chained == isolated
    record = read_record()
    assert_markers_match_checkpoint(record, "mp_tandem")
    assert_no_wal_replay_bleed(record)


def test_kp_h3_chain_hex_order_invariant():
    """chain_hex must match chain_ref and stay stable under row-order permutation."""
    clear_lane_state()
    run_slug_sequence(["mp_west", "mp_control", "mp_south"])
    record = read_record()
    assert record["chain_hex"] == chain_hex(record["rows"])
    shuffled = list(reversed(record["rows"]))
    assert chain_hex(shuffled) == record["chain_hex"]


def test_kp_h4_corrupt_lane_state_recovery():
    """Truncated lane-state JSON must not wedge later isolated exports."""
    clear_lane_state()
    run_slug("mp_north")
    STATE.write_text('{"by_slug":{"mp_north":{"committed_gen":99')
    isolated = isolated_slug_bytes("mp_south")
    record = read_record()
    assert record["scenario"] == "mp_south"
    assert_rows_match_segment(record, "mp_south")
    assert isolated == OUTPUT.read_bytes()
    assert_no_wal_replay_bleed(record)


def test_kp_h5_wal_obs_no_replay_after_slug_pivot():
    """Switching north to west must not replay prior slug wal material into the export."""
    clear_lane_state()
    run_slug("mp_north")
    run_slug("mp_west")
    record = read_record()
    assert record["scenario"] == "mp_west"
    assert load_lane_state().get("active_slug") == "mp_west"
    assert_no_wal_replay_bleed(record)


def test_kp_h6_shared_entity_cells_not_resurrected():
    """North after south must not replay south segment cells for shared roster entities."""
    clear_lane_state()
    run_slug_sequence(["mp_south", "mp_north"])
    record = read_record()
    north_cells = load_segment_cells(load_case_segment("mp_north"))
    south_cells = load_segment_cells(load_case_segment("mp_south"))
    for row in record["rows"]:
        ent = row["entity"]
        assert row["book_cell"] == north_cells[ent]
        assert row["book_cell"] != south_cells[ent]


def test_kp_h7_delayed_wal_bleed_after_four_pivot():
    """Four scenario pivots before tandem must not inject wal_replay observations."""
    clear_lane_state()
    run_slug_sequence(["mp_tandem", "mp_control", "mp_west", "mp_east", "mp_tandem"])
    record = read_record()
    assert_no_wal_replay_bleed(record)
    assert_markers_match_checkpoint(record, "mp_tandem")
    assert len(record["observations"]) >= 12


def test_kp_h8_generation_increments_on_repeat():
    """Three consecutive north runs must advance committed_gen monotonically."""
    clear_lane_state()
    gens: list[int] = []
    for _ in range(3):
        run_slug("mp_north")
        gens.append(committed_gen("mp_north"))
    assert gens[0] < gens[1] < gens[2], "committed_gen must increase across repeat north runs"


def test_kp_h9_echo_after_marathon_prime():
    """Echo after a five-slug marathon must bind echo cells and checkpoint markers."""
    prime = ["mp_north", "mp_south", "mp_west", "mp_east", "mp_control"]
    run_slug_sequence(prime)
    run_slug("mp_echo")
    record = read_record()
    assert record["scenario"] == "mp_echo"
    assert_rows_match_segment(record, "mp_echo")
    assert_markers_match_checkpoint(record, "mp_echo")
    assert_no_wal_replay_bleed(record)


def test_kp_h10_phase_one_survives_journal_stress():
    """Phase-one evidence must survive north->south->north with journal activity."""
    clear_lane_state()
    run_slug_sequence(["mp_north", "mp_south", "mp_north"])
    record = read_record()
    for ent in load_case_entities("mp_north"):
        phase_one = [
            item for item in record["evidence"] if item["id"].startswith(ent) and item["phase"] == 1
        ]
        assert phase_one, f"phase-one evidence missing for {ent}"
        assert any(item["payload"] == "wave1" for item in phase_one)


def test_kp_h11_tandem_payloads_after_slug_prime():
    """Tandem must retain wave payloads after west and east runs in one process."""
    clear_lane_state()
    run_slug_sequence(["mp_west", "mp_east", "mp_tandem"])
    record = read_record()
    for ent in load_case_entities("mp_tandem"):
        payloads = {item["payload"] for item in record["evidence"] if item["id"].startswith(ent)}
        assert "wave1" in payloads and "wave2" in payloads


def test_kp_h12_state_truncation_recovery():
    """Deleting lane state mid-sequence must not wedge later isolated runs."""
    clear_lane_state()
    run_slug_sequence(["mp_north", "mp_west"])
    if STATE.exists():
        STATE.unlink()
    isolated = isolated_slug_bytes("mp_south")
    record = read_record()
    assert record["scenario"] == "mp_south"
    assert_rows_match_segment(record, "mp_south")
    assert isolated == OUTPUT.read_bytes()


def test_kp_h13_triple_switch_byte_stable():
    """North after north->south->north must match an isolated north export."""
    clear_lane_state()
    run_slug_sequence(["mp_north", "mp_south", "mp_north"])
    chained = OUTPUT.read_bytes()
    isolated = isolated_slug_bytes("mp_north")
    assert chained == isolated
    assert_rows_match_segment(read_record(), "mp_north")


def test_kp_h14_tandem_three_cycle_evidence():
    """Tandem with three cycles must retain phase-one and phase-two evidence per entity."""
    clear_lane_state()
    run_slug("mp_tandem")
    record = read_record()
    phases = {item["phase"] for item in record["evidence"]}
    assert 1 in phases and 2 in phases
    for ent in load_case_entities("mp_tandem"):
        ids = [item["id"] for item in record["evidence"] if item["id"].startswith(ent)]
        assert len(ids) >= 4


def test_kp_h15_reconcile_not_blocked_on_repeat():
    """Repeat north runs must not stall on generation-floor reconcile errors."""
    clear_lane_state()
    for _ in range(2):
        run_slug("mp_north")
    record = read_record()
    assert record["scenario"] == "mp_north"
    assert_rows_match_segment(record, "mp_north")


def test_kp_h16_west_east_no_stamp_bleed():
    """Switching west then east must not merge west stamp material into east export."""
    clear_lane_state()
    run_slug_sequence(["mp_west", "mp_east"])
    record = read_record()
    assert record["scenario"] == "mp_east"
    assert_rows_match_segment(record, "mp_east")
    assert_markers_match_checkpoint(record, "mp_east")


def test_kp_h17_chain_stable_after_journal_prime():
    """South chain_hex must match isolated south after north journal priming."""
    clear_lane_state()
    run_slug("mp_north")
    run_slug("mp_south")
    stressed = read_record()
    run_slug("mp_south")
    isolated = read_record()
    assert stressed["chain_hex"] == isolated["chain_hex"]


def test_kp_h18_echo_wal_replay_clean():
    """Echo slug must not carry wal_replay rows from prior marathon slugs."""
    clear_lane_state()
    run_slug_sequence(["mp_north", "mp_west", "mp_east", "mp_echo"])
    record = read_record()
    assert_no_wal_replay_bleed(record)
    obs_phases = {item["phase"] for item in record["observations"]}
    assert "wal_replay" not in obs_phases


def test_kp_h19_evidence_phase_floor_after_echo():
    """Echo repeat run must retain phase-one evidence after generation floor advances."""
    clear_lane_state()
    run_slug("mp_echo")
    run_slug("mp_echo")
    record = read_record()
    phases = {item["phase"] for item in record["evidence"]}
    assert 1 in phases and 2 in phases
    assert committed_gen("mp_echo") >= 2


def test_kp_h20_control_clears_cross_slug_roster():
    """Running west then east must not leak west roster markers into east export."""
    clear_lane_state()
    run_slug("mp_west")
    run_slug("mp_east")
    record = read_record()
    expected = load_checkpoint_markers("east")
    assert len(record["rows"]) == len(expected)
    for row in record["rows"]:
        assert row["marker"] == expected[row["entity"]]


def test_kp_h21_south_stable_after_north_prime():
    """South after north prime must stay byte-stable and keep south segment cells."""
    clear_lane_state()
    run_slug("mp_north")
    run_slug("mp_south")
    first = OUTPUT.read_bytes()
    run_slug("mp_south")
    second = OUTPUT.read_bytes()
    assert first == second
    assert_rows_match_segment(read_record(), "mp_south")


def test_kp_h22_tandem_checkpoint_stem():
    """Tandem checkpoint stem must resolve the tandem bind profile."""
    clear_lane_state()
    run_slug("mp_tandem")
    record = read_record()
    expected = load_checkpoint_markers("tandem")
    assert set(expected.keys()) == {row["entity"] for row in record["rows"]}
    for row in record["rows"]:
        assert row["marker"] == expected[row["entity"]]


def test_kp_h23_interleaved_six_pass_generation_isolation():
    """Interleaved six-slug passes must keep per-slug committed_gen isolated."""
    clear_lane_state()
    sequence = [
        "mp_north",
        "mp_south",
        "mp_north",
        "mp_west",
        "mp_east",
        "mp_tandem",
        "mp_echo",
        "mp_north",
    ]
    run_slug_sequence(sequence)
    assert committed_gen("mp_north") >= 2
    assert committed_gen("mp_echo") >= 1
    record = read_record()
    assert record["scenario"] == "mp_north"
    assert_no_wal_replay_bleed(record)


def test_kp_h24_byte_identical_repeat_with_state():
    """Repeat west runs with persisted lane state must yield byte-identical exports."""
    clear_lane_state()
    run_slug("mp_west")
    first = OUTPUT.read_bytes()
    run_slug("mp_west")
    second = OUTPUT.read_bytes()
    assert first == second


def test_kp_h25_lane_state_advances_on_repeat():
    """Lane state committed_gen must advance across repeat runs of the same slug."""
    clear_lane_state()
    run_slug("mp_south")
    first_gen = committed_gen("mp_south")
    run_slug("mp_south")
    second_gen = committed_gen("mp_south")
    assert second_gen > first_gen


def test_kp_h26_fracture_chain_after_echo_prime():
    """Tandem chain after echo prime must match isolated tandem bytes."""
    clear_lane_state()
    run_slug_sequence(["mp_echo", "mp_west", "mp_tandem"])
    chained = OUTPUT.read_bytes()
    isolated = isolated_slug_bytes("mp_tandem")
    assert chained == isolated
    assert_markers_match_checkpoint(read_record(), "mp_tandem")


def test_kp_h27_all_slugs_chain_ref_agreement():
    """Every shipped slug export must agree with chain_ref on chain_hex."""
    for slug in ALL_SLUGS:
        clear_lane_state()
        run_slug(slug)
        record = read_record()
        assert record["chain_hex"] == chain_hex(record["rows"]), f"{slug}: chain_hex drift"


def test_kp_h28_segment_branch_in_observations():
    """Each slug must emit observations carrying the active segment branch."""
    for slug in ALL_SLUGS:
        clear_lane_state()
        run_slug(slug)
        record = read_record()
        branch = load_segment_branch(load_case_segment(slug))
        obs_branches = {item.get("branch") for item in record["observations"] if item.get("branch")}
        assert branch in obs_branches, f"{slug}: missing segment branch in observations"


def test_kp_h29_corrupt_lane_wal_obs_recovery():
    """Malformed lane-state JSON must not replay wal material into later exports."""
    clear_lane_state()
    STATE.write_text('{"wal_obs":[')
    run_slug("mp_west")
    record = read_record()
    assert record["scenario"] == "mp_west"
    assert_no_wal_replay_bleed(record)
    assert_rows_match_segment(record, "mp_west")


def test_kp_h30_control_pivot_between_tandem_runs():
    """Control pivot between tandem runs must keep tandem markers byte-stable."""
    clear_lane_state()
    run_slug("mp_tandem")
    first = OUTPUT.read_bytes()
    run_slug("mp_control")
    run_slug("mp_tandem")
    second = OUTPUT.read_bytes()
    assert first == second
    assert_markers_match_checkpoint(read_record(), "mp_tandem")
