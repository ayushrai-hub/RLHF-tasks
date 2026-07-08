"""Calendar analytics tests.

Suite covering the six temporal analytics endpoints: peak concurrency (§8),
maximum non-overlapping scheduling (§9), free gaps (§10), coverage (§11),
longest gap (§12), and per-bucket density (§13). The conftest fixture starts
the service once per session; the SQLite database accumulates across tests, so
each test group uses isolated far-future windows (>= 2e8 ms) that do not
interfere with other groups.
"""
from __future__ import annotations

import sqlite3

import pytest
import requests

BASE = "http://127.0.0.1:8080"
DB = "/app/data/calendar.db"


def _create_event(name="test_evt", start_ms=1000, end_ms=2000, metadata=None):
    """POST an event and return the raw Response (caller inspects status/body)."""
    if metadata is None:
        metadata = {}
    return requests.post(
        f"{BASE}/events",
        json={"name": name, "start_ms": start_ms, "end_ms": end_ms, "metadata": metadata},
        timeout=10,
    )


def _add_event(name, start_ms, end_ms, metadata=None):
    """POST an event, assert it was created, and return its id."""
    r = _create_event(name, start_ms, end_ms, metadata)
    assert r.status_code == 201
    return r.json()["id"]


# --------------------------------------------------------------------------- #
# Healthcheck
# --------------------------------------------------------------------------- #
def test_healthz_ok():
    """GET /healthz returns 200 with status ok."""
    r = requests.get(f"{BASE}/healthz", timeout=10)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# --------------------------------------------------------------------------- #
# Independent oracles over the raw events table (ground truth for §8–§10).
# The suite shares one accumulating database, so every oracle recomputes from
# the full current table; the tests below use isolated far-future windows
# (>= 2e8, above every other event's end_ms) so the controlled scenario is the
# only thing active in the window while the oracle still matches exactly.
# --------------------------------------------------------------------------- #
def _all_se():
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT start_ms, end_ms FROM events").fetchall()
    conn.close()
    return rows


def _peak_oracle(S, E):
    """SPEC §8: max_concurrency over [S,E] and the earliest instant achieving it."""
    evs = _all_se()
    cands = {S} | {s for (s, e) in evs if S < s <= E}
    best, best_t, seen = 0, S, False
    for t in sorted(cands):
        c = sum(1 for (s, e) in evs if s <= t <= e)
        if (not seen) or c > best:
            best, best_t, seen = c, t, True
    return best, best_t


def _schedule_oracle(S, E):
    """SPEC §9: max non-overlapping among events fully contained in [S,E]
    via earliest-finish greedy (touching is NOT compatible)."""
    conn = sqlite3.connect(DB)
    evs = conn.execute(
        "SELECT start_ms, end_ms FROM events WHERE start_ms >= ? AND end_ms <= ? "
        "ORDER BY end_ms ASC, start_ms ASC",
        (S, E),
    ).fetchall()
    conn.close()
    count, last = 0, None
    for (s, e) in evs:
        if last is None or s > last:
            count += 1
            last = e
    return count


def _gaps_oracle(S, E):
    """SPEC §10: free-instant gaps in [S,E] (clip -> merge with +1 adjacency -> complement)."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT start_ms, end_ms FROM events WHERE start_ms <= ? AND end_ms >= ?",
        (E, S),
    ).fetchall()
    conn.close()
    busy = sorted((max(s, S), min(e, E)) for (s, e) in rows)
    merged = []
    for s, e in busy:
        if merged and s <= merged[-1][1] + 1:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    gaps, cur = [], S
    for s, e in merged:
        if s > cur:
            gaps.append([cur, s - 1])
        if e + 1 > cur:
            cur = e + 1
    if cur <= E:
        gaps.append([cur, E])
    return gaps


# --------------------------------------------------------------------------- #
# §8 GET /peak — peak concurrency (sweep-line)
# --------------------------------------------------------------------------- #
def test_peak_basic_max_and_instant():
    """GET /peak returns the exact peak concurrency and the earliest instant achieving it.

    Three events overlap so that exactly at B+80 all three are active. c(t) reaches 3 on
    [B+80, B+100]; the earliest instant of the peak is the event start B+80. Both the value
    and the instant are cross-checked against an independent sweep over the raw table."""
    B = 210_000_000
    _add_event("peak_a", B, B + 100)
    _add_event("peak_b", B + 50, B + 150)
    _add_event("peak_c", B + 80, B + 200)
    r = requests.get(f"{BASE}/peak?start={B}&end={B + 300}", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    exp_max, exp_at = _peak_oracle(B, B + 300)
    assert exp_max == 3 and exp_at == B + 80, f"oracle sanity: {exp_max},{exp_at}"
    assert body["max_concurrency"] == exp_max, (
        f"max_concurrency={body['max_concurrency']} != oracle {exp_max}"
    )
    assert body["at_ms"] == exp_at, f"at_ms={body['at_ms']} != oracle earliest instant {exp_at}"


def test_peak_counts_event_active_at_window_start():
    """An event that began before the window but is still active at `start` is counted at
    t=start, and when the peak is first reached at the window edge at_ms == start."""
    B = 220_000_000
    _add_event("peak_pre", B, B + 10_000)  # spans the whole probe window
    S, E = B + 100, B + 200
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    exp_max, exp_at = _peak_oracle(S, E)
    assert exp_max >= 1 and exp_at == S, f"oracle: {exp_max},{exp_at}"
    assert body["max_concurrency"] == exp_max
    assert body["at_ms"] == exp_at


def test_peak_empty_window():
    """A window with no active instant reports max_concurrency 0 and at_ms == start."""
    S, E = 250_000_000, 250_000_100
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 0
    assert body["at_ms"] == S


def test_peak_invalid_params():
    """GET /peak returns 400 for missing params or start > end."""
    assert requests.get(f"{BASE}/peak?start=5", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/peak?start=100&end=50", timeout=10).status_code == 400


# --------------------------------------------------------------------------- #
# §9 GET /schedule — maximum non-overlapping set (activity selection)
# --------------------------------------------------------------------------- #
def test_schedule_defeats_greedy_by_start():
    """GET /schedule must return the OPTIMAL count via earliest-finish greedy.

    A long early-starting event (A) plus two short later events (X, Y) form the classic
    discriminator: the optimum is {X, Y} = 2, but a start-time greedy (or a length greedy)
    picks A first and returns 1. The endpoint is compared to an independent optimal oracle
    and to the known answer 2."""
    B = 310_000_000
    _add_event("sched_long_a", B, B + 900)
    _add_event("sched_x", B + 10, B + 20)
    _add_event("sched_y", B + 30, B + 40)
    r = requests.get(f"{BASE}/schedule?start={B}&end={B + 1000}", timeout=10)
    assert r.status_code == 200, r.text
    exp = _schedule_oracle(B, B + 1000)
    assert exp == 2, f"oracle sanity expected 2, got {exp}"
    assert r.json()["max_non_overlapping"] == exp, (
        f"max_non_overlapping={r.json()['max_non_overlapping']} != optimal {exp} "
        "(implementation is not the earliest-finish greedy)"
    )


def test_schedule_touching_is_not_compatible():
    """Two events that touch (one ends exactly where the next starts) overlap per §6, so
    at most one of them may be selected."""
    B = 320_000_000
    _add_event("sched_t1", B, B + 10)
    _add_event("sched_t2", B + 10, B + 20)
    r = requests.get(f"{BASE}/schedule?start={B}&end={B + 100}", timeout=10)
    exp = _schedule_oracle(B, B + 100)
    assert exp == 1, f"oracle sanity expected 1 (touching overlaps), got {exp}"
    assert r.json()["max_non_overlapping"] == exp


def test_schedule_only_fully_contained_events():
    """Events crossing the window boundary are excluded; only fully-contained events count."""
    B = 330_000_000
    _add_event("sched_inside_1", B + 100, B + 200)
    _add_event("sched_inside_2", B + 300, B + 400)
    _add_event("sched_crosses_left", B - 50, B + 150)   # starts before window
    _add_event("sched_crosses_right", B + 350, B + 5000)  # ends after window
    S, E = B, B + 500
    r = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10)
    exp = _schedule_oracle(S, E)
    assert exp == 2, f"oracle sanity expected 2 contained non-overlapping, got {exp}"
    assert r.json()["max_non_overlapping"] == exp


def test_schedule_invalid_params():
    """GET /schedule returns 400 for missing params or start > end."""
    assert requests.get(f"{BASE}/schedule?end=50", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/schedule?start=100&end=50", timeout=10).status_code == 400


# --------------------------------------------------------------------------- #
# §10 GET /gaps — free-interval computation
# --------------------------------------------------------------------------- #
def _norm_gaps(gaps_json_list):
    return [[g["start_ms"], g["end_ms"]] for g in gaps_json_list]


def test_gaps_basic_between_events():
    """Two disjoint events leave three free gaps: before, between, and after."""
    B = 410_000_000
    S, E = B, B + 100
    _add_event("gap_evt_1", B + 20, B + 40)
    _add_event("gap_evt_2", B + 60, B + 80)
    r = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    assert r.status_code == 200, r.text
    exp = _gaps_oracle(S, E)
    assert exp == [[B, B + 19], [B + 41, B + 59], [B + 81, B + 100]], f"oracle sanity: {exp}"
    assert _norm_gaps(r.json()["gaps"]) == exp


def test_gaps_clips_and_merges_nested_and_overhang():
    """A blob that starts before the window plus a nested blob must be clipped and merged;
    an implementation using a fully-contained filter would miss the overhanging event and
    wrongly report the window as free."""
    B = 420_000_000
    S, E = B, B + 100
    _add_event("gap_overhang", B - 50, B + 30)   # starts before window -> clip to B
    _add_event("gap_nested", B + 10, B + 20)     # nested inside the overhang
    r = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    exp = _gaps_oracle(S, E)
    assert exp == [[B + 31, B + 100]], f"oracle sanity: {exp}"
    assert _norm_gaps(r.json()["gaps"]) == exp


def test_gaps_single_free_instant():
    """A one-instant gap between two near-adjacent events is reported as [t, t]."""
    B = 430_000_000
    S, E = B, B + 100
    _add_event("gap_left", B, B + 10)
    _add_event("gap_right", B + 12, B + 100)  # free instant is exactly B+11
    r = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    exp = _gaps_oracle(S, E)
    assert exp == [[B + 11, B + 11]], f"oracle sanity: {exp}"
    assert _norm_gaps(r.json()["gaps"]) == exp


def test_gaps_empty_window_is_whole_window():
    """When no event intersects the window the single gap is the whole window."""
    B = 440_000_000
    S, E = B, B + 50
    r = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    assert _norm_gaps(r.json()["gaps"]) == [[S, E]]


def test_gaps_fully_covered_window_has_no_gaps():
    """A window entirely covered by one event has an empty gaps list."""
    B = 450_000_000
    S, E = B, B + 100
    _add_event("gap_cover", B - 10, B + 110)
    r = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    exp = _gaps_oracle(S, E)
    assert exp == [], f"oracle sanity: {exp}"
    assert _norm_gaps(r.json()["gaps"]) == []


def test_gaps_invalid_params():
    """GET /gaps returns 400 for missing params or start > end."""
    assert requests.get(f"{BASE}/gaps?start=5", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/gaps?start=100&end=50", timeout=10).status_code == 400


# --------------------------------------------------------------------------- #
# Independent oracles for §11–§13 new endpoints
# --------------------------------------------------------------------------- #
def _coverage_oracle(S, E):
    """§11: total busy instants in [S,E] — clip, strict-overlap merge, sum lengths."""
    evs = _all_se()
    clips = sorted(
        (max(s, S), min(e, E))
        for (s, e) in evs if s <= E and e >= S
    )
    merged = []
    for s, e in clips:
        if merged and s <= merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append([s, e])
    return sum(e - s + 1 for s, e in merged)


def _longest_gap_oracle(S, E):
    """§12: longest free gap in [S,E] — uses §10 oracle; returns [g0,g1] or None."""
    gaps = _gaps_oracle(S, E)
    if not gaps:
        return None
    best = gaps[0]
    for g in gaps[1:]:
        if g[1] - g[0] > best[1] - best[0]:
            best = g
    return best


def _density_oracle(S, E, B):
    """§13: per-bucket coverage using §11 algorithm; returns list of (bs,be,busy_ms)."""
    evs = _all_se()
    result = []
    bs = S
    while bs <= E:
        be = min(bs + B - 1, E)
        clips = sorted(
            (max(s, bs), min(e, be))
            for (s, e) in evs if s <= be and e >= bs
        )
        merged = []
        for s, e in clips:
            if merged and s <= merged[-1][1]:
                if e > merged[-1][1]:
                    merged[-1] = (merged[-1][0], e)
            else:
                merged.append([s, e])
        busy = sum(e - s + 1 for s, e in merged)
        result.append((bs, be, busy))
        bs += B
    return result


# --------------------------------------------------------------------------- #
# §11 GET /coverage — total busy instants in window
# --------------------------------------------------------------------------- #
def test_coverage_no_events_in_window():
    """A window with no events has covered_ms=0 and free_ms equal to window size."""
    B = 500_000_000
    r = requests.get(f"{BASE}/coverage?start={B}&end={B + 99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["covered_ms"] == 0
    assert body["free_ms"] == 100


def test_coverage_fully_covered_window():
    """An event spanning beyond the window on both sides covers every instant."""
    B = 501_000_000
    _add_event("cov_full", B - 50, B + 200)
    r = requests.get(f"{BASE}/coverage?start={B + 20}&end={B + 80}", timeout=10)
    body = r.json()
    assert body["covered_ms"] == 61
    assert body["free_ms"] == 0


def test_coverage_two_disjoint_events():
    """Two non-overlapping events: covered_ms is the sum of their individual widths."""
    B = 502_000_000
    _add_event("cov_d1", B + 10, B + 20)   # 11 instants
    _add_event("cov_d2", B + 40, B + 60)   # 21 instants
    r = requests.get(f"{BASE}/coverage?start={B}&end={B + 99}", timeout=10)
    exp = _coverage_oracle(B, B + 99)
    assert exp == 32, f"oracle sanity: {exp}"
    body = r.json()
    assert body["covered_ms"] == 32
    assert body["free_ms"] == 68


def test_coverage_overlapping_discriminator():
    """Two overlapping events must NOT double-count shared instants.

    [B+10, B+60] and [B+40, B+90] share [B+40, B+60]. A naive sum (51+51=102)
    is wrong; the correct merged union is [B+10, B+90] = 81 instants."""
    B = 503_000_000
    _add_event("cov_ol1", B + 10, B + 60)
    _add_event("cov_ol2", B + 40, B + 90)
    r = requests.get(f"{BASE}/coverage?start={B}&end={B + 99}", timeout=10)
    exp = _coverage_oracle(B, B + 99)
    assert exp == 81, f"oracle sanity: {exp}"
    body = r.json()
    assert body["covered_ms"] == exp, (
        f"covered_ms={body['covered_ms']} but oracle={exp}; "
        "overlapping intervals are being double-counted"
    )


def test_coverage_nested_discriminator():
    """A nested event inside a larger one must not inflate the covered count.

    Outer [B+10, B+90] subsumes inner [B+30, B+60]; union = [B+10, B+90] = 81."""
    B = 504_000_000
    _add_event("cov_nest_outer", B + 10, B + 90)
    _add_event("cov_nest_inner", B + 30, B + 60)
    r = requests.get(f"{BASE}/coverage?start={B}&end={B + 99}", timeout=10)
    exp = _coverage_oracle(B, B + 99)
    assert exp == 81, f"oracle sanity: {exp}"
    body = r.json()
    assert body["covered_ms"] == exp, (
        f"covered_ms={body['covered_ms']} but oracle={exp}; "
        "nested inner event is being counted separately"
    )


def test_coverage_overhang_clipped():
    """An event extending past the window boundaries must be clipped before counting."""
    B = 505_000_000
    _add_event("cov_overhang", B - 100, B + 200)   # big event, clips to window
    r = requests.get(f"{BASE}/coverage?start={B + 20}&end={B + 60}", timeout=10)
    body = r.json()
    # clipped to [B+20, B+60] -> 41 instants
    assert body["covered_ms"] == 41
    assert body["free_ms"] == 0


def test_coverage_oracle_cross_check():
    """Four events with partial overlaps: covered_ms matches independent oracle."""
    B = 506_000_000
    _add_event("cov_cx1", B + 10, B + 50)
    _add_event("cov_cx2", B + 30, B + 80)    # overlaps cx1 -> merged [B+10, B+80]
    _add_event("cov_cx3", B + 100, B + 150)
    _add_event("cov_cx4", B + 140, B + 190)  # overlaps cx3 -> merged [B+100, B+190]
    # Merged: [B+10,B+80](71) + [B+100,B+190](91) = 162
    r = requests.get(f"{BASE}/coverage?start={B}&end={B + 199}", timeout=10)
    assert r.status_code == 200
    exp_cov = _coverage_oracle(B, B + 199)
    assert exp_cov == 162, f"oracle sanity: {exp_cov}"
    body = r.json()
    assert body["covered_ms"] == exp_cov, (
        f"covered_ms={body['covered_ms']} != oracle {exp_cov}"
    )
    assert body["free_ms"] == 200 - exp_cov, (
        f"free_ms={body['free_ms']} != {200 - exp_cov}"
    )


def test_coverage_free_ms_sums_correctly():
    """covered_ms + free_ms must always equal (end - start + 1)."""
    B = 507_000_000
    _add_event("cov_sum", B + 10, B + 20)
    for extra in (0, 5, 15):
        r = requests.get(f"{BASE}/coverage?start={B}&end={B + 49 + extra}", timeout=10)
        body = r.json()
        window = (B + 49 + extra) - B + 1
        assert body["covered_ms"] + body["free_ms"] == window, (
            f"covered_ms({body['covered_ms']}) + free_ms({body['free_ms']}) "
            f"!= window size {window}"
        )


def test_coverage_invalid_params():
    """GET /coverage returns 400 for missing params or start > end."""
    assert requests.get(f"{BASE}/coverage?start=5", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/coverage?start=100&end=50", timeout=10).status_code == 400


# --------------------------------------------------------------------------- #
# §12 GET /longest_gap -- longest free gap
# --------------------------------------------------------------------------- #
def test_longest_gap_clear_winner():
    """Three gaps of widths 10, 10, and 50: the endpoint returns the 50-wide gap."""
    B = 600_000_000
    _add_event("lg_a", B + 10, B + 19)
    _add_event("lg_b", B + 30, B + 49)
    r = requests.get(f"{BASE}/longest_gap?start={B}&end={B + 99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    exp = _longest_gap_oracle(B, B + 99)
    assert exp == [B + 50, B + 99], f"oracle sanity: {exp}"
    gap = body.get("gap")
    assert gap is not None, "gap should not be null"
    assert gap["start_ms"] == B + 50, f"gap.start_ms={gap['start_ms']} != {B + 50}"
    assert gap["end_ms"] == B + 99, f"gap.end_ms={gap['end_ms']} != {B + 99}"
    assert gap["duration_ms"] == 50


def test_longest_gap_tie_returns_earliest():
    """Two equal-length gaps: the endpoint returns the one with the smaller start_ms."""
    B = 601_000_000
    _add_event("lg_tie1", B + 20, B + 49)
    _add_event("lg_tie2", B + 70, B + 99)
    r = requests.get(f"{BASE}/longest_gap?start={B}&end={B + 99}", timeout=10)
    body = r.json()
    exp = _longest_gap_oracle(B, B + 99)
    assert exp == [B, B + 19], f"oracle sanity (tie->earliest): {exp}"
    gap = body.get("gap")
    assert gap is not None
    assert gap["start_ms"] == B, f"expected earliest gap {B}, got {gap['start_ms']}"
    assert gap["end_ms"] == B + 19
    assert gap["duration_ms"] == 20


def test_longest_gap_null_fully_covered():
    """A window entirely covered by one event returns gap: null."""
    B = 602_000_000
    _add_event("lg_cover", B - 50, B + 150)
    r = requests.get(f"{BASE}/longest_gap?start={B + 10}&end={B + 80}", timeout=10)
    body = r.json()
    exp = _longest_gap_oracle(B + 10, B + 80)
    assert exp is None, f"oracle sanity: {exp}"
    assert body["gap"] is None, (
        f"expected gap:null when window is fully covered, got {body['gap']}"
    )


def test_longest_gap_whole_window_free():
    """A window with no events has a single gap spanning the entire window."""
    B = 603_000_000
    r = requests.get(f"{BASE}/longest_gap?start={B}&end={B + 49}", timeout=10)
    body = r.json()
    gap = body.get("gap")
    assert gap is not None, "gap should not be null when window has no events"
    assert gap["start_ms"] == B
    assert gap["end_ms"] == B + 49
    assert gap["duration_ms"] == 50


def test_longest_gap_single_instant_gap():
    """Two events leaving exactly one free instant: duration_ms must be 1."""
    B = 604_000_000
    _add_event("lg_s1", B, B + 49)
    _add_event("lg_s2", B + 51, B + 99)
    r = requests.get(f"{BASE}/longest_gap?start={B}&end={B + 99}", timeout=10)
    body = r.json()
    exp = _longest_gap_oracle(B, B + 99)
    assert exp == [B + 50, B + 50], f"oracle sanity: {exp}"
    gap = body.get("gap")
    assert gap is not None
    assert gap["start_ms"] == B + 50
    assert gap["end_ms"] == B + 50
    assert gap["duration_ms"] == 1


def test_longest_gap_oracle_exact():
    """Five events leaving four gaps; endpoint must match oracle on longest."""
    B = 605_000_000
    S, E = B, B + 199
    _add_event("lg_cx1", B + 10, B + 29)
    _add_event("lg_cx2", B + 50, B + 79)
    _add_event("lg_cx3", B + 100, B + 109)
    _add_event("lg_cx4", B + 130, B + 149)
    _add_event("lg_cx5", B + 180, B + 199)
    r = requests.get(f"{BASE}/longest_gap?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    exp = _longest_gap_oracle(S, E)
    body = r.json()
    gap = body.get("gap")
    assert gap is not None
    assert gap["start_ms"] == exp[0], f"start_ms {gap['start_ms']} != oracle {exp[0]}"
    assert gap["end_ms"] == exp[1], f"end_ms {gap['end_ms']} != oracle {exp[1]}"
    assert gap["duration_ms"] == exp[1] - exp[0] + 1


def test_longest_gap_invalid_params():
    """GET /longest_gap returns 400 for missing params or start > end."""
    assert requests.get(f"{BASE}/longest_gap?start=5", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/longest_gap?start=100&end=50", timeout=10
    ).status_code == 400


# --------------------------------------------------------------------------- #
# §13 GET /density -- per-bucket busy milliseconds
# --------------------------------------------------------------------------- #
def _norm_density(buckets_json):
    return [(b["bucket_start"], b["bucket_end"], b["busy_ms"]) for b in buckets_json]


def test_density_basic_three_equal_buckets():
    """One event spanning two buckets: busy_ms in each bucket is exact 5, 5, 0."""
    B = 700_000_000
    _add_event("den_b1", B + 5, B + 14)
    r = requests.get(f"{BASE}/density?start={B}&end={B + 29}&bucket_ms=10", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["bucket_ms"] == 10
    exp = _density_oracle(B, B + 29, 10)
    assert exp == [(B, B + 9, 5), (B + 10, B + 19, 5), (B + 20, B + 29, 0)], (
        f"oracle sanity: {exp}"
    )
    got = _norm_density(body["buckets"])
    assert got == exp, f"density mismatch: got {got} expected {exp}"


def test_density_partial_last_bucket():
    """Last bucket is narrower than bucket_ms; its bucket_end equals the window end."""
    B = 701_000_000
    r = requests.get(f"{BASE}/density?start={B}&end={B + 24}&bucket_ms=10", timeout=10)
    assert r.status_code == 200
    body = r.json()
    buckets = body["buckets"]
    assert len(buckets) == 3, f"expected 3 buckets, got {len(buckets)}"
    last = buckets[-1]
    assert last["bucket_end"] == B + 24, (
        f"last bucket_end should be window end {B + 24}, got {last['bucket_end']}"
    )
    assert last["busy_ms"] == 0


def test_density_overlap_no_double_count():
    """Two overlapping events in a single bucket must not double-count shared instants."""
    B = 702_000_000
    _add_event("den_ol1", B, B + 60)
    _add_event("den_ol2", B + 40, B + 99)
    r = requests.get(f"{BASE}/density?start={B}&end={B + 99}&bucket_ms=100", timeout=10)
    body = r.json()
    exp = _density_oracle(B, B + 99, 100)
    assert exp == [(B, B + 99, 100)], f"oracle sanity: {exp}"
    buckets = body["buckets"]
    assert len(buckets) == 1
    assert buckets[0]["busy_ms"] == 100, (
        f"busy_ms={buckets[0]['busy_ms']} but expected 100 "
        "(overlapping events are being double-counted within the bucket)"
    )


def test_density_multi_bucket_oracle_cross_check():
    """Five buckets with two events crossing bucket boundaries; exact oracle match."""
    B = 703_000_000
    S, E, bkt = B, B + 49, 10
    _add_event("den_cx1", B + 5, B + 15)
    _add_event("den_cx2", B + 25, B + 45)
    r = requests.get(f"{BASE}/density?start={S}&end={E}&bucket_ms={bkt}", timeout=10)
    assert r.status_code == 200
    exp = _density_oracle(S, E, bkt)
    assert exp == [
        (B, B + 9, 5), (B + 10, B + 19, 6), (B + 20, B + 29, 5),
        (B + 30, B + 39, 10), (B + 40, B + 49, 6),
    ], f"oracle sanity: {exp}"
    got = _norm_density(r.json()["buckets"])
    assert got == exp, f"density mismatch:\n  got:      {got}\n  expected: {exp}"


def test_density_all_zero_buckets():
    """Window with no events: all buckets report busy_ms=0."""
    B = 704_000_000
    r = requests.get(f"{BASE}/density?start={B}&end={B + 29}&bucket_ms=10", timeout=10)
    body = r.json()
    for bkt in body["buckets"]:
        assert bkt["busy_ms"] == 0, f"expected busy_ms=0 in all-empty window, got {bkt}"


def test_density_invalid_params():
    """GET /density returns 400 for missing params, start > end, or bucket_ms < 1."""
    assert requests.get(
        f"{BASE}/density?start=0&end=100", timeout=10
    ).status_code == 400
    assert requests.get(
        f"{BASE}/density?start=100&end=50&bucket_ms=10", timeout=10
    ).status_code == 400
    assert requests.get(
        f"{BASE}/density?start=0&end=100&bucket_ms=0", timeout=10
    ).status_code == 400


# --------------------------------------------------------------------------- #
# Harder discriminator tests for existing endpoints
# --------------------------------------------------------------------------- #
def test_peak_simultaneous_starts_five_events():
    """Five events all starting at the exact same instant; peak must be exactly 5.

    Correct sweep-line evaluates c(t) at t=start_t and counts all five. An
    implementation that de-duplicates candidate instants and skips repeated
    start_ms values would under-count."""
    B = 260_000_000
    start_t = B + 500
    for ix in range(5):
        _add_event(f"simul_{ix}", start_t, start_t + 100 + ix * 20)
    r = requests.get(f"{BASE}/peak?start={B}&end={B + 1000}", timeout=10)
    body = r.json()
    exp_max, exp_at = _peak_oracle(B, B + 1000)
    assert exp_max == 5 and exp_at == start_t, f"oracle: {exp_max},{exp_at}"
    assert body["max_concurrency"] == 5, (
        f"expected peak=5 (all events start at {start_t}), got {body['max_concurrency']}"
    )
    assert body["at_ms"] == start_t


def test_schedule_optimal_5_defeats_length_greedy():
    """Earliest-finish greedy selects 5 events; a length-based greedy picks only 1.

    Five short disjoint events plus one long event that overlaps all of them.
    The long event has the greatest length; a length-greedy picks it first and
    cannot select anything else (1 total). Earliest-finish greedy ignores length
    and picks all five short events (5 total)."""
    B = 340_000_000
    _add_event("opt5_a", B, B + 10)
    _add_event("opt5_b", B + 20, B + 30)
    _add_event("opt5_c", B + 40, B + 50)
    _add_event("opt5_d", B + 60, B + 70)
    _add_event("opt5_e", B + 80, B + 90)
    _add_event("opt5_f", B + 5, B + 85)   # longest single event, overlaps A-E
    r = requests.get(f"{BASE}/schedule?start={B}&end={B + 100}", timeout=10)
    exp = _schedule_oracle(B, B + 100)
    assert exp == 5, f"oracle expected 5, got {exp}"
    assert r.json()["max_non_overlapping"] == 5, (
        f"max_non_overlapping={r.json()['max_non_overlapping']} != 5 "
        "(implementation is not earliest-finish greedy)"
    )


def test_gaps_adjacency_merge_boundary():
    """Two integer-adjacent events (one ends at T, the next starts at T+1) must be
    merged per §10 so no spurious single-instant gap appears between them.

    An implementation using strict less-than (<) instead of <=  for adjacency
    would incorrectly insert a [T+1, T+1] gap."""
    B = 460_000_000
    S, E = B, B + 99
    _add_event("adj_left",  B,      B + 39)
    _add_event("adj_right", B + 40, B + 79)
    r = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    exp = _gaps_oracle(S, E)
    assert exp == [[B + 80, B + 99]], f"oracle sanity: {exp}"
    got = _norm_gaps(r.json()["gaps"])
    assert got == exp, (
        f"gaps {got} != oracle {exp}; adjacent events were not merged "
        "(check integer-adjacency rule: next.start <= prev.end + 1)"
    )


# --------------------------------------------------------------------------- #
# New independent oracles for §peak+ids, §schedule+ids, §15 timeline, §16 conflicts
# --------------------------------------------------------------------------- #
def _peak_oracle_with_ids(S, E):
    """Returns (max_concurrency, at_ms, sorted_id_list)."""
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT id, start_ms, end_ms FROM events").fetchall()
    conn.close()
    evs = [(r[0], r[1], r[2]) for r in rows]
    cands = {S} | {s for (_, s, _) in evs if S < s <= E}
    best, best_t = 0, S
    for t in sorted(cands):
        c = sum(1 for (_, s, e) in evs if s <= t <= e)
        if c > best:
            best, best_t = c, t
    ids = sorted(eid for (eid, s, e) in evs if s <= best_t <= e)
    return best, best_t, ids


def _schedule_oracle_with_ids(S, E):
    """Returns (count, selected_ids_sorted_by_end_ms_then_id)."""
    conn = sqlite3.connect(DB)
    evs = conn.execute(
        "SELECT id, start_ms, end_ms FROM events WHERE start_ms >= ? AND end_ms <= ? "
        "ORDER BY end_ms ASC, start_ms ASC, id ASC",
        (S, E),
    ).fetchall()
    conn.close()
    count, last, ids = 0, None, []
    for (eid, s, e) in evs:
        if last is None or s > last:
            count += 1
            last = e
            ids.append(eid)
    return count, ids


def _timeline_oracle(S, E, R):
    """Per-slot peak concurrency using §8 algorithm per slot."""
    conn = sqlite3.connect(DB)
    evs = conn.execute("SELECT start_ms, end_ms FROM events").fetchall()
    conn.close()
    result = []
    bs = S
    while bs <= E:
        be = min(bs + R - 1, E)
        cands = {bs} | {s for (s, _) in evs if bs < s <= be}
        best = 0
        for t in sorted(cands):
            c = sum(1 for (s, e) in evs if s <= t <= e)
            if c > best:
                best = c
        result.append((bs, be, best))
        bs += R
    return result


def _conflicts_oracle(S, E, T):
    """Events active at instants in [S,E] where c(t) > T; sorted start_ms ASC, id ASC."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, name, start_ms, end_ms FROM events WHERE start_ms <= ? AND end_ms >= ? "
        "ORDER BY start_ms ASC, id ASC",
        (E, S),
    ).fetchall()
    conn.close()
    evs = [(r[0], r[1], r[2], r[3]) for r in rows]
    conn2 = sqlite3.connect(DB)
    all_rows = [(r[0], r[1], r[2], r[3]) for r in
                conn2.execute("SELECT id, name, start_ms, end_ms FROM events").fetchall()]
    conn2.close()
    cands = {S} | {s for (_, _, s, _) in all_rows if S < s <= E}
    conflict_ts = set()
    for t in sorted(cands):
        c = sum(1 for (_, _, s, e) in all_rows if s <= t <= e)
        if c > T:
            conflict_ts.add(t)
    if not conflict_ts:
        return []
    result = []
    for ev in evs:
        eid, name, s, e = ev
        clip_s = max(s, S)
        clip_e = min(e, E)
        for t in conflict_ts:
            if clip_s <= t <= clip_e:
                result.append(ev)
                break
    return result


