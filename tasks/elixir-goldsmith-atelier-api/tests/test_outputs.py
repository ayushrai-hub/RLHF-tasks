"""
Aurum & Astralis Goldsmith Atelier API — verifier.

These tests run in declaration order against the live server on :8080.
The DB is reseeded by the test.sh wrapper before pytest starts, so test
ordering matters — later tests may rely on the state established by earlier
ones (e.g. the audit chain accumulates across the suite).
"""

from __future__ import annotations

import hashlib
import math

import requests

BASE = "http://127.0.0.1:8080"
S = requests.Session()


# ---- helpers -------------------------------------------------------------


def _get(path: str, **kw):
    return S.get(f"{BASE}{path}", timeout=10, **kw)


def _post(path: str, body=None):
    if body is None:
        return S.post(
            f"{BASE}{path}",
            data="{}",
            headers={"content-type": "application/json"},
            timeout=10,
        )
    return S.post(f"{BASE}{path}", json=body, timeout=10)


def _post_raw(path: str, raw: str, ctype: str = "application/json"):
    return S.post(
        f"{BASE}{path}", data=raw, headers={"content-type": ctype}, timeout=10
    )


def _json(resp) -> dict:
    return resp.json()


def _err(resp) -> str:
    return _json(resp).get("error", "")


def _approx(a: float, b: float, tol: float = 1e-5) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def _walk_to_chased(serial: str) -> int:
    """
    Create a fresh piece and walk it ingot_selected → chased. Returns the new
    piece_id. Uses goldsmith 1 (albrecht) as the responsible smith and a
    per-piece unique casting window so that multiple calls don't collide on
    `crucible_overlap` / `goldsmith_busy`.
    """
    r = _post(
        "/pieces",
        {
            "serial": serial,
            "intent_kind": "ring",
            "alloy_grade": "18K",
            "target_mass_g": 25.0,
        },
    )
    assert r.status_code == 201, r.text
    pid = _json(r)["piece_id"]

    # Assign to smith 1.
    r = _post("/goldsmiths/1/assign", {"piece_id": pid})
    assert r.status_code == 200, r.text

    # Add an assay.
    r = _post(f"/pieces/{pid}/assay", {"goldsmith_id": 1, "fineness_per_mille": 999})
    assert r.status_code == 201, r.text

    # ingot_selected → assayed
    r = _post(f"/pieces/{pid}/advance-stage")
    assert r.status_code == 200, r.text

    # assayed → cast_active
    r = _post(f"/pieces/{pid}/advance-stage")
    assert r.status_code == 200, r.text

    # Each piece gets a unique 1-second window in the distant past.
    # That keeps multiple _walk_to_chased calls non-overlapping on both the
    # crucible and the goldsmith.
    base = 1577836800 + pid * 3600  # 2020-01-01T00:00:00Z + pid hours
    import time

    starts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(base))
    ends = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(base + 60))

    # Cast in the past so the window has ended.  Crucible 2 permits 18K.
    r = _post(
        f"/pieces/{pid}/cast",
        {
            "crucible_id": 2,
            "goldsmith_id": 1,
            "poured_mass_g": 25.0,
            "starts_at": starts,
            "ends_at": ends,
        },
    )
    assert r.status_code == 201, r.text

    # cast_active → cast_complete
    r = _post(f"/pieces/{pid}/advance-stage")
    assert r.status_code == 200, r.text

    # cast_complete → chased
    r = _post(f"/pieces/{pid}/advance-stage")
    assert r.status_code == 200, r.text

    return pid


def _walk_to_cast_active(
    serial: str, intent: str, grade: str, mass: float, smith_id: int
) -> int:
    """
    Create a fresh piece, assign it, assay it, and advance it to cast_active.
    The caller is responsible for booking any casting window.
    """
    r = _post(
        "/pieces",
        {
            "serial": serial,
            "intent_kind": intent,
            "alloy_grade": grade,
            "target_mass_g": mass,
        },
    )
    assert r.status_code == 201, r.text
    pid = _json(r)["piece_id"]
    assert _post(f"/goldsmiths/{smith_id}/assign", {"piece_id": pid}).status_code == 200
    assert (
        _post(
            f"/pieces/{pid}/assay",
            {"goldsmith_id": smith_id, "fineness_per_mille": 999},
        ).status_code
        == 201
    )
    assert _post(f"/pieces/{pid}/advance-stage").status_code == 200
    assert _post(f"/pieces/{pid}/advance-stage").status_code == 200
    return pid


# ---- class: health -------------------------------------------------------


class TestHealth:
    def test_001_health_ok(self):
        r = _get("/health")
        assert r.status_code == 200
        assert _json(r) == {"status": "ok"}


# ---- class: goldsmith creation (reference) -------------------------------


class TestGoldsmithCreate:
    def test_010_goldsmith_success(self):
        # Use mentor_id=7 (gerold, isolated in seed) so later cohort tests
        # rooted at smith 1 stay byte-identical to the seed tree.
        r = _post(
            "/goldsmiths",
            {
                "name": "iulius",
                "rank": "journeyman",
                "specialty": "ring",
                "mentor_id": 7,
            },
        )
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["name"] == "iulius"
        assert body["mentor_id"] == 7
        assert "goldsmith_id" in body

    def test_011_duplicate_name(self):
        r = _post(
            "/goldsmiths", {"name": "albrecht", "rank": "master", "specialty": "ring"}
        )
        assert r.status_code == 409
        assert _err(r) == "duplicate_name"

    def test_012_bad_rank(self):
        r = _post(
            "/goldsmiths",
            {"name": "junius", "rank": "grandmaster", "specialty": "ring"},
        )
        assert r.status_code == 422
        assert _err(r) == "missing_field"

    def test_013_bad_specialty(self):
        r = _post(
            "/goldsmiths", {"name": "kaiser", "rank": "master", "specialty": "armour"}
        )
        assert r.status_code == 422
        assert _err(r) == "missing_field"

    def test_014_missing_name(self):
        r = _post("/goldsmiths", {"rank": "master", "specialty": "ring"})
        assert r.status_code == 422
        assert _err(r) == "missing_field"

    def test_015_mentor_not_found(self):
        r = _post(
            "/goldsmiths",
            {
                "name": "lothar",
                "rank": "apprentice",
                "specialty": "ring",
                "mentor_id": 9999,
            },
        )
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"


