"""Verifier for the routenet hard-negative sampler.

These tests run the sampler CLI directly (so they catch problems with the
shipped entry point, not just the inner module) and compare the output to
ground truth recomputed from the live PostgreSQL database. They also exercise
the static audit and a determinism check across repeated runs.

The runtime tree under `/app/src/` is the image of the `environment/src/`
sources, copied in at image build time. Any repair under `environment/` shows
up at the `/app/src/` paths the test commands invoke below.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


SEED_A = 17
SEED_B = 4242
K = 128

CANONICAL_NEGATIVES = Path("/app/output/negatives.json")
CANONICAL_AUDIT = Path("/app/output/audit.json")


def run_sampler(out_path, seed, k, env=None):
    env_full = dict(os.environ)
    if env:
        env_full.update(env)
    res = subprocess.run(
        [
            "node",
            "/app/src/cli/sample.js",
            f"--seed={seed}",
            f"--k={k}",
            f"--output={out_path}",
        ],
        capture_output=True,
        text=True,
        env=env_full,
        timeout=120,
    )
    if res.returncode != 0:
        raise AssertionError(
            f"sample CLI exited with code {res.returncode}\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
    with open(out_path, "r") as fh:
        return json.loads(fh.read())


def run_audit(out_path):
    res = subprocess.run(
        [
            "node",
            "/app/scripts/audit.js",
            f"--output={out_path}",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        with open(out_path, "r") as fh:
            payload = fh.read()
    except OSError:
        raise AssertionError(
            f"audit did not produce {out_path}; rc={res.returncode}\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
    return json.loads(payload)


def _canon_pair(pair):
    a, b = int(pair[0]), int(pair[1])
    return (a, b) if a < b else (b, a)


def _pair_set(pairs):
    return {_canon_pair(p) for p in pairs}


@pytest.fixture(scope="session")
def sampler_output_seed_a(output_dir):
    out_path = output_dir / "negatives.alpha.json"
    return run_sampler(out_path, SEED_A, K)


@pytest.fixture(scope="session")
def sampler_output_seed_b(output_dir):
    out_path = output_dir / "negatives.beta.json"
    return run_sampler(out_path, SEED_B, K)


@pytest.fixture(scope="session")
def audit_report(output_dir):
    out_path = output_dir / "audit.json"
    return run_audit(out_path)


def test_canonical_negatives_output_exists():
    """Agent run must leave the canonical negatives artifact on disk."""
    assert CANONICAL_NEGATIVES.is_file(), (
        f"missing canonical output: {CANONICAL_NEGATIVES}"
    )
    blob = json.loads(CANONICAL_NEGATIVES.read_text())
    assert isinstance(blob, dict), "top-level value must be an object"
    for key in ("seed", "k", "source", "negatives"):
        assert key in blob, f"missing required top-level key: {key!r}"
    assert blob["source"] == "postgres", (
        "canonical negatives must be postgres-backed (source='postgres')"
    )
    assert isinstance(blob["negatives"], list), "negatives must be a list"
    assert len(blob["negatives"]) == blob["k"], "negatives length must match k"


def test_canonical_audit_output_exists():
    """Agent run must leave a passing audit report at the canonical path."""
    assert CANONICAL_AUDIT.is_file(), f"missing canonical audit: {CANONICAL_AUDIT}"
    blob = json.loads(CANONICAL_AUDIT.read_text())
    assert blob.get("status") == "ok", (
        f"canonical audit must report status ok, got {blob!r}"
    )


def test_sampler_writes_required_schema(sampler_output_seed_a):
    """The sampler CLI must emit the documented JSON shape."""
    blob = sampler_output_seed_a
    assert isinstance(blob, dict), "top-level value must be an object"
    for key in ("seed", "k", "source", "negatives"):
        assert key in blob, f"missing required top-level key: {key!r}"
    assert blob["seed"] == SEED_A, "seed must echo the --seed argument"
    assert blob["k"] == K, "k must echo the --k argument"
    assert isinstance(blob["negatives"], list), "negatives must be a list"


def test_negatives_have_correct_count_and_shape(sampler_output_seed_a):
    """Each negative is a 2-element list of integers; total count equals k."""
    negatives = sampler_output_seed_a["negatives"]
    assert len(negatives) == K, f"sampler must emit {K} negatives, got {len(negatives)}"
    for pair in negatives:
        assert isinstance(pair, list) and len(pair) == 2, (
            f"each negative must be a 2-element list, got {pair!r}"
        )
        u, v = pair
        assert isinstance(u, int) and isinstance(v, int), (
            f"node ids must be integers, got {(type(u), type(v))}"
        )
        assert u != v, f"negative pair must have distinct endpoints, got [{u}, {v}]"


def test_source_label_marks_postgres_as_origin(sampler_output_seed_a):
    """The on-disk snapshot is no longer the source of truth."""
    assert sampler_output_seed_a["source"] == "postgres", (
        "source field must be the literal string 'postgres'"
    )


def test_node_ids_are_known(sampler_output_seed_a, graph_facts):
    """All sampled nodes must exist in the live nodes table."""
    node_ids = graph_facts["node_ids"]
    for u, v in sampler_output_seed_a["negatives"]:
        assert u in node_ids, f"sampled u={u} is not in the nodes table"
        assert v in node_ids, f"sampled v={v} is not in the nodes table"


def test_negatives_are_unique_unordered_pairs(sampler_output_seed_a):
    """Duplicates (in either orientation) corrupt the negative set."""
    pairs = _pair_set(sampler_output_seed_a["negatives"])
    assert len(pairs) == K, (
        f"required {K} unique unordered pairs, got {len(pairs)} "
        f"(input length was {len(sampler_output_seed_a['negatives'])})"
    )


def test_no_train_edge_leakage(sampler_output_seed_a, graph_facts):
    """No negative may collide with a known train edge."""
    pairs = _pair_set(sampler_output_seed_a["negatives"])
    leaks = pairs & graph_facts["train_edges"]
    assert len(leaks) == 0, f"negatives collide with train edges: {sorted(leaks)}"


def test_no_validation_edge_leakage(sampler_output_seed_a, graph_facts):
    """The original symptom: validation edges leaking into negatives."""
    pairs = _pair_set(sampler_output_seed_a["negatives"])
    leaks = pairs & graph_facts["val_edges"]
    assert len(leaks) == 0, (
        f"negatives collide with validation edges (this corrupts AUC): {sorted(leaks)}"
    )


def test_no_test_edge_leakage(sampler_output_seed_a, graph_facts):
    """Test edges must also be kept out of the negative set."""
    pairs = _pair_set(sampler_output_seed_a["negatives"])
    leaks = pairs & graph_facts["test_edges"]
    assert len(leaks) == 0, f"negatives collide with test edges: {sorted(leaks)}"


def test_graph_distance_constraint(sampler_output_seed_a, graph_facts):
    """Every negative is at distance 2 or 3 in the TRAIN subgraph."""
    distances = graph_facts["distances"]
    bad = [
        ((u, v), distances.get(u, {}).get(v))
        for u, v in sampler_output_seed_a["negatives"]
        if distances.get(u, {}).get(v) is None
        or distances.get(u, {}).get(v) < 2
        or distances.get(u, {}).get(v) > 3
    ]
    assert len(bad) == 0, (
        "negatives violate the train-subgraph distance window [2, 3]: " + str(bad[:8])
    )


def test_second_seed_produces_a_different_set(sampler_output_seed_a, sampler_output_seed_b):
    """Different seeds must not produce the same negatives - otherwise the
    seed is being ignored."""
    a = _pair_set(sampler_output_seed_a["negatives"])
    b = _pair_set(sampler_output_seed_b["negatives"])
    assert a != b, "two different seeds produced the same set of negatives"


def test_second_seed_satisfies_all_invariants(sampler_output_seed_b, graph_facts):
    """The structural guarantees must hold for any seed, not just seed=17."""
    pairs = _pair_set(sampler_output_seed_b["negatives"])
    assert len(pairs) == K
    distances = graph_facts["distances"]
    forbidden = (
        graph_facts["train_edges"]
        | graph_facts["val_edges"]
        | graph_facts["test_edges"]
    )
    intersection = pairs & forbidden
    assert len(intersection) == 0, f"leakage on seed B: {sorted(intersection)}"
    for u, v in pairs:
        d = distances.get(u, {}).get(v)
        assert d is not None and 2 <= d <= 3, (
            f"seed B negative ({u},{v}) has train-distance {d}"
        )


def test_determinism_repeat_same_seed(output_dir, sampler_output_seed_a):
    """Re-running with the same --seed and --k must give the same unordered set."""
    repeat_path = output_dir / "negatives.repeat.json"
    repeat = run_sampler(repeat_path, SEED_A, K)
    assert _pair_set(repeat["negatives"]) == _pair_set(sampler_output_seed_a["negatives"]), (
        "sampler is not deterministic in the seed"
    )


def test_smaller_k_is_consistent(output_dir, graph_facts):
    """Asking for fewer negatives should still satisfy every invariant."""
    out_path = output_dir / "negatives.small.json"
    blob = run_sampler(out_path, seed=3, k=32)
    assert blob["k"] == 32
    pairs = _pair_set(blob["negatives"])
    assert len(pairs) == 32
    forbidden = (
        graph_facts["train_edges"]
        | graph_facts["val_edges"]
        | graph_facts["test_edges"]
    )
    intersection = pairs & forbidden
    assert len(intersection) == 0, f"sampler leaked split edges into negatives: {sorted(intersection)}"
    distances = graph_facts["distances"]
    for u, v in pairs:
        d = distances.get(u, {}).get(v)
        assert d is not None and 2 <= d <= 3


def test_static_audit_reports_ok(audit_report):
    """The shipped audit must accept the repaired sampler source."""
    assert audit_report["status"] == "ok", (
        f"audit failed with violations: {audit_report.get('violations')!r}"
    )
    violations = audit_report.get("violations", [])
    assert isinstance(violations, list), "audit must emit a list of violations"
    assert len(violations) == 0, (
        f"audit found {len(violations)} unresolved violations: {violations!r}"
    )


def test_third_seed_invariants_at_small_cardinality(output_dir, graph_facts):
    """The structural guarantees must hold even at small batch sizes (k=16)
    and at unrelated seeds. This is the cross-seed/cross-k sanity check."""
    out_path = output_dir / "negatives.gamma.json"
    blob = run_sampler(out_path, seed=7, k=16)
    assert blob["k"] == 16
    pairs = _pair_set(blob["negatives"])
    assert len(pairs) == 16, "sampler emitted duplicate pairs at k=16"
    forbidden = (
        graph_facts["train_edges"]
        | graph_facts["val_edges"]
        | graph_facts["test_edges"]
    )
    intersection = pairs & forbidden
    assert len(intersection) == 0, f"leakage at small batch: {sorted(intersection)}"
    distances = graph_facts["distances"]
    for u, v in pairs:
        d = distances.get(u, {}).get(v)
        assert d is not None and 2 <= d <= 3