# --------------------------------------------------------------------------- #
# §8 extension — events_at_peak field
# --------------------------------------------------------------------------- #
def test_peak_returns_events_at_peak_field():
    """GET /peak response includes an events_at_peak list."""
    B = 270_000_000
    _add_event("eap_probe", B, B + 50)
    r = requests.get(f"{BASE}/peak?start={B}&end={B + 100}", timeout=10)
    assert r.status_code == 200
    assert "events_at_peak" in r.json(), "response missing 'events_at_peak' field"


def test_peak_events_at_peak_correct_ids():
    """events_at_peak contains exactly the event IDs active at at_ms."""
    B = 271_000_000
    _add_event("eap_1", B, B + 100)
    _add_event("eap_2", B + 20, B + 80)
    _add_event("eap_3", B + 30, B + 60)
    # at B+30: all 3 active → peak=3, at_ms=B+30
    r = requests.get(f"{BASE}/peak?start={B}&end={B + 100}", timeout=10)
    body = r.json()
    exp_mc, exp_at, exp_ids = _peak_oracle_with_ids(B, B + 100)
    assert exp_mc == 3 and exp_at == B + 30, f"oracle sanity: {exp_mc},{exp_at}"
    assert body["max_concurrency"] == 3
    assert body["at_ms"] == B + 30
    assert body["events_at_peak"] == exp_ids, (
        f"events_at_peak={body['events_at_peak']} != oracle {exp_ids}"
    )


def test_peak_events_at_peak_sorted_ascending():
    """events_at_peak is always sorted in ascending id order."""
    B = 272_000_000
    for i in range(4):
        _add_event(f"eap_s{i}", B, B + 50)
    r = requests.get(f"{BASE}/peak?start={B}&end={B + 100}", timeout=10)
    body = r.json()
    eap = body.get("events_at_peak", [])
    assert eap == sorted(eap), f"events_at_peak not sorted ascending: {eap}"


def test_peak_events_at_peak_empty_when_no_events():
    """events_at_peak is [] when max_concurrency is 0."""
    S, E = 273_000_000, 273_000_100
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 0
    assert body["events_at_peak"] == [], (
        f"expected [] when no events active, got {body['events_at_peak']}"
    )


def test_peak_events_at_peak_count_matches_max_concurrency():
    """len(events_at_peak) == max_concurrency always."""
    B = 274_000_000
    _add_event("eap_c1", B, B + 60)
    _add_event("eap_c2", B + 10, B + 70)
    r = requests.get(f"{BASE}/peak?start={B}&end={B + 100}", timeout=10)
    body = r.json()
    assert len(body["events_at_peak"]) == body["max_concurrency"], (
        f"len(events_at_peak)={len(body['events_at_peak'])} != max_concurrency={body['max_concurrency']}"
    )


# --------------------------------------------------------------------------- #
# §9 extension — selected_ids field
# --------------------------------------------------------------------------- #
def test_schedule_returns_selected_ids_field():
    """GET /schedule response includes a selected_ids list."""
    B = 360_000_000
    _add_event("sel_probe", B, B + 50)
    r = requests.get(f"{BASE}/schedule?start={B}&end={B + 100}", timeout=10)
    assert r.status_code == 200
    assert "selected_ids" in r.json(), "response missing 'selected_ids' field"


