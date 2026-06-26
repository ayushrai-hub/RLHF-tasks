"""Verifier for logrecover recovery_report.json."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ENV_ROOT = Path("/app/environment")
REPORT = Path("/app/output/recovery_report.json")
PACK = Path("/app/fixtures/scenarios/pack.json")
FROZEN_HASHES = Path("/app/environment/data/config/frozen_stream_hashes.json")

SID_ALPHA = "case_a_clock_tie"
SID_TAIL = "case_b_trailer_rot"
SID_RING = "case_c_member_scope"


def _pack() -> dict:
    return json.loads(PACK.read_text())


def _frozen_stream_hashes() -> dict[str, str]:
    return json.loads(FROZEN_HASHES.read_text())


def _expected_digest(sid: str) -> str:
    return _frozen_stream_hashes()[sid]


def _quorum_need(sid: str) -> int:
    for scenario in _pack()["scenarios"]:
        if scenario["id"] == sid:
            return int(scenario["quorum_need"])
    raise KeyError(sid)


def _environ_for_build() -> dict[str, str]:
    return os.environ.copy()


def rebuild_logrecover() -> None:
    subprocess.run(
        [
            "/usr/local/go/bin/go",
            "build",
            "-C",
            "/app/environment",
            "-o",
            "/app/logrecover",
            "/app/environment/cmd/logrecover",
        ],
        cwd="/app/environment",
        check=True,
        env=_environ_for_build(),
    )


def run_logrecover() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "/app/logrecover",
            "--pack",
            str(PACK),
            "--out",
            str(REPORT),
        ],
        cwd="/",
        check=True,
        env=_environ_for_build(),
    )


@pytest.fixture(scope="session", autouse=True)
def _session_build() -> None:
    rebuild_logrecover()


@pytest.fixture()
def report() -> dict:
    run_logrecover()
    return json.loads(REPORT.read_text())


def _scenario(report: dict, sid: str) -> dict:
    sc = report["scenarios"][sid]
    assert isinstance(sc, dict)
    return sc


def test_report_schema(report: dict) -> None:
    """recovery_report.json matches the published contract."""
    assert report["schema_version"] == 3
    assert report["recovery_budget_ms"] == _pack()["recovery_budget_ms"]
    assert set(report["scenarios"].keys()) == {SID_ALPHA, SID_TAIL, SID_RING}
    for sid in report["scenarios"]:
        row = report["scenarios"][sid]
        assert set(row.keys()) >= {
            "canonical_digest_hex",
            "recovered_events",
            "quorum_size_seen",
            "recovery_elapsed_ms",
            "data_loss_events",
            "partition_healed",
            "merge_mode",
        }
        assert len(row["canonical_digest_hex"]) == 64


def test_bundle_zero_loss(report: dict) -> None:
    """Every bundled scenario reports zero data loss."""
    for sid in report["scenarios"]:
        assert _scenario(report, sid)["data_loss_events"] == 0


def test_epoch_closed_satisfied(report: dict) -> None:
    """Heal epoch is satisfied for each bundled scenario."""
    for sid in report["scenarios"]:
        assert _scenario(report, sid)["partition_healed"] is True


def test_m0_fingerprint(report: dict) -> None:
    """Lamport ties merge to the frozen canonical stream."""
    row = _scenario(report, SID_ALPHA)
    assert row["canonical_digest_hex"] == _expected_digest(SID_ALPHA)
    assert row["recovered_events"] >= 1


def test_m1_fingerprint(report: dict) -> None:
    """Invalid tail frames are rejected instead of polluting the merge."""
    row = _scenario(report, SID_TAIL)
    assert row["canonical_digest_hex"] == _expected_digest(SID_TAIL)
    assert row["recovered_events"] >= 1


def test_m2_fingerprint(report: dict) -> None:
    """Membership sizing excludes replicas still isolated at heal epoch."""
    row = _scenario(report, SID_RING)
    assert row["canonical_digest_hex"] == _expected_digest(SID_RING)
    assert row["quorum_size_seen"] == _quorum_need(SID_RING)
    assert row["recovered_events"] >= 1


def test_timing_budget(report: dict) -> None:
    """Summed virtual recovery time stays under the pack budget."""
    total = sum(
        _scenario(report, sid)["recovery_elapsed_ms"]
        for sid in report["scenarios"]
    )
    assert total <= _pack()["recovery_budget_ms"]
    for sid in report["scenarios"]:
        assert _scenario(report, sid)["recovery_elapsed_ms"] >= 1


def test_rebuild_idempotent(report: dict) -> None:
    """A second driver run reproduces the same canonical digests."""
    run_logrecover()
    second = json.loads(REPORT.read_text())
    for sid in report["scenarios"]:
        assert (
            report["scenarios"][sid]["canonical_digest_hex"]
            == second["scenarios"][sid]["canonical_digest_hex"]
        )