# ---- class: piece creation (reference) -----------------------------------


class TestPieceCreate:
    def test_020_piece_success(self):
        r = _post(
            "/pieces",
            {
                "serial": "AA-9001",
                "intent_kind": "ring",
                "alloy_grade": "24K",
                "target_mass_g": 10.0,
            },
        )
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["stage"] == "ingot_selected"
        assert body["serial"] == "AA-9001"

    def test_021_duplicate_serial(self):
        r = _post(
            "/pieces",
            {
                "serial": "AA-0001",
                "intent_kind": "ring",
                "alloy_grade": "24K",
                "target_mass_g": 5.0,
            },
        )
        assert r.status_code == 409
        assert _err(r) == "duplicate_serial"

    def test_022_bad_intent(self):
        r = _post(
            "/pieces",
            {
                "serial": "AA-9002",
                "intent_kind": "spittoon",
                "alloy_grade": "24K",
                "target_mass_g": 5.0,
            },
        )
        assert r.status_code == 422
        assert _err(r) == "missing_field"

    def test_023_bad_grade(self):
        r = _post(
            "/pieces",
            {
                "serial": "AA-9003",
                "intent_kind": "ring",
                "alloy_grade": "9K",
                "target_mass_g": 5.0,
            },
        )
        assert r.status_code == 422
        assert _err(r) == "missing_field"

    def test_024_bad_mass(self):
        r = _post(
            "/pieces",
            {
                "serial": "AA-9004",
                "intent_kind": "ring",
                "alloy_grade": "24K",
                "target_mass_g": 0,
            },
        )
        assert r.status_code == 422
        assert _err(r) == "missing_field"

    def test_025_parent_not_found(self):
        r = _post(
            "/pieces",
            {
                "serial": "AA-9005",
                "intent_kind": "ring",
                "alloy_grade": "24K",
                "target_mass_g": 5.0,
                "parent_id": 9999,
            },
        )
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"


# ---- class: piece read ---------------------------------------------------


class TestPieceShow:
    def test_030_show_piece(self):
        r = _get("/pieces/1")
        assert r.status_code == 200
        body = _json(r)
        assert body["serial"] == "AA-0001"
        assert body["stage"] == "released"

    def test_031_show_404(self):
        r = _get("/pieces/99999")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"


# ---- class: search -------------------------------------------------------


class TestSearch:
    def test_040_search_stage_chased(self):
        r = _get("/pieces/search?stage=chased")
        assert r.status_code == 200
        ids = sorted(p["piece_id"] for p in _json(r)["pieces"])
        # Pieces 6, 13, 14, 15, 16 are chased in the seed.
        assert {6, 13, 14, 15, 16}.issubset(set(ids))

    def test_041_search_intent_brooch(self):
        r = _get("/pieces/search?intent_kind=brooch")
        assert r.status_code == 200
        ids = sorted(p["piece_id"] for p in _json(r)["pieces"])
        # Brooch seeded: 3, 8, 9, 10.
        assert {3, 8, 9, 10} == set(ids)

    def test_042_search_alloy_24K(self):
        r = _get("/pieces/search?alloy_grade=24K")
        assert r.status_code == 200
        ids = {p["piece_id"] for p in _json(r)["pieces"]}
        # Seeded 24K: 1, 5, 19. Plus AA-9001 from test_020.
        assert {1, 5, 19}.issubset(ids)

    def test_043_search_goldsmith(self):
        r = _get("/pieces/search?goldsmith=5")
        assert r.status_code == 200
        ids = sorted(p["piece_id"] for p in _json(r)["pieces"])
        # Smith 5 assigned: 8, 9.
        assert {8, 9} == set(ids)

    def test_044_search_combined(self):
        r = _get("/pieces/search?intent_kind=ring&stage=released")
        assert r.status_code == 200
        ids = sorted(p["piece_id"] for p in _json(r)["pieces"])
        # Released rings: 1, 4.
        assert {1, 4} == set(ids)

    def test_045_search_bad_stage_422(self):
        r = _get("/pieces/search?stage=polishing")
        assert r.status_code == 422
        assert _err(r) == "invalid_filter"

    def test_046_search_bad_intent_422(self):
        r = _get("/pieces/search?intent_kind=tankard")
        assert r.status_code == 422
        assert _err(r) == "invalid_filter"

    def test_047_search_bad_goldsmith_422(self):
        r = _get("/pieces/search?goldsmith=nine")
        assert r.status_code == 422
        assert _err(r) == "invalid_goldsmith_id"

    def test_048_search_unknown_goldsmith_empty(self):
        r = _get("/pieces/search?goldsmith=99999")
        assert r.status_code == 200
        assert _json(r)["pieces"] == []


# ---- class: provenance ---------------------------------------------------


class TestProvenance:
    def test_050_chain_three(self):
        r = _get("/pieces/10/provenance")
        assert r.status_code == 200
        chain = _json(r)["chain"]
        ids = [c["piece_id"] for c in chain]
        assert ids == [10, 9, 8]

    def test_051_chain_single(self):
        r = _get("/pieces/1/provenance")
        assert r.status_code == 200
        ids = [c["piece_id"] for c in _json(r)["chain"]]
        assert ids == [1]

    def test_052_chain_cycle_stops(self):
        r = _get("/pieces/17/provenance")
        assert r.status_code == 200
        ids = [c["piece_id"] for c in _json(r)["chain"]]
        # 17 → 18 → (would go back to 17 but stops).
        assert ids == [17, 18]

    def test_053_provenance_404(self):
        r = _get("/pieces/99999/provenance")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"