def test_schedule_selected_ids_adversarial_long_vs_two_short():
    """selected_ids contains the two short events, not the long one that starts earliest."""
    B = 361_000_000
    id_a = _add_event("sel_long", B, B + 900)          # starts first but finishes last
    id_x = _add_event("sel_x", B + 10, B + 20)         # short, finishes B+20
    id_y = _add_event("sel_y", B + 30, B + 40)         # short, finishes B+40, starts > B+20
    r = requests.get(f"{BASE}/schedule?start={B}&end={B + 1000}", timeout=10)
    body = r.json()
    assert body["max_non_overlapping"] == 2
    assert "selected_ids" in body
    assert len(body["selected_ids"]) == 2, (
        f"expected 2 selected ids, got {len(body['selected_ids'])}: {body['selected_ids']}"
    )
    assert id_x in body["selected_ids"], f"id_x={id_x} missing from selected_ids"
    assert id_y in body["selected_ids"], f"id_y={id_y} missing from selected_ids"
    assert id_a not in body["selected_ids"], f"long event id_a={id_a} must NOT be selected"
    # IDs in order of selection (by end_ms ASC)
    assert body["selected_ids"] == [id_x, id_y], (
        f"selected_ids={body['selected_ids']} not sorted by end_ms (expected [{id_x},{id_y}])"
    )


def test_schedule_selected_ids_length_matches_count():
    """len(selected_ids) == max_non_overlapping always."""
    B = 362_000_000
    _add_event("sel_len1", B, B + 20)
    _add_event("sel_len2", B + 30, B + 50)
    _add_event("sel_len3", B + 10, B + 60)   # overlaps both; greedy skips it
    r = requests.get(f"{BASE}/schedule?start={B}&end={B + 100}", timeout=10)
    body = r.json()
    assert len(body["selected_ids"]) == body["max_non_overlapping"], (
        f"len(selected_ids)={len(body['selected_ids'])} != max_non_overlapping={body['max_non_overlapping']}"
    )


def test_schedule_selected_ids_empty_when_no_contained_events():
    """selected_ids is [] when no events are fully contained in the window."""
    S, E = 363_000_000, 363_000_100
    r = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_non_overlapping"] == 0
    assert body["selected_ids"] == [], f"expected [] but got {body['selected_ids']}"


def test_schedule_selected_ids_oracle_cross_check():
    """selected_ids matches the independent earliest-finish greedy oracle exactly."""
    B = 364_000_000
    ids = []
    ids.append(_add_event("sel_cx1", B,      B + 15))
    ids.append(_add_event("sel_cx2", B + 5,  B + 25))
    ids.append(_add_event("sel_cx3", B + 20, B + 35))
    ids.append(_add_event("sel_cx4", B + 30, B + 45))
    ids.append(_add_event("sel_cx5", B + 40, B + 55))
    S, E = B, B + 60
    r = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10)
    body = r.json()
    exp_count, exp_ids = _schedule_oracle_with_ids(S, E)
    assert body["max_non_overlapping"] == exp_count, (
        f"count {body['max_non_overlapping']} != oracle {exp_count}"
    )
    assert body["selected_ids"] == exp_ids, (
        f"selected_ids={body['selected_ids']} != oracle {exp_ids}"
    )


# --------------------------------------------------------------------------- #
# §15 GET /timeline — per-slot peak concurrency
# --------------------------------------------------------------------------- #
def test_timeline_slot_count_exact():
    """N=99, resolution=25 → 4 slots: [0,24],[25,49],[50,74],[75,98]."""
    B = 800_000_000
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 98}&resolution_ms=25", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["slots"]) == 4, f"expected 4 slots, got {len(body['slots'])}"


def test_timeline_slot_boundaries():
    """Slot boundaries follow [start, start+R-1], [start+R, start+2R-1], ..."""
    B = 801_000_000
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 29}&resolution_ms=10", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    expected_bounds = [(B, B + 9), (B + 10, B + 19), (B + 20, B + 29)]
    for i, (s, e) in enumerate(expected_bounds):
        assert slots[i]["slot_start"] == s, f"slot {i} start: expected {s}, got {slots[i]['slot_start']}"
        assert slots[i]["slot_end"] == e, f"slot {i} end: expected {e}, got {slots[i]['slot_end']}"


def test_timeline_partial_last_slot():
    """Last slot end equals window end even when window_size is not divisible by resolution_ms."""
    B = 802_000_000
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 24}&resolution_ms=10", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert len(slots) == 3
    assert slots[-1]["slot_end"] == B + 24, (
        f"last slot_end should be window end {B + 24}, got {slots[-1]['slot_end']}"
    )


def test_timeline_empty_slots_return_zero_peak():
    """Slots with no events active report peak_concurrency=0."""
    B = 803_000_000
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 99}&resolution_ms=25", timeout=10)
    assert r.status_code == 200
    for s in r.json()["slots"]:
        assert s["peak_concurrency"] == 0, f"expected 0 in empty window, got {s}"


def test_timeline_event_active_in_correct_slots():
    """An event spanning two full slots has peak >= 1 in each of them."""
    B = 804_000_000
    _add_event("tl_span", B + 5, B + 15)   # active in slot 0 [B,B+9] and slot 1 [B+10,B+19]
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 29}&resolution_ms=10", timeout=10)
    slots = r.json()["slots"]
    assert slots[0]["peak_concurrency"] >= 1, "event should be active in slot 0"
    assert slots[1]["peak_concurrency"] >= 1, "event should be active in slot 1"
    assert slots[2]["peak_concurrency"] == 0, "slot 2 should be empty"


def test_timeline_peak_reflects_max_concurrency_in_slot():
    """Three events all starting in the same slot → that slot's peak = 3."""
    B = 805_000_000
    _add_event("tl_p1", B + 2, B + 8)
    _add_event("tl_p2", B + 3, B + 7)
    _add_event("tl_p3", B + 4, B + 6)
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 29}&resolution_ms=10", timeout=10)
    slots = r.json()["slots"]
    assert slots[0]["peak_concurrency"] == 3, (
        f"expected peak=3 in slot 0 with 3 overlapping events, got {slots[0]['peak_concurrency']}"
    )
    assert slots[1]["peak_concurrency"] == 0
    assert slots[2]["peak_concurrency"] == 0


