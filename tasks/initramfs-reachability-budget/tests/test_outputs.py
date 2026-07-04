"""Verifier for reconstructed HARD q7 grid packs."""

import hashlib
import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest

MAX_GZIP_BYTES = 4800
PACKS = ("sc_w1", "sc_c2", "sc_h3", "sc_j4")

ENV = Path("/app/environment")
TESTS = Path(__file__).resolve().parent
DRV_BIN = "/app/environment/tools/drv_q7/drv_q7"
CPIO_CHK = "/app/environment/tools/cpio_chk/cpio_chk"
CPIO_CHK_DIR = ENV / "tools" / "cpio_chk"
CPIO_CHK_SHA256 = {
    "engine.go": "e61bf090c153486ccc8987969565ffb361f4ebe47db1f4c6d074bed5966f7c31",
    "go.mod": "dd6c23b119471d4697774538c64626188fca4b39838ca5e611ba678abb677406",
    "main.go": "3a16b63270f11230c46b3d2107b6a0e5da84728683ac0632c67a0089b836b76a",
}
SCRATCH = Path("/app/output/scratch")
INC_STORE = Path("/app/output/inc_store/seed.json")
INC_FIXTURE = ENV / "fixtures" / "inc_seed.json"


def _load_lane(pack: str) -> tuple[str, list[str]]:
    raw = (ENV / "vstamp_v" / f"{pack}_vstamp.toml").read_bytes()
    doc = tomllib.loads(raw.decode())
    return doc["lane_class"], list(doc["required"])


def _load_registry(deps_path: Path) -> dict[str, list[str]]:
    doc = json.loads(deps_path.read_text())
    registry: dict[str, list[str]] = {}
    for entry in doc.get("nodes", []):
        registry[entry["id"]] = list(entry.get("deps", []))
    for node_id, meta in doc.get("registry", {}).items():
        if node_id in registry:
            continue
        if isinstance(meta, list):
            registry[node_id] = list(meta)
        else:
            registry[node_id] = list(meta.get("deps", []))
    return registry


def _closure_rows(registry: dict[str, list[str]], seeds: list[str]) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    pending = list(seeds)
    while pending:
        node_id = pending.pop()
        if node_id in rows:
            continue
        node = registry.get(node_id)
        if node is None:
            continue
        rows[node_id] = list(node)
        for dep in reversed(node):
            if dep not in rows:
                pending.append(dep)
    return rows


def _resolve_required_warm(req: str, rows: dict[str, list[str]]) -> str:
    return req if req in rows else ""


def _resolve_required_cold(
    req: str,
    rows: dict[str, list[str]],
    alias_map: dict[str, str],
    blob_sizes: dict[str, int],
) -> str:
    seen: set[str] = set()
    current = req
    cycle: list[str] = []
    while True:
        seen.add(current)
        cycle.append(current)
        nxt = alias_map.get(current)
        if nxt is None:
            break
        if nxt in seen:
            largest = cycle[0]
            max_size = blob_sizes.get(largest, 0)
            for node in cycle:
                size = blob_sizes.get(node, 0)
                if size > max_size or (size == max_size and node < largest):
                    largest = node
                    max_size = size
            return largest
        current = nxt
    if current in rows:
        return current
    if current != req:
        return current
    return ""


def _resolve_deps(
    deps: list[str],
    lane_class: str,
    rows: dict[str, list[str]],
    alias_map: dict[str, str],
    blob_sizes: dict[str, int],
    members: set[str],
) -> list[str]:
    resolved: list[str] = []
    for dep in deps:
        if lane_class == "W":
            target = dep if dep in rows else ""
        else:
            target = _resolve_required_cold(dep, rows, alias_map, blob_sizes)
        if target and target in members:
            resolved.append(target)
    return resolved