# ---- class: contribution -------------------------------------------------


class TestContribution:
    def test_060_dag_two_roots(self):
        r = _get("/pieces/12/contribution")
        assert r.status_code == 200
        roots = _json(r)["root_contributions"]
        by_id = {r["root_piece_id"]: r["contribution"] for r in roots}
        # piece 12 = 0.7 of piece 1 + 0.3 of piece 4.
        assert _approx(by_id[1], 0.7, tol=1e-6)
        assert _approx(by_id[4], 0.3, tol=1e-6)
        # Sorted ascending by root id.
        assert [r["root_piece_id"] for r in roots] == sorted(by_id.keys())

    def test_061_root_self(self):
        r = _get("/pieces/1/contribution")
        assert r.status_code == 200
        roots = _json(r)["root_contributions"]
        assert len(roots) == 1
        assert roots[0]["root_piece_id"] == 1
        assert _approx(roots[0]["contribution"], 1.0, tol=1e-6)

    def test_062_contribution_404(self):
        r = _get("/pieces/99999/contribution")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"


# ---- class: trend --------------------------------------------------------


class TestTrend:
    def test_070_piece_7_refining(self):
        r = _get("/pieces/7/trend")
        assert r.status_code == 200
        body = _json(r)
        assert body["n_buckets"] == 5
        assert _approx(body["slope"], 8.0, tol=1e-6)
        assert _approx(body["r2"], 0.984615, tol=1e-6)
        assert _approx(body["mk_z"], 2.204541, tol=1e-6)
        assert _approx(body["ts_slope"], 7.916667, tol=1e-6)
        assert body["direction"] == "refining"

    def test_071_piece_lt_3_buckets_null(self):
        # piece 1 has only one assay → 1 bucket → all stats null.
        r = _get("/pieces/1/trend")
        assert r.status_code == 200
        body = _json(r)
        assert body["slope"] is None
        assert body["r2"] is None
        assert body["mk_z"] is None
        assert body["ts_slope"] is None
        assert body["direction"] is None

    def test_072_trend_404(self):
        r = _get("/pieces/99999/trend")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"


# ---- class: workload -----------------------------------------------------


class TestWorkload:
    def test_080_smith_1_composite(self):
        r = _get("/goldsmiths/1/workload")
        assert r.status_code == 200
        body = _json(r)
        # composite = 4.0 × 1.05 × 1.10 = 4.62.
        assert _approx(body["composite_grade"], 4.62, tol=1e-4)

    def test_081_smith_5_composite(self):
        r = _get("/goldsmiths/5/workload")
        assert r.status_code == 200
        body = _json(r)
        # composite = 4.0 × 1.10 × 1.0 = 4.4.
        assert _approx(body["composite_grade"], 4.40, tol=1e-4)

    def test_082_smith_2_null(self):
        r = _get("/goldsmiths/2/workload")
        assert r.status_code == 200
        # Smith 2's active pieces (12, 17, 18) have no hallmarks → null.
        assert _json(r)["composite_grade"] is None

    def test_083_workload_404(self):
        r = _get("/goldsmiths/99999/workload")
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"


# ---- class: cohort -------------------------------------------------------


class TestCohort:
    def test_090_smith_1_cohort(self):
        r = _get("/goldsmiths/1/cohort")
        assert r.status_code == 200
        body = _json(r)
        ids = [m["goldsmith_id"] for m in body["members"]]
        assert ids == [1, 2, 3, 4]
        assert body["cohort_total_released"] == 3

    def test_091_smith_5_cohort(self):
        r = _get("/goldsmiths/5/cohort")
        assert r.status_code == 200
        body = _json(r)
        ids = [m["goldsmith_id"] for m in body["members"]]
        assert ids == [5, 6]
        # smith 5 has 1 released piece (9), smith 6 has 0.
        assert body["cohort_total_released"] == 1

    def test_092_cohort_404(self):
        r = _get("/goldsmiths/99999/cohort")
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"


# ---- class: assign -------------------------------------------------------


class TestAssign:
    def test_100_assign_success(self):
        # Piece 11 was seeded unassigned. Assign to smith 7 (gerold).
        r = _post("/goldsmiths/7/assign", {"piece_id": 11})
        assert r.status_code == 200
        body = _json(r)
        assert body == {"goldsmith_id": 7, "piece_id": 11}

    def test_101_smith_404(self):
        r = _post("/goldsmiths/99999/assign", {"piece_id": 11})
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"

    def test_102_piece_404(self):
        r = _post("/goldsmiths/7/assign", {"piece_id": 99999})
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"

    def test_103_already_assigned(self):
        # Piece 11 is now assigned (from test_100). Re-assign should 409.
        r = _post("/goldsmiths/8/assign", {"piece_id": 11})
        assert r.status_code == 409
        assert _err(r) == "already_assigned"

    def test_104_missing_piece_id(self):
        r = _post("/goldsmiths/7/assign", {})
        assert r.status_code == 422
        assert _err(r) == "missing_field"


# ---- class: assay --------------------------------------------------------


class TestAssay:
    def test_110_assay_success(self):
        # Piece 11 is ingot_selected; no assay yet in seed.
        r = _post("/pieces/11/assay", {"goldsmith_id": 7, "fineness_per_mille": 750})
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["piece_id"] == 11
        assert body["fineness_per_mille"] == 750

    def test_111_piece_404(self):
        r = _post("/pieces/99999/assay", {"goldsmith_id": 1, "fineness_per_mille": 999})
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"

    def test_112_already_released(self):
        r = _post("/pieces/1/assay", {"goldsmith_id": 1, "fineness_per_mille": 999})
        assert r.status_code == 409
        assert _err(r) == "already_released"

    def test_113_smith_404(self):
        r = _post(
            "/pieces/11/assay", {"goldsmith_id": 99999, "fineness_per_mille": 999}
        )
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"

    def test_114_bad_fineness(self):
        r = _post("/pieces/11/assay", {"goldsmith_id": 7, "fineness_per_mille": 2000})
        assert r.status_code == 422
        assert _err(r) == "invalid_fineness"