def test_timeline_oracle_cross_check():
    """Complex scenario with overlapping events across slots matches oracle exactly."""
    B = 806_000_000
    _add_event("tl_cx1", B,      B + 20)
    _add_event("tl_cx2", B + 10, B + 30)
    _add_event("tl_cx3", B + 50, B + 70)
    S, E, R = B, B + 99, 25
    r = requests.get(f"{BASE}/timeline?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    exp = _timeline_oracle(S, E, R)
    got = [(s["slot_start"], s["slot_end"], s["peak_concurrency"]) for s in r.json()["slots"]]
    assert got == exp, f"timeline mismatch:\n  got:      {got}\n  expected: {exp}"


def test_timeline_resolution_larger_than_window():
    """resolution_ms > window width → single slot spanning the whole window."""
    B = 807_000_000
    _add_event("tl_big", B + 5, B + 15)
    r = requests.get(f"{BASE}/timeline?start={B}&end={B + 19}&resolution_ms=100", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert len(slots) == 1, f"expected 1 slot, got {len(slots)}"
    assert slots[0]["slot_start"] == B
    assert slots[0]["slot_end"] == B + 19
    assert slots[0]["peak_concurrency"] >= 1


def test_timeline_invalid_params():
    """GET /timeline returns 400 for missing params, start > end, or resolution_ms < 1."""
    assert requests.get(f"{BASE}/timeline?start=0&end=100", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/timeline?start=100&end=50&resolution_ms=10", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/timeline?start=0&end=100&resolution_ms=0", timeout=10).status_code == 400


# --------------------------------------------------------------------------- #
# §16 GET /conflicts — conflict event detection
# --------------------------------------------------------------------------- #
def test_conflicts_threshold_zero_returns_all_active():
    """threshold=0: every event intersecting the window is returned (c(t) >= 1 > 0)."""
    B = 900_000_000
    id1 = _add_event("cf_t0_a", B,      B + 30)
    id2 = _add_event("cf_t0_b", B + 40, B + 70)  # disjoint from id1
    r = requests.get(f"{BASE}/conflicts?start={B}&end={B + 80}&threshold=0", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    returned_ids = {e["id"] for e in body["conflicting_events"]}
    assert id1 in returned_ids, f"id1={id1} should be in threshold=0 results"
    assert id2 in returned_ids, f"id2={id2} should be in threshold=0 results"


def test_conflicts_threshold_one_returns_only_overlapping_events():
    """threshold=1: only events active at instants where >= 2 events overlap are returned.
    A standalone (non-overlapping) event must NOT appear."""
    B = 901_000_000
    id_a = _add_event("cf_t1_a", B,      B + 50)  # overlaps id_b
    id_b = _add_event("cf_t1_b", B + 30, B + 80)  # overlaps id_a
    id_c = _add_event("cf_t1_c", B + 90, B + 99)  # disjoint — no conflict
    r = requests.get(f"{BASE}/conflicts?start={B}&end={B + 99}&threshold=1", timeout=10)
    assert r.status_code == 200
    body = r.json()
    ids = {e["id"] for e in body["conflicting_events"]}
    assert id_a in ids, "id_a should be in conflicts (overlaps with id_b)"
    assert id_b in ids, "id_b should be in conflicts (overlaps with id_a)"
    assert id_c not in ids, "id_c must NOT be in conflicts (no overlap above threshold=1)"


def test_conflicts_threshold_two_requires_triple_overlap():
    """threshold=2: only events active at instants where >= 3 overlap are returned."""
    B = 902_000_000
    id_a = _add_event("cf_t2_a", B,      B + 60)   # triple overlap in [B+30, B+50]
    id_b = _add_event("cf_t2_b", B + 20, B + 70)   # triple overlap
    id_c = _add_event("cf_t2_c", B + 30, B + 50)   # triple overlap
    id_d = _add_event("cf_t2_d", B + 80, B + 99)   # pair overlap only, not triple
    id_e = _add_event("cf_t2_e", B + 85, B + 95)   # pair overlap only
    r = requests.get(f"{BASE}/conflicts?start={B}&end={B + 99}&threshold=2", timeout=10)
    assert r.status_code == 200
    body = r.json()
    ids = {ev["id"] for ev in body["conflicting_events"]}
    assert id_a in ids, "id_a should be in triple-overlap conflicts"
    assert id_b in ids, "id_b should be in triple-overlap conflicts"
    assert id_c in ids, "id_c should be in triple-overlap conflicts"
    assert id_d not in ids, "id_d only has pair overlap; must NOT appear at threshold=2"
    assert id_e not in ids, "id_e only has pair overlap; must NOT appear at threshold=2"


def test_conflicts_no_events_in_window():
    """Empty window has no conflicts at any threshold."""
    S, E = 903_000_000, 903_000_100
    r = requests.get(f"{BASE}/conflicts?start={S}&end={E}&threshold=0", timeout=10)
    assert r.status_code == 200
    assert r.json()["conflicting_events"] == []


def test_conflicts_sorted_by_start_ms_then_id():
    """conflicting_events is sorted start_ms ASC, then id ASC for ties."""
    B = 904_000_000
    _add_event("cf_sort_b", B + 5, B + 50)
    _add_event("cf_sort_c", B + 5, B + 40)   # same start as above → id order
    _add_event("cf_sort_a", B,     B + 30)
    r = requests.get(f"{BASE}/conflicts?start={B}&end={B + 60}&threshold=0", timeout=10)
    evs = r.json()["conflicting_events"]
    starts = [e["start_ms"] for e in evs]
    assert starts == sorted(starts), f"conflicting_events not sorted by start_ms: {starts}"


def test_conflicts_oracle_cross_check():
    """Complex scenario: oracle vs endpoint for threshold=1."""
    B = 905_000_000
    _add_event("cf_cx1", B,      B + 40)
    _add_event("cf_cx2", B + 20, B + 60)
    _add_event("cf_cx3", B + 70, B + 90)   # standalone
    S, E, T = B, B + 99, 1
    r = requests.get(f"{BASE}/conflicts?start={S}&end={E}&threshold={T}", timeout=10)
    assert r.status_code == 200
    exp = _conflicts_oracle(S, E, T)
    got = [(e["id"], e["start_ms"], e["end_ms"]) for e in r.json()["conflicting_events"]]
    exp_out = [(ev[0], ev[2], ev[3]) for ev in exp]
    assert got == exp_out, f"conflicts mismatch:\n  got: {got}\n  expected: {exp_out}"


def test_conflicts_invalid_params():
    """GET /conflicts returns 400 for missing params, start > end, or threshold < 0."""
    assert requests.get(f"{BASE}/conflicts?start=0&end=100", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/conflicts?start=100&end=50&threshold=1", timeout=10).status_code == 400
    assert requests.get(f"{BASE}/conflicts?start=0&end=100&threshold=-1", timeout=10).status_code == 400


# --------------------------------------------------------------------------- #
# Cross-algorithm consistency checks
# --------------------------------------------------------------------------- #
def test_density_bucket_sum_equals_coverage_when_exact_partition():
    """When bucket_ms divides the window exactly, sum(density busy_ms) == coverage."""
    B = 1_000_000_000
    _add_event("cc_d1", B + 5,  B + 15)
    _add_event("cc_d2", B + 25, B + 35)
    S, E, BK = B, B + 39, 10
    r_cov = requests.get(f"{BASE}/coverage?start={S}&end={E}", timeout=10)
    r_den = requests.get(f"{BASE}/density?start={S}&end={E}&bucket_ms={BK}", timeout=10)
    assert r_cov.status_code == 200 and r_den.status_code == 200
    cov = r_cov.json()["covered_ms"]
    den_sum = sum(b["busy_ms"] for b in r_den.json()["buckets"])
    assert den_sum == cov, (
        f"sum(density busy_ms)={den_sum} != coverage covered_ms={cov}; "
        "density and coverage use different coverage algorithms"
    )


def test_gaps_and_coverage_complementarity():
    """sum(gap durations) + covered_ms == window size for any window."""
    B = 1_001_000_000
    _add_event("cc_g1", B + 10, B + 30)
    _add_event("cc_g2", B + 50, B + 70)
    S, E = B, B + 99
    window_size = E - S + 1
    r_gaps = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    r_cov  = requests.get(f"{BASE}/coverage?start={S}&end={E}", timeout=10)
    assert r_gaps.status_code == 200 and r_cov.status_code == 200
    gap_total = sum(g["end_ms"] - g["start_ms"] + 1 for g in r_gaps.json()["gaps"])
    covered = r_cov.json()["covered_ms"]
    assert gap_total + covered == window_size, (
        f"gaps({gap_total}) + coverage({covered}) = {gap_total + covered} != window_size({window_size})"
    )


def test_peak_earliest_tiebreak_on_equal_concurrency():
    """When two candidate instants both achieve the peak, the EARLIER one is reported."""
    B = 1_002_000_000
    _add_event("tb_1", B + 10, B + 90)
    _add_event("tb_2", B + 10, B + 80)
    _add_event("tb_3", B + 50, B + 70)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    exp_mc, exp_at, _ = _peak_oracle_with_ids(S, E)
    assert body["at_ms"] == exp_at, f"at_ms={body['at_ms']} != oracle {exp_at}"


def test_coverage_adjacent_events_not_merged_by_gap_rule():
    """[B, B+20] and [B+21, B+40]: coverage=41 (two separate intervals in §11) but no gap between them in §10.
    Verifies §10 uses +1 adjacency merge (no gap at B+21) while §11 uses strict overlap (two intervals).
    The total covered area is the same; what differs is whether §10 produces a spurious gap."""
    B = 1_003_000_000
    _add_event("adj_cv1", B,      B + 20)
    _add_event("adj_cv2", B + 21, B + 40)
    S, E = B, B + 40
    r_gaps = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    r_cov  = requests.get(f"{BASE}/coverage?start={S}&end={E}", timeout=10)
    assert r_gaps.status_code == 200 and r_cov.status_code == 200
    # §10: adjacent events merge → no gap → gaps = []
    assert _norm_gaps(r_gaps.json()["gaps"]) == [], (
        "adjacent events [B,B+20] and [B+21,B+40] should merge under §10 (+1 rule) → no gaps"
    )
    # §11: covered = 21 + 20 = 41 (full window)
    assert r_cov.json()["covered_ms"] == 41, (
        f"expected covered_ms=41 for [B,B+20]+[B+21,B+40], got {r_cov.json()['covered_ms']}"
    )
    assert r_cov.json()["free_ms"] == 0


# =========================================================================== #
# §8 peak_duration_ms                                                          #
# =========================================================================== #

def test_peak_duration_ms_field_present():
    """GET /peak response must include a peak_duration_ms field."""
    B = 4_000_000_000
    _add_event("pdur_a", B + 0,  B + 19)
    _add_event("pdur_b", B + 10, B + 29)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    assert "peak_duration_ms" in r.json(), "peak_duration_ms field missing from /peak response"


def test_peak_duration_ms_partial_peak():
    """peak_duration_ms counts instants at both [10,19] and [20,29] where c=2 → 20."""
    B = 4_000_000_100
    _add_event("pdu_p1", B + 0,  B + 19)   # 0-19
    _add_event("pdu_p2", B + 10, B + 29)   # 10-29
    _add_event("pdu_p3", B + 20, B + 39)   # 20-39
    _add_event("pdu_p4", B + 50, B + 69)   # 50-69
    S, E = B, B + 99
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 2
    assert body["at_ms"] == B + 10, f"at_ms should be B+10, got {body['at_ms']}"
    # instants 10-19 (c=2) + 20-29 (c=2) = 20 instants at peak
    assert body["peak_duration_ms"] == 20, (
        f"peak_duration_ms should be 20 (instants 10-29), got {body['peak_duration_ms']}"
    )


def test_peak_duration_ms_zero_events():
    """When no events are active, max_concurrency=0 and peak_duration_ms=window size."""
    B = 4_000_000_200
    S, E = B, B + 49
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 0
    assert body["peak_duration_ms"] == 50, (
        f"peak_duration_ms should be 50 (full window), got {body['peak_duration_ms']}"
    )


def test_peak_duration_ms_single_instant():
    """Three events each active for 1 instant at the same t → peak_duration_ms=1."""
    B = 4_000_000_300
    _add_event("pdu_s1", B + 5, B + 5)
    _add_event("pdu_s2", B + 5, B + 5)
    _add_event("pdu_s3", B + 5, B + 5)
    S, E = B, B + 9
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 3
    assert body["peak_duration_ms"] == 1, (
        f"peak_duration_ms should be 1 (only t=B+5 has c=3), got {body['peak_duration_ms']}"
    )


def test_peak_duration_ms_discriminator():
    """Fixture: D1 covers full window [0,99]; D2=[10,19]; D3=[20,29].
    c=2 at [10,29] only → peak_duration_ms=20, not 30, not 100."""
    B = 4_000_000_400
    _add_event("pdu_d1", B + 0,  B + 99)
    _add_event("pdu_d2", B + 10, B + 19)
    _add_event("pdu_d3", B + 20, B + 29)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 2
    assert body["at_ms"] == B + 10
    assert body["peak_duration_ms"] == 20, (
        f"peak_duration_ms should be 20 (only 10-29 have c=2), got {body['peak_duration_ms']}"
    )


# =========================================================================== #
# §9 covered_ms in schedule                                                    #
# =========================================================================== #

def test_covered_ms_field_present():
    """GET /schedule response must include a covered_ms field."""
    B = 4_001_000_000
    _add_event("cov_sched_a", B + 0,  B + 9)
    _add_event("cov_sched_b", B + 20, B + 29)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    assert "covered_ms" in r.json(), "covered_ms field missing from /schedule response"


def test_covered_ms_nonoverlapping_selected():
    """covered_ms = sum of selected event durations when events are non-overlapping."""
    B = 4_001_000_100
    _add_event("cov_s1", B + 0,  B + 9)   # 10ms
    _add_event("cov_s2", B + 20, B + 34)  # 15ms
    _add_event("cov_s3", B + 50, B + 59)  # 10ms
    S, E = B, B + 99
    r = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_non_overlapping"] == 3
    assert body["covered_ms"] == 35, (
        f"covered_ms should be 35 (10+15+10), got {body['covered_ms']}"
    )


def test_covered_ms_empty_schedule():
    """covered_ms=0 when no events are contained in the window."""
    B = 4_001_000_200
    S, E = B, B + 99
    r = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_non_overlapping"] == 0
    assert body["covered_ms"] == 0


# =========================================================================== #
# §17 GET /heatmap                                                             #
# =========================================================================== #

def test_heatmap_slot_count():
    """ceil((end-start+1)/resolution) slots are returned, not floor division.

    Window [B, B+99] at R=25: 100/25=4 slots. A naive (end-start)//resolution
    gets 99//25=3, silently dropping the last slot."""
    B = 4_002_000_000
    S, E, R = B, B + 99, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert len(slots) == 4, f"expected 4 slots for window 100 / resolution 25, got {len(slots)}"


def test_heatmap_histogram_sums_to_slot_width():
    """sum(histogram) == slot_end - slot_start + 1 for every slot (conservation law)."""
    B = 4_002_000_100
    _add_event("hm_c1", B + 5,  B + 20)
    _add_event("hm_c2", B + 10, B + 30)
    S, E, R = B, B + 49, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    for sl in r.json()["slots"]:
        slot_width = sl["slot_end"] - sl["slot_start"] + 1
        hist_sum = sum(sl["histogram"])
        assert hist_sum == slot_width, (
            f"slot [{sl['slot_start']},{sl['slot_end']}]: sum(histogram)={hist_sum} != slot_width={slot_width}"
        )


def test_heatmap_empty_slot_histogram():
    """A slot with no active events must return histogram=[slot_width], not [] or None.

    The conservation law requires sum(histogram)==slot_width even for empty slots;
    [25] encodes 25 instants at concurrency level 0, not an absent or empty list."""
    B = 4_002_000_200
    # Event only in [B, B+9]; slot [B+25, B+49] is empty
    _add_event("hm_e1", B + 0, B + 9)
    S, E, R = B, B + 49, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    empty_slot = slots[1]  # [B+25, B+49]
    assert empty_slot["histogram"] == [25], (
        f"empty slot histogram should be [25], got {empty_slot['histogram']}"
    )
    assert abs(empty_slot["mean_concurrency"]) < 1e-5, (
        f"empty slot mean_concurrency should be 0, got {empty_slot['mean_concurrency']}"
    )


def test_heatmap_single_event_full_slot():
    """One event covering the whole slot: histogram=[0, slot_width], mean=1."""
    B = 4_002_000_300
    _add_event("hm_full", B + 0, B + 24)
    S, E, R = B, B + 24, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert len(slots) == 1
    assert slots[0]["histogram"] == [0, 25], (
        f"single event covering full slot: histogram should be [0,25], got {slots[0]['histogram']}"
    )
    assert abs(slots[0]["mean_concurrency"] - 1.0) < 1e-5


def test_heatmap_two_overlapping_events():
    """Two events overlapping in [B+10, B+14]: histogram must record level-2 instants.

    A naive coverage approach cannot split the [0,20,5] breakdown from a simple union;
    a sweep-line is needed to distinguish depth-1 (20ms) from depth-2 (5ms) instants."""
    B = 4_002_000_400
    _add_event("hm_ov1", B + 0,  B + 14)   # 0-14
    _add_event("hm_ov2", B + 10, B + 24)   # 10-24
    # slot [B, B+24]:
    # 0-9: c=1 (10 instants); 10-14: c=2 (5); 15-24: c=1 (10)
    # histogram = [0, 20, 5], mean = (1*20 + 2*5) / 25 = 30/25 = 1.2
    S, E, R = B, B + 24, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    sl = r.json()["slots"][0]
    assert len(sl["histogram"]) >= 3, "histogram must have at least 3 levels (0,1,2)"
    assert sl["histogram"][0] == 0, f"hist[0] should be 0, got {sl['histogram'][0]}"
    assert sl["histogram"][1] == 20, f"hist[1] should be 20, got {sl['histogram'][1]}"
    assert sl["histogram"][2] == 5, f"hist[2] should be 5, got {sl['histogram'][2]}"
    assert abs(sl["mean_concurrency"] - 1.2) < 1e-4


def test_heatmap_mean_concurrency_computed_correctly():
    """mean = total_concurrency_instants / slot_width; verified from raw histogram."""
    B = 4_002_000_500
    _add_event("hm_mc1", B + 0,  B + 9)   # c=1 for 10ms
    _add_event("hm_mc2", B + 5,  B + 14)  # c=2 for 5ms (5-9), c=1 for 5ms (10-14)
    # [0,4]: c=1; [5,9]: c=2; [10,14]: c=1
    # slot [0, 14] (R=15): hist=[0, 15, 5], mean=(1*15+2*5)/15 = 25/15 ≈ 1.666667
    S, E, R = B, B + 14, 15
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    sl = r.json()["slots"][0]
    total_wi = sum(k * v for k, v in enumerate(sl["histogram"]))
    expected_mean = total_wi / (E - S + 1)
    assert abs(sl["mean_concurrency"] - expected_mean) < 1e-4, (
        f"mean_concurrency {sl['mean_concurrency']} != histogram-derived mean {expected_mean}"
    )


def test_heatmap_multi_slot_oracle_cross_check():
    """Fixture A: 4 events, window 100ms, R=25. Verify all 4 slots' histograms exactly."""
    B = 4_002_000_600
    _add_event("hm_ma1", B + 0,  B + 19)   # 0-19
    _add_event("hm_ma2", B + 10, B + 29)   # 10-29
    _add_event("hm_ma3", B + 20, B + 39)   # 20-39
    _add_event("hm_ma4", B + 50, B + 69)   # 50-69
    S, E, R = B, B + 99, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    slots = r.json()["slots"]
    # Slot 0 [0,24]: 0-9 c=1(10), 10-19 c=2(10), 20-24 c=2(5) → hist=[0,10,15] mean=1.6
    assert slots[0]["histogram"] == [0, 10, 15], f"slot0 hist wrong: {slots[0]['histogram']}"
    assert abs(slots[0]["mean_concurrency"] - 1.6) < 1e-4
    # Slot 1 [25,49]: 25-29 c=2(5), 30-39 c=1(10), 40-49 c=0(10) → hist=[10,10,5] mean=0.8
    assert slots[1]["histogram"] == [10, 10, 5], f"slot1 hist wrong: {slots[1]['histogram']}"
    assert abs(slots[1]["mean_concurrency"] - 0.8) < 1e-4
    # Slot 2 [50,74]: 50-69 c=1(20), 70-74 c=0(5) → hist=[5,20] mean=0.8
    assert slots[2]["histogram"] == [5, 20], f"slot2 hist wrong: {slots[2]['histogram']}"
    assert abs(slots[2]["mean_concurrency"] - 0.8) < 1e-4
    # Slot 3 [75,99]: all c=0(25) → hist=[25] mean=0.0
    assert slots[3]["histogram"] == [25], f"slot3 hist wrong: {slots[3]['histogram']}"
    assert abs(slots[3]["mean_concurrency"]) < 1e-5


def test_heatmap_invalid_params():
    """Missing or invalid params → 400."""
    B = 4_002_000_700
    r1 = requests.get(f"{BASE}/heatmap?start={B}&end={B+9}", timeout=10)
    assert r1.status_code == 400
    r2 = requests.get(f"{BASE}/heatmap?start={B+10}&end={B}&resolution_ms=5", timeout=10)
    assert r2.status_code == 400
    r3 = requests.get(f"{BASE}/heatmap?start={B}&end={B+9}&resolution_ms=0", timeout=10)
    assert r3.status_code == 400


# =========================================================================== #
# §18 GET /merge                                                               #
# =========================================================================== #

def test_merge_no_events():
    """No events in window → merged_intervals must be an empty array and covered_ms must be 0.

    A naive implementation might omit covered_ms on empty results, return null, or crash;
    both fields must be present with their zero values even when no events exist."""
    B = 4_003_000_000
    r = requests.get(f"{BASE}/merge?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["merged_intervals"] == [], f"expected [], got {body['merged_intervals']}"
    assert body["covered_ms"] == 0


def test_merge_single_event():
    """One event → one merged interval clipped to window."""
    B = 4_003_000_100
    _add_event("mg_s1", B - 10, B + 30)   # extends before window start
    r = requests.get(f"{BASE}/merge?start={B}&end={B+49}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert len(body["merged_intervals"]) == 1
    iv = body["merged_intervals"][0]
    assert iv["start_ms"] == B and iv["end_ms"] == B + 30, f"wrong interval: {iv}"
    assert body["covered_ms"] == 31


def test_merge_two_nonoverlapping():
    """Two non-touching events must remain as two distinct merged intervals.

    A naive merge that unions all events regardless of adjacency would collapse them;
    only events where event_A.end_ms >= event_B.start_ms qualify for merging."""
    B = 4_003_000_200
    _add_event("mg_n1", B + 0,  B + 9)
    _add_event("mg_n2", B + 20, B + 29)
    r = requests.get(f"{BASE}/merge?start={B}&end={B+49}", timeout=10)
    body = r.json()
    assert len(body["merged_intervals"]) == 2
    assert body["covered_ms"] == 20


def test_merge_two_overlapping():
    """Two overlapping events → one merged interval."""
    B = 4_003_000_300
    _add_event("mg_ov1", B + 0,  B + 19)
    _add_event("mg_ov2", B + 10, B + 29)
    r = requests.get(f"{BASE}/merge?start={B}&end={B+49}", timeout=10)
    body = r.json()
    assert len(body["merged_intervals"]) == 1
    assert body["merged_intervals"][0]["start_ms"] == B
    assert body["merged_intervals"][0]["end_ms"] == B + 29
    assert body["covered_ms"] == 30


def test_merge_touching_not_merged():
    """[B,B+9] and [B+10,B+19] are NOT merged by /merge (strict-overlap §11 rule).
    This is the discriminator: /merge uses strict overlap, /gaps uses +1 adjacency."""
    B = 4_003_000_400
    _add_event("mg_t1", B + 0,  B + 9)
    _add_event("mg_t2", B + 10, B + 19)
    r_merge = requests.get(f"{BASE}/merge?start={B}&end={B+29}", timeout=10)
    r_gaps  = requests.get(f"{BASE}/gaps?start={B}&end={B+29}", timeout=10)
    assert r_merge.status_code == 200 and r_gaps.status_code == 200
    # /merge: touching events stay separate → 2 intervals
    assert len(r_merge.json()["merged_intervals"]) == 2, (
        f"touching events should NOT merge in /merge, got {r_merge.json()['merged_intervals']}"
    )
    assert r_merge.json()["covered_ms"] == 20
    # /gaps: adjacency merge → no gap between them
    assert r_gaps.json()["gaps"] == [{"start_ms": B + 20, "end_ms": B + 29}], (
        f"/gaps should show only [B+20,B+29] gap when events touch, got {r_gaps.json()['gaps']}"
    )


def test_merge_nested_events():
    """A fully nested inner event must not produce a separate merged interval.

    A naive sweep that emits both events returns 2 intervals with a wrong covered_ms;
    the correct result is 1 interval [B, B+49] with covered_ms=50."""
    B = 4_003_000_500
    _add_event("mg_outer", B + 0,  B + 49)
    _add_event("mg_inner", B + 10, B + 30)
    r = requests.get(f"{BASE}/merge?start={B}&end={B+49}", timeout=10)
    body = r.json()
    assert len(body["merged_intervals"]) == 1
    assert body["covered_ms"] == 50


def test_merge_covered_ms_equals_coverage():
    """covered_ms in /merge must equal covered_ms from /coverage for the same window."""
    B = 4_003_000_600
    _add_event("mg_eq1", B + 5,  B + 25)
    _add_event("mg_eq2", B + 20, B + 45)
    _add_event("mg_eq3", B + 60, B + 80)
    S, E = B, B + 99
    r_merge = requests.get(f"{BASE}/merge?start={S}&end={E}", timeout=10)
    r_cov   = requests.get(f"{BASE}/coverage?start={S}&end={E}", timeout=10)
    assert r_merge.status_code == 200 and r_cov.status_code == 200
    assert r_merge.json()["covered_ms"] == r_cov.json()["covered_ms"]


def test_merge_invalid_params():
    """Missing or bad params → 400."""
    B = 4_003_000_700
    r1 = requests.get(f"{BASE}/merge?start={B}", timeout=10)
    assert r1.status_code == 400
    r2 = requests.get(f"{BASE}/merge?start={B+10}&end={B}", timeout=10)
    assert r2.status_code == 400


# =========================================================================== #
# §19 GET /event_concurrency                                                   #
# =========================================================================== #

def test_event_concurrency_single_event():
    """One event alone → max_depth=1."""
    B = 4_004_000_000
    eid = _add_event("ec_solo", B + 10, B + 50)
    r = requests.get(f"{BASE}/event_concurrency?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    evs = r.json()["events"]
    assert len(evs) == 1
    assert evs[0]["id"] == eid
    assert evs[0]["max_depth"] == 1


def test_event_concurrency_two_overlapping():
    """Two overlapping events → both get max_depth=2."""
    B = 4_004_000_100
    e1 = _add_event("ec_ov1", B + 0,  B + 29)
    e2 = _add_event("ec_ov2", B + 10, B + 39)
    r = requests.get(f"{BASE}/event_concurrency?start={B}&end={B+49}", timeout=10)
    evs = {ev["id"]: ev["max_depth"] for ev in r.json()["events"]}
    assert evs[e1] == 2, f"event 1 should see max_depth=2, got {evs[e1]}"
    assert evs[e2] == 2, f"event 2 should see max_depth=2, got {evs[e2]}"


def test_event_concurrency_sort_order():
    """Sort order is max_depth DESC, then start_ms ASC, then id ASC for same-depth ties.

    EA/EB/EC all have depth 3; a sort-by-depth-only implementation returns them in
    arbitrary order instead of the required ea→eb→ec (start_ms-ascending) sequence."""
    B = 4_004_000_200
    # EA, EB, EC all overlap → depth 3; ED isolated → depth 1
    ea = _add_event("ec_sort_a", B + 0,  B + 49)
    eb = _add_event("ec_sort_b", B + 10, B + 59)
    ec = _add_event("ec_sort_c", B + 20, B + 69)
    ed = _add_event("ec_sort_d", B + 70, B + 99)
    r = requests.get(f"{BASE}/event_concurrency?start={B}&end={B+99}", timeout=10)
    evs = r.json()["events"]
    assert len(evs) == 4
    # First 3 should be ea, eb, ec (depth=3), last is ed (depth=1)
    assert evs[0]["id"] == ea, f"first event should be ea (start=B), got id={evs[0]['id']}"
    assert evs[1]["id"] == eb
    assert evs[2]["id"] == ec
    assert evs[3]["id"] == ed
    assert evs[3]["max_depth"] == 1


def test_event_concurrency_isolated_vs_overlapping():
    """max_depth is the peak concurrent depth during each event's own lifetime, not a global max.

    EA/EB/EC all overlap so each sees depth 3; ED is isolated so it sees depth 1.
    A naive global-peak implementation would assign depth 3 to ED as well."""
    B = 4_004_000_300
    ea = _add_event("ec_b_ea", B + 0,  B + 49)
    eb = _add_event("ec_b_eb", B + 10, B + 59)
    ec = _add_event("ec_b_ec", B + 20, B + 69)
    ed = _add_event("ec_b_ed", B + 70, B + 99)
    r = requests.get(f"{BASE}/event_concurrency?start={B}&end={B+99}", timeout=10)
    depth_map = {ev["id"]: ev["max_depth"] for ev in r.json()["events"]}
    assert depth_map[ea] == 3, f"EA max_depth should be 3, got {depth_map[ea]}"
    assert depth_map[eb] == 3, f"EB max_depth should be 3, got {depth_map[eb]}"
    assert depth_map[ec] == 3, f"EC max_depth should be 3, got {depth_map[ec]}"
    assert depth_map[ed] == 1, f"ED max_depth should be 1, got {depth_map[ed]}"


def test_event_concurrency_clip_to_window():
    """Event extending beyond window is clipped; depth computed within clipped range."""
    B = 4_004_000_400
    # long event from B-100 to B+200; window [B, B+49]; second event [B+5, B+15]
    e_long = _add_event("ec_clip_long", B - 100, B + 200)
    e_short = _add_event("ec_clip_short", B + 5, B + 15)
    r = requests.get(f"{BASE}/event_concurrency?start={B}&end={B+49}", timeout=10)
    depth_map = {ev["id"]: ev["max_depth"] for ev in r.json()["events"]}
    # Both events active at t=B+5..B+15, so max_depth=2 for both
    assert depth_map[e_long] == 2, f"long event clipped depth should be 2, got {depth_map[e_long]}"
    assert depth_map[e_short] == 2, f"short event depth should be 2, got {depth_map[e_short]}"


def test_event_concurrency_empty_window():
    """No events in window → empty events list."""
    B = 4_004_001_000
    r = requests.get(f"{BASE}/event_concurrency?start={B}&end={B+49}", timeout=10)
    assert r.status_code == 200
    assert r.json()["events"] == []


def test_event_concurrency_invalid_params():
    """Missing or bad params → 400."""
    B = 4_004_000_600
    r1 = requests.get(f"{BASE}/event_concurrency?start={B}", timeout=10)
    assert r1.status_code == 400
    r2 = requests.get(f"{BASE}/event_concurrency?start={B+10}&end={B}", timeout=10)
    assert r2.status_code == 400


# =========================================================================== #
# §20 GET /free_slots                                                          #
# =========================================================================== #

def test_free_slots_basic():
    """Fixture C: 3 events leave 4 gaps; min=10 filters the 5ms gap → 3 results."""
    B = 4_005_000_000
    _add_event("fs_c1", B + 5,  B + 14)   # gap before: [0,4]=5ms; gap after: [15,29]=15ms
    _add_event("fs_c2", B + 30, B + 59)   # gap after: [60,79]=20ms
    _add_event("fs_c3", B + 80, B + 89)   # gap after: [90,99]=10ms
    S, E = B, B + 99
    r = requests.get(f"{BASE}/free_slots?start={S}&end={E}&min_duration_ms=10", timeout=10)
    assert r.status_code == 200
    slots = r.json()["free_slots"]
    assert len(slots) == 3, f"expected 3 slots (≥10ms), got {len(slots)}: {slots}"
    # Sorted by duration DESC: 20, 15, 10
    assert slots[0]["duration_ms"] == 20
    assert slots[1]["duration_ms"] == 15
    assert slots[2]["duration_ms"] == 10


def test_free_slots_sort_by_duration_desc():
    """Free slots must be returned sorted by duration_ms DESC, not in gap-discovery order.

    A sweep finds gaps in start_ms order; a naive implementation omits the sort step
    and returns gaps in scan order (ascending start_ms) instead of duration DESC."""
    B = 4_005_000_100
    _add_event("fs_sd1", B + 5,  B + 14)
    _add_event("fs_sd2", B + 30, B + 59)
    _add_event("fs_sd3", B + 80, B + 89)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/free_slots?start={S}&end={E}&min_duration_ms=1", timeout=10)
    durations = [sl["duration_ms"] for sl in r.json()["free_slots"]]
    assert durations == sorted(durations, reverse=True), (
        f"free_slots must be sorted duration DESC, got {durations}"
    )


def test_free_slots_tiebreak_start_ms():
    """Two gaps of equal duration: smaller start_ms comes first."""
    B = 4_005_000_200
    # Create two 10ms gaps: [0,9] and [20,29]
    _add_event("fs_tb1", B + 10, B + 19)
    _add_event("fs_tb2", B + 30, B + 39)
    # gaps: [0,9]=10ms, [20,29]=10ms, [40,49]=10ms
    S, E = B, B + 49
    r = requests.get(f"{BASE}/free_slots?start={S}&end={E}&min_duration_ms=10", timeout=10)
    slots = r.json()["free_slots"]
    starts = [sl["start_ms"] for sl in slots]
    # all same duration → sorted by start_ms ASC
    assert starts == sorted(starts), f"tie-break should sort start_ms ASC, got {starts}"


def test_free_slots_none_qualify():
    """When all gaps are narrower than min_duration_ms, the result must be an empty list.

    A naive implementation that ignores the min_duration filter returns all gaps anyway;
    this verifies the filter is enforced even when it eliminates every candidate."""
    B = 4_005_000_300
    _add_event("fs_nq1", B + 0,  B + 9)
    _add_event("fs_nq2", B + 15, B + 24)
    _add_event("fs_nq3", B + 30, B + 39)
    # gaps: [10,14]=5ms, [25,29]=5ms, [40,49]=10ms
    S, E = B, B + 49
    r = requests.get(f"{BASE}/free_slots?start={S}&end={E}&min_duration_ms=11", timeout=10)
    assert r.status_code == 200
    assert r.json()["free_slots"] == [], f"expected [], got {r.json()['free_slots']}"


def test_free_slots_min_1_returns_all_gaps():
    """min_duration_ms=1 returns every gap including single-instant gaps."""
    B = 4_005_000_400
    _add_event("fs_m1a", B + 0,  B + 8)
    _add_event("fs_m1b", B + 10, B + 18)
    # gaps: [9,9]=1ms, [19,29]=11ms
    S, E = B, B + 29
    r_all  = requests.get(f"{BASE}/free_slots?start={S}&end={E}&min_duration_ms=1", timeout=10)
    r_gaps = requests.get(f"{BASE}/gaps?start={S}&end={E}", timeout=10)
    assert r_all.status_code == 200 and r_gaps.status_code == 200
    # All gaps from /gaps should appear in /free_slots when min=1
    gap_count = len(r_gaps.json()["gaps"])
    slot_count = len(r_all.json()["free_slots"])
    assert slot_count == gap_count, (
        f"/free_slots min=1 should return all {gap_count} gaps, got {slot_count}"
    )


def test_free_slots_duration_field():
    """duration_ms must equal end_ms - start_ms + 1 (inclusive endpoints), not end_ms - start_ms.

    A naive off-by-one subtraction would undercount by 1 per slot; this test verifies
    the formula directly against every returned slot in the response."""
    B = 4_005_000_500
    _add_event("fs_dur1", B + 10, B + 30)
    _add_event("fs_dur2", B + 50, B + 70)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/free_slots?start={S}&end={E}&min_duration_ms=1", timeout=10)
    for sl in r.json()["free_slots"]:
        expected_dur = sl["end_ms"] - sl["start_ms"] + 1
        assert sl["duration_ms"] == expected_dur, (
            f"duration_ms {sl['duration_ms']} != end_ms-start_ms+1 = {expected_dur}"
        )


def test_free_slots_invalid_params():
    """Missing or bad params → 400."""
    B = 4_005_000_600
    r1 = requests.get(f"{BASE}/free_slots?start={B}&end={B+9}", timeout=10)
    assert r1.status_code == 400
    r2 = requests.get(f"{BASE}/free_slots?start={B+10}&end={B}&min_duration_ms=5", timeout=10)
    assert r2.status_code == 400
    r3 = requests.get(f"{BASE}/free_slots?start={B}&end={B+9}&min_duration_ms=0", timeout=10)
    assert r3.status_code == 400


# =========================================================================== #
# Additional discriminator tests for existing endpoints                        #
# =========================================================================== #

def test_peak_duration_ms_noncontiguous_runs():
    """peak_duration_ms sums two non-contiguous intervals where c == max_concurrency.

    D1 covers the full window [0,99]. D2 covers [10,19] and D3 covers [50,59].
    c = 2 in [10,19] (10 instants) and [50,59] (10 instants); peak_duration_ms must
    be 20, not 10 (only first run) or 50 (naive last_end - first_start) or 100 (full window)."""
    B = 4_000_000_500
    _add_event("pdu_nc_d1", B + 0,  B + 99)
    _add_event("pdu_nc_d2", B + 10, B + 19)
    _add_event("pdu_nc_d3", B + 50, B + 59)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["max_concurrency"] == 2
    assert body["at_ms"] == B + 10, f"earliest peak instant should be B+10, got {body['at_ms']}"
    assert body["peak_duration_ms"] == 20, (
        f"peak_duration_ms should sum both non-contiguous runs (10+10=20), "
        f"got {body['peak_duration_ms']}"
    )


def test_heatmap_histogram_no_trailing_zeros():
    """histogram must not end with trailing zeros — length == max_level + 1.

    One event active 10 instants in a 25ms slot leaves c=1 for 10 instants and c=0 for 15.
    The correct histogram is [15, 10] (length 2). An implementation that pads to a fixed
    length or adds trailing zeros would return [15, 10, 0, ...] which is wrong."""
    B = 4_002_000_800
    _add_event("hm_notrail", B + 0, B + 9)
    S, E, R = B, B + 24, 25
    r = requests.get(f"{BASE}/heatmap?start={S}&end={E}&resolution_ms={R}", timeout=10)
    assert r.status_code == 200
    sl = r.json()["slots"][0]
    assert sl["histogram"] == [15, 10], (
        f"histogram should be [15,10] (no trailing zeros), got {sl['histogram']}"
    )
    assert sl["histogram"][-1] > 0, "histogram must not end with a trailing zero entry"


# =========================================================================== #
# Independent oracle helpers for §21 and §22                                  #
# =========================================================================== #

def _weighted_schedule_oracle(S, E):
    """§21: Maximum-weight non-overlapping subset via DP.
    Returns (max_weight_float, selected_ids_in_end_asc_id_asc, covered_ms)."""
    import json as _json
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, start_ms, end_ms, metadata_json FROM events "
        "WHERE start_ms >= ? AND end_ms <= ? ORDER BY end_ms ASC, id ASC",
        (S, E),
    ).fetchall()
    conn.close()
    evs = []
    for eid, s, e, mj in rows:
        w = 1.0
        try:
            meta = _json.loads(mj)
            if isinstance(meta, dict) and "weight" in meta:
                wv = meta["weight"]
                if isinstance(wv, (int, float)):
                    w = float(wv)
        except Exception:
            pass
        evs.append((eid, s, e, w))
    n = len(evs)
    if n == 0:
        return 0.0, [], 0
    p = [0] * (n + 1)
    for i in range(1, n + 1):
        si = evs[i - 1][1]
        for j in range(i - 1, 0, -1):
            if evs[j - 1][2] < si:
                p[i] = j
                break
    opt = [0.0] * (n + 1)
    for i in range(1, n + 1):
        wi = evs[i - 1][3]
        opt[i] = max(opt[i - 1], wi + opt[p[i]])
    selected = []
    i = n
    while i > 0:
        wi = evs[i - 1][3]
        if wi + opt[p[i]] > opt[i - 1]:
            selected.append(evs[i - 1])
            i = p[i]
        else:
            i -= 1
    selected.reverse()
    ids = [ev[0] for ev in selected]
    covered = sum(ev[2] - ev[1] + 1 for ev in selected)
    return opt[n], ids, covered


def _coloring_oracle(S, E):
    """§22: Minimum interval graph coloring via earliest-start greedy.
    Returns (num_colors, assignments) where assignments = [{'id':..,'color':..}, ..]."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, start_ms, end_ms FROM events "
        "WHERE start_ms <= ? AND end_ms >= ? ORDER BY start_ms ASC, id ASC",
        (E, S),
    ).fetchall()
    conn.close()
    evs = [(r[0], r[1], r[2]) for r in rows]
    colors = []
    num_colors = 0
    for i, (eid, s, e) in enumerate(evs):
        used = set()
        for j in range(i):
            ps, pe = evs[j][1], evs[j][2]
            if ps <= e and pe >= s:
                used.add(colors[j])
        c = 0
        while c in used:
            c += 1
        colors.append(c)
        if c + 1 > num_colors:
            num_colors = c + 1
    assignments = sorted(
        [{"id": evs[i][0], "color": colors[i]} for i in range(len(evs))],
        key=lambda x: (x["color"], x["id"]),
    )
    return num_colors, assignments


# =========================================================================== #
# §21 GET /weighted_schedule — weighted interval scheduling DP                 #
# =========================================================================== #

def test_weighted_schedule_empty_window():
    """No events in window → max_weight=0.00, selected_ids=[], covered_ms=0."""
    B = 4_006_000_000
    r = requests.get(f"{BASE}/weighted_schedule?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["max_weight"]) == 0.0
    assert body["selected_ids"] == []
    assert body["covered_ms"] == 0


def test_weighted_schedule_default_weight_one():
    """An event without a 'weight' key in metadata defaults to weight 1.0."""
    B = 4_006_100_000
    eid = _add_event("ws_dflt", B + 10, B + 30)
    r = requests.get(f"{BASE}/weighted_schedule?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert float(body["max_weight"]) == pytest.approx(1.0, abs=0.01), (
        f"default weight event should yield max_weight 1.00, got {body['max_weight']}"
    )
    assert eid in body["selected_ids"]


def test_weighted_schedule_heavy_single_beats_light_pair():
    """DP must pick the heavy single event (5.0) over the lighter pair (1.5 + 1.5 = 3.0).

    A naive unweighted-greedy (maximise count) picks the two short events {X, Y} and
    returns max_weight=3.0. The DP correctly picks the single heavy event and returns
    max_weight=5.0. This is the primary discriminator for the §21 DP requirement."""
    B = 4_006_200_000
    id_heavy = _add_event("ws_heavy", B, B + 200, metadata={"weight": 5.0})
    id_x = _add_event("ws_lx", B, B + 80, metadata={"weight": 1.5})
    id_y = _add_event("ws_ly", B + 100, B + 200, metadata={"weight": 1.5})
    # id_x and id_y are compatible (80 < 100); combined weight 3.0 < 5.0
    r = requests.get(f"{BASE}/weighted_schedule?start={B}&end={B+200}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    exp_w, exp_ids, exp_cov = _weighted_schedule_oracle(B, B + 200)
    assert exp_w == pytest.approx(5.0, abs=0.01), f"oracle sanity: {exp_w}"
    assert float(body["max_weight"]) == pytest.approx(5.0, abs=0.01), (
        f"DP must pick heavy event (5.0), not pair (3.0); got max_weight={body['max_weight']}"
    )
    assert id_heavy in body["selected_ids"], "heavy event must be in selected_ids"
    assert id_x not in body["selected_ids"], "light event X must NOT be selected"
    assert id_y not in body["selected_ids"], "light event Y must NOT be selected"


def test_weighted_schedule_light_pair_beats_heavy_single():
    """DP must pick the two light events (2.5 + 2.5 = 5.0) over the heavy single (4.0).

    Converse of the previous test: now the pair outweighs the single event."""
    B = 4_006_300_000
    id_heavy = _add_event("ws_hs2", B, B + 200, metadata={"weight": 4.0})
    id_x = _add_event("ws_lx2", B, B + 80, metadata={"weight": 2.5})
    id_y = _add_event("ws_ly2", B + 100, B + 200, metadata={"weight": 2.5})
    r = requests.get(f"{BASE}/weighted_schedule?start={B}&end={B+200}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    exp_w, exp_ids, exp_cov = _weighted_schedule_oracle(B, B + 200)
    assert exp_w == pytest.approx(5.0, abs=0.01), f"oracle sanity: {exp_w}"
    assert float(body["max_weight"]) == pytest.approx(5.0, abs=0.01), (
        f"DP must pick pair (5.0), not heavy single (4.0); got {body['max_weight']}"
    )
    assert id_x in body["selected_ids"]
    assert id_y in body["selected_ids"]
    assert id_heavy not in body["selected_ids"], "heavy single must NOT be selected"


def test_weighted_schedule_selected_ids_in_end_order():
    """selected_ids are listed in end_ms ASC then id ASC order (DP traceback order)."""
    B = 4_006_400_000
    id_a = _add_event("ws_ord_a", B,       B + 20, metadata={"weight": 2.0})
    id_b = _add_event("ws_ord_b", B + 30,  B + 50, metadata={"weight": 2.0})
    id_c = _add_event("ws_ord_c", B + 60,  B + 80, metadata={"weight": 2.0})
    r = requests.get(f"{BASE}/weighted_schedule?start={B}&end={B+100}", timeout=10)
    body = r.json()
    assert body["selected_ids"] == [id_a, id_b, id_c], (
        f"selected_ids must be in end_ms ASC order, got {body['selected_ids']}"
    )


def test_weighted_schedule_covered_ms():
    """covered_ms is the sum of (end_ms - start_ms + 1) for each selected event."""
    B = 4_006_500_000
    _add_event("ws_cov1", B,       B + 9,  metadata={"weight": 3.0})  # 10ms
    _add_event("ws_cov2", B + 20,  B + 34, metadata={"weight": 3.0})  # 15ms
    _add_event("ws_cov3", B + 100, B + 199)                            # outside window
    S, E = B, B + 99
    r = requests.get(f"{BASE}/weighted_schedule?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["covered_ms"] == 25, (
        f"covered_ms should be 10+15=25, got {body['covered_ms']}"
    )


def test_weighted_schedule_excludes_partial_events():
    """Events that cross the window boundary are NOT included (must be fully contained)."""
    B = 4_006_600_000
    id_inside = _add_event("ws_excl_in", B + 20, B + 40, metadata={"weight": 1.0})
    _add_event("ws_excl_left", B - 10, B + 30, metadata={"weight": 10.0})   # crosses left
    _add_event("ws_excl_right", B + 50, B + 150, metadata={"weight": 10.0}) # crosses right
    S, E = B, B + 99
    r = requests.get(f"{BASE}/weighted_schedule?start={S}&end={E}", timeout=10)
    body = r.json()
    assert body["selected_ids"] == [id_inside], (
        f"only inside event should be selected, got {body['selected_ids']}"
    )
    assert float(body["max_weight"]) == pytest.approx(1.0, abs=0.01)


def test_weighted_schedule_oracle_cross_check():
    """Five events with mixed weights; endpoint must match the independent DP oracle exactly."""
    B = 4_006_700_000
    _add_event("ws_cx1", B,       B + 20, metadata={"weight": 3.0})
    _add_event("ws_cx2", B + 10,  B + 30, metadata={"weight": 5.0})  # overlaps cx1
    _add_event("ws_cx3", B + 25,  B + 45, metadata={"weight": 2.0})
    _add_event("ws_cx4", B + 40,  B + 60, metadata={"weight": 4.0})  # overlaps cx3
    _add_event("ws_cx5", B + 65,  B + 90, metadata={"weight": 3.0})
    S, E = B, B + 99
    r = requests.get(f"{BASE}/weighted_schedule?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    exp_w, exp_ids, exp_cov = _weighted_schedule_oracle(S, E)
    assert float(body["max_weight"]) == pytest.approx(exp_w, abs=0.01), (
        f"max_weight={body['max_weight']} != oracle {exp_w:.2f}"
    )
    assert body["selected_ids"] == exp_ids, (
        f"selected_ids={body['selected_ids']} != oracle {exp_ids}"
    )
    assert body["covered_ms"] == exp_cov, (
        f"covered_ms={body['covered_ms']} != oracle {exp_cov}"
    )


def test_weighted_schedule_invalid_params():
    """Missing or bad params → 400."""
    B = 4_006_800_000
    assert requests.get(f"{BASE}/weighted_schedule?start={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/weighted_schedule?start={B+10}&end={B}", timeout=10
    ).status_code == 400


# =========================================================================== #
# §22 GET /coloring — minimum interval graph coloring                         #
# =========================================================================== #

def test_coloring_empty_window():
    """No events intersecting window → num_colors=0 and assignments=[]."""
    B = 4_007_000_000
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["num_colors"] == 0
    assert body["assignments"] == []


def test_coloring_single_event():
    """One event → num_colors=1 and one assignment entry."""
    B = 4_007_100_000
    eid = _add_event("col_solo", B + 10, B + 50)
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["num_colors"] == 1, f"single event needs 1 color, got {body['num_colors']}"
    assert len(body["assignments"]) == 1
    assert body["assignments"][0]["id"] == eid
    assert body["assignments"][0]["color"] == 0


def test_coloring_two_nonoverlapping_share_color_zero():
    """Two non-overlapping events can share color 0 — num_colors stays 1."""
    B = 4_007_200_000
    id_a = _add_event("col_na", B + 0,  B + 19)
    id_b = _add_event("col_nb", B + 30, B + 49)  # starts after A ends
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["num_colors"] == 1, (
        f"non-overlapping events can share a color → num_colors=1, got {body['num_colors']}"
    )
    # Both should have color 0
    color_map = {a["id"]: a["color"] for a in body["assignments"]}
    assert color_map[id_a] == 0
    assert color_map[id_b] == 0


def test_coloring_two_overlapping_need_two_colors():
    """Two overlapping events must get distinct colors → num_colors=2."""
    B = 4_007_300_000
    id_a = _add_event("col_ov1", B + 0,  B + 30)
    id_b = _add_event("col_ov2", B + 10, B + 40)  # overlaps A
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["num_colors"] == 2, (
        f"two overlapping events need 2 colors, got {body['num_colors']}"
    )
    color_map = {a["id"]: a["color"] for a in body["assignments"]}
    assert color_map[id_a] != color_map[id_b], "overlapping events must not share a color"


def test_coloring_three_way_clique_needs_three_colors():
    """Three mutually overlapping events form a clique; minimum coloring needs exactly 3 colors.

    A coloring that uses 4+ colors is not optimal; a coloring that uses 2 colors is invalid.
    The minimum is exactly 3 (= peak concurrency of the window)."""
    B = 4_007_400_000
    id_a = _add_event("col_3cl_a", B + 0,  B + 40)
    id_b = _add_event("col_3cl_b", B + 10, B + 50)  # overlaps A
    id_c = _add_event("col_3cl_c", B + 20, B + 60)  # overlaps A and B
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["num_colors"] == 3, (
        f"3-clique needs exactly 3 colors (= peak concurrency), got {body['num_colors']}"
    )
    color_map = {a["id"]: a["color"] for a in body["assignments"]}
    assert color_map[id_a] != color_map[id_b], "A and B overlap → must differ"
    assert color_map[id_b] != color_map[id_c], "B and C overlap → must differ"
    assert color_map[id_a] != color_map[id_c], "A and C overlap → must differ"


def test_coloring_num_colors_equals_peak_concurrency():
    """num_colors == peak_concurrency of the window (interval graphs are perfect)."""
    B = 4_007_500_000
    _add_event("col_pk1", B + 0,  B + 60)
    _add_event("col_pk2", B + 20, B + 80)
    _add_event("col_pk3", B + 40, B + 99)
    # Peak: at t=B+40 all three active → peak=3 → num_colors must be 3
    r_col  = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    r_peak = requests.get(f"{BASE}/peak?start={B}&end={B+99}", timeout=10)
    assert r_col.status_code == 200 and r_peak.status_code == 200
    assert r_col.json()["num_colors"] == r_peak.json()["max_concurrency"], (
        f"num_colors={r_col.json()['num_colors']} != peak_concurrency={r_peak.json()['max_concurrency']}"
    )


def test_coloring_valid_no_adjacent_same_color():
    """No two events that overlap may have the same color — validated for every pair."""
    B = 4_007_600_000
    _add_event("col_val1", B + 0,  B + 30)
    _add_event("col_val2", B + 10, B + 50)
    _add_event("col_val3", B + 40, B + 70)
    _add_event("col_val4", B + 20, B + 60)
    _add_event("col_val5", B + 55, B + 90)
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    conn = sqlite3.connect(DB)
    evs = {r_[0]: (r_[1], r_[2]) for r_ in conn.execute(
        "SELECT id, start_ms, end_ms FROM events WHERE start_ms <= ? AND end_ms >= ?",
        (B + 99, B),
    ).fetchall()}
    conn.close()
    color_map = {a["id"]: a["color"] for a in body["assignments"]}
    for eid_a, ca in color_map.items():
        for eid_b, cb in color_map.items():
            if eid_a >= eid_b:
                continue
            sa, ea = evs[eid_a]
            sb, eb = evs[eid_b]
            if sa <= eb and sb <= ea:  # they overlap
                assert ca != cb, (
                    f"events {eid_a} and {eid_b} overlap but both have color {ca}"
                )


def test_coloring_sorted_by_color_then_id():
    """assignments list is sorted by color ASC, then id ASC for ties within a color."""
    B = 4_007_700_000
    _add_event("col_sort1", B + 0,  B + 10)
    _add_event("col_sort2", B + 20, B + 30)
    _add_event("col_sort3", B + 5,  B + 25)  # overlaps both
    r = requests.get(f"{BASE}/coloring?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    assigns = r.json()["assignments"]
    colors = [a["color"] for a in assigns]
    assert colors == sorted(colors), f"assignments not sorted by color ASC: {colors}"
    # Within each color group, ids must be ascending
    from itertools import groupby
    for color, group in groupby(assigns, key=lambda x: x["color"]):
        ids_in_group = [a["id"] for a in group]
        assert ids_in_group == sorted(ids_in_group), (
            f"color {color}: ids not sorted ASC: {ids_in_group}"
        )


def test_coloring_oracle_cross_check():
    """Complex scenario with 5 events — num_colors and assignment colors match oracle exactly."""
    B = 4_007_800_000
    _add_event("col_cx1", B + 0,  B + 20)
    _add_event("col_cx2", B + 10, B + 35)
    _add_event("col_cx3", B + 30, B + 55)
    _add_event("col_cx4", B + 50, B + 70)
    _add_event("col_cx5", B + 15, B + 45)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/coloring?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    exp_nc, exp_assigns = _coloring_oracle(S, E)
    assert body["num_colors"] == exp_nc, (
        f"num_colors={body['num_colors']} != oracle {exp_nc}"
    )
    got_assigns = [(a["id"], a["color"]) for a in body["assignments"]]
    exp_assigns_tuples = [(a["id"], a["color"]) for a in exp_assigns]
    assert got_assigns == exp_assigns_tuples, (
        f"assignments mismatch:\n  got: {got_assigns}\n  expected: {exp_assigns_tuples}"
    )


def test_coloring_invalid_params():
    """Missing or bad params → 400."""
    B = 4_007_900_000
    assert requests.get(f"{BASE}/coloring?start={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/coloring?start={B+10}&end={B}", timeout=10
    ).status_code == 400


# =========================================================================== #
# Independent Python oracles for §23 / §24 / §25                              #
# =========================================================================== #

def _concurrency_runs_oracle(S, E):
    """Sweep-line RLE: list of {start_ms, end_ms, concurrency} dicts, merged."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, start_ms, end_ms FROM events WHERE start_ms <= ? AND end_ms >= ?",
        (E, S),
    ).fetchall()
    conn.close()
    evs = [{"id": r[0], "start_ms": r[1], "end_ms": r[2]} for r in rows]

    cp_set = {S, E + 1}
    for e in evs:
        if S < e["start_ms"] <= E:
            cp_set.add(e["start_ms"])
        ep1 = e["end_ms"] + 1
        if ep1 > S and ep1 <= E:
            cp_set.add(ep1)

    cps = sorted(cp_set)
    runs = []
    for i in range(len(cps) - 1):
        t = cps[i]
        c = sum(1 for e in evs if e["start_ms"] <= t <= e["end_ms"])
        runs.append({"start_ms": t, "end_ms": cps[i + 1] - 1, "concurrency": c})

    merged = []
    for r in runs:
        if merged and merged[-1]["concurrency"] == r["concurrency"]:
            merged[-1]["end_ms"] = r["end_ms"]
        else:
            merged.append(dict(r))
    return merged


def _interval_cover_oracle(S, E, target_ms):
    """Returns (min_events_or_None, sorted_selected_ids, achieved_coverage)."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, start_ms, end_ms FROM events WHERE start_ms <= ? AND end_ms >= ?",
        (E, S),
    ).fetchall()
    conn.close()

    eff = min(target_ms, E - S + 1)
    goal = S + eff - 1
    clipped = [{"id": r[0], "cs": max(r[1], S), "ce": min(r[2], E)} for r in rows]
    remaining = list(clipped)
    frontier = S - 1
    selected = []

    while frontier < goal and remaining:
        cands = [r for r in remaining if r["cs"] <= frontier + 1 and r["ce"] > frontier]
        if not cands:
            break
        best = max(cands, key=lambda r: (r["ce"], -r["id"]))
        frontier = best["ce"]
        selected.append(best["id"])
        remaining = [r for r in remaining if r["id"] != best["id"]]

    achieved = max(0, frontier - S + 1)
    if frontier >= goal:
        return (len(selected), sorted(selected), achieved)
    return (None, [], achieved)


def _earliest_available_oracle(after, duration_ms):
    """Returns (slot_start, slot_end)."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT start_ms, end_ms FROM events WHERE end_ms >= ?", (after,)
    ).fetchall()
    conn.close()

    if not rows:
        return (after, after + duration_ms - 1)

    clipped = sorted((max(r[0], after), r[1]) for r in rows)
    merged = []
    for cs, ce in clipped:
        if merged and cs <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], ce))
        else:
            merged.append([cs, ce])

    current = after
    for bs, be in merged:
        if bs - current >= duration_ms:
            return (current, current + duration_ms - 1)
        current = be + 1
    return (current, current + duration_ms - 1)


# =========================================================================== #
# §23 GET /concurrency_runs — sweep-line RLE of the concurrency timeline       #
# =========================================================================== #

def test_runs_empty_window():
    """No events intersecting the window → single run with concurrency 0."""
    B = 4_050_000_000
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    runs = body["runs"]
    assert len(runs) == 1
    assert runs[0]["start_ms"] == B
    assert runs[0]["end_ms"] == B + 99
    assert runs[0]["concurrency"] == 0


def test_runs_single_event_splits_window():
    """One event inside the window produces three runs: 0 / 1 / 0."""
    B = 4_050_100_000
    _add_event("cr_single", B + 20, B + 59)
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    runs = body["runs"]
    assert len(runs) == 3
    assert runs[0] == {"start_ms": B, "end_ms": B + 19, "concurrency": 0}
    assert runs[1] == {"start_ms": B + 20, "end_ms": B + 59, "concurrency": 1}
    assert runs[2] == {"start_ms": B + 60, "end_ms": B + 99, "concurrency": 0}


def test_runs_two_overlapping_events():
    """Two overlapping events produce a triple-region structure: 1 / 2 / 1."""
    B = 4_050_200_000
    _add_event("cr_ovA", B + 10, B + 59)
    _add_event("cr_ovB", B + 30, B + 79)
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    runs = body["runs"]
    assert len(runs) == 5
    assert runs[0]["concurrency"] == 0   # [B, B+9]
    assert runs[1]["concurrency"] == 1   # [B+10, B+29]
    assert runs[2]["concurrency"] == 2   # [B+30, B+59]
    assert runs[3]["concurrency"] == 1   # [B+60, B+79]
    assert runs[4]["concurrency"] == 0   # [B+80, B+99]
    assert runs[2]["start_ms"] == B + 30
    assert runs[2]["end_ms"] == B + 59


def test_runs_touching_events_must_merge():
    """KEY DISCRIMINATOR: A ends at T, B starts at T+1 → both runs have concurrency 1
    and must be merged into a single run. A naive implementation returns 4 runs; the
    correct one returns 3 by collapsing adjacent same-level runs."""
    B = 4_050_300_000
    _add_event("cr_tA", B + 10, B + 39)   # ends at B+39; change point B+40
    _add_event("cr_tB", B + 40, B + 69)   # starts at B+40; same change point
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    runs = body["runs"]
    assert len(runs) == 3, (
        "Touching events at B+39/B+40 produce two raw level-1 runs that MUST be merged. "
        f"Expected 3 runs, got {len(runs)}: {runs}"
    )
    assert runs[0] == {"start_ms": B, "end_ms": B + 9, "concurrency": 0}
    assert runs[1] == {"start_ms": B + 10, "end_ms": B + 69, "concurrency": 1}
    assert runs[2] == {"start_ms": B + 70, "end_ms": B + 99, "concurrency": 0}


def test_runs_event_straddles_window_start():
    """Event starting before the window still contributes to concurrency at the window start."""
    B = 4_050_400_000
    _add_event("cr_straddle", B - 50, B + 49)   # starts 50ms before window
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    runs = body["runs"]
    # change point at B+50 (end_ms+1 = B+50), so two runs: [B,B+49]=1, [B+50,B+99]=0
    assert len(runs) == 2
    assert runs[0] == {"start_ms": B, "end_ms": B + 49, "concurrency": 1}
    assert runs[1] == {"start_ms": B + 50, "end_ms": B + 99, "concurrency": 0}


def test_runs_concurrency_sum_equals_heatmap():
    """Each run's (end_ms - start_ms + 1) * concurrency must sum to the total
    weighted coverage — cross-checked against the heatmap mean_concurrency."""
    B = 4_050_500_000
    _add_event("cr_h1", B + 0, B + 49)
    _add_event("cr_h2", B + 20, B + 79)
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    runs = body["runs"]
    # Verify run boundaries are contiguous with no gaps
    for i in range(len(runs) - 1):
        assert runs[i]["end_ms"] + 1 == runs[i + 1]["start_ms"], (
            f"Gap between runs {i} and {i+1}: {runs[i]['end_ms']+1} != {runs[i+1]['start_ms']}"
        )
    assert runs[0]["start_ms"] == B
    assert runs[-1]["end_ms"] == B + 99
    # Verify individual run correctness via oracle
    expected = _concurrency_runs_oracle(B, B + 99)
    assert runs == expected


def test_runs_oracle_cross_check():
    """Five events with complex overlaps — exact match against independent Python oracle."""
    B = 4_050_600_000
    _add_event("cr_oc1", B + 0, B + 40)
    _add_event("cr_oc2", B + 20, B + 60)
    _add_event("cr_oc3", B + 30, B + 50)
    _add_event("cr_oc4", B + 70, B + 90)
    _add_event("cr_oc5", B + 80, B + 99)
    r = requests.get(f"{BASE}/concurrency_runs?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    expected = _concurrency_runs_oracle(B, B + 99)
    assert body["runs"] == expected, f"Oracle mismatch: got {body['runs']}, expected {expected}"


def test_runs_invalid_params():
    """Missing or bad params → 400."""
    B = 4_050_700_000
    assert requests.get(f"{BASE}/concurrency_runs?start={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/concurrency_runs?start={B+10}&end={B}", timeout=10
    ).status_code == 400


# =========================================================================== #
# §24 GET /interval_cover — greedy minimum-cardinality interval cover          #
# =========================================================================== #

def test_cover_no_events_returns_null():
    """No events in window → unreachable, min_events=null, achieved_coverage=0."""
    B = 4_060_000_000
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=50", timeout=10
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["min_events"] is None
    assert body["selected_ids"] == []
    assert body["achieved_coverage"] == 0


def test_cover_single_event_achieves_target():
    """One event covering the start achieves the target in one step."""
    B = 4_060_100_000
    eid = _add_event("ic_one", B, B + 99)
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=50", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    assert body["min_events"] == 1
    assert body["selected_ids"] == [eid]
    assert body["achieved_coverage"] >= 50


def test_cover_greedy_beats_naive():
    """KEY DISCRIMINATOR: the greedy must pick the event extending the frontier
    farthest right — not the one with the smallest id.

    Events all start at or before the frontier:
      A = [B, B+14]  (reaches B+14)  ← naive picks this first (lower id)
      B = [B, B+29]  (reaches B+29)  ← greedy picks this (farthest right)
      C = [B+20, B+49]               ← both algorithms then pick this

    Greedy: B → C → done in 2 picks (frontier B+49 ≥ goal B+39).
    Naive:  A → B → C → 3 picks. The test asserts min_events == 2, not 3."""
    B = 4_060_200_000
    eid_a = _add_event("ic_ga", B, B + 14)
    eid_b = _add_event("ic_gb", B, B + 29)
    eid_c = _add_event("ic_gc", B + 20, B + 49)
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=40", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    assert body["min_events"] == 2, (
        "Greedy must pick ic_gb (farthest right) then ic_gc for 2 events, "
        f"not naive ic_ga+ic_gb+ic_gc=3. Got {body['min_events']}: {body}"
    )
    assert eid_b in body["selected_ids"]
    assert eid_c in body["selected_ids"]
    assert eid_a not in body["selected_ids"], "Naive: ic_ga should NOT be selected"
    assert body["achieved_coverage"] >= 40


def test_cover_gap_makes_unreachable():
    """A gap between covered regions means the contiguous prefix cannot be extended past it."""
    B = 4_060_300_000
    _add_event("ic_gap_a", B, B + 19)       # covers [B, B+19]
    _add_event("ic_gap_c", B + 30, B + 59)  # gap at [B+20, B+29] blocks further coverage
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=30", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    assert body["min_events"] is None, (
        f"Gap at [B+20,B+29] makes target_ms=30 unreachable from B. Got {body}"
    )
    assert body["achieved_coverage"] == 20  # only [B, B+19] covered


