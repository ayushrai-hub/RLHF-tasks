"""arrival-audit trace verifier — contract-derived expectations."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

TRACE_PATH = Path("/app/output/arrival_trace.json")
WORKSPACE = Path("/app/data/workspace")
FIXTURES = Path("/app/environment/fixtures/wave")
ENV_ROOT = Path("/app/environment")
BIN_PATH = Path("/app/bin/arrival-audit")
SCENARIOS = ["wave_once", "wave_twice", "pause_trap", "stale_marker"]


def _sha16(payload: str | bytes) -> str:
    if isinstance(payload, str):
        payload = payload.encode()
    proc = subprocess.run(
        ["openssl", "dgst", "-sha256", "-hex"],
        input=payload,
        check=True,
        capture_output=True,
    )
    digest = proc.stdout.decode().strip().split()[-1]
    return digest[:16]


def _edge_fp(label: str, body: bytes) -> str:
    return _sha16(f"{label}|".encode() + body)


def _retention_stamp(gen: int, fixture_body: bytes) -> str:
    return _sha16(f"{gen}|".encode() + fixture_body)


def _row_seal(row: dict[str, Any]) -> str:
    canonical = "|".join(
        [
            str(row["scenario"]),
            str(row["wave_gen"]),
            str(row["edge_fp_host"]),
            str(row["edge_fp_work"]),
            str(row["miss_gap"]),
            str(row["gen_skew"]),
            str(row["retention_stamp"]),
        ]
    )
    return _sha16(canonical)


def _report_digest(rows: list[dict[str, Any]]) -> str:
    fragments: list[str] = []
    for row in rows:
        fragments.append(
            ";".join(
                [
                    str(row["scenario"]),
                    str(row["wave_gen"]),
                    str(row["edge_fp_host"]),
                    str(row["edge_fp_work"]),
                    str(row["miss_gap"]),
                    str(row["gen_skew"]),
                    str(row["retention_stamp"]),
                    str(row["row_seal"]),
                ]
            )
        )
    joined = "\n".join(sorted(fragments))
    return _sha16(joined)


def _replay_token(report_digest: str, workspace: str) -> str:
    return _sha16(f"{report_digest}|{workspace}")


def _fixture_body(gen: int) -> bytes:
    return (FIXTURES / f"gen{gen}" / "active.log").read_bytes()


def _wave_marker(view: str) -> int:
    marker = WORKSPACE / "layers" / view / "wave_gen"
    if not marker.exists():
        return 1
    text = marker.read_text(encoding="utf-8").strip()
    try:
        val = int(text)
    except ValueError:
        return 1
    return val if val >= 1 else 1


def _build_arrival_audit() -> None:
    subprocess.run(
        ["go", "build", "-o", "/app/bin/arrival-audit", "./driver/"],
        cwd=ENV_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _run_arrival_audit() -> dict[str, Any]:
    if TRACE_PATH.exists():
        TRACE_PATH.unlink()
    subprocess.run(
        [
            "/app/bin/arrival-audit",
            "--trace",
            "/app/output/arrival_trace.json",
            "--workspace",
            "/app/data/workspace",
            "--fixtures",
            "/app/environment/fixtures/wave",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(TRACE_PATH.read_text(encoding="utf-8"))


def _row(doc: dict[str, Any], scenario: str) -> dict[str, Any]:
    for run in doc.get("runs") or []:
        if run.get("scenario") == scenario:
            return run
    raise AssertionError(f"missing scenario row {scenario}")


def _wipe_workspace() -> None:
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    subprocess.run(
        [
            "bash",
            "/app/environment/scripts/setup_fanout.sh",
            "/app/data/workspace",
            "/app/environment/fixtures/wave",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def audit_doc() -> dict[str, Any]:
    _build_arrival_audit()
    _wipe_workspace()
    return _run_arrival_audit()


def test_vc01_fresh_run_shape(audit_doc: dict[str, Any]) -> None:
    """Baseline runs array and global fields after first audit."""
    assert isinstance(audit_doc.get("runs"), list)
    assert len(audit_doc["runs"]) == len(SCENARIOS)
    names = {row["scenario"] for row in audit_doc["runs"]}
    assert names == set(SCENARIOS)
    for key in ("report_digest", "replay_token"):
        val = audit_doc.get(key)
        assert isinstance(val, str) and len(val) == 16
    for row in audit_doc["runs"]:
        for field in (
            "scenario",
            "wave_gen",
            "edge_fp_host",
            "edge_fp_work",
            "miss_gap",
            "gen_skew",
            "retention_stamp",
            "row_seal",
        ):
            assert field in row
    once = _row(audit_doc, "wave_once")
    assert once["miss_gap"] == 0
    assert once["gen_skew"] == 0
    assert once["wave_gen"] == 1


def test_vc02_dual_run_digest_stable(audit_doc: dict[str, Any]) -> None:
    """Identical report_digest and replay_token across consecutive audits."""
    first_digest = audit_doc["report_digest"]
    first_token = audit_doc["replay_token"]
    second = _run_arrival_audit()
    assert second["report_digest"] == first_digest
    assert second["replay_token"] == first_token
    sealed_rows: list[dict[str, Any]] = []
    for row in audit_doc["runs"]:
        sealed = dict(row)
        sealed["row_seal"] = _row_seal(sealed)
        sealed_rows.append(sealed)
    assert first_digest == _report_digest(sealed_rows)
    once = _row(audit_doc, "wave_once")
    assert once["retention_stamp"] == _retention_stamp(1, _fixture_body(1))


def test_vc03_auth_gap_after_close(audit_doc: dict[str, Any]) -> None:
    """Coordinated repair drives miss_gap to zero for every scenario."""
    for scenario in SCENARIOS:
        row = _row(audit_doc, scenario)
        assert row["miss_gap"] == 0, f"{scenario} miss_gap={row['miss_gap']}"


def test_vc04_edge_fp_divergence() -> None:
    """Contract view fingerprint: edge_fp_host/work follow sha256('label|' + body)[:16] at scenario completion."""
    _wipe_workspace()
    doc = _run_arrival_audit()
    row = _row(doc, "wave_once")
    assert row["miss_gap"] == 0
    assert row["gen_skew"] == 0
    view_body = _fixture_body(2)
    assert row["edge_fp_host"] == _edge_fp("host", view_body)
    assert row["edge_fp_work"] == _edge_fp("work", view_body)
    assert row["edge_fp_host"] != row["edge_fp_work"]


def test_vc05_green_count_mismatch(audit_doc: dict[str, Any]) -> None:
    """Contract published entry probe: published/ file count matches fixture gen directory with miss_gap zero."""
    pub_dir = WORKSPACE / "published"
    entries = [p for p in pub_dir.iterdir() if p.is_file()]
    assert len(entries) >= 1
    row = _row(audit_doc, "wave_once")
    expected = len(list((FIXTURES / "gen1").iterdir()))
    assert len(entries) == expected
    assert row["miss_gap"] == 0


def test_vc06_pause_trap_clear() -> None:
    """Pause trap row records zero gap and zero gen skew after coordinated reopen and recycle."""
    _wipe_workspace()
    doc = _run_arrival_audit()
    row = _row(doc, "pause_trap")
    assert row["miss_gap"] == 0
    assert row["gen_skew"] == 0
    assert row["wave_gen"] == 2


def test_vc07_second_wave_drift(audit_doc: dict[str, Any]) -> None:
    """Second rename wave stays aligned in wave_twice scenario."""
    row = _row(audit_doc, "wave_twice")
    assert row["wave_gen"] == 2
    assert row["miss_gap"] == 0
    assert row["gen_skew"] == 0
    stamp = _retention_stamp(2, _fixture_body(2))
    assert row["retention_stamp"] == stamp


def test_vc08_stamp_body_match(audit_doc: dict[str, Any]) -> None:
    """retention_stamp matches sha256 prefix of archived fixture body."""
    for scenario in SCENARIOS:
        row = _row(audit_doc, scenario)
        gen = int(row["wave_gen"])
        expected = _retention_stamp(gen, _fixture_body(gen))
        assert row["retention_stamp"] == expected, scenario


def test_vc09_regen_required() -> None:
    """Verifier rebuild blocks static output file."""
    _wipe_workspace()
    fake = {
        "runs": [],
        "report_digest": "0" * 16,
        "replay_token": "0" * 16,
    }
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACE_PATH.write_text(json.dumps(fake), encoding="utf-8")
    if BIN_PATH.exists():
        BIN_PATH.unlink()
    _build_arrival_audit()
    doc = _run_arrival_audit()
    assert doc["runs"], "arrival-audit must regenerate non-empty runs"
    assert doc["report_digest"] != fake["report_digest"]
    sealed_rows: list[dict[str, Any]] = []
    for row in doc["runs"]:
        sealed = dict(row)
        sealed["row_seal"] = _row_seal(sealed)
        sealed_rows.append(sealed)
    assert doc["report_digest"] == _report_digest(sealed_rows)
    once = _row(doc, "wave_once")
    assert once["retention_stamp"] == _retention_stamp(1, _fixture_body(1))


def test_vc10_envelope_digest_match(audit_doc: dict[str, Any]) -> None:
    """report_digest matches recomputed canonical envelope from row fields."""
    rows = audit_doc["runs"]
    sealed_rows: list[dict[str, Any]] = []
    for row in rows:
        assert row["miss_gap"] == 0
        assert row["gen_skew"] == 0
        gen = int(row["wave_gen"])
        assert row["retention_stamp"] == _retention_stamp(gen, _fixture_body(gen))
        sealed = dict(row)
        sealed["row_seal"] = _row_seal(sealed)
        sealed_rows.append(sealed)
    expected_digest = _report_digest(sealed_rows)
    assert audit_doc["report_digest"] == expected_digest
    expected_token = _replay_token(expected_digest, str(WORKSPACE))
    assert audit_doc["replay_token"] == expected_token


def test_vc11_stale_marker_skew(audit_doc: dict[str, Any]) -> None:
    """stale_marker omits recycle; gen_skew must still be zero when batch close keeps markers aligned."""
    row = _row(audit_doc, "stale_marker")
    assert row["wave_gen"] == 1
    assert row["miss_gap"] == 0
    assert row["gen_skew"] == 0
    host_gen = _wave_marker("host")
    work_gen = _wave_marker("work")
    assert host_gen == work_gen
    assert row["gen_skew"] == host_gen - work_gen


def test_vc12_gen_skew_live_match(audit_doc: dict[str, Any]) -> None:
    """stale_marker is the final scenario; live markers must match its recorded gen_skew."""
    row = _row(audit_doc, "stale_marker")
    host_gen = _wave_marker("host")
    work_gen = _wave_marker("work")
    assert row["gen_skew"] == host_gen - work_gen
    assert row["gen_skew"] == 0