def _survivor_graph(pack: str) -> tuple[list[str], dict[str, list[str]]]:
    deps_path = ENV / "node_v" / f"{pack}_deps.json"
    doc = json.loads(deps_path.read_text())
    registry = _load_registry(deps_path)
    seeds = doc.get("seeds")
    if seeds is None:
        seeds = list(registry)
    rows = _closure_rows(registry, seeds)

    lane_class, required = _load_lane(pack)
    rel_doc = json.loads((ENV / "rel_v" / f"{pack}_rel.json").read_text())
    alias_map = rel_doc.get("map", {})
    blob_doc = json.loads((ENV / "blob_v" / f"{pack}_blobs.json").read_text())
    blob_sizes = blob_doc["sizes"]

    survivors: list[str] = []
    req_for_survivor: dict[str, str] = {}
    seen: set[str] = set()
    for req in required:
        if lane_class == "W":
            target = _resolve_required_warm(req, rows)
        else:
            target = _resolve_required_cold(req, rows, alias_map, blob_sizes)
        if not target or target in seen:
            continue
        seen.add(target)
        survivors.append(target)
        req_for_survivor[target] = req

    member_set = set(survivors)
    deps_by_survivor: dict[str, list[str]] = {}
    for target, req in req_for_survivor.items():
        deps_by_survivor[target] = _resolve_deps(
            list(rows.get(req, [])),
            lane_class,
            rows,
            alias_map,
            blob_sizes,
            member_set,
        )

    return survivors, deps_by_survivor