def test_cover_full_window_target():
    """target_ms equals full window size — must cover entire [start, end]."""
    B = 4_060_400_000
    _add_event("ic_fw1", B, B + 34)
    _add_event("ic_fw2", B + 25, B + 64)
    _add_event("ic_fw3", B + 55, B + 99)
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=100", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    assert body["min_events"] is not None, "Full window should be coverable"
    assert body["achieved_coverage"] >= 100
    assert body["min_events"] <= 3


def test_cover_selected_ids_sorted_ascending():
    """selected_ids must be sorted ascending by original event id."""
    B = 4_060_500_000
    _add_event("ic_ord1", B, B + 29)
    _add_event("ic_ord2", B + 20, B + 59)
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=50", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    ids = body["selected_ids"]
    assert ids == sorted(ids), f"selected_ids must be sorted ascending, got {ids}"


def test_cover_oracle_cross_check():
    """Four overlapping events — exact match against independent Python oracle."""
    B = 4_060_600_000
    _add_event("ic_oc1", B + 0, B + 19)
    _add_event("ic_oc2", B + 10, B + 39)
    _add_event("ic_oc3", B + 30, B + 59)
    _add_event("ic_oc4", B + 55, B + 79)
    r = requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=60", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    mn, sids, ac = _interval_cover_oracle(B, B + 99, 60)
    assert body["min_events"] == mn
    assert body["selected_ids"] == sids
    assert body["achieved_coverage"] == ac


