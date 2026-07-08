import json
import os
import shutil
import subprocess
from pathlib import Path

APP = Path("/app/environment")
BUILD_DIR = Path("/tmp/gatectl-build")
BIN = BUILD_DIR / "debug" / "gatectl"


def _build_binary() -> None:
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(BUILD_DIR)
    subprocess.run(
        ["cargo", "build", "--manifest-path", "/app/environment/Cargo.toml"],
        check=True,
        cwd=APP,
        env=env,
    )


def _workspace(tmp_path: Path, name: str) -> Path:
    dst = tmp_path / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    return dst


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [str(BIN), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr
    return proc


def _seed(root: Path) -> list[dict]:
    rows = []
    for line in (root / "seed.txt").read_text().splitlines():
        if not line.strip():
            continue
        tag, lane, weight = line.split("|")
        rows.append({"tag": tag, "lane": lane, "weight": int(weight)})
    return rows


def _jsonl(path: Path) -> list[dict]:
    assert path.exists(), f"missing {path}"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row_obs(root: Path) -> list[dict]:
    return _jsonl(root / ".state" / "row-obs.jsonl")


def _dispatch_obs(root: Path) -> list[dict]:
    return _jsonl(root / ".state" / "dispatch-obs.jsonl")


def _reset_products(root: Path) -> None:
    for name in ("row-obs.jsonl", "dispatch-obs.jsonl"):
        p = root / ".state" / name
        if p.exists():
            p.unlink()


def _remove_state(root: Path, *names: str) -> None:
    for name in names:
        p = root / ".state" / name
        if p.exists():
            p.unlink()


def _latest_row_map(root: Path) -> dict[str, dict]:
    return {f"{row['tag']}:{row['wave']}": row for row in _row_obs(root)}


def _fire_sequence(root: Path) -> list[dict]:
    fires = [r for r in _dispatch_obs(root) if r["phase"] == "fire"]
    fires.sort(key=lambda r: r["slot"])
    return fires


def _assert_unique_fires(root: Path) -> None:
    fires = [r for r in _dispatch_obs(root) if r["phase"] == "fire"]
    assert len(fires) == len({(r["tag"], r["wave"]) for r in fires})


def _assert_monotone_slots(root: Path) -> None:
    slots = [r["slot"] for r in _dispatch_obs(root) if r["phase"] == "fire"]
    assert slots == sorted(slots)
    assert slots == list(range(1, len(slots) + 1))


def _assert_dispatch_row_alignment(root: Path) -> None:
    latest = _latest_row_map(root)
    for row in _dispatch_obs(root):
        if row["phase"] == "fire":
            assert latest[f"{row['tag']}:{row['wave']}"]["state"] == "sent"


def _assert_all_sent(root: Path, keys: set[tuple[str, int]]) -> None:
    latest = _latest_row_map(root)
    for tag, wave in keys:
        row = latest.get(f"{tag}:{wave}")
        assert row, f"missing row obs for {tag}:{wave}"
        assert row["state"] == "sent", latest


def _converge_s4_with_duplicate_echo(root: Path) -> None:
    _run(root, "open", str(root), "s4")
    _run(root, "offer", str(root), "echo")
    _run(root, "cycle", str(root), "--partial")
    _run(root, "offer", str(root), "echo")
    _run(root, "cycle", str(root), "--partial")
    _run(root, "offer", str(root), "slip")
    _run(root, "cycle", str(root), "--partial")
    _run(root, "raise", str(root))
    _reset_products(root)
    _run(root, "sweep", str(root))


def test_recovery_a_duplicate_tag_waves_and_lane_order(tmp_path: Path) -> None:
    """Duplicate offered tags must remain distinct by wave while dispatch honors runtime lane order after recovery."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_a")
    _converge_s4_with_duplicate_echo(root)

    seed_keys = {(r["tag"], 1) for r in _seed(root)}
    offered_keys = {("echo", 2), ("echo", 3), ("slip", 4)}
    _assert_all_sent(root, seed_keys | offered_keys)
    _assert_unique_fires(root)
    _assert_monotone_slots(root)
    _assert_dispatch_row_alignment(root)

    fires = _fire_sequence(root)
    assert [(r["tag"], r["wave"]) for r in fires if r["tag"] == "echo"] == [
        ("echo", 2),
        ("echo", 3),
    ]
    lanes = {f"{row['tag']}:{row['wave']}": row["lane"] for row in _row_obs(root)}
    lane_trace = [lanes[f"{r['tag']}:{r['wave']}"] for r in fires]
    assert lane_trace == sorted(lane_trace, key={"pre": 0, "hold": 1, "live": 2}.get)
    assert [r["tag"] for r in fires[-3:]] == ["bravo", "mild", "omega"]


def test_recovery_b_anchor_rebuilds_after_primary_state_loss(tmp_path: Path) -> None:
    """The recovery anchor must regenerate a converged view after checkpoint, carry, witness, and products are removed."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_b")
    _converge_s4_with_duplicate_echo(root)
    expected_rows = _row_obs(root)
    expected_dispatch = _dispatch_obs(root)

    _reset_products(root)
    _remove_state(root, "ckpt.json", "defer-carry.tab", "defer-witness.bin")
    _run(root, "sweep", str(root), "--again")

    assert _row_obs(root) == expected_rows
    assert _dispatch_obs(root) == expected_dispatch