# ---- class: hallmark -----------------------------------------------------


class TestHallmark:
    def test_120_hallmark_success(self):
        # Piece 13 is chased — eligible.
        r = _post("/pieces/13/hallmark", {"goldsmith_id": 1, "letter": "A"})
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["piece_id"] == 13
        assert body["letter"] == "A"

    def test_121_hallmark_piece_404(self):
        r = _post("/pieces/99999/hallmark", {"goldsmith_id": 1, "letter": "A"})
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"

    def test_122_hallmark_wrong_stage(self):
        # Piece 5 is cast_complete, not chased.
        r = _post("/pieces/5/hallmark", {"goldsmith_id": 3, "letter": "A"})
        assert r.status_code == 409
        assert _err(r) == "wrong_stage"

    def test_123_hallmark_smith_404(self):
        # Piece 14 is chased.
        r = _post("/pieces/14/hallmark", {"goldsmith_id": 99999, "letter": "A"})
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"

    def test_124_hallmark_bad_letter(self):
        # Use smith 6 (frieda) who has no prior hallmarks, so the per-smith
        # monotonic constraint can't fire and we genuinely test letter validation.
        r = _post("/pieces/14/hallmark", {"goldsmith_id": 6, "letter": "Q"})
        assert r.status_code == 422
        assert _err(r) == "invalid_letter"


# ---- class: advance-stage ------------------------------------------------


class TestAdvanceStage:
    def test_130_advance_19_to_cast_complete(self):
        # Piece 19 is cast_active with casting ending 2026-01-10T09:00:00Z (in past).
        r = _post("/pieces/19/advance-stage")
        assert r.status_code == 200, r.text
        body = _json(r)
        assert body == {"piece_id": 19, "stage": "cast_complete"}

    def test_131_advance_404(self):
        r = _post("/pieces/99999/advance-stage")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"

    def test_132_advance_already_released(self):
        r = _post("/pieces/1/advance-stage")
        assert r.status_code == 409
        assert _err(r) == "already_released"

    def test_133_advance_hallmarked_wrong_stage(self):
        # Piece 7 is hallmarked — advance-stage refuses (must use /release).
        r = _post("/pieces/7/advance-stage")
        assert r.status_code == 409
        assert _err(r) == "wrong_stage"

    def test_134_advance_missing_hallmark(self):
        # Piece 6 is chased but has no hallmark — cannot advance to hallmarked.
        r = _post("/pieces/6/advance-stage")
        assert r.status_code == 409
        assert _err(r) == "missing_hallmark"


# ---- class: cast ---------------------------------------------------------


class TestCast:
    PIECE_FOR_CAST = None
    PIECE_FOR_OVERLAP = None

    def test_140_cast_404_piece(self):
        r = _post(
            "/pieces/99999/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 1,
                "poured_mass_g": 5.0,
                "starts_at": "2030-01-01T08:00:00Z",
                "ends_at": "2030-01-01T09:00:00Z",
            },
        )
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"

    def test_141_cast_wrong_stage(self):
        # Piece 11 is ingot_selected (not cast_active).
        r = _post(
            "/pieces/11/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 1,
                "poured_mass_g": 5.0,
                "starts_at": "2030-01-01T08:00:00Z",
                "ends_at": "2030-01-01T09:00:00Z",
            },
        )
        assert r.status_code == 409
        assert _err(r) == "wrong_stage"

    def test_142_create_piece_for_cast(self):
        # Create a fresh piece and walk it to cast_active.
        # 18K so crucible 1 (permitted_alloys=[14K,18K]) is legal.
        r = _post(
            "/pieces",
            {
                "serial": "AA-9100",
                "intent_kind": "ring",
                "alloy_grade": "18K",
                "target_mass_g": 12.0,
            },
        )
        pid = _json(r)["piece_id"]
        TestCast.PIECE_FOR_CAST = pid
        # Assign smith 7, add assay, walk to cast_active.
        assert _post("/goldsmiths/7/assign", {"piece_id": pid}).status_code == 200
        assert (
            _post(
                f"/pieces/{pid}/assay", {"goldsmith_id": 7, "fineness_per_mille": 999}
            ).status_code
            == 201
        )
        assert _post(f"/pieces/{pid}/advance-stage").status_code == 200  # → assayed
        assert _post(f"/pieces/{pid}/advance-stage").status_code == 200  # → cast_active

    def test_143_cast_invalid_window(self):
        pid = TestCast.PIECE_FOR_CAST
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 7,
                "poured_mass_g": 12.0,
                "starts_at": "2030-02-01T09:00:00Z",
                "ends_at": "2030-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "invalid_window"

    def test_144_cast_invalid_mass(self):
        pid = TestCast.PIECE_FOR_CAST
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 7,
                "poured_mass_g": -1.0,
                "starts_at": "2030-02-01T08:00:00Z",
                "ends_at": "2030-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "invalid_mass"

    def test_145_cast_capacity_exceeded(self):
        pid = TestCast.PIECE_FOR_CAST
        # Crucible 1 capacity is 200g; ask for 300g.
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 7,
                "poured_mass_g": 300.0,
                "starts_at": "2030-02-01T08:00:00Z",
                "ends_at": "2030-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "capacity_exceeded"

    def test_146_cast_smith_404(self):
        pid = TestCast.PIECE_FOR_CAST
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 99999,
                "poured_mass_g": 12.0,
                "starts_at": "2030-02-01T08:00:00Z",
                "ends_at": "2030-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 404
        assert _err(r) == "goldsmith_not_found"

    def test_147_cast_crucible_404(self):
        pid = TestCast.PIECE_FOR_CAST
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 99999,
                "goldsmith_id": 7,
                "poured_mass_g": 12.0,
                "starts_at": "2030-02-01T08:00:00Z",
                "ends_at": "2030-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 404
        assert _err(r) == "crucible_not_found"

    def test_148_cast_success(self):
        pid = TestCast.PIECE_FOR_CAST
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 7,
                "poured_mass_g": 12.0,
                "starts_at": "2030-02-01T08:00:00Z",
                "ends_at": "2030-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["piece_id"] == pid
        assert body["crucible_id"] == 1

    def test_149_cast_crucible_overlap(self):
        # Make a SECOND cast_active piece, then try to book overlapping crucible 1.
        # 18K so crucible 1 is permitted.
        r = _post(
            "/pieces",
            {
                "serial": "AA-9101",
                "intent_kind": "ring",
                "alloy_grade": "18K",
                "target_mass_g": 8.0,
            },
        )
        pid2 = _json(r)["piece_id"]
        TestCast.PIECE_FOR_OVERLAP = pid2
        assert _post("/goldsmiths/8/assign", {"piece_id": pid2}).status_code == 200
        assert (
            _post(
                f"/pieces/{pid2}/assay", {"goldsmith_id": 8, "fineness_per_mille": 999}
            ).status_code
            == 201
        )
        assert _post(f"/pieces/{pid2}/advance-stage").status_code == 200
        assert _post(f"/pieces/{pid2}/advance-stage").status_code == 200

        # Overlaps test_148's window 08:00–09:00 on crucible 1.
        r = _post(
            f"/pieces/{pid2}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 8,
                "poured_mass_g": 8.0,
                "starts_at": "2030-02-01T08:30:00Z",
                "ends_at": "2030-02-01T09:30:00Z",
            },
        )
        assert r.status_code == 409
        assert _err(r) == "crucible_overlap"

    def test_150_cast_goldsmith_busy(self):
        # Smith 7 booked test_148. Smith 7 tries an overlapping cast on a
        # different crucible (2) for the overlap piece.
        pid2 = TestCast.PIECE_FOR_OVERLAP
        r = _post(
            f"/pieces/{pid2}/cast",
            {
                "crucible_id": 2,
                "goldsmith_id": 7,
                "poured_mass_g": 8.0,
                "starts_at": "2030-02-01T08:30:00Z",
                "ends_at": "2030-02-01T09:30:00Z",
            },
        )
        assert r.status_code == 409
        assert _err(r) == "goldsmith_busy"