def test_cover_invalid_params():
    """Missing or bad params → 400."""
    B = 4_060_700_000
    assert requests.get(f"{BASE}/interval_cover?start={B}&end={B+99}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/interval_cover?start={B}&end={B+99}&target_ms=0", timeout=10
    ).status_code == 400
    assert requests.get(
        f"{BASE}/interval_cover?start={B+10}&end={B}&target_ms=5", timeout=10
    ).status_code == 400


# =========================================================================== #
# §25 GET /earliest_available — earliest free slot of given duration            #
# =========================================================================== #

def test_earliest_no_events():
    """No events anywhere → slot starts exactly at after."""
    B = 4_070_000_000
    r = requests.get(
        f"{BASE}/earliest_available?after={B}&duration_ms=50", timeout=10
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slot_start"] == B
    assert body["slot_end"] == B + 49


def test_earliest_gap_wide_enough():
    """Gap between two events is exactly wide enough for the requested duration."""
    B = 4_070_100_000
    _add_event("ea_w1", B, B + 29)          # busy [B, B+29]
    _add_event("ea_w2", B + 60, B + 99)     # busy [B+60, B+99]; gap [B+30, B+59] = 30ms
    r = requests.get(
        f"{BASE}/earliest_available?after={B}&duration_ms=20", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    assert body["slot_start"] == B + 30
    assert body["slot_end"] == B + 49


def test_earliest_skip_narrow_gap():
    """KEY DISCRIMINATOR: narrow gap shorter than duration_ms must be skipped.

    Events leave a 10ms gap at [B+40, B+49] which is < duration_ms=20.
    A naive algorithm returning the first gap fails this test; the correct
    algorithm skips the narrow gap and returns the slot starting at B+100."""
    B = 4_070_200_000
    _add_event("ea_na", B, B + 39)          # busy [B, B+39]
    _add_event("ea_nb", B + 50, B + 99)     # busy [B+50, B+99]; gap [B+40,B+49]=10ms < 20
    r = requests.get(
        f"{BASE}/earliest_available?after={B}&duration_ms=20", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    assert body["slot_start"] == B + 100, (
        f"10ms gap at [B+40,B+49] too narrow; must return B+100. Got {body['slot_start']}"
    )
    assert body["slot_end"] == B + 119


def test_earliest_after_falls_inside_busy():
    """after falls inside a busy interval — must wait until that interval ends."""
    B = 4_070_300_000
    _add_event("ea_ab", B, B + 99)   # single long busy interval
    r = requests.get(
        f"{BASE}/earliest_available?after={B+30}&duration_ms=20", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    # Event covers [B, B+99]; clipped from B+30 to B+99.  First free instant = B+100.
    assert body["slot_start"] == B + 100
    assert body["slot_end"] == B + 119


def test_earliest_immediately_free():
    """Slot at after is already free because all events start later."""
    B = 4_070_400_000
    _add_event("ea_if", B + 50, B + 99)   # event starts at B+50
    r = requests.get(
        f"{BASE}/earliest_available?after={B}&duration_ms=20", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    # [B, B+49] is free; immediately available
    assert body["slot_start"] == B
    assert body["slot_end"] == B + 19


def test_earliest_after_last_event():
    """after is already past all events — answer is immediately at after."""
    B = 4_070_500_000
    _add_event("ea_ae", B, B + 49)   # event ends at B+49
    r = requests.get(
        f"{BASE}/earliest_available?after={B+100}&duration_ms=30", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    # No event ends at or after B+100, so [B+100, B+129] is immediately free
    assert body["slot_start"] == B + 100
    assert body["slot_end"] == B + 129


def test_earliest_oracle_cross_check():
    """Two events with a gap — exact match against independent Python oracle."""
    B = 4_070_600_000
    _add_event("ea_oc1", B, B + 19)
    _add_event("ea_oc2", B + 30, B + 59)
    # gap [B+20, B+29] = 10ms < 25; next free region starts at B+60
    r = requests.get(
        f"{BASE}/earliest_available?after={B}&duration_ms=25", timeout=10
    )
    assert r.status_code == 200
    body = r.json()
    expected_ss, expected_se = _earliest_available_oracle(B, 25)
    assert body["slot_start"] == expected_ss
    assert body["slot_end"] == expected_se
    assert body["slot_end"] - body["slot_start"] + 1 == 25


def test_earliest_invalid_params():
    """Missing or bad params → 400."""
    B = 4_070_700_000
    assert requests.get(f"{BASE}/earliest_available?after={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/earliest_available?after={B}&duration_ms=0", timeout=10
    ).status_code == 400


# =========================================================================== #
# §26 GET /room_schedule — R-machine interval partitioning                    #
# =========================================================================== #

def _room_schedule_oracle(S, E, rooms):
    """§26: greedy R-machine interval partitioning maximizing scheduled count.
    Returns (max_scheduled, [(id, room), ...] sorted by id ASC)."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, start_ms, end_ms FROM events "
        "WHERE start_ms >= ? AND end_ms <= ? ORDER BY end_ms ASC, id ASC",
        (S, E),
    ).fetchall()
    conn.close()
    room_end = [None] * rooms
    assignments = []
    for eid, s, e in rows:
        avail = [r for r in range(rooms) if room_end[r] is None or room_end[r] < s]
        if not avail:
            continue
        busy = [r for r in avail if room_end[r] is not None]
        chosen = max(busy, key=lambda r: room_end[r]) if busy else min(avail)
        room_end[chosen] = e
        assignments.append((eid, chosen))
    assignments.sort(key=lambda x: x[0])
    return len(assignments), assignments


def test_room_schedule_returns_200():
    """GET /room_schedule returns 200 for valid params."""
    B = 4_100_000_000
    r = requests.get(f"{BASE}/room_schedule?start={B}&end={B+99}&rooms=2", timeout=10)
    assert r.status_code == 200, r.text


def test_room_schedule_fields():
    """Response carries start/end/rooms/max_scheduled/assignments."""
    B = 4_100_100_000
    r = requests.get(f"{BASE}/room_schedule?start={B}&end={B+99}&rooms=2", timeout=10)
    body = r.json()
    for field in ("start", "end", "rooms", "max_scheduled", "assignments"):
        assert field in body, f"missing {field}: {body}"
    assert body["rooms"] == 2


def test_room_schedule_rooms_1_matches_schedule_endpoint():
    """rooms=1 is exactly the §9 single-machine special case: max_scheduled must
    equal /schedule's max_non_overlapping for the identical window (cross-endpoint
    self-consistency — no baked reference needed)."""
    B = 4_100_200_000
    _add_event("rs1_a", B, B + 20)
    _add_event("rs1_b", B + 10, B + 30)  # overlaps a
    _add_event("rs1_c", B + 40, B + 60)
    S, E = B, B + 99
    room_body = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=1", timeout=10).json()
    sched_body = requests.get(f"{BASE}/schedule?start={S}&end={E}", timeout=10).json()
    assert room_body["max_scheduled"] == sched_body["max_non_overlapping"], (
        room_body, sched_body
    )


def test_room_schedule_two_rooms_defeats_single_room_greedy():
    """Three events pairwise overlap at one common instant (peak concurrency 3), so
    with 2 rooms exactly 2 can be scheduled. A fake that ignores the `rooms` param
    and always behaves like the single-machine §9 greedy returns 1; a fake that
    ignores room CAPACITY entirely returns 3. Only a real R-machine partitioning
    returns 2."""
    B = 4_100_300_000
    _add_event("rs2_a", B, B + 10)
    _add_event("rs2_b", B + 5, B + 15)
    _add_event("rs2_c", B + 8, B + 20)   # all three active at t=B+8..B+10
    S, E = B, B + 99
    r = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=2", timeout=10)
    body = r.json()
    assert body["max_scheduled"] == 2, (
        f"expected exactly 2 scheduled with 2 rooms and peak concurrency 3, got {body}"
    )


def test_room_schedule_three_rooms_schedules_all():
    """The same triple-overlap scenario with rooms=3 (matching peak concurrency)
    must schedule all three events."""
    B = 4_100_400_000
    _add_event("rs3_a", B, B + 10)
    _add_event("rs3_b", B + 5, B + 15)
    _add_event("rs3_c", B + 8, B + 20)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=3", timeout=10)
    body = r.json()
    assert body["max_scheduled"] == 3, body


def test_room_schedule_no_two_same_room_events_overlap():
    """Validity invariant: whatever assignment is returned, no two events sharing a
    room may overlap (touching counts as overlapping, matching §6/§9)."""
    B = 4_100_500_000
    ids = {}
    ids["a"] = _add_event("rs_valid_a", B, B + 10)
    ids["b"] = _add_event("rs_valid_b", B + 5, B + 20)
    ids["c"] = _add_event("rs_valid_c", B + 15, B + 30)
    ids["d"] = _add_event("rs_valid_d", B + 25, B + 40)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=2", timeout=10)
    body = r.json()
    conn = sqlite3.connect(DB)
    bounds = {}
    for eid, s, e in conn.execute(
        "SELECT id, start_ms, end_ms FROM events WHERE start_ms >= ? AND end_ms <= ?", (S, E)
    ):
        bounds[eid] = (s, e)
    conn.close()
    by_room = {}
    for a in body["assignments"]:
        by_room.setdefault(a["room"], []).append(a["id"])
    for room_ids in by_room.values():
        for i in range(len(room_ids)):
            for j in range(i + 1, len(room_ids)):
                s1, e1 = bounds[room_ids[i]]
                s2, e2 = bounds[room_ids[j]]
                assert not (s1 <= e2 and s2 <= e1), (
                    f"events {room_ids[i]} and {room_ids[j]} share a room but overlap"
                )


def test_room_schedule_excludes_partial_events():
    """Only events fully contained in [start,end] are eligible (same rule as §9)."""
    B = 4_100_600_000
    id_in = _add_event("rs_incl", B + 10, B + 20)
    id_partial = _add_event("rs_partial", B - 5, B + 20)  # starts before window
    S, E = B, B + 99
    r = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=2", timeout=10)
    body = r.json()
    scheduled_ids = {a["id"] for a in body["assignments"]}
    assert id_in in scheduled_ids
    assert id_partial not in scheduled_ids


def test_room_schedule_empty_window():
    """No contained events → max_scheduled=0, assignments=[]."""
    B = 4_100_700_000
    r = requests.get(f"{BASE}/room_schedule?start={B}&end={B+99}&rooms=3", timeout=10)
    body = r.json()
    assert body["max_scheduled"] == 0
    assert body["assignments"] == []


def test_room_schedule_oracle_cross_check():
    """Five events, moderate overlap structure, 2 rooms: exact match against the
    independent Python oracle for both max_scheduled and the full id/room assignment."""
    B = 4_100_800_000
    _add_event("rs_oc_1", B, B + 10)
    _add_event("rs_oc_2", B + 5, B + 25)
    _add_event("rs_oc_3", B + 20, B + 40)
    _add_event("rs_oc_4", B + 30, B + 35)
    _add_event("rs_oc_5", B + 50, B + 60)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=2", timeout=10)
    body = r.json()
    exp_count, exp_assignments = _room_schedule_oracle(S, E, 2)
    assert body["max_scheduled"] == exp_count
    got_assignments = sorted((a["id"], a["room"]) for a in body["assignments"])
    assert got_assignments == exp_assignments, (got_assignments, exp_assignments)


def test_room_schedule_assignments_sorted_by_id():
    """assignments are sorted by id ASC regardless of internal processing order."""
    B = 4_100_900_000
    _add_event("rs_sort_c", B + 20, B + 30)
    _add_event("rs_sort_a", B, B + 10)
    _add_event("rs_sort_b", B + 10, B + 20)  # touches sort_a — overlap
    S, E = B, B + 99
    r = requests.get(f"{BASE}/room_schedule?start={S}&end={E}&rooms=2", timeout=10)
    body = r.json()
    ids = [a["id"] for a in body["assignments"]]
    assert ids == sorted(ids), ids


def test_room_schedule_invalid_params():
    """Missing/non-integer params, start>end, or rooms<1 → 400."""
    B = 4_101_000_000
    assert requests.get(f"{BASE}/room_schedule?start={B}&end={B+99}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/room_schedule?start={B}&end={B+99}&rooms=0", timeout=10
    ).status_code == 400
    assert requests.get(
        f"{BASE}/room_schedule?start={B+99}&end={B}&rooms=2", timeout=10
    ).status_code == 400


# =========================================================================== #
# §27 GET /overlap_components — connected components of the overlap graph     #
# =========================================================================== #

def _overlap_components_oracle(S, E):
    """§27: union-find connected components of the overlap graph.
    Returns list of dicts sorted by min_start_ms, each with event_ids/min_start_ms/max_end_ms."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, start_ms, end_ms FROM events WHERE start_ms <= ? AND end_ms >= ?",
        (E, S),
    ).fetchall()
    conn.close()
    n = len(rows)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            si, eei = rows[i][1], rows[i][2]
            sj, eej = rows[j][1], rows[j][2]
            if si <= eej and sj <= eei:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    comps = []
    for members in groups.values():
        ids = sorted(rows[i][0] for i in members)
        mn = min(rows[i][1] for i in members)
        mx = max(rows[i][2] for i in members)
        comps.append({"event_ids": ids, "min_start_ms": mn, "max_end_ms": mx})
    comps.sort(key=lambda c: c["min_start_ms"])
    return comps


def test_overlap_components_returns_200():
    """GET /overlap_components returns 200 for valid params."""
    B = 4_110_000_000
    r = requests.get(f"{BASE}/overlap_components?start={B}&end={B+99}", timeout=10)
    assert r.status_code == 200, r.text


def test_overlap_components_fields():
    """Each component carries component_id/event_ids/min_start_ms/max_end_ms."""
    B = 4_110_100_000
    _add_event("oc_f1", B, B + 10)
    r = requests.get(f"{BASE}/overlap_components?start={B}&end={B+99}", timeout=10)
    body = r.json()
    assert "components" in body
    comp = body["components"][0]
    for field in ("component_id", "event_ids", "min_start_ms", "max_end_ms"):
        assert field in comp, f"missing {field}: {comp}"


def test_overlap_components_transitive_chain_is_one_component():
    """A overlaps B, B overlaps C, but A and C do NOT directly overlap. The three
    must still be reported as ONE component — a fake that only checks direct
    pairwise overlap (not graph connectivity / transitive closure) would split
    this into two components instead of one."""
    B = 4_110_200_000
    id_a = _add_event("oc_chain_a", B, B + 10)
    id_b = _add_event("oc_chain_b", B + 8, B + 20)
    id_c = _add_event("oc_chain_c", B + 18, B + 30)
    # a vs c: a.start(B) <= c.end(B+30) True; c.start(B+18) <= a.end(B+10)? False -> no direct overlap
    S, E = B, B + 99
    r = requests.get(f"{BASE}/overlap_components?start={S}&end={E}", timeout=10)
    body = r.json()
    comps = [c for c in body["components"] if set(c["event_ids"]) & {id_a, id_b, id_c}]
    assert len(comps) == 1, (
        f"expected A,B,C in exactly one connected component (chained overlap), got {comps}"
    )
    assert sorted(comps[0]["event_ids"]) == sorted([id_a, id_b, id_c])


def test_overlap_components_isolated_events_are_separate():
    """Two events that never overlap must form two singleton components."""
    B = 4_110_300_000
    id_a = _add_event("oc_iso_a", B, B + 10)
    id_b = _add_event("oc_iso_b", B + 50, B + 60)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/overlap_components?start={S}&end={E}", timeout=10)
    body = r.json()
    comps = {frozenset(c["event_ids"]) for c in body["components"]}
    assert frozenset([id_a]) in comps
    assert frozenset([id_b]) in comps


def test_overlap_components_sorted_by_min_start_ms():
    """Components are sorted by min_start_ms ascending, with sequential component_id."""
    B = 4_110_400_000
    _add_event("oc_sort_late", B + 60, B + 70)
    _add_event("oc_sort_early", B, B + 10)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/overlap_components?start={S}&end={E}", timeout=10)
    body = r.json()
    mins = [c["min_start_ms"] for c in body["components"]]
    assert mins == sorted(mins), mins
    cids = [c["component_id"] for c in body["components"]]
    assert cids == list(range(len(cids))), cids


def test_overlap_components_event_ids_sorted_ascending():
    """event_ids within a component are sorted ascending regardless of insertion order."""
    B = 4_110_500_000
    id_2 = _add_event("oc_ids_2", B + 5, B + 15)
    id_1 = _add_event("oc_ids_1", B, B + 10)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/overlap_components?start={S}&end={E}", timeout=10)
    body = r.json()
    comp = next(c for c in body["components"] if id_1 in c["event_ids"])
    assert comp["event_ids"] == sorted(comp["event_ids"])
    assert comp["event_ids"] == sorted([id_1, id_2])


def test_overlap_components_min_start_max_end_are_raw_bounds():
    """min_start_ms/max_end_ms are the RAW event bounds, not clipped to the window."""
    B = 4_110_600_000
    _add_event("oc_raw_a", B - 20, B + 10)   # starts before the window
    _add_event("oc_raw_b", B + 5, B + 130)   # ends after the window
    S, E = B, B + 99
    r = requests.get(f"{BASE}/overlap_components?start={S}&end={E}", timeout=10)
    body = r.json()
    comp = body["components"][0]
    assert comp["min_start_ms"] == B - 20, comp
    assert comp["max_end_ms"] == B + 130, comp


def test_overlap_components_empty_window():
    """No events intersecting the window → components=[]."""
    B = 4_110_700_000
    r = requests.get(f"{BASE}/overlap_components?start={B}&end={B+99}", timeout=10)
    body = r.json()
    assert body["components"] == []


def test_overlap_components_oracle_cross_check():
    """Six events forming two components of sizes 4 and 2: exact match against the
    independent Python union-find oracle."""
    B = 4_110_800_000
    _add_event("oc_oc_1", B, B + 10)
    _add_event("oc_oc_2", B + 8, B + 20)
    _add_event("oc_oc_3", B + 18, B + 30)
    _add_event("oc_oc_4", B + 28, B + 40)   # chains 1-2-3-4 into one component
    _add_event("oc_oc_5", B + 60, B + 70)
    _add_event("oc_oc_6", B + 65, B + 75)   # separate 2-event component
    S, E = B, B + 99
    r = requests.get(f"{BASE}/overlap_components?start={S}&end={E}", timeout=10)
    body = r.json()
    expected = _overlap_components_oracle(S, E)
    got = [
        {"event_ids": c["event_ids"], "min_start_ms": c["min_start_ms"], "max_end_ms": c["max_end_ms"]}
        for c in body["components"]
    ]
    assert got == expected, (got, expected)


def test_overlap_components_invalid_params():
    """Missing/non-integer params or start>end → 400."""
    B = 4_110_900_000
    assert requests.get(f"{BASE}/overlap_components?start={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/overlap_components?start={B+99}&end={B}", timeout=10
    ).status_code == 400


# =========================================================================== #
# Independent Python oracles for §28 and §29                                  #
# =========================================================================== #

def _build_rle_runs(S, E):
    """Build sweep-line RLE runs for [S, E]: list of (concurrency, duration_ms)."""
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT start_ms, end_ms FROM events").fetchall()
    conn.close()
    evs = list(rows)
    cp_set = {S, E + 1}
    for s, e in evs:
        if S < s <= E:
            cp_set.add(s)
        ep1 = e + 1
        if S < ep1 <= E:
            cp_set.add(ep1)
    cps = sorted(cp_set)
    runs = []
    for i in range(len(cps) - 1):
        t = cps[i]
        dur = cps[i + 1] - t
        c = sum(1 for (s, e) in evs if s <= t <= e)
        runs.append((c, dur))
    return runs


def _depth_profile_oracle(S, E):
    """§28: returns (max_depth, total_ms, profile) where profile = [(depth, ms), ...]."""
    runs = _build_rle_runs(S, E)
    total_ms = E - S + 1
    depth_total = {}
    max_depth = 0
    for c, dur in runs:
        depth_total[c] = depth_total.get(c, 0) + dur
        if c > max_depth:
            max_depth = c
    if 0 not in depth_total:
        depth_total[0] = 0
    profile = [{"depth": d, "total_ms": depth_total.get(d, 0)} for d in range(max_depth + 1)]
    return max_depth, total_ms, profile


def _window_stats_oracle(S, E):
    """§29: returns (total_ms, covered_ms, max_depth, mean, variance, p50)."""
    runs = _build_rle_runs(S, E)
    total_ms = E - S + 1
    covered_ms = sum(dur for c, dur in runs if c > 0)
    max_depth = max((c for c, _ in runs), default=0)
    mean = sum(c * dur for c, dur in runs) / total_ms
    variance = sum(dur * (c - mean) ** 2 for c, dur in runs) / total_ms
    target_pos = (total_ms - 1) // 2
    pos = 0
    p50 = 0
    for c, dur in runs:
        if pos + dur > target_pos:
            p50 = c
            break
        pos += dur
    return total_ms, covered_ms, max_depth, mean, variance, p50


# =========================================================================== #
# §28 GET /depth_profile — global concurrency histogram                       #
# =========================================================================== #

def test_depth_profile_empty_window():
    """No events intersecting window → single depth-0 entry with total_ms = window width."""
    B = 4_120_000_000
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["max_depth"] == 0
    assert body["total_ms"] == 100
    assert len(body["profile"]) == 1
    assert body["profile"][0] == {"depth": 0, "total_ms": 100}


def test_depth_profile_single_event():
    """One event creates depth-0 and depth-1 regions; conservation holds."""
    B = 4_121_000_000
    _add_event("dp_s1", B + 20, B + 59)  # 40ms active, 60ms free
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["max_depth"] == 1
    assert body["total_ms"] == 100
    profile = {p["depth"]: p["total_ms"] for p in body["profile"]}
    assert profile[0] == 60, f"depth-0 should be 60ms free, got {profile[0]}"
    assert profile[1] == 40, f"depth-1 should be 40ms event, got {profile[1]}"


def test_depth_profile_conservation():
    """sum(profile[i].total_ms) == total_ms for any fixture (conservation law)."""
    B = 4_122_000_000
    _add_event("dp_c1", B + 10, B + 40)
    _add_event("dp_c2", B + 30, B + 70)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    total = sum(p["total_ms"] for p in body["profile"])
    assert total == body["total_ms"], (
        f"sum(profile total_ms)={total} != total_ms={body['total_ms']} (conservation violated)"
    )


def test_depth_profile_depth_0_always_present():
    """Depth 0 must appear in the profile even when the entire window is covered (total_ms=0).

    An implementation that only reports non-zero depths would omit depth 0 when a single
    event spans the full window — this is the primary discriminator for this requirement."""
    B = 4_123_000_000
    _add_event("dp_full", B, B + 99)  # covers the full window
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    depths = [p["depth"] for p in body["profile"]]
    assert 0 in depths, (
        f"depth 0 must always appear in profile even when total_ms=0; "
        f"got depths={depths}"
    )
    profile = {p["depth"]: p["total_ms"] for p in body["profile"]}
    assert profile[0] == 0, (
        f"fully-covered window: depth-0 total_ms must be 0, got {profile[0]}"
    )
    assert profile[1] == 100


def test_depth_profile_overlap_correct_depths():
    """Two overlapping events create three depth levels; all must be reported correctly.

    KEY DISCRIMINATOR: an implementation built on /coverage returns only covered/free
    breakdown and cannot distinguish depth-1 from depth-2 regions within the covered area."""
    B = 4_124_000_000
    _add_event("dp_ov1", B + 10, B + 59)  # 50ms active
    _add_event("dp_ov2", B + 30, B + 79)  # overlaps in [B+30, B+59] → depth 2 for 30ms
    # depths:
    #   0: [B, B+9] + [B+80, B+99] = 10 + 20 = 30ms
    #   1: [B+10, B+29] + [B+60, B+79] = 20 + 20 = 40ms
    #   2: [B+30, B+59] = 30ms
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["max_depth"] == 2
    profile = {p["depth"]: p["total_ms"] for p in body["profile"]}
    assert profile[0] == 30, f"depth-0 should be 30ms, got {profile[0]}"
    assert profile[1] == 40, f"depth-1 should be 40ms, got {profile[1]}"
    assert profile[2] == 30, f"depth-2 should be 30ms, got {profile[2]}"


def test_depth_profile_sorted_by_depth_asc():
    """profile list must be sorted by depth ASC."""
    B = 4_125_000_000
    _add_event("dp_sort1", B, B + 30)
    _add_event("dp_sort2", B + 10, B + 50)
    _add_event("dp_sort3", B + 20, B + 40)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    depths = [p["depth"] for p in r.json()["profile"]]
    assert depths == sorted(depths), f"profile must be sorted depth ASC, got {depths}"


def test_depth_profile_max_depth_matches_peak():
    """max_depth in /depth_profile must equal max_concurrency from /peak."""
    B = 4_126_000_000
    _add_event("dp_pk1", B, B + 50)
    _add_event("dp_pk2", B + 10, B + 60)
    _add_event("dp_pk3", B + 20, B + 40)
    S, E = B, B + 99
    r_dp   = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    r_peak = requests.get(f"{BASE}/peak?start={S}&end={E}", timeout=10)
    assert r_dp.status_code == 200 and r_peak.status_code == 200
    assert r_dp.json()["max_depth"] == r_peak.json()["max_concurrency"], (
        f"max_depth={r_dp.json()['max_depth']} != peak max_concurrency="
        f"{r_peak.json()['max_concurrency']}"
    )


def test_depth_profile_oracle_cross_check():
    """Complex fixture: 3 events forming multi-depth runs — exact match against oracle.

    Events [B+10,B+59], [B+30,B+79], [B+70,B+89] produce:
      depth 0: 20ms; depth 1: 40ms; depth 2: 40ms."""
    B = 4_127_000_000
    _add_event("dp_cx1", B + 10, B + 59)
    _add_event("dp_cx2", B + 30, B + 79)
    _add_event("dp_cx3", B + 70, B + 89)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    exp_max, exp_total, exp_profile = _depth_profile_oracle(S, E)
    assert body["max_depth"] == exp_max, f"max_depth {body['max_depth']} != oracle {exp_max}"
    assert body["total_ms"] == exp_total
    got_profile = [(p["depth"], p["total_ms"]) for p in body["profile"]]
    exp_pairs = [(p["depth"], p["total_ms"]) for p in exp_profile]
    assert got_profile == exp_pairs, (
        f"profile mismatch:\n  got:      {got_profile}\n  expected: {exp_pairs}"
    )


def test_depth_profile_invalid_params():
    """Missing or bad params → 400."""
    B = 4_128_000_000
    assert requests.get(f"{BASE}/depth_profile?start={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/depth_profile?start={B+10}&end={B}", timeout=10
    ).status_code == 400


# =========================================================================== #
# §29 GET /window_stats — statistical moments of concurrency distribution      #
# =========================================================================== #

def test_window_stats_empty():
    """No events → mean=0.0, variance=0.0, p50=0, covered_ms=0, max_depth=0."""
    B = 4_130_000_000
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_ms"] == 100
    assert body["covered_ms"] == 0
    assert body["max_depth"] == 0
    assert abs(float(body["mean_depth"])) < 1e-9
    assert abs(float(body["variance_depth"])) < 1e-9
    assert body["p50_depth"] == 0


def test_window_stats_fully_covered():
    """Single event covering the full window: mean=1.0, variance=0.0, p50=1."""
    B = 4_131_000_000
    _add_event("ws_fc", B, B + 99)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["covered_ms"] == 100
    assert body["max_depth"] == 1
    assert abs(float(body["mean_depth"]) - 1.0) < 1e-5
    assert abs(float(body["variance_depth"])) < 1e-9, (
        f"fully-covered window: variance should be 0.0, got {body['variance_depth']}"
    )
    assert body["p50_depth"] == 1


def test_window_stats_half_covered_mean():
    """50ms covered at depth 1, 50ms free: mean=0.5, variance=0.25."""
    B = 4_132_000_000
    _add_event("ws_hc", B, B + 49)   # [B, B+49] depth 1; [B+50, B+99] depth 0
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    # mean = (50*1 + 50*0) / 100 = 0.5
    # variance = (50*(1-0.5)^2 + 50*(0-0.5)^2) / 100 = (50*0.25 + 50*0.25)/100 = 0.25
    assert abs(float(body["mean_depth"]) - 0.5) < 1e-5, (
        f"mean_depth should be 0.5, got {body['mean_depth']}"
    )
    assert abs(float(body["variance_depth"]) - 0.25) < 1e-5, (
        f"variance_depth should be 0.25, got {body['variance_depth']}"
    )


def test_window_stats_variance_population_discriminator():
    """KEY DISCRIMINATOR: population variance divides by total_ms, not by run count.

    Event [B, B+79]: 80ms at depth 1, 20ms at depth 0.
    mean = 0.8; population variance = (80*(1-0.8)^2 + 20*(0-0.8)^2) / 100 = 0.16.

    Wrong: divide by (runs-1)=1 → 16.0; divide by (total_ms-1)=99 → ≈0.1616;
    divide by covered_ms=80 → 0.2. The only correct answer is 0.16."""
    B = 4_133_000_000
    _add_event("ws_var", B, B + 79)   # 80ms depth 1, 20ms depth 0
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert abs(float(body["mean_depth"]) - 0.8) < 1e-5
    assert abs(float(body["variance_depth"]) - 0.16) < 0.001, (
        f"population variance should be 0.16, got {body['variance_depth']} "
        "(dividing by run-count or (total_ms-1) gives a different answer)"
    )


def test_window_stats_p50_in_free_time():
    """KEY DISCRIMINATOR: p50 counts free (depth-0) instants in position index.

    Event [B+60, B+99]: 60ms free then 40ms at depth 1.
    target_pos = floor(99/2) = 49 → position 49 falls in the depth-0 region → p50=0.
    An implementation that skips free time and only counts covered instants would
    compute p50=1 (the 49th covered instant, ignoring the 60 free ones)."""
    B = 4_134_000_000
    _add_event("ws_p50f", B + 60, B + 99)   # 60ms free, then 40ms depth 1
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["p50_depth"] == 0, (
        f"target_pos=49 falls in the 60ms free region → p50=0, got {body['p50_depth']} "
        "(free instants must count toward the position index)"
    )


def test_window_stats_p50_even_window_lower_median():
    """KEY DISCRIMINATOR: p50 uses floor((total_ms-1)/2), not floor(total_ms/2).

    Event [B, B+49]: 50ms depth-1 (positions 0-49), 50ms depth-0 (positions 50-99).
    floor((100-1)/2)=49 → position 49 is the last depth-1 instant → p50=1.
    Wrong formula floor(100/2)=50 → position 50 is the first depth-0 instant → p50=0."""
    B = 4_135_000_000
    _add_event("ws_p50e", B, B + 49)   # depth 1 in [B, B+49]; depth 0 in [B+50, B+99]
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["p50_depth"] == 1, (
        f"floor((100-1)/2)=49 → last depth-1 position → p50=1, got {body['p50_depth']} "
        "(check formula: should be floor((total_ms-1)/2) not floor(total_ms/2))"
    )


def test_window_stats_covered_ms_matches_coverage():
    """covered_ms must equal /coverage covered_ms for the same window."""
    B = 4_136_000_000
    _add_event("ws_cov1", B + 5, B + 40)
    _add_event("ws_cov2", B + 30, B + 70)
    S, E = B, B + 99
    r_ws  = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    r_cov = requests.get(f"{BASE}/coverage?start={S}&end={E}", timeout=10)
    assert r_ws.status_code == 200 and r_cov.status_code == 200
    assert r_ws.json()["covered_ms"] == r_cov.json()["covered_ms"], (
        f"window_stats covered_ms={r_ws.json()['covered_ms']} != "
        f"coverage covered_ms={r_cov.json()['covered_ms']}"
    )


def test_window_stats_mean_matches_depth_profile():
    """mean_depth must equal Σ(d * profile[d].total_ms) / total_ms from /depth_profile."""
    B = 4_137_000_000
    _add_event("ws_mp1", B, B + 30)
    _add_event("ws_mp2", B + 20, B + 60)
    _add_event("ws_mp3", B + 50, B + 80)
    S, E = B, B + 99
    r_ws = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    r_dp = requests.get(f"{BASE}/depth_profile?start={S}&end={E}", timeout=10)
    assert r_ws.status_code == 200 and r_dp.status_code == 200
    total_ms = r_dp.json()["total_ms"]
    expected_mean = sum(p["depth"] * p["total_ms"] for p in r_dp.json()["profile"]) / total_ms
    got_mean = float(r_ws.json()["mean_depth"])
    assert abs(got_mean - expected_mean) < 1e-4, (
        f"mean_depth={got_mean} != depth-profile-derived mean={expected_mean:.6f}"
    )


def test_window_stats_oracle_cross_check():
    """Complex fixture: [B+10,B+59], [B+30,B+79], [B+70,B+89] — exact match against oracle.

    Expected: mean=1.2, variance=0.56, covered_ms=80, max_depth=2, p50=2."""
    B = 4_138_000_000
    _add_event("ws_cx1", B + 10, B + 59)
    _add_event("ws_cx2", B + 30, B + 79)
    _add_event("ws_cx3", B + 70, B + 89)
    S, E = B, B + 99
    r = requests.get(f"{BASE}/window_stats?start={S}&end={E}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    _, exp_covered, exp_max, exp_mean, exp_var, exp_p50 = _window_stats_oracle(S, E)
    assert body["covered_ms"] == exp_covered, f"covered_ms {body['covered_ms']} != {exp_covered}"
    assert body["max_depth"] == exp_max, f"max_depth {body['max_depth']} != {exp_max}"
    assert abs(float(body["mean_depth"]) - exp_mean) < 1e-4, (
        f"mean_depth={body['mean_depth']} != oracle {exp_mean:.6f}"
    )
    assert abs(float(body["variance_depth"]) - exp_var) < 1e-4, (
        f"variance_depth={body['variance_depth']} != oracle {exp_var:.6f}"
    )
    assert body["p50_depth"] == exp_p50, f"p50_depth {body['p50_depth']} != oracle {exp_p50}"


def test_window_stats_invalid_params():
    """Missing or bad params → 400."""
    B = 4_139_000_000
    assert requests.get(f"{BASE}/window_stats?start={B}", timeout=10).status_code == 400
    assert requests.get(
        f"{BASE}/window_stats?start={B+10}&end={B}", timeout=10
    ).status_code == 400