def test_recovery_c_partial_anchor_survives_before_raise(tmp_path: Path) -> None:
    """If primary deferral ledgers vanish before raise, partial-cycle anchor material must still admit witnessed offers."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_c")
    _run(root, "open", str(root), "s2")
    _run(root, "offer", str(root), "apex")
    _run(root, "cycle", str(root), "--partial")
    _run(root, "offer", str(root), "dock")
    _run(root, "cycle", str(root), "--partial")
    _remove_state(root, "ckpt.json", "defer-carry.tab", "defer-witness.bin")
    _run(root, "raise", str(root))
    _reset_products(root)
    _run(root, "sweep", str(root))

    _assert_all_sent(root, {(r["tag"], 1) for r in _seed(root)} | {("apex", 2), ("dock", 3)})
    _assert_unique_fires(root)
    _assert_dispatch_row_alignment(root)


def test_recovery_d_sweep_again_is_idempotent_across_full_cycle(tmp_path: Path) -> None:
    """Repeated republish and a full cycle must not replay fire events or renumber slots."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_d")
    _converge_s4_with_duplicate_echo(root)
    expected_dispatch = _dispatch_obs(root)

    for _ in range(2):
        _reset_products(root)
        _run(root, "sweep", str(root), "--again")
        assert _dispatch_obs(root) == expected_dispatch

    _run(root, "cycle", str(root))
    _reset_products(root)
    _run(root, "sweep", str(root), "--again")
    assert _dispatch_obs(root) == expected_dispatch
    _assert_monotone_slots(root)


def test_recovery_e_stale_durable_merged_with_checkpoint_view(tmp_path: Path) -> None:
    """A stale durable row table must not downgrade sent rows when checkpoint and anchor material are newer."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_e")
    _run(root, "open", str(root), "s3")
    _run(root, "offer", str(root), "cove")
    _run(root, "cycle", str(root), "--partial")
    _run(root, "raise", str(root))
    stale_durable = (root / ".state" / "durable.json").read_text()
    _reset_products(root)
    _run(root, "sweep", str(root))
    expected_rows = _row_obs(root)
    expected_dispatch = _dispatch_obs(root)

    (root / ".state" / "durable.json").write_text(stale_durable)
    _reset_products(root)
    _run(root, "sweep", str(root), "--again")

    assert _row_obs(root) == expected_rows
    assert _dispatch_obs(root) == expected_dispatch


def test_recovery_g_pick_tie_break_tag_then_wave(tmp_path: Path) -> None:
    """When lane and weight tie, pick must order by tag then wave before fire slots are assigned."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_g")
    _run(root, "open", str(root), "s5")
    _run(root, "offer", str(root), "echo")
    _run(root, "cycle", str(root), "--partial")
    _run(root, "raise", str(root))
    _reset_products(root)
    _run(root, "sweep", str(root))

    fires = _fire_sequence(root)
    fired_pairs = [(r["tag"], r["wave"]) for r in fires]
    assert fired_pairs.index(("echo", 1)) < fired_pairs.index(("echo", 2))
    assert fired_pairs.index(("alpha", 1)) < fired_pairs.index(("beta", 1))
    _assert_all_sent(root, {("echo", 1), ("echo", 2), ("alpha", 1), ("beta", 1)})
    _assert_unique_fires(root)
    _assert_monotone_slots(root)
    _assert_dispatch_row_alignment(root)


def test_recovery_f_unwitnessed_offer_stays_deferred_after_replay(tmp_path: Path) -> None:
    """Recovery must not manufacture witness quorum for an offer that never crossed a partial cycle."""
    _build_binary()
    root = _workspace(tmp_path, "recovery_f")
    _run(root, "open", str(root), "s1")
    _run(root, "offer", str(root), "ghost")
    _run(root, "raise", str(root))
    _reset_products(root)
    _run(root, "sweep", str(root))

    latest = _latest_row_map(root)
    assert latest["ghost:2"]["state"] == "wait"
    assert ("ghost", 2) not in {(r["tag"], r["wave"]) for r in _fire_sequence(root)}
    _assert_all_sent(root, {(r["tag"], 1) for r in _seed(root)})

    _remove_state(root, "ckpt.json", "defer-carry.tab", "defer-witness.bin")
    _reset_products(root)
    _run(root, "sweep", str(root), "--again")
    latest = _latest_row_map(root)
    assert latest["ghost:2"]["state"] == "wait"
    assert ("ghost", 2) not in {(r["tag"], r["wave"]) for r in _fire_sequence(root)}