# ---- class: bulk-cast ----------------------------------------------------


class TestBulkCast:
    BULK_ATOMIC_PIECE = None

    def test_151_bulk_cast_empty_batch(self):
        r = _post("/pieces/bulk-cast", {"casts": []})
        assert r.status_code == 422
        assert _err(r) == "empty_batch"

    def test_152_bulk_cast_invalid_body(self):
        r = _post_raw("/pieces/bulk-cast", "{not json}")
        assert r.status_code == 422
        assert _err(r) == "invalid_body"

    def test_153_bulk_cast_duplicate_piece_precedes_row_validation(self):
        pid = _walk_to_cast_active("AA-9500", "ring", "18K", 10.0, 7)
        r = _post(
            "/pieces/bulk-cast",
            {
                "casts": [
                    {
                        "piece_id": pid,
                        "crucible_id": 1,
                        "goldsmith_id": 7,
                        "poured_mass_g": 10.0,
                        "starts_at": "2032-01-01T08:00:00Z",
                        "ends_at": "2032-01-01T09:00:00Z",
                    },
                    {
                        "piece_id": pid,
                        "crucible_id": 99999,
                        "goldsmith_id": 99999,
                        "poured_mass_g": -1.0,
                        "starts_at": "2032-01-01T09:00:00Z",
                        "ends_at": "2032-01-01T08:00:00Z",
                    },
                ]
            },
        )
        assert r.status_code == 422
        assert _err(r) == "dup_in_batch"

    def test_154_bulk_cast_collects_existing_and_batch_conflicts(self):
        first = _walk_to_cast_active("AA-9501", "ring", "18K", 10.0, 7)
        second = _walk_to_cast_active("AA-9502", "ring", "18K", 11.0, 8)
        third = _walk_to_cast_active("AA-9503", "ring", "18K", 12.0, 6)
        TestBulkCast.BULK_ATOMIC_PIECE = first

        r = _post(
            "/pieces/bulk-cast",
            {
                "casts": [
                    {
                        "piece_id": first,
                        "crucible_id": 1,
                        "goldsmith_id": 7,
                        "poured_mass_g": 10.0,
                        "starts_at": "2032-02-01T08:00:00Z",
                        "ends_at": "2032-02-01T09:00:00Z",
                    },
                    {
                        "piece_id": second,
                        "crucible_id": 1,
                        "goldsmith_id": 8,
                        "poured_mass_g": 11.0,
                        "starts_at": "2032-02-01T08:30:00Z",
                        "ends_at": "2032-02-01T09:30:00Z",
                    },
                    {
                        "piece_id": third,
                        "crucible_id": 2,
                        "goldsmith_id": 7,
                        "poured_mass_g": 12.0,
                        "starts_at": "2032-02-01T08:15:00Z",
                        "ends_at": "2032-02-01T08:45:00Z",
                    },
                    {
                        "piece_id": 1,
                        "crucible_id": 1,
                        "goldsmith_id": 7,
                        "poured_mass_g": 5.0,
                        "starts_at": "2032-02-01T10:00:00Z",
                        "ends_at": "2032-02-01T11:00:00Z",
                    },
                    {
                        "piece_id": 99999,
                        "crucible_id": 1,
                        "goldsmith_id": 7,
                        "poured_mass_g": 5.0,
                        "starts_at": "2032-02-01T12:00:00Z",
                        "ends_at": "2032-02-01T13:00:00Z",
                    },
                ]
            },
        )
        assert r.status_code == 422, r.text
        body = _json(r)
        assert body["error"] == "validation_failed"
        codes = {(e["index"], e["code"]) for e in body["errors"]}
        assert (1, "crucible_overlap_batch") in codes
        assert (2, "goldsmith_busy_batch") in codes
        assert (3, "already_released") in codes
        assert (4, "piece_not_found") in codes

    def test_155_bulk_cast_failed_batch_is_atomic(self):
        pid = TestBulkCast.BULK_ATOMIC_PIECE
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 7,
                "poured_mass_g": 10.0,
                "starts_at": "2032-02-01T08:00:00Z",
                "ends_at": "2032-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 201, r.text

    def test_156_bulk_cast_success_and_audit_entry(self):
        before_actions = [
            e["action"] for e in _json(_get("/audit?limit=200"))["entries"]
        ]
        first = _walk_to_cast_active("AA-9504", "ring", "18K", 9.0, 8)
        second = _walk_to_cast_active("AA-9505", "ring", "22K", 12.0, 7)
        r = _post(
            "/pieces/bulk-cast",
            {
                "casts": [
                    {
                        "piece_id": first,
                        "crucible_id": 1,
                        "goldsmith_id": 8,
                        "poured_mass_g": 9.0,
                        "starts_at": "2032-03-01T08:00:00Z",
                        "ends_at": "2032-03-01T09:00:00Z",
                    },
                    {
                        "piece_id": second,
                        "crucible_id": 2,
                        "goldsmith_id": 7,
                        "poured_mass_g": 12.0,
                        "starts_at": "2032-03-01T08:30:00Z",
                        "ends_at": "2032-03-01T09:30:00Z",
                    },
                ]
            },
        )
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["count"] == 2
        assert len(body["casting_ids"]) == 2
        assert body["casting_ids"] == sorted(body["casting_ids"])
        after_actions = [
            e["action"] for e in _json(_get("/audit?limit=200"))["entries"]
        ]
        assert after_actions.count("bulk_cast") == before_actions.count("bulk_cast") + 1


