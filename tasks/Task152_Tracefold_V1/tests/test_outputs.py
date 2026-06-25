"""Verifier for epoch-scoped patch projection and deferred cursor probing."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

APP = Path("/app")
REPORT = APP / "output" / "tracefold_report.json"
STOCK_SEED = APP / "data" / "seed" / "scenarios.json"
ALT_SEED = Path(__file__).resolve().parent / "data" / "alt_scenarios.json"
TRAP_SEED = Path(__file__).resolve().parent / "data" / "trap_scenarios.json"
RUNTIME_SEED = Path("/tmp/tracefold_v1_runtime.json")
PERMUTED_SEED = Path("/tmp/tracefold_v1_permuted.json")
MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1
CURSOR_SEED = 0x510E527FADE682D1
TOMBSTONE_TAG = 0x9B05688C2B3E6C1F
LINEAGE_SEED = 0x3AC436F52B5D874C
LINEAGE_COMMITTED_TAG = 0xBB589C9EE109634B
LINEAGE_REJECTED_TAG = 0x6D06EEF0001D4E1D
LINEAGE_TOMBSTONE_TAG = 0x4E4BA86B24A11805
LINEAGE_UPDATE_TAG = 0x59F45A2C5FBE7459
DISCARD_SEED = 0x350E77B783BDBB19
DISCARD_COMMITTED_TAG = 0x79807B231990101E
DISCARD_REJECTED_TAG = 0x753ED9C978EF5FBE
DISCARD_TOMBSTONE_TAG = 0x1A0C4EEA92D866DD
DISCARD_UPDATE_TAG = 0x1BF18C857F45647A
_BUILT_RELEASE_ONCE = False

def _rol64(value: int, amount: int) -> int:
    amount %= 64
    value &= MASK64
    return value if amount == 0 else ((value << amount) & MASK64) | (value >> (64 - amount))

def _ror64(value: int, amount: int) -> int:
    amount %= 64
    value &= MASK64
    return value if amount == 0 else (value >> amount) | ((value << (64 - amount)) & MASK64)

def _rol32(value: int, amount: int) -> int:
    amount %= 32
    value &= MASK32
    return value if amount == 0 else ((value << amount) & MASK32) | (value >> (32 - amount))

def _fold(acc: int, patch: dict[str, Any], tombstone: bool) -> int:
    tagged = acc ^ _rol64(patch["patch_id"], 11) ^ (TOMBSTONE_TAG if tombstone else 0)
    delta = 0 if tombstone else patch["delta"]
    mask = 0 if tombstone else patch["toggle_mask"]
    mixed = (
        tagged
        ^ _rol64(patch["seq"], (patch["revision"] & 31) + 1)
        ^ _ror64(delta, patch["seq"] & 31)
        ^ _rol64(mask, 23)
    )
    return (_rol64(mixed, 17) * 0x9E3779B185EBCA87) & MASK64

def _raw_audit_digest(
    seed: dict[str, Any],
    indexes: set[int] | None,
    digest_seed: int,
    committed_tag: int,
    rejected_tag: int,
    tombstone_tag: int,
    update_tag: int,
) -> str:
    acc = (
        digest_seed
        ^ _rol64(seed["lane_id"], 3)
        ^ _rol64(seed["base_epoch"], 9)
        ^ _rol64(seed["base_seq"], 17)
        ^ _ror64(seed["base_value"], 11)
        ^ _rol64(seed["base_flags"], 29)
    )
    for index, patch in enumerate(seed["patches"]):
        if indexes is not None and index not in indexes:
            continue
        mixed = (
            acc
            ^ _rol64(index + 1, 5)
            ^ _rol64(patch["epoch"], 7)
            ^ _rol64(patch["seq"], 13)
            ^ _rol64(patch["revision"], 19)
            ^ _rol64(patch["patch_id"], 31)
            ^ _rol64(patch["lane_id"], 37)
            ^ _ror64(patch["delta"], patch["seq"] & 31)
            ^ _rol64(patch["toggle_mask"], patch["revision"] & 31)
            ^ (committed_tag if patch["committed"] else rejected_tag)
            ^ (tombstone_tag if patch["kind"] == "tombstone" else update_tag)
        )
        acc = (_rol64(mixed, 23) * 0x9E3779B97F4A7C15) & MASK64
    return f"{acc:016x}"

def _winner_indexes(seed: dict[str, Any]) -> set[int]:
    eligible = [
        (index, patch)
        for index, patch in enumerate(seed["patches"])
        if patch["committed"]
        and patch["lane_id"] == seed["lane_id"]
        and patch["epoch"] >= seed["base_epoch"]
        and patch["seq"] > seed["base_seq"]
    ]
    active_epoch = max((patch["epoch"] for _, patch in eligible), default=seed["base_epoch"])
    selected: dict[int, int] = {}
    for index, patch in eligible:
        if patch["epoch"] != active_epoch:
            continue
        current_index = selected.get(patch["seq"])
        if current_index is None:
            selected[patch["seq"]] = index
            continue
        current = seed["patches"][current_index]
        if (patch["revision"], patch["patch_id"]) > (current["revision"], current["patch_id"]):
            selected[patch["seq"]] = index
    return set(selected.values())

def _lineage_digest(seed: dict[str, Any]) -> str:
    return _raw_audit_digest(
        seed,
        None,
        LINEAGE_SEED,
        LINEAGE_COMMITTED_TAG,
        LINEAGE_REJECTED_TAG,
        LINEAGE_TOMBSTONE_TAG,
        LINEAGE_UPDATE_TAG,
    )

def _discard_digest(seed: dict[str, Any]) -> str:
    winners = _winner_indexes(seed)
    discards = set(range(len(seed["patches"]))) - winners
    return _raw_audit_digest(
        seed,
        discards,
        DISCARD_SEED,
        DISCARD_COMMITTED_TAG,
        DISCARD_REJECTED_TAG,
        DISCARD_TOMBSTONE_TAG,
        DISCARD_UPDATE_TAG,
    )
def _projection(seed: dict[str, Any]) -> dict[str, int]:
    eligible = [
        patch
        for patch in seed["patches"]
        if patch["committed"]
        and patch["lane_id"] == seed["lane_id"]
        and patch["epoch"] >= seed["base_epoch"]
        and patch["seq"] > seed["base_seq"]
    ]
    active_epoch = max((patch["epoch"] for patch in eligible), default=seed["base_epoch"])
    selected: dict[int, dict[str, Any]] = {}
    for patch in eligible:
        if patch["epoch"] != active_epoch:
            continue
        current = selected.get(patch["seq"])
        if current is None or (patch["revision"], patch["patch_id"]) > (
            current["revision"],
            current["patch_id"],
        ):
            selected[patch["seq"]] = patch

    cursor = {
        "epoch": seed["base_epoch"],
        "seq": seed["base_seq"],
        "value": seed["base_value"],
        "flags": seed["base_flags"],
        "digest": CURSOR_SEED,
        "applied_count": 0,
        "tombstone_count": 0,
    }
    for seq in sorted(selected):
        patch = selected[seq]
        tombstone = patch["kind"] == "tombstone"
        cursor["epoch"] = patch["epoch"]
        cursor["seq"] = patch["seq"]
        if tombstone:
            cursor["tombstone_count"] += 1
        else:
            cursor["value"] = (
                cursor["value"]
                + _rol64(patch["delta"], (patch["revision"] % 31) + 1)
            ) & MASK64
            cursor["flags"] = (
                cursor["flags"] ^ _rol32(patch["toggle_mask"], patch["seq"] & 31)
            ) & MASK32
            cursor["applied_count"] += 1
        cursor["digest"] = _fold(cursor["digest"], patch, tombstone)
    return cursor

def _expected(seed: dict[str, Any]) -> dict[str, Any]:
    cursor = _projection(seed)
    probe = seed["probe"]
    matched = (
        cursor["epoch"] == probe["required_epoch"]
        and cursor["applied_count"] >= probe["min_applied"]
        and probe["modulus"] != 0
        and cursor["value"] % probe["modulus"] == probe["remainder"]
        and cursor["flags"] & probe["required_flags"] == probe["required_flags"]
    )
    row = {
        "verdict": "match" if matched else "miss",
        "epoch": cursor["epoch"],
        "seq": cursor["seq"],
        "value": cursor["value"],
        "flags": cursor["flags"],
        "digest": f"{cursor['digest']:016x}",
        "applied_count": cursor["applied_count"],
        "tombstone_count": cursor["tombstone_count"],
    }
    return {"row": row, "label": seed["labels"]["deferred"]}

def _build_and_emit(seed: Path) -> dict[str, Any]:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    global _BUILT_RELEASE_ONCE
    if not _BUILT_RELEASE_ONCE:
        subprocess.run(["cargo", "build", "--release", "--locked", "--offline"], cwd=APP, check=True)
        _BUILT_RELEASE_ONCE = True
    subprocess.run(
        [str(APP / "target" / "release" / "tracefold")],
        cwd=APP,
        check=True,
        env={**os.environ, "TRACEFOLD_OUT": str(REPORT), "TRACEFOLD_SEED": str(seed)},
    )
    return json.loads(REPORT.read_text(encoding="utf-8"))

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _report(root: dict[str, Any]) -> dict[str, Any]:
    return root["tracefold_report"]

def _assert_scenario(root: dict[str, Any], seed: dict[str, Any]) -> None:
    report = _report(root)
    expected = _expected(seed)
    assert report["paths"]["direct"] == expected["row"]
    assert report["paths"]["deferred"] == expected["row"]
    assert report["lineage_digest"] == _lineage_digest(seed)
    assert report["discard_digest"] == _discard_digest(seed)
    assert report["line_source"] == {"label": expected["label"], "ok": True}
    for name in (
        "projection_complete",
        "epoch_barrier",
        "revision_tiebreak",
        "tombstone_suppression",
        "deferred_not_looser",
        "deferred_recheck",
        "worker_reuse_safe",
        "restart_projection_parity",
    ):
        assert report[name] is True

@pytest.fixture(scope="session")
def stock_seed() -> dict[str, Any]:
    return _load(STOCK_SEED)

@pytest.fixture(scope="session")
def run_report() -> dict[str, Any]:
    return _build_and_emit(STOCK_SEED)

def test_paths_match_canonical_projection(run_report: dict[str, Any], stock_seed: dict[str, Any]) -> None:
    """Check paths match canonical projection for the public and generated trace scenarios."""
    expected = _expected(stock_seed)["row"]
    assert _report(run_report)["paths"] == {"direct": expected, "deferred": expected}

def test_audit_digests_cover_delivery_and_discards(run_report: dict[str, Any], stock_seed: dict[str, Any]) -> None:
    """Check audit digests cover raw delivery and non-winning patches."""
    report = _report(run_report)
    assert report["lineage_digest"] == _lineage_digest(stock_seed)
    assert report["discard_digest"] == _discard_digest(stock_seed)
@pytest.mark.parametrize(
    "name",
    (
        "projection_complete",
        "epoch_barrier",
        "revision_tiebreak",
        "tombstone_suppression",
        "deferred_not_looser",
        "deferred_recheck",
        "worker_reuse_safe",
        "restart_projection_parity",
    ),
)
def test_cursor_invariant(run_report: dict[str, Any], name: str) -> None:
    """Check cursor invariant for the public and generated trace scenarios."""
    assert _report(run_report)[name] is True

def test_line_names_executing_worker(run_report: dict[str, Any], stock_seed: dict[str, Any]) -> None:
    """Check line names executing worker for the public and generated trace scenarios."""
    assert _report(run_report)["line_source"] == {
        "label": stock_seed["labels"]["deferred"],
        "ok": True,
    }

def test_emit_determinism() -> None:
    """Check emit determinism for the public and generated trace scenarios."""
    assert _build_and_emit(STOCK_SEED) == _build_and_emit(STOCK_SEED)

def test_alternate_epoch_and_tombstones() -> None:
    """Check alternate epoch and tombstones for the public and generated trace scenarios."""
    seed = _load(ALT_SEED)
    _assert_scenario(_build_and_emit(ALT_SEED), seed)

def test_same_epoch_boundary_trap() -> None:
    """Check same epoch boundary trap for the public and generated trace scenarios."""
    seed = _load(TRAP_SEED)
    _assert_scenario(_build_and_emit(TRAP_SEED), seed)

def test_runtime_ties_barriers_and_permutation() -> None:
    """Check projection stability while audit digests record raw ordering."""
    seed = {
        "lane_id": 22,
        "base_epoch": 1,
        "base_seq": 5,
        "base_value": 240,
        "base_flags": 3,
        "probe": {
            "modulus": 41,
            "remainder": 5,
            "required_flags": 270851,
            "required_epoch": 9,
            "min_applied": 3,
        },
        "labels": {"direct": 27, "deferred": 66},
        "patches": [
            {"epoch": 4, "seq": 6, "revision": 8, "patch_id": 2, "lane_id": 22, "committed": True, "kind": "update", "delta": 500, "toggle_mask": 16},
            {"epoch": 9, "seq": 7, "revision": 2, "patch_id": 7, "lane_id": 22, "committed": True, "kind": "update", "delta": 10, "toggle_mask": 1},
            {"epoch": 9, "seq": 7, "revision": 5, "patch_id": 9, "lane_id": 22, "committed": True, "kind": "update", "delta": 20, "toggle_mask": 2},
            {"epoch": 9, "seq": 7, "revision": 5, "patch_id": 18, "lane_id": 22, "committed": True, "kind": "update", "delta": 40, "toggle_mask": 4},
            {"epoch": 9, "seq": 8, "revision": 3, "patch_id": 24, "lane_id": 22, "committed": True, "kind": "tombstone", "delta": 77, "toggle_mask": 4294967295},
            {"epoch": 9, "seq": 10, "revision": 4, "patch_id": 31, "lane_id": 22, "committed": True, "kind": "update", "delta": 6, "toggle_mask": 8},
            {"epoch": 9, "seq": 12, "revision": 6, "patch_id": 47, "lane_id": 22, "committed": True, "kind": "tombstone", "delta": 8, "toggle_mask": 64},
            {"epoch": 9, "seq": 14, "revision": 2, "patch_id": 53, "lane_id": 22, "committed": True, "kind": "update", "delta": 11, "toggle_mask": 16},
            {"epoch": 21, "seq": 40, "revision": 9, "patch_id": 80, "lane_id": 77, "committed": True, "kind": "update", "delta": 9999, "toggle_mask": 4294967295},
        ],
    }
    RUNTIME_SEED.write_text(json.dumps(seed), encoding="utf-8")
    first = _build_and_emit(RUNTIME_SEED)
    _assert_scenario(first, seed)
    permuted = {**seed, "patches": list(reversed(seed["patches"]))}
    PERMUTED_SEED.write_text(json.dumps(permuted), encoding="utf-8")
    second = _build_and_emit(PERMUTED_SEED)
    _assert_scenario(second, permuted)
    first_report = _report(first)
    second_report = _report(second)
    assert first_report["paths"] == second_report["paths"]
    assert first_report["line_source"] == second_report["line_source"]
    for name in (
        "projection_complete",
        "epoch_barrier",
        "revision_tiebreak",
        "tombstone_suppression",
        "deferred_not_looser",
        "deferred_recheck",
        "worker_reuse_safe",
        "restart_projection_parity",
    ):
        assert first_report[name] == second_report[name]
    assert first_report["lineage_digest"] != second_report["lineage_digest"]
    assert first_report["discard_digest"] != second_report["discard_digest"]

def test_runtime_ignored_rows_still_change_discard_digest() -> None:
    """Ignored rows do not change projection but must change both audit digests."""
    seed = {
        "lane_id": 9,
        "base_epoch": 1,
        "base_seq": 0,
        "base_value": 111,
        "base_flags": 2,
        "probe": {
            "modulus": 7,
            "remainder": 0,
            "required_flags": 2,
            "required_epoch": 3,
            "min_applied": 1,
        },
        "labels": {"direct": 8, "deferred": 18},
        "patches": [
            {"epoch": 3, "seq": 1, "revision": 4, "patch_id": 10, "lane_id": 9, "committed": True, "kind": "update", "delta": 5, "toggle_mask": 0},
            {"epoch": 3, "seq": 2, "revision": 1, "patch_id": 11, "lane_id": 9, "committed": True, "kind": "tombstone", "delta": 99, "toggle_mask": 7},
        ],
    }
    noisy = {
        **seed,
        "patches": seed["patches"]
        + [
            {"epoch": 99, "seq": 3, "revision": 30, "patch_id": 500, "lane_id": 99, "committed": True, "kind": "update", "delta": 123456, "toggle_mask": 4294967295},
            {"epoch": 3, "seq": 4, "revision": 31, "patch_id": 501, "lane_id": 9, "committed": False, "kind": "tombstone", "delta": 98765, "toggle_mask": 15},
        ],
    }
    RUNTIME_SEED.write_text(json.dumps(seed), encoding="utf-8")
    clean = _build_and_emit(RUNTIME_SEED)
    _assert_scenario(clean, seed)
    PERMUTED_SEED.write_text(json.dumps(noisy), encoding="utf-8")
    dirty = _build_and_emit(PERMUTED_SEED)
    _assert_scenario(dirty, noisy)
    assert _report(clean)["paths"] == _report(dirty)["paths"]
    assert _report(clean)["lineage_digest"] != _report(dirty)["lineage_digest"]
    assert _report(clean)["discard_digest"] != _report(dirty)["discard_digest"]

def test_runtime_losing_revision_is_discarded_but_not_projected() -> None:
    """A losing same-sequence revision affects discard_digest without changing projection."""
    seed = {
        "lane_id": 44,
        "base_epoch": 2,
        "base_seq": 0,
        "base_value": 50,
        "base_flags": 1,
        "probe": {
            "modulus": 5,
            "remainder": 0,
            "required_flags": 1,
            "required_epoch": 6,
            "min_applied": 1,
        },
        "labels": {"direct": 19, "deferred": 29},
        "patches": [
            {"epoch": 6, "seq": 1, "revision": 5, "patch_id": 90, "lane_id": 44, "committed": True, "kind": "update", "delta": 25, "toggle_mask": 0},
            {"epoch": 6, "seq": 2, "revision": 2, "patch_id": 91, "lane_id": 44, "committed": True, "kind": "tombstone", "delta": 77, "toggle_mask": 4},
        ],
    }
    noisy = {
        **seed,
        "patches": [
            seed["patches"][0],
            {"epoch": 6, "seq": 1, "revision": 4, "patch_id": 999, "lane_id": 44, "committed": True, "kind": "update", "delta": 9999, "toggle_mask": 4294967295},
            seed["patches"][1],
        ],
    }
    RUNTIME_SEED.write_text(json.dumps(seed), encoding="utf-8")
    clean = _build_and_emit(RUNTIME_SEED)
    _assert_scenario(clean, seed)
    PERMUTED_SEED.write_text(json.dumps(noisy), encoding="utf-8")
    dirty = _build_and_emit(PERMUTED_SEED)
    _assert_scenario(dirty, noisy)
    assert _report(clean)["paths"] == _report(dirty)["paths"]
    assert _report(clean)["discard_digest"] != _report(dirty)["discard_digest"]