def _kahn_lex_order(members: list[str], deps_by_node: dict[str, list[str]]) -> list[str]:
    out_edges: dict[str, list[str]] = {}
    in_degree = {node: 0 for node in members}
    member_set = set(members)
    for node in members:
        for dep in deps_by_node.get(node, []):
            if dep not in member_set:
                continue
            out_edges.setdefault(dep, []).append(node)
            in_degree[node] += 1

    available = sorted(node for node, deg in in_degree.items() if deg == 0)
    order: list[str] = []
    while available:
        current = available[0]
        available = available[1:]
        order.append(current)
        for child in out_edges.get(current, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                available.append(child)
                available.sort()
    if len(order) != len(members):
        raise AssertionError(f"dependency cycle among survivors: {members}")
    return order


def _canonical_bundle_order(pack: str) -> list[str]:
    members, deps_by_node = _survivor_graph(pack)
    return _kahn_lex_order(members, deps_by_node)

def _env() -> dict[str, str]:
    out = os.environ.copy()
    out["Q7_ENV_ROOT"] = "/app/environment"
    out["Q7_DRV_BIN"] = str(ENV / "tools" / "drv_q7" / "drv_q7")
    return out

def rebuild() -> None:
    subprocess.run(["bash", "/app/environment/scripts/build_q7.sh"], check=True, env=_env())

def run_batch() -> None:
    subprocess.run(["bash", "/app/environment/scripts/batch_q7.sh"], check=True, env=_env())

def recover_inc_store() -> None:
    subprocess.run(["bash", "/app/environment/migrations/rst7.sh", "recover"], check=True, env=_env())

@pytest.fixture(scope="module")
def graded() -> dict[str, str]:
    rebuild()
    recover_inc_store()
    run_batch()
    return {}

def test_cpio_chk_sources_unchanged() -> None:
    """Ensures verification tool sources under cpio_chk were not modified."""
    for name, expected in CPIO_CHK_SHA256.items():
        path = CPIO_CHK_DIR / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"{name} was modified"

def test_concurrent_inc_seq_no_lost_updates(graded: dict[str, str]) -> None:
    """Verifies that running the 4 matrix legs concurrently increments seq by exactly 4 with no lost updates."""
    recover_inc_store()
    text = INC_STORE.read_text()
    before = json.loads(text)["seq"]
    run_batch()
    text2 = INC_STORE.read_text()
    after = json.loads(text2)["seq"]
    assert after == before + 4

def test_topological_bundle_ordering(graded: dict[str, str]) -> None:
    """Verifies bundle plaintext uses Kahn topological order with lexicographic tie-break."""
    for pack in PACKS:
        bundle_path = SCRATCH / (pack + "_bu" + "ndl" + "e.c" + "pio" + ".gz")
        proc = subprocess.run(
            ["gzip", "-dc", str(bundle_path)], capture_output=True, check=True, text=True
        )
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        actual_order = [line.split("|")[0] for line in lines]
        expected_order = _canonical_bundle_order(pack)
        assert actual_order == expected_order, (
            f"{pack}: expected {expected_order}, got {actual_order}"
        )


def test_dependency_order_beats_alphabetical(graded: dict[str, str]) -> None:
    """sc_j4 diamond deps require j4 before j2 even though j2 sorts earlier alphabetically."""
    bundle_path = SCRATCH / ("sc_j4_bu" + "ndl" + "e.c" + "pio" + ".gz")
    proc = subprocess.run(
        ["gzip", "-dc", str(bundle_path)], capture_output=True, check=True, text=True
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    actual_order = [line.split("|")[0] for line in lines]
    alpha_order = sorted(actual_order)
    assert alpha_order == ["j0", "j1", "j2", "j4"]
    assert actual_order == ["j0", "j1", "j4", "j2"]
    assert actual_order != alpha_order


def test_sc_h3_alias_dep_ordering(graded: dict[str, str]) -> None:
    """Held pack resolves b3->a2 dependency through alias cycle to z8 before b3."""
    bundle_path = SCRATCH / ("sc_h" + "3_bu" + "ndl" + "e.c" + "pio" + ".gz")
    proc = subprocess.run(
        ["gzip", "-dc", str(bundle_path)], capture_output=True, check=True, text=True
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    actual_order = [line.split("|")[0] for line in lines]
    expected = _canonical_bundle_order("sc_h3")
    assert actual_order == expected
    assert actual_order.index("z8") < actual_order.index("b3")

def test_transitive_alias_with_cycles(graded: dict[str, str]) -> None:
    """Verifies that a cyclic alias correctly resolves to the largest byte size in the cycle."""
    ledger_path = SCRATCH / ("sc_h" + "3_l" + "edg" + "er." + "jso" + "n")
    text = ledger_path.read_text()
    doc = json.loads(text)
    blob_ids = {row["blob_id"] for row in doc["rows"]}
    assert "z8" in blob_ids
    assert "x9" not in blob_ids
    assert "a2" not in blob_ids

def test_audit_trail_consistency(graded: dict[str, str]) -> None:
    """Validates audit_trail mirrors incremental-store bump history from concurrent builds."""
    recover_inc_store()
    run_batch()
    run_batch()

    ledger_path = SCRATCH / ("sc_j" + "4_l" + "edg" + "er." + "jso" + "n")
    text = ledger_path.read_text()
    doc = json.loads(text)
    trail = doc.get("audit_trail", [])

    store = json.loads(INC_STORE.read_text())
    history = store.get("history", [])
    assert store["seq"] == 9
    assert history == [2, 3, 4, 5, 6, 7, 8, 9]
    # sc_j4 ledger is written before its own bump in the second batch.
    assert 4 <= len(trail) <= 7
    assert trail == history[: len(trail)]

def test_stage_a_gating(graded: dict[str, str]) -> None:
    """Verifies that when seq < 0, stage A does not walk the transitive registry."""
    subprocess.run(["bash", "/app/environment/migrations/rst7.sh", "clean"], check=True, env=_env())
    run_batch()
    ledger_path = SCRATCH / ("sc_w" + "1_l" + "edg" + "er." + "jso" + "n")
    text = ledger_path.read_text()
    doc = json.loads(text)
    blob_ids = {row["blob_id"] for row in doc["rows"]}
    assert "k2" in blob_ids
    assert "k1" not in blob_ids
    assert "k0" not in blob_ids
    recover_inc_store()
    run_batch()

def test_terminal_files(graded: dict[str, str]) -> None:
    """Verifies that cpio_chk produces the terminal files with correct sizes and digests."""
    bundle_out = Path("/app/output/final_bundle.cpio.gz")
    ledger_out = Path("/app/output/build_ledger.json")
    if bundle_out.exists():
        bundle_out.unlink()
    if ledger_out.exists():
        ledger_out.unlink()

    subprocess.run([
        CPIO_CHK, "--gr" + "id-a" + "ll",
        "--bu" + "ndl" + "e-ou" + "t", str(bundle_out),
        "--le" + "dge" + "r-ou" + "t", str(ledger_out)
    ], check=True, env=_env())

    assert bundle_out.exists()
    assert ledger_out.exists()

    assert bundle_out.stat().st_size <= MAX_GZIP_BYTES

    gold = {}
    for p in Path("/app/environment/blob_v").glob("*blo" + "bs." + "jso" + "n"):
        d = json.loads(p.read_text())
        gold.update(d.get("sizes", {}))

    text = ledger_out.read_text()
    doc = json.loads(text)

    rows = doc.get("rows", [])
    assert len(rows) > 0

    digest_lines = []
    for row in rows:
        bid = row["blob_id"]
        assert bid in gold
        size = gold[bid]
        proc = subprocess.run(
            ["sha" + "256" + "sum"], input=f"{bid}|{size}", capture_output=True, text=True
        )
        expected_fp = proc.stdout[:64]
        assert row["row_fp"] == expected_fp
        digest_lines.append(f"{bid}|{size}")

    proc = subprocess.run(
        ["sha" + "256" + "sum"], input="\n".join(digest_lines), capture_output=True, text=True
    )
    expected_digest = proc.stdout[:64]
    assert doc.get("bundle_digest") == expected_digest