# ---- class: release ------------------------------------------------------


class TestRelease:
    def test_160_release_success(self):
        # Piece 8 is hallmarked (smith 5). Release it.
        r = _post("/pieces/8/release")
        assert r.status_code == 200, r.text
        body = _json(r)
        assert body["piece_id"] == 8
        assert body["stage"] == "released"
        assert "released_at" in body

    def test_161_release_404(self):
        r = _post("/pieces/99999/release")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"

    def test_162_release_already_released(self):
        r = _post("/pieces/1/release")
        assert r.status_code == 409
        assert _err(r) == "already_released"

    def test_163_release_wrong_stage(self):
        # Piece 6 is chased.
        r = _post("/pieces/6/release")
        assert r.status_code == 409
        assert _err(r) == "wrong_stage"


# ---- class: bulk-hallmark -----------------------------------------------


class TestBulkHallmark:
    def test_170_bulk_empty_batch(self):
        r = _post("/pieces/bulk-hallmark", {"hallmarks": []})
        assert r.status_code == 422
        assert _err(r) == "empty_batch"

    def test_171_bulk_invalid_body(self):
        r = _post_raw("/pieces/bulk-hallmark", "{not json}")
        assert r.status_code == 422
        assert _err(r) == "invalid_body"

    def test_172_bulk_dup_in_batch(self):
        # Two rows with same (piece, goldsmith).
        r = _post(
            "/pieces/bulk-hallmark",
            {
                "hallmarks": [
                    {"piece_id": 14, "goldsmith_id": 1, "letter": "A"},
                    {"piece_id": 14, "goldsmith_id": 1, "letter": "Q"},
                ]
            },
        )
        assert r.status_code == 422
        assert _err(r) == "dup_in_batch"

    def test_173_bulk_validation_failed(self):
        # 4 rows: 0=OK, 1=released_piece, 2=invalid_letter, 3=piece_not_found.
        r = _post(
            "/pieces/bulk-hallmark",
            {
                "hallmarks": [
                    {"piece_id": 14, "goldsmith_id": 1, "letter": "A"},
                    {"piece_id": 1, "goldsmith_id": 1, "letter": "A"},
                    {"piece_id": 15, "goldsmith_id": 1, "letter": "Q"},
                    {"piece_id": 9999, "goldsmith_id": 1, "letter": "A"},
                ]
            },
        )
        assert r.status_code == 422
        body = _json(r)
        assert body["error"] == "validation_failed"
        codes = {(e["index"], e["code"]) for e in body["errors"]}
        assert (1, "already_released") in codes
        assert (2, "invalid_letter") in codes
        assert (3, "piece_not_found") in codes

    def test_174_bulk_atomicity_after_fail(self):
        # The failed batch above must not have inserted ANY hallmark.
        # We verify by checking workload's letter_base hasn't changed:
        # smith 1's composite remains 4.62 if pieces 14, 15 still unhallmarked.
        # (Piece 13 was hallmarked in test_120 already.)
        r = _get("/goldsmiths/1/workload")
        assert r.status_code == 200
        # The single hallmark on piece 13 added letter A for an active
        # piece — but with bulk failing atomicity, 14 & 15 stay unhallmarked.
        # Composite math now spans pieces 3, 7, 13 (each A, all rings except 3).
        # letter_base = (4+4+4)/3 = 4.0; specialty mean (1.0+1.1+1.1)/3 = 3.2/3
        # = 1.066666...; streak still A,A,A → 0.10.
        # composite = 4.0 * 1.066666... * 1.10 = 4.6933...
        # Just sanity-check it's not enormously different.
        comp = _json(r)["composite_grade"]
        assert comp is not None
        assert 4.0 < comp < 5.5

    def test_175_bulk_success(self):
        # Hallmark pieces 14, 15, 16 in a single batch.
        r = _post(
            "/pieces/bulk-hallmark",
            {
                "hallmarks": [
                    {"piece_id": 14, "goldsmith_id": 1, "letter": "A"},
                    {"piece_id": 15, "goldsmith_id": 1, "letter": "B"},
                    {"piece_id": 16, "goldsmith_id": 1, "letter": "A"},
                ]
            },
        )
        assert r.status_code == 201, r.text
        body = _json(r)
        assert body["count"] == 3
        assert len(body["hallmark_ids"]) == 3


