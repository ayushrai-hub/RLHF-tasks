"""Verifier for staged beam envelope integration."""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import textwrap
from pathlib import Path

import pytest

from beam_invariants import (
    moment_about_left,
    pin_pin_reactions_point,
    pin_pin_reactions_udl,
    vertical_resultant,
)

ROOT = Path("/app")
APP = ROOT / "environment"
BIN = APP / "bin" / "beam-envelope"
FIXTURES = APP / "fixtures"
OUT = ROOT / "output" / "envelope_report.json"
TOL = 1e-3
GENERATED_CASE_SEED = 29


def _run(stages: list[Path], combine: str, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(BIN)]
    for stage in stages:
        cmd.extend(["--stage", str(stage)])
    cmd.extend(["--combine", combine, "--out", str(out)])
    proc = subprocess.run(cmd, cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(out.read_text())


def test_simple_single_span_baseline(built_bin) -> None:
    """Simple deck baseline produces finite envelope values."""
    report = _run([FIXTURES / "simple" / "deck_base.beam"], "service", OUT)
    assert report["beam_id"] == "deck_a"
    assert report["envelope"]["max_moment_nm"] > 0


def test_vertical_equilibrium_simple(built_bin) -> None:
    """Total vertical reactions equal applied vertical load resultant."""
    report = _run([FIXTURES / "simple" / "deck_base.beam"], "service", OUT)
    loads = {"point_forces": [(12000.0, 4.0)], "point_moments": [(2000.0, 6.0)]}
    resultant = vertical_resultant(loads)
    env = report["envelope"]
    assert abs((env["left_reaction_n"] + env["right_reaction_n"]) - resultant) < TOL


def test_global_moment_equilibrium(built_bin) -> None:
    """Global moment equilibrium holds about the left support."""
    report = _run([FIXTURES / "simple" / "deck_base.beam"], "service", OUT)
    loads = {"point_forces": [(12000.0, 4.0)]}
    m_left = moment_about_left(loads)
    env = report["envelope"]
    length = 8.0
    assert abs(env["right_reaction_n"] * length - m_left) < 5.0


def test_point_moment_jump_no_shear_jump(built_bin, tmp_path: Path) -> None:
    """Point moment changes envelope moment without changing reaction resultant."""
    span = tmp_path / "pm.beam"
    span.write_text(
        textwrap.dedent(
            """
            beam_id=T1
            revision=1
            nodes:
            0.0 PIN
            6.0 PIN
            segments:
            main 0.0 6.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 6.0 factor=1.0
            load_cases:
            live
            POINT_M 5000 3.0
            combinations:
            c live:1.0
            """
        ).strip()
        + "\n"
    )
    report = _run([span], "c", tmp_path / "out.json")
    assert abs(report["envelope"]["left_reaction_n"]) < TOL
    assert abs(report["envelope"]["right_reaction_n"]) < TOL
    assert report["envelope"]["max_moment_nm"] >= 5000.0 - TOL


def test_point_force_shear_jump(built_bin, tmp_path: Path) -> None:
    """Point force changes reaction split consistent with pin-pin statics."""
    span = tmp_path / "pf.beam"
    span.write_text(
        textwrap.dedent(
            """
            beam_id=T2
            revision=1
            nodes:
            0.0 PIN
            5.0 PIN
            segments:
            main 0.0 5.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 5.0 factor=1.0
            load_cases:
            dead
            POINT_F 10000 2.0
            combinations:
            c dead:1.0
            """
        ).strip()
        + "\n"
    )
    report = _run([span], "c", tmp_path / "out.json")
    left, right = pin_pin_reactions_point(5.0, 10000.0, 2.0)
    assert abs(report["envelope"]["left_reaction_n"] - left) < TOL
    assert abs(report["envelope"]["right_reaction_n"] - right) < TOL


def test_udl_boundary_polynomial_slope(built_bin, tmp_path: Path) -> None:
    """Partial UDL produces interior moment exceeding endpoint values."""
    span = tmp_path / "udl.beam"
    span.write_text(
        textwrap.dedent(
            """
            beam_id=T3
            revision=1
            nodes:
            0.0 PIN
            8.0 PIN
            segments:
            main 0.0 8.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 8.0 factor=1.0
            load_cases:
            dead
            UDL 2000 2.0 6.0
            combinations:
            c dead:1.0
            """
        ).strip()
        + "\n"
    )
    report = _run([span], "c", tmp_path / "out.json")
    left, right = pin_pin_reactions_udl(8.0, 2000.0, 2.0, 6.0)
    assert abs(report["envelope"]["left_reaction_n"] - left) < TOL
    assert abs(report["envelope"]["right_reaction_n"] - right) < TOL
    assert report["envelope"]["max_moment_nm"] >= 8000.0 - TOL


def test_coincident_moment_udl_side_semantics(built_bin) -> None:
    """Coincident point moment and UDL end obey right-side moment semantics."""
    report = _run([FIXTURES / "piecewise" / "moment_udl_coincident.beam"], "check", OUT)
    assert report["envelope"]["max_moment_nm"] >= 14000.0 - 50.0


def test_support_settlement_reflected(built_bin, tmp_path: Path) -> None:
    """Prescribed settlement shifts deflection extrema."""
    span = tmp_path / "settle.beam"
    span.write_text(
        textwrap.dedent(
            """
            beam_id=T4
            revision=1
            nodes:
            0.0 PIN settlement_mm=2.0
            6.0 PIN settlement_mm=0.0
            segments:
            main 0.0 6.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 6.0 factor=1.0
            load_cases:
            dead
            POINT_F 5000 3.0
            combinations:
            c dead:1.0
            """
        ).strip()
        + "\n"
    )
    report = _run([span], "c", tmp_path / "out.json")
    assert report["envelope"]["max_deflection_mm"] >= 1.0


def test_amended_load_case_uses_new_segment_frame(built_bin, tmp_path: Path) -> None:
    """Replacement load case uses amended segment origin for global coordinates."""
    base = FIXTURES / "simple" / "deck_base.beam"
    amend = FIXTURES / "staged" / "deck_amend_accept.beam"
    report = _run([base, amend], "service", tmp_path / "amended.json")
    left_expected, _ = pin_pin_reactions_point(8.0, 10000.0, 3.0)
    assert abs(report["envelope"]["left_reaction_n"] - left_expected) < TOL


def test_rejected_amendment_preserves_report(built_bin, tmp_path: Path) -> None:
    """Rejected amendment leaves envelope identical to pre-reject committed revision."""
    base = FIXTURES / "simple" / "deck_base.beam"
    before = _run([base], "service", tmp_path / "before.json")
    reject = FIXTURES / "staged" / "deck_amend_reject.beam"
    after = _run([base, reject], "service", tmp_path / "after.json")
    assert after["envelope"] == before["envelope"]
    assert after["provenance"]["rejected_stages"] >= 1


def test_valid_amendment_after_reject_clears_stale_deflection(built_bin, tmp_path: Path) -> None:
    """Accepted amendment after rejection does not reuse rejected deflection state."""
    base = FIXTURES / "simple" / "deck_base.beam"
    reject = FIXTURES / "staged" / "deck_amend_reject.beam"
    accept = FIXTURES / "staged" / "deck_amend_accept.beam"
    only_reject = _run([base, reject], "service", tmp_path / "reject.json")
    full = _run([base, reject, accept], "service", tmp_path / "full.json")
    assert full["envelope"]["max_deflection_mm"] != only_reject["envelope"]["max_deflection_mm"]


def test_combination_recomputed_after_revision(built_bin, tmp_path: Path) -> None:
    """Reusing a combination name after commit reflects the new revision envelope."""
    base = FIXTURES / "simple" / "deck_base.beam"
    amend = FIXTURES / "staged" / "deck_amend_accept.beam"
    before = _run([base], "service", tmp_path / "b.json")
    after = _run([base, amend], "service", tmp_path / "a.json")
    assert after["envelope"]["left_reaction_n"] != before["envelope"]["left_reaction_n"]


def test_combination_factor_regrouping(built_bin, tmp_path: Path) -> None:
    """Equivalent factor grouping yields the same reactions."""
    span = tmp_path / "regroup.beam"
    span.write_text(
        textwrap.dedent(
            """
            beam_id=T5
            revision=1
            nodes:
            0.0 PIN
            6.0 PIN
            segments:
            main 0.0 6.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 6.0 factor=1.0
            load_cases:
            a
            POINT_F 4000 2.0
            b
            POINT_F 2000 4.0
            combinations:
            c1 a:1.0 b:1.0
            c2 a:0.5 b:0.5
            c2 b:0.5 a:0.5
            """
        ).strip()
        + "\n"
    )
    r1 = _run([span], "c1", tmp_path / "r1.json")
    r2 = _run([span], "c2", tmp_path / "r2.json")
    assert abs(r1["envelope"]["left_reaction_n"] - r2["envelope"]["left_reaction_n"]) < TOL


def test_load_case_order_irrelevant(built_bin, tmp_path: Path) -> None:
    """Load-case declaration order does not change combination reactions."""
    a = tmp_path / "order_a.beam"
    b = tmp_path / "order_b.beam"
    a.write_text(
        textwrap.dedent(
            """
            beam_id=T6
            revision=1
            nodes:
            0.0 PIN
            5.0 PIN
            segments:
            main 0.0 5.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 5.0 factor=1.0
            load_cases:
            one
            POINT_F 3000 2.0
            two
            POINT_F 2000 3.0
            combinations:
            c one:1.0 two:1.0
            """
        ).strip()
        + "\n"
    )
    b.write_text(
        textwrap.dedent(
            """
            beam_id=T6
            revision=1
            nodes:
            0.0 PIN
            5.0 PIN
            segments:
            main 0.0 5.0 E_gpa=200 section_width_mm=150 section_depth_mm=300
            stiffness:
            R1 main 0.0 5.0 factor=1.0
            load_cases:
            two
            POINT_F 2000 3.0
            one
            POINT_F 3000 2.0
            combinations:
            c one:1.0 two:1.0
            """
        ).strip()
        + "\n"
    )
    r1 = _run([a], "c", tmp_path / "o1.json")
    r2 = _run([b], "c", tmp_path / "o2.json")
    assert abs(r1["envelope"]["left_reaction_n"] - r2["envelope"]["left_reaction_n"]) < TOL


def test_envelope_includes_endpoints_and_interior(built_bin) -> None:
    """Envelope extrema are finite and bracket interior values."""
    report = _run([FIXTURES / "simple" / "deck_base.beam"], "service", OUT)
    env = report["envelope"]
    assert env["max_moment_nm"] >= env["min_moment_nm"]
    assert env["max_shear_n"] >= env["min_shear_n"]


def test_byte_identical_regeneration(built_bin, tmp_path: Path) -> None:
    """Repeated execution produces byte-identical output."""
    stages = [FIXTURES / "simple" / "deck_base.beam"]
    out1 = tmp_path / "a.json"
    out2 = tmp_path / "b.json"
    _run(stages, "service", out1)
    _run(stages, "service", out2)
    assert out1.read_bytes() == out2.read_bytes()


def test_fatal_parse_removes_output(built_bin, tmp_path: Path) -> None:
    """Fatal parse exits non-zero and removes output."""
    bad = tmp_path / "bad.beam"
    bad.write_text("revision=1\n")
    out = tmp_path / "missing.json"
    cmd = [str(BIN), "--stage", str(bad), "--combine", "service", "--out", str(out)]
    proc = subprocess.run(cmd, cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode != 0
    with pytest.raises(FileNotFoundError):
        out.read_text()


def test_report_provenance_matches_envelope_revision(built_bin, tmp_path: Path) -> None:
    """Provenance committed revision matches the revision used for envelope values."""
    base = FIXTURES / "simple" / "deck_base.beam"
    amend = FIXTURES / "staged" / "deck_amend_accept.beam"
    report = _run([base, amend], "service", tmp_path / "prov.json")
    assert report["provenance"]["committed_revision"] == 2
    digest = report["report_digest"]
    payload = (
        f"{report['beam_id']}|{report['combination']}|"
        f"{report['provenance']['committed_revision']}|"
        f"{report['provenance']['amendment_generation']}|"
        f"{report['envelope']['max_moment_nm']}|"
        f"{report['envelope']['max_deflection_mm']}"
    )
    assert digest == "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def test_cross_beam_cache_isolation(built_bin, tmp_path: Path) -> None:
    """Reused combination names after revision bump do not return stale envelopes."""
    base = FIXTURES / "simple" / "deck_base.beam"
    amend = FIXTURES / "staged" / "deck_amend_accept.beam"
    before = _run([base], "service", tmp_path / "before.json")
    after = _run([base, amend], "service", tmp_path / "after.json")
    assert before["beam_id"] == after["beam_id"]
    assert before["envelope"]["left_reaction_n"] != after["envelope"]["left_reaction_n"]


def test_generated_seed_vertical_equilibrium(built_bin, tmp_path: Path) -> None:
    """Deterministic generated case satisfies vertical equilibrium."""
    rng = random.Random(GENERATED_CASE_SEED)
    length = 4.0 + rng.random() * 4.0
    force = 2000.0 + rng.random() * 8000.0
    pos = 1.0 + rng.random() * (length - 2.0)
    span = tmp_path / "gen.beam"
    span.write_text(
        f"beam_id=G{int(length*10)}\nrevision=1\nnodes:\n0.0 PIN\n{length} PIN\n"
        f"segments:\nmain 0.0 {length} E_gpa=200 section_width_mm=150 section_depth_mm=300\n"
        f"stiffness:\nR1 main 0.0 {length} factor=1.0\nload_cases:\ndead\n"
        f"POINT_F {force:.3f} {pos:.3f}\ncombinations:\nc dead:1.0\n"
    )
    report = _run([span], "c", tmp_path / "gen.json")
    left, right = pin_pin_reactions_point(length, force, pos)
    assert abs(report["envelope"]["left_reaction_n"] - left) < 1.0
    assert abs(report["envelope"]["right_reaction_n"] - right) < 1.0
