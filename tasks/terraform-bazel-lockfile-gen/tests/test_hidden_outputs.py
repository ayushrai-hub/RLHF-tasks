"""Hidden verifier edge cases for terraform-bazel-lockfile-gen."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

APP = Path("/app")
OUT = APP / "output"
JOURNAL = APP / "environment" / ".runtime" / "journal"
ENV = APP / "environment"
TAIL_PATH = JOURNAL / "replay_tail.json"
CHAIN_PATH = JOURNAL / "replay_chain.jsonl"
HARNESS = Path("/tests/support/run_apply_checks.sh")
PAYLOAD_PATH = ENV / "svc_c" / "fixtures" / "payload.json"
ROOTS_INDEX = ENV / "meta" / "roots_index.json"
ROOTS_DIR = ENV / "fixtures" / "roots"
AMENDMENTS = ENV / "docs" / "vol_h" / "amendments"


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


def _epoch_state() -> dict[str, int]:
    path = JOURNAL / "epoch.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _slot(entry: str) -> dict:
    ledger = json.loads((JOURNAL / "closure.json").read_text(encoding="utf-8"))
    slots = ledger.get("slots", {})
    assert entry in slots, f"missing journal slot for entry {entry}"
    return slots[entry]


def _replay_gen() -> int:
    path = JOURNAL / "replay_gen.json"
    if not path.is_file():
        return 0
    return json.loads(path.read_text(encoding="utf-8")).get("gen", 0)


def _replay_tail() -> dict:
    assert TAIL_PATH.is_file(), "replay_tail.json missing"
    return json.loads(TAIL_PATH.read_text(encoding="utf-8"))


def _depot_checksum(mod: str) -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/catalog", timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise AssertionError(f"Sidecar unreachable: {exc}") from exc
    return data["packages"][mod]["checksum"]


def _version_map() -> dict[str, str]:
    lock = _load("lock_snapshot.json")
    return {r["module_id"]: r["version"] for r in lock["rows"]}


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


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stop_depot() -> None:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            cmdline = (proc / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "ignore")
        except OSError:
            continue
        if "/app/environment/bin/depotd" in cmdline:
            try:
                os.kill(int(proc.name), signal.SIGTERM)
            except OSError:
                pass
    time.sleep(0.2)


def _assert_module_lock_aligned() -> None:
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    stub = _load("module_lock.bzl")
    keys = sorted(r["repo_key"] for r in lock["rows"])
    digest = {r["repo_key"]: r["digest"] for r in checksum["rows"]}
    expected_lines = [f"lock({k},{digest[k]})" for k in keys]
    assert stub["lines"] == expected_lines


def test_h01_epoch_chain_head_full_rotation() -> None:
    """Each entry accrues epoch counters and the replay-chain head tracks the final apply."""
    _run("alpha", wipe_journal=True)
    for entry in ("beta", "gamma", "delta", "epsilon", "alpha"):
        _run(entry)
    state = _epoch_state()
    assert state.get("beta", 0) == 1
    assert state.get("gamma", 0) == 1
    assert state.get("delta", 0) == 1
    assert state.get("epsilon", 0) == 1
    assert state.get("alpha", 0) == 2
    chain = _load_chain_lines()
    assert chain[-1]["entry_id"] == "alpha"
    assert chain[-1]["gen"] == _replay_gen()
    assert _replay_tail()["gen"] == _replay_gen()
    _assert_chain_prefix_chain()


def test_h02_slot_seal_matches_emitted_link_digest() -> None:
    """Active slot link_digest, replay tail, and emitted artifacts must agree."""
    _run("epsilon", wipe_journal=True)
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    expected = _link_digest(lock["rows"], checksum["rows"])
    slot = _slot("epsilon")
    tail = _replay_tail()
    assert slot.get("seed_digest") == _expected_seed_digest("epsilon")
    assert slot.get("link_digest") == expected
    assert slot.get("sealed_at_gen") == _replay_gen()
    assert tail["entry_id"] == "epsilon"
    assert tail["link_digest"] == expected
    assert tail["gen"] == _replay_gen()
    _assert_module_lock_aligned()


def test_h03_long_chain_binds_tail_seed_and_chain_gen() -> None:
    """Eight-step rotation must keep tail seed_digest, replay_gen, and chain tail gen aligned each step."""
    sequence = ["beta", "alpha", "gamma", "epsilon", "delta", "beta", "epsilon", "alpha"]
    _run("alpha", wipe_journal=True)
    for entry in sequence:
        _run(entry)
        tail = _replay_tail()
        chain = _load_chain_lines()
        assert tail["seed_digest"] == _expected_seed_digest(entry)
        assert tail["gen"] == _replay_gen()
        assert chain[-1]["gen"] == _replay_gen()
        assert chain[-1]["entry_id"] == entry
        _assert_chain_prefix_chain()
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    by_key = {r["repo_key"]: r["digest"] for r in checksum["rows"]}
    for row in lock["rows"]:
        assert by_key[row["repo_key"]] == _depot_checksum(row["module_id"])
    assert lock["entry_id"] == "alpha"
    assert _version_map()["mod_core"] == "2.1.0"
    _assert_module_lock_aligned()


def test_h04_wiped_output_and_stale_tail_forces_seal_rebuild() -> None:
    """Deleted output plus stale tail link_digest must rebuild seal without losing beta slot nodes."""
    _run("beta", wipe_journal=True)
    beta_nodes = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    expected_dig = _slot("beta")["link_digest"]
    chain_len = len(_load_chain_lines())
    shutil.rmtree(OUT)
    tail = _replay_tail()
    tail["link_digest"] = "deadbeef"
    TAIL_PATH.write_text(json.dumps(tail) + "\n", encoding="utf-8")
    _run("beta", wipe_output=False)
    assert {r["module_id"] for r in _load("lock_snapshot.json")["rows"]} == beta_nodes
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == expected_dig
    assert _replay_tail()["entry_id"] == "beta"
    assert len(_load_chain_lines()) == chain_len + 1
    _assert_chain_prefix_chain()


def test_h05_injected_alpha_nodes_evicted_on_return() -> None:
    """Delta nodes injected into the alpha slot must be evicted on the next alpha apply."""
    sequence = ["alpha", "delta", "epsilon", "beta", "delta", "epsilon"]
    _run("alpha", wipe_journal=True)
    alpha_modules = set(_slot("alpha")["nodes"].keys())
    alpha_pins = dict(_slot("alpha")["pins"])
    for entry in sequence:
        _run(entry)
    _run("delta")
    delta_nodes = dict(_slot("delta")["nodes"])
    ledger = json.loads((JOURNAL / "closure.json").read_text(encoding="utf-8"))
    ledger["slots"]["alpha"]["nodes"] = delta_nodes
    ledger["slots"]["alpha"]["seed_digest"] = "stale-alpha"
    (JOURNAL / "closure.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _run("alpha", wipe_output=False)
    assert set(_slot("alpha")["nodes"].keys()) == alpha_modules
    assert _slot("alpha")["pins"] == alpha_pins
    assert _slot("alpha")["seed_digest"] == _expected_seed_digest("alpha")


def test_h06_gamma_mirror_scoped_after_beta_return() -> None:
    """Beta return must not leak mirror hosts while gamma slot keeps legacy mirror only on mod_legacy."""
    _run("gamma", wipe_journal=True)
    gamma_mirror = next(r["url"] for r in _load("repo_table.bzl")["rows"] if r["module_id"] == "mod_legacy")
    assert gamma_mirror == "https://mirror.example/legacy"
    _run("beta")
    for row in _load("repo_table.bzl")["rows"]:
        assert "mirror.example" not in row["url"]
    _run("gamma")
    assert next(r["url"] for r in _load("repo_table.bzl")["rows"] if r["module_id"] == "mod_legacy") == gamma_mirror
    for row in _load("repo_table.bzl")["rows"]:
        if row["module_id"] != "mod_legacy":
            assert "mirror.example" not in row["url"]


def test_h07_tampered_beta_sealed_at_gen_rebuilds_tail() -> None:
    """Stale beta sealed_at_gen must force tail and slot seal rebuild on return from gamma."""
    _run("beta", wipe_journal=True)
    beta_modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    expected_dig = _slot("beta")["link_digest"]
    _run("gamma")
    ledger = json.loads((JOURNAL / "closure.json").read_text(encoding="utf-8"))
    ledger["slots"]["beta"]["sealed_at_gen"] = 0
    (JOURNAL / "closure.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _run("beta", wipe_output=False)
    assert {r["module_id"] for r in _load("lock_snapshot.json")["rows"]} == beta_modules
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == expected_dig
    assert _slot("beta")["sealed_at_gen"] == _replay_gen()
    assert _replay_tail()["link_digest"] == expected_dig


def test_h08_phantom_gamma_and_stale_seed_do_not_poison_beta() -> None:
    """Inactive gamma phantom slot plus stale beta seed must not change beta closure on re-apply."""
    _run("beta", wipe_journal=True)
    beta_modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    closure = JOURNAL / "closure.json"
    ledger = json.loads(closure.read_text(encoding="utf-8"))
    ledger.setdefault("slots", {})["gamma"] = {
        "seed_digest": "mod_legacy|legacy",
        "nodes": {"mod_phantom": {"version": "9.9.9", "deps": []}},
        "pins": {"mod_phantom": "9.9.9"},
        "link_digest": "deadbeef",
        "sealed_at_gen": 0,
    }
    ledger["slots"]["beta"]["seed_digest"] = "stale-beta"
    closure.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    _run("beta", wipe_output=False)
    assert {r["module_id"] for r in _load("lock_snapshot.json")["rows"]} == beta_modules
    assert _slot("beta")["seed_digest"] == _expected_seed_digest("beta")


def test_h09_epsilon_chain_corruption_restores_graph_pin() -> None:
    """Epsilon graph pin must survive chain-prefix corruption and witness rebuild."""
    _run("epsilon", wipe_journal=True)
    versions = _version_map()
    assert versions["mod_core"] == "2.1.0"
    chain_lines = CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    bad = json.loads(chain_lines[-1])
    bad["chain_prefix"] = "deadbeef"
    chain_lines[-1] = json.dumps(bad, separators=(",", ":"))
    CHAIN_PATH.write_text("\n".join(chain_lines) + "\n", encoding="utf-8")
    _run("epsilon", wipe_output=False)
    assert _version_map()["mod_core"] == "2.1.0"
    assert "mod_core/3.0.0" not in {r["repo_key"] for r in _load("lock_snapshot.json")["rows"]}
    assert len(_load_chain_lines()) == 1
    _assert_chain_prefix_chain()
    assert _slot("epsilon")["pins"]["mod_core"] == "2.1.0"


def test_h10_interleaved_chain_then_prefix_corrupt_restores_snapshots() -> None:
    """Ten-step tour snapshots must survive corrupting the final chain prefix before alpha return."""
    sequence = ["beta", "gamma", "epsilon", "delta", "alpha", "gamma", "beta", "delta", "epsilon", "alpha"]
    _run("alpha", wipe_journal=True)
    snapshots: dict[str, str] = {}
    for entry in sequence:
        _run(entry)
        lock = _load("lock_snapshot.json")
        checksum = _load("checksum_rows.json")
        dig = _link_digest(lock["rows"], checksum["rows"])
        snapshots[entry] = dig
        _assert_chain_prefix_chain()
    lines = CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    bad = json.loads(lines[-1])
    bad["chain_prefix"] = "deadbeef"
    lines[-1] = json.dumps(bad, separators=(",", ":"))
    CHAIN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _run("alpha", wipe_output=False)
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == snapshots["alpha"]
    assert len(_load_chain_lines()) == 1
    _assert_chain_prefix_chain()


def test_h11_tail_wipe_and_chain_corrupt_rebuilds_epsilon_seal() -> None:
    """Deleted tail plus corrupt chain prefix must rebuild epsilon seal and single-line witness."""
    _run("epsilon", wipe_journal=True)
    expected = _slot("epsilon")["link_digest"]
    chain_lines = CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    bad = json.loads(chain_lines[-1])
    bad["chain_prefix"] = "deadbeef"
    chain_lines[-1] = json.dumps(bad, separators=(",", ":"))
    CHAIN_PATH.write_text("\n".join(chain_lines) + "\n", encoding="utf-8")
    TAIL_PATH.unlink(missing_ok=True)
    _run("epsilon", wipe_output=False)
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == expected
    tail = _replay_tail()
    assert tail["entry_id"] == "epsilon"
    assert tail["link_digest"] == expected
    assert len(_load_chain_lines()) == 1
    _assert_chain_prefix_chain()


def test_h12_corrupt_chain_prefix_forces_hydrate_miss() -> None:
    """A broken chain prefix must invalidate hydrate and rebuild prefix linkage on re-apply."""
    _run("delta", wipe_journal=True)
    delta_modules = {r["module_id"] for r in _load("lock_snapshot.json")["rows"]}
    chain_lines = CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    assert len(chain_lines) >= 1
    bad = json.loads(chain_lines[-1])
    bad["chain_prefix"] = "deadbeef"
    chain_lines[-1] = json.dumps(bad, separators=(",", ":"))
    CHAIN_PATH.write_text("\n".join(chain_lines) + "\n", encoding="utf-8")
    _run("delta", wipe_output=False)
    assert {r["module_id"] for r in _load("lock_snapshot.json")["rows"]} == delta_modules
    assert len(_load_chain_lines()) == 1
    _assert_chain_prefix_chain()
    assert _replay_tail()["entry_id"] == "delta"
    assert _slot("delta")["link_digest"] == _replay_tail()["link_digest"]


def test_h13_dynamic_root_uses_generic_policy_pin_and_lowest_dep_pin() -> None:
    """Verifier-added zeta root must honor generic amendment pins and lowest dep pins."""
    payload_backup = PAYLOAD_PATH.read_text(encoding="utf-8")
    index_backup = ROOTS_INDEX.read_text(encoding="utf-8")
    zeta_root = ROOTS_DIR / "root_zeta.json"
    amend_path = AMENDMENTS / "zeta_probe.html"
    zeta_packages = {
        "mod_combo": {
            "versions": ["1.0.0"],
            "latest": "1.0.0",
            "deps": {"1.0.0": ["mod_left@1.0.0", "mod_right@1.0.0"]},
            "repo": "https://depot.example/mod_combo",
            "checksum": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        },
        "mod_left": {
            "versions": ["1.0.0"],
            "latest": "1.0.0",
            "deps": {"1.0.0": ["mod_base@2.0.0", "mod_shared@1.2.0"]},
            "repo": "https://depot.example/mod_left",
            "checksum": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        },
        "mod_right": {
            "versions": ["1.0.0"],
            "latest": "1.0.0",
            "deps": {"1.0.0": ["mod_base@1.0.0", "mod_shared@1.1.0"]},
            "repo": "https://depot.example/mod_right",
            "checksum": "1111111111111111111111111111111111111111111111111111111111111111",
        },
        "mod_shared": {
            "versions": ["1.0.0", "1.1.0", "1.2.0"],
            "latest": "1.2.0",
            "deps": {"1.0.0": [], "1.1.0": [], "1.2.0": []},
            "repo": "https://depot.example/mod_shared",
            "checksum": "2222222222222222222222222222222222222222222222222222222222222222",
        },
    }
    try:
        payload = json.loads(payload_backup)
        payload["packages"].update(zeta_packages)
        _write_json(PAYLOAD_PATH, payload)
        _write_json(zeta_root, {"storage_class": "standard", "seeds": ["mod_combo"]})
        index = json.loads(index_backup)
        index["entries"]["zeta"] = "root_zeta.json"
        _write_json(ROOTS_INDEX, index)
        amend_path.write_text(
            "<p>For root matrix entry zeta, module mod_base must remain on series 1.0.0.</p>\n",
            encoding="utf-8",
        )
        _stop_depot()
        _run("zeta", wipe_journal=True)
        versions = _version_map()
        assert versions["mod_base"] == "1.0.0"
        assert versions["mod_combo"] == "1.0.0"
        assert versions["mod_left"] == "1.0.0"
        assert versions["mod_right"] == "1.0.0"
        assert versions["mod_shared"] == "1.1.0"
        checksum = _load("checksum_rows.json")
        for row in checksum["rows"]:
            mod = row["repo_key"].split("/")[0]
            assert row["digest"] == _depot_checksum(mod)
    finally:
        PAYLOAD_PATH.write_text(payload_backup, encoding="utf-8")
        ROOTS_INDEX.write_text(index_backup, encoding="utf-8")
        zeta_root.unlink(missing_ok=True)
        amend_path.unlink(missing_ok=True)
        _stop_depot()


def test_h14_live_catalog_checksum_rotation_reseals_cached_slot() -> None:
    """Live sidecar checksum rotation must reseal cached beta outputs without wiping output."""
    payload_backup = PAYLOAD_PATH.read_text(encoding="utf-8")
    new_checksum = "9" * 64
    try:
        _run("beta", wipe_journal=True)
        old_dig = _slot("beta")["link_digest"]
        payload = json.loads(payload_backup)
        payload["packages"]["mod_graph"]["checksum"] = new_checksum
        _write_json(PAYLOAD_PATH, payload)
        _stop_depot()
        _run("beta", wipe_output=False)
        checksum = _load("checksum_rows.json")
        graph_row = next(r for r in checksum["rows"] if r["repo_key"].startswith("mod_graph/"))
        assert graph_row["digest"] == new_checksum
        _assert_module_lock_aligned()
        lock = _load("lock_snapshot.json")
        new_dig = _link_digest(lock["rows"], checksum["rows"])
        assert new_dig != old_dig
        assert _slot("beta")["link_digest"] == new_dig
        assert _replay_tail()["link_digest"] == new_dig
    finally:
        PAYLOAD_PATH.write_text(payload_backup, encoding="utf-8")
        _stop_depot()


def test_h15_malformed_replay_chain_line_forces_witness_rebuild() -> None:
    """Malformed replay-chain records must force a single genesis-linked witness rebuild."""
    _run("delta", wipe_journal=True)
    expected = _slot("delta")["link_digest"]
    with CHAIN_PATH.open("a", encoding="utf-8") as handle:
        handle.write("not-json-chain-row\n")
    _run("delta", wipe_output=False)
    chain = _load_chain_lines()
    assert len(chain) == 1
    assert chain[0]["chain_prefix"] == "genesis"
    assert chain[0]["entry_id"] == "delta"
    lock = _load("lock_snapshot.json")
    checksum = _load("checksum_rows.json")
    assert _link_digest(lock["rows"], checksum["rows"]) == expected
    assert _replay_tail()["entry_id"] == "delta"
    assert _replay_tail()["link_digest"] == expected
    assert _slot("delta")["link_digest"] == expected
    _assert_chain_prefix_chain()