# ---- class: audit --------------------------------------------------------


class TestAudit:
    def test_180_audit_has_entries(self):
        r = _get("/audit")
        assert r.status_code == 200
        entries = _json(r)["entries"]
        # We expect: advance 19 (test_130), one cast (test_148),
        # one hallmark (test_120), one release (test_160),
        # one bulk_hallmark (test_175) — at minimum 5 entries.
        actions = [e["action"] for e in entries]
        assert "advance_stage" in actions
        assert "cast" in actions
        assert "hallmark" in actions
        assert "release" in actions
        assert "bulk_hallmark" in actions

    def test_181_audit_verify_true(self):
        r = _get("/audit/verify")
        assert r.status_code == 200
        body = _json(r)
        assert body["verified"] is True
        assert body["entries_checked"] >= 5

    def test_182_audit_chain_hash_correct(self):
        # Recompute the chain client-side and verify the server matches.
        r = _get("/audit?limit=200")
        entries = _json(r)["entries"]
        prev = "0" * 64
        for e in entries:
            seq = e["seq"]
            action = e["action"]
            payload = e["payload"]
            expect = hashlib.sha256(f"{prev}|{action}|{payload}".encode()).hexdigest()
            assert e["prev_hash"] == prev, f"prev mismatch at seq {seq}"
            assert e["entry_hash"] == expect, f"hash mismatch at seq {seq}"
            prev = e["entry_hash"]

    def test_183_audit_since_filter(self):
        # Get all entries, then re-fetch with since=<first.seq> and confirm
        # the first row is gone from the filtered response.
        r = _get("/audit?limit=200")
        all_entries = _json(r)["entries"]
        if len(all_entries) >= 2:
            first_seq = all_entries[0]["seq"]
            r2 = _get(f"/audit?since={first_seq}")
            entries2 = _json(r2)["entries"]
            assert all(e["seq"] > first_seq for e in entries2)

    def test_184_audit_assign_does_not_append(self):
        # Assign endpoint does NOT append. Take pre-count, assign, post-count.
        before = len(_json(_get("/audit?limit=200"))["entries"])

        # Create a new piece + assign it.
        r = _post(
            "/pieces",
            {
                "serial": "AA-9200",
                "intent_kind": "ring",
                "alloy_grade": "22K",
                "target_mass_g": 5.0,
            },
        )
        pid = _json(r)["piece_id"]
        r = _post("/goldsmiths/8/assign", {"piece_id": pid})
        assert r.status_code == 200

        after = len(_json(_get("/audit?limit=200"))["entries"])
        assert after == before, "assign should not append an audit entry"


# ---- class: crucible permitted alloys + master-rank constraint -----------


class TestAlloyAndRank:
    """
    Read-only inspection of the crucible matrix via cast attempts on
    freshly walked-through pieces. These tests come AFTER the main cast
    tests because they create more cast_active pieces.
    """

    @staticmethod
    def _walk_to_cast_active(
        serial: str, intent: str, grade: str, mass: float, smith_id: int
    ) -> int:
        r = _post(
            "/pieces",
            {
                "serial": serial,
                "intent_kind": intent,
                "alloy_grade": grade,
                "target_mass_g": mass,
            },
        )
        pid = _json(r)["piece_id"]
        assert (
            _post(f"/goldsmiths/{smith_id}/assign", {"piece_id": pid}).status_code
            == 200
        )
        assert (
            _post(
                f"/pieces/{pid}/assay",
                {"goldsmith_id": smith_id, "fineness_per_mille": 999},
            ).status_code
            == 201
        )
        assert _post(f"/pieces/{pid}/advance-stage").status_code == 200
        assert _post(f"/pieces/{pid}/advance-stage").status_code == 200
        return pid

    def test_190_alloy_incompatible_22K_on_crucible_1(self):
        # Crucible 1 permits 14K/18K only. A 22K piece must be rejected.
        pid = self._walk_to_cast_active("AA-9300", "ring", "22K", 5.0, 1)
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 1,
                "poured_mass_g": 5.0,
                "starts_at": "2031-01-01T08:00:00Z",
                "ends_at": "2031-01-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "alloy_grade_incompatible"

    def test_191_alloy_incompatible_24K_on_crucible_2(self):
        # Crucible 2 permits up to 22K. A 24K piece must be rejected.
        pid = self._walk_to_cast_active("AA-9301", "ring", "24K", 8.0, 1)
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 2,
                "goldsmith_id": 1,
                "poured_mass_g": 8.0,
                "starts_at": "2031-02-01T08:00:00Z",
                "ends_at": "2031-02-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "alloy_grade_incompatible"

    def test_192_rank_insufficient_24K_journeyman(self):
        # 24K + non-master smith → 422 rank_insufficient.
        # Smith 8 (hilde) is journeyman.
        pid = self._walk_to_cast_active("AA-9302", "ring", "24K", 6.0, 8)
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 3,
                "goldsmith_id": 8,
                "poured_mass_g": 6.0,
                "starts_at": "2031-03-01T08:00:00Z",
                "ends_at": "2031-03-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "rank_insufficient"

    def test_193_rank_master_24K_succeeds(self):
        # 24K + master smith → success.
        pid = self._walk_to_cast_active("AA-9303", "ring", "24K", 6.0, 1)
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 3,
                "goldsmith_id": 1,
                "poured_mass_g": 6.0,
                "starts_at": "2031-04-01T08:00:00Z",
                "ends_at": "2031-04-01T09:00:00Z",
            },
        )
        assert r.status_code == 201, r.text

    def test_194_precedence_alloy_beats_capacity(self):
        # 22K piece on crucible 1, mass also too large (300 > 200).
        # alloy_grade_incompatible must win over capacity_exceeded.
        pid = self._walk_to_cast_active("AA-9304", "ring", "22K", 300.0, 1)
        r = _post(
            f"/pieces/{pid}/cast",
            {
                "crucible_id": 1,
                "goldsmith_id": 1,
                "poured_mass_g": 300.0,
                "starts_at": "2031-05-01T08:00:00Z",
                "ends_at": "2031-05-01T09:00:00Z",
            },
        )
        assert r.status_code == 422
        assert _err(r) == "alloy_grade_incompatible"


