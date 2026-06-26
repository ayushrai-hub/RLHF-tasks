"""Public verifier surface for terraform-bazel-lockfile-gen."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

APP = Path("/app")
OUT = APP / "output"
JOURNAL = APP / "environment" / ".runtime" / "journal"
ENV = APP / "environment"
CLOSURE_PATH = JOURNAL / "closure.json"
TAIL_PATH = JOURNAL / "replay_tail.json"
CHAIN_PATH = JOURNAL / "replay_chain.jsonl"
HARNESS = Path("/tests/support/run_apply_checks.sh")


def _link_digest(lock_rows, checksum_rows) -> str:
    payload = {"lock": lock_rows, "checksum": checksum_rows}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _run(entry: str = "alpha", *, wipe_journal: bool = False, wipe_output: bool = True) -> None:
    env = os.environ.copy()
    env["ROOT_ENTRY"] = entry
    if wipe_journal and JOURNAL.exists():
        shutil.rmtree(JOURNAL)
    if wipe_output and OUT.exists():
        shutil.rmtree(OUT)
    proc = subprocess.run(["bash", str(HARNESS)], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def _load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def _version_map() -> dict[str, str]:
    lock = _load("lock_snapshot.json")
    return {r["module_id"]: r["version"] for r in lock["rows"]}


def _slot(entry: str) -> dict:
    ledger = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    slots = ledger.get("slots", {})
    assert entry in slots, f"missing journal slot for entry {entry}"
    return slots[entry]


def _replay_gen() -> int:
    path = JOURNAL / "replay_gen.json"
    if not path.is_file():
        return 0
    return json.loads(path.read_text(encoding="utf-8")).get("gen", 0)


def _replay_tail() -> dict:
    assert TAIL_PATH.is_file(), "replay_tail.json missing after apply"
    return json.loads(TAIL_PATH.read_text(encoding="utf-8"))


def _expected_seed_digest(entry: str) -> str:
    rel = json.loads((ENV / "meta/roots_index.json").read_text(encoding="utf-8"))["entries"][entry]
    roots = json.loads((ENV / "fixtures/roots" / rel).read_text(encoding="utf-8"))
    seeds = sorted(roots["seeds"])
    return ",".join(seeds) + "|" + roots["storage_class"]


def _load_chain_lines() -> list[dict]:
    if not CHAIN_PATH.is_file():
        return []
    out: list[dict] = []
    for raw in CHAIN_PATH.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def _assert_chain_prefix_chain() -> None:
    raw_lines = [ln for ln in CHAIN_PATH.read_text(encoding="utf-8").split("\n") if ln]
    expected = "genesis"
    for raw in raw_lines:
        rec = json.loads(raw)
        assert rec["chain_prefix"] == expected, rec
        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _assert_module_lock_aligned() -> None:
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    stub = _load("module_lock.bzl")
    assert stub["entry_id"] == lock["entry_id"]
    keys = sorted(r["repo_key"] for r in lock["rows"])
    digest = {r["repo_key"]: r["digest"] for r in checksum["rows"]}
    expected_lines = [f"lock({k},{digest[k]})" for k in keys]
    assert stub["lines"] == expected_lines
    rollup = hashlib.sha256("\n".join(expected_lines).encode("utf-8")).hexdigest()
    assert stub["stub_rollup"] == rollup


def _assert_tail_matches_active(entry: str) -> None:
    tail = _replay_tail()
    slot = _slot(entry)
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    expected = _link_digest(lock["rows"], checksum["rows"])
    assert tail["entry_id"] == entry
    assert tail["seed_digest"] == _expected_seed_digest(entry)
    assert tail["link_digest"] == expected
    assert tail["gen"] == _replay_gen()
    assert slot.get("seed_digest") == _expected_seed_digest(entry)
    assert slot.get("link_digest") == expected
    assert slot.get("sealed_at_gen") == _replay_gen()


def test_p01_twenty_step_rotation_preserves_seals_and_chain() -> None:
    """A twenty-step tour must preserve slot seals, epoch counters, and chain prefix linkage."""
    sequence = [
        "beta", "gamma", "delta", "epsilon", "alpha", "delta", "gamma", "beta",
        "epsilon", "alpha", "gamma", "delta", "beta", "alpha", "beta", "epsilon",
        "delta", "gamma", "alpha", "beta",
    ]
    _run("alpha", wipe_journal=True)
    epoch = json.loads((JOURNAL / "epoch.json").read_text(encoding="utf-8"))
    seals: dict[str, str] = {"alpha": _slot("alpha")["link_digest"]}
    for entry in sequence:
        _run(entry)
        epoch = json.loads((JOURNAL / "epoch.json").read_text(encoding="utf-8"))
        assert epoch.get(entry, 0) >= 1
        lock = _load("lock_snapshot.json")
        checksum = _load("checksum_rows.json")
        dig = _link_digest(lock["rows"], checksum["rows"])
        assert _slot(entry)["link_digest"] == dig
        _assert_tail_matches_active(entry)
        _assert_module_lock_aligned()
        _assert_chain_prefix_chain()
        seals[entry] = dig
    for entry in ("alpha", "beta", "gamma", "delta", "epsilon"):
        _run(entry)
        assert _slot(entry)["link_digest"] == seals[entry]
        _assert_module_lock_aligned()
    assert len(_load_chain_lines()) >= len(sequence) + 1


def test_p02_chain_and_artifact_tamper_recovery() -> None:
    """Tampering replay chain, module lock, and lock snapshot must each heal on the next apply."""
    _run("beta", wipe_journal=True)
    original = {
        "lock": _load("lock_snapshot.json"),
        "checksum": _load("checksum_rows.json"),
        "stub": _load("module_lock.bzl"),
        "chain": CHAIN_PATH.read_text(encoding="utf-8"),
    }
    CHAIN_PATH.write_text('{"entry_id":"gamma","gen":0,"link_digest":"dead","chain_prefix":"deadbeef"}\n', encoding="utf-8")
    _run("beta", wipe_output=False)
    _assert_chain_prefix_chain()
    assert len(_load_chain_lines()) == 1
    _assert_module_lock_aligned()
    (OUT / "module_lock.bzl").write_text(json.dumps({"entry_id": "beta", "lines": [], "stub_rollup": "00"}) + "\n", encoding="utf-8")
    _run("beta", wipe_output=False)
    assert _load("module_lock.bzl") == original["stub"]
    (OUT / "lock_snapshot.json").write_text(json.dumps({"entry_id": "beta", "rows": []}) + "\n", encoding="utf-8")
    _run("beta", wipe_output=False)
    assert _load("lock_snapshot.json") == original["lock"]
    _assert_tail_matches_active("beta")


def test_p03_alpha_beta_alpha_chain_and_digest_roundtrip() -> None:
    """Returning to alpha after beta must restore digest, pins, tail, and rebuild chain prefix linkage."""
    _run("alpha", wipe_journal=True)
    dig_first = _link_digest(_load("lock_snapshot.json")["rows"], _load("checksum_rows.json")["rows"])
    vers_first = _version_map()
    tail_first = dict(_replay_tail())
    chain_len_first = len(_load_chain_lines())
    _run("beta")
    _assert_chain_prefix_chain()
    _run("alpha")
    dig_second = _link_digest(_load("lock_snapshot.json")["rows"], _load("checksum_rows.json")["rows"])
    assert dig_first == dig_second
    assert _version_map() == vers_first
    assert _version_map()["mod_core"] == "2.1.0"
    assert _slot("alpha")["pins"]["mod_core"] == "2.1.0"
    assert _replay_tail()["entry_id"] == "alpha"
    assert _replay_tail()["seed_digest"] == _expected_seed_digest("alpha")
    assert _replay_tail()["link_digest"] == dig_second
    assert _replay_tail()["gen"] == tail_first["gen"] + 2
    assert len(_load_chain_lines()) == chain_len_first + 2
    _assert_module_lock_aligned()
    _assert_chain_prefix_chain()


def test_p04_stale_seed_digest_forces_recompute() -> None:
    """Corrupted beta slot seed_digest bypasses cache and evicts phantom nodes."""
    _run("beta", wipe_journal=True)
    ledger = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    slot = ledger.setdefault("slots", {}).setdefault("beta", {})
    slot.setdefault("nodes", {})["mod_phantom"] = {"version": "9.9.9", "deps": []}
    slot["seed_digest"] = "stale-digest"
    CLOSURE_PATH.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _run("beta", wipe_output=False)
    modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    assert "mod_phantom" not in modules
    assert {r["repo_key"] for r in _load("lock_snapshot.json")["rows"]} == {
        "mod_graph/1.0.0", "mod_core/2.1.0", "mod_base/1.0.0",
    }
    assert _slot("beta")["seed_digest"] == _expected_seed_digest("beta")
    _assert_tail_matches_active("beta")


def test_p06_beta_survives_detour_and_chain_wipe_recovery() -> None:
    """Beta closure must survive delta/epsilon detours and rebuild chain witness after journal wipe."""
    _run("beta", wipe_journal=True)
    beta_keys = {r["repo_key"] for r in _load("lock_snapshot.json")["rows"]}
    beta_pins = dict(_slot("beta")["pins"])
    beta_dig = _slot("beta")["link_digest"]
    _run("delta")
    assert _version_map()["mod_core"] == "3.0.0"
    _run("epsilon")
    assert _version_map()["mod_core"] == "2.1.0"
    CHAIN_PATH.unlink(missing_ok=True)
    _run("beta", wipe_output=False)
    keys = {r["repo_key"] for r in _load("lock_snapshot.json")["rows"]}
    assert keys == beta_keys
    assert _slot("beta")["pins"] == beta_pins
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == beta_dig
    assert len(_load_chain_lines()) == 1
    _assert_chain_prefix_chain()
    _assert_tail_matches_active("beta")


def test_p07_mirror_isolation_and_stale_seed_on_return() -> None:
    """Legacy mirror must stay scoped; stale epsilon seed_digest must force rebuild without pin drift."""
    _run("gamma", wipe_journal=True)
    gamma_pins = dict(_slot("gamma")["pins"])
    _run("epsilon")
    epsilon_pins = dict(_slot("epsilon")["pins"])
    ledger = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    ledger["slots"]["epsilon"]["seed_digest"] = "stale-seed"
    CLOSURE_PATH.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _run("epsilon", wipe_output=False)
    assert _slot("epsilon")["seed_digest"] == _expected_seed_digest("epsilon")
    assert _slot("epsilon")["pins"] == epsilon_pins
    _run("alpha")
    repo = _load("repo_table.bzl")
    for row in repo["rows"]:
        assert "mirror.example" not in row["url"]
    assert _slot("gamma")["pins"] == gamma_pins
    assert _slot("epsilon")["pins"] == epsilon_pins
    _assert_module_lock_aligned()


def test_p09_alpha_closure_excludes_unreached_modules() -> None:
    """Alpha seed closure must not include modules outside the transitive graph."""
    _run("alpha", wipe_journal=True)
    modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    assert modules == {"mod_core", "mod_base"}
    assert set(_slot("alpha").get("nodes", {}).keys()) == modules
    assert _slot("alpha")["pins"]["mod_core"] == "2.1.0"
    assert _slot("alpha")["seed_digest"] == _expected_seed_digest("alpha")
    _assert_tail_matches_active("alpha")


def test_p10_tour_then_mid_chain_corrupt_restores_snapshots() -> None:
    """Mid-chain prefix corruption must rebuild witness yet preserve per-entry slot digests on return."""
    _run("alpha", wipe_journal=True)
    snapshots: dict[str, str] = {}
    for entry in ("beta", "gamma", "delta", "epsilon", "alpha"):
        _run(entry)
        lock = _load("lock_snapshot.json")
        checksum = _load("checksum_rows.json")
        snapshots[entry] = _link_digest(lock["rows"], checksum["rows"])
    lines = CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 3
    mid = json.loads(lines[1])
    mid["chain_prefix"] = "deadbeef"
    lines[1] = json.dumps(mid, separators=(",", ":"))
    CHAIN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for entry in ("gamma", "delta", "epsilon"):
        _run(entry, wipe_output=False)
        lock = _load("lock_snapshot.json")
        checksum = _load("checksum_rows.json")
        assert _link_digest(lock["rows"], checksum["rows"]) == snapshots[entry]
        _assert_chain_prefix_chain()


def test_p12_foreign_replay_tail_invalidates_hydrate() -> None:
    """A replay tail stamped for another entry must not satisfy hydrate for the active entry."""
    _run("beta", wipe_journal=True)
    beta_modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    chain_before = len(_load_chain_lines())
    TAIL_PATH.write_text(
        json.dumps(
            {
                "entry_id": "gamma",
                "seed_digest": _expected_seed_digest("gamma"),
                "link_digest": "deadbeef",
                "gen": _replay_gen(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _run("beta", wipe_output=False)
    assert {r["module_id"] for r in _load("lock_snapshot.json")["rows"]} == beta_modules
    _assert_tail_matches_active("beta")
    assert len(_load_chain_lines()) == chain_before + 1
    _assert_chain_prefix_chain()


def test_p13_wipe_output_and_tail_then_recover_same_seal() -> None:
    """Wiping output and replay tail on a cache hit must restore prior beta seal and tail."""
    _run("beta", wipe_journal=True)
    expected_dig = _slot("beta")["link_digest"]
    shutil.rmtree(OUT)
    TAIL_PATH.unlink(missing_ok=True)
    _run("beta", wipe_output=False)
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == expected_dig
    _assert_tail_matches_active("beta")
    _assert_chain_prefix_chain()


def test_p14_sixteen_apply_chain_gen_and_prefix_monotonic() -> None:
    """Sixteen consecutive applies must advance replay_gen, tail.gen, and chain prefix linkage together."""
    sequence = [
        "alpha", "beta", "gamma", "delta", "epsilon", "alpha", "beta", "gamma",
        "delta", "beta", "epsilon", "alpha", "gamma", "delta", "epsilon", "beta",
    ]
    _run("alpha", wipe_journal=True)
    expected_gen = _replay_gen()
    assert expected_gen >= 1
    for entry in sequence:
        _run(entry)
        expected_gen += 1
        assert _replay_gen() == expected_gen
        assert _replay_tail()["gen"] == expected_gen
        assert _replay_tail()["entry_id"] == entry
        chain = _load_chain_lines()
        assert chain[-1]["entry_id"] == entry
        assert chain[-1]["gen"] == expected_gen
        _assert_chain_prefix_chain()
        _assert_module_lock_aligned()
        _assert_tail_matches_active(entry)


def test_p15_mid_chain_prefix_corruption_rebuilds_witness() -> None:
    """Breaking prefix linkage on a middle chain line must force witness rebuild, not append past corruption."""
    _run("alpha", wipe_journal=True)
    for entry in ("beta", "gamma", "delta"):
        _run(entry)
    lines = CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 3
    mid = json.loads(lines[1])
    mid["chain_prefix"] = "deadbeef"
    lines[1] = json.dumps(mid, separators=(",", ":"))
    CHAIN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    delta_modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    _run("delta", wipe_output=False)
    assert {r["module_id"] for r in _load("lock_snapshot.json")["rows"]} == delta_modules
    assert len(_load_chain_lines()) == 1
    _assert_chain_prefix_chain()
    _assert_tail_matches_active("delta")