# ---- class: hallmark monotonic timestamp constraint ----------------------


class TestMonotonicHallmark:
    """
    Smith 1 already has hallmarks in the seed with the latest at
    2026-02-01T10:00:00Z (piece 7). Plus tests above added hallmarks on
    pieces 13 and 14/15/16 with `now()` timestamps (~2026-06-xx). Any new
    hallmark by smith 1 with recorded_at older than the latest must be
    rejected with 409 ts_not_monotonic.
    """

    def test_200_monotonic_violation_explicit_ts(self):
        # Use a fresh chased piece + smith 1 + an explicit historical ts.
        pid = _walk_to_chased("AA-9400")
        r = _post(
            f"/pieces/{pid}/hallmark",
            {"goldsmith_id": 1, "letter": "A", "recorded_at": "2024-01-01T00:00:00Z"},
        )
        assert r.status_code == 409
        assert _err(r) == "ts_not_monotonic"

    def test_201_monotonic_ok_future_ts(self):
        pid = _walk_to_chased("AA-9401")
        r = _post(
            f"/pieces/{pid}/hallmark",
            {"goldsmith_id": 1, "letter": "A", "recorded_at": "2099-12-31T23:59:59Z"},
        )
        assert r.status_code == 201, r.text

    def test_202_first_hallmark_for_smith_passes(self):
        # Smith 6 (frieda) has NO hallmarks. First one with any ts succeeds.
        pid = _walk_to_chased("AA-9402")
        r = _post(
            f"/pieces/{pid}/hallmark",
            {"goldsmith_id": 6, "letter": "B", "recorded_at": "2020-01-01T00:00:00Z"},
        )
        assert r.status_code == 201, r.text


# ---- class: lineage grade ------------------------------------------------


class TestLineageGrade:
    def test_210_piece_10_grade_3_333333(self):
        r = _get("/pieces/10/lineage-grade")
        assert r.status_code == 200, r.text
        body = _json(r)
        assert _approx(body["lineage_grade"], 3.333333, tol=1e-6)
        ancestors = body["ancestors"]
        depths = [a["depth"] for a in ancestors]
        assert depths == [1, 2]
        assert {a["piece_id"] for a in ancestors} == {9, 8}

    def test_211_piece_1_empty_lineage(self):
        # Piece 1 has no parent → no ancestors.
        r = _get("/pieces/1/lineage-grade")
        assert r.status_code == 422
        assert _err(r) == "empty_lineage"

    def test_212_piece_17_cycle_empty_lineage(self):
        # Cycle 17↔18 — neither has any hallmark, so empty_lineage.
        r = _get("/pieces/17/lineage-grade")
        assert r.status_code == 422
        assert _err(r) == "empty_lineage"

    def test_213_lineage_404(self):
        r = _get("/pieces/99999/lineage-grade")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"


# ---- class: mass attribution ---------------------------------------------


class TestMassAttribution:
    def test_220_piece_12_single_hop(self):
        # piece 12 target_mass = 300.0; components {1:0.7, 4:0.3}.
        r = _get("/pieces/12/mass-attribution")
        assert r.status_code == 200, r.text
        body = _json(r)
        assert _approx(body["target_mass_g"], 300.0)
        by_id = {
            a["root_piece_id"]: a["attribution_g"] for a in body["root_attributions"]
        }
        assert _approx(by_id[1], 210.0, tol=1e-4)
        assert _approx(by_id[4], 90.0, tol=1e-4)
        # Sum equals target_mass_g.
        assert _approx(sum(by_id.values()), 300.0, tol=1e-4)

    def test_221_piece_20_two_hop(self):
        # piece 20 target_mass = 400.0; components {12:0.5, 8:0.5}.
        # piece 12 → {1:0.7, 4:0.3}, so piece 1 gets 400*0.5*0.7=140, piece 4: 60.
        # piece 8 is a root → gets 200.
        r = _get("/pieces/20/mass-attribution")
        assert r.status_code == 200, r.text
        body = _json(r)
        by_id = {
            a["root_piece_id"]: a["attribution_g"] for a in body["root_attributions"]
        }
        assert _approx(by_id[1], 140.0, tol=1e-4)
        assert _approx(by_id[4], 60.0, tol=1e-4)
        assert _approx(by_id[8], 200.0, tol=1e-4)
        assert _approx(sum(by_id.values()), 400.0, tol=1e-4)
        # Sort order ascending.
        ids = [a["root_piece_id"] for a in body["root_attributions"]]
        assert ids == sorted(ids)

    def test_222_piece_1_self_root(self):
        # Piece 1 has no components → it itself is the root with full mass.
        r = _get("/pieces/1/mass-attribution")
        assert r.status_code == 200
        body = _json(r)
        roots = body["root_attributions"]
        assert len(roots) == 1
        assert roots[0]["root_piece_id"] == 1
        assert _approx(roots[0]["attribution_g"], 50.0)

    def test_223_mass_attribution_404(self):
        r = _get("/pieces/99999/mass-attribution")
        assert r.status_code == 404
        assert _err(r) == "piece_not_found"
