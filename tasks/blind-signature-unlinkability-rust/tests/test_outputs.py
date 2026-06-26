"""Tests for the Blind Signature Unlinkability Verifier.

Expected values are derived from settings.toml and the transcript using the
specified model (polynomial hash, similarity correlation, clamped timing,
greedy one-to-one adversary matching, entropy in bits, population batch std).
An independent reference is embedded; tests assert concrete values and
cross-consistency without pointing at any source location.
"""
import json
import math
import subprocess
from pathlib import Path

REPORT = Path("/app/output/verification_report.json")
BINARY = "/app/target/release/blind-signature-unlinkability"
TRANSCRIPT = Path("/app/data/transcript.json")
ARGS = ["--config-dir", "/app/config", "--data-file", "/app/data/transcript.json",
        "--output", "/app/output/verification_report.json"]

PRIME = 65521
DETECTION = 0.30
MIN_UNLINK = 0.40
SEC_BITS = 8
TIMING_W = 0.15
ENTROPY_THRESH = 3.5
MAX_STD = 0.25
SUSPICIOUS = 0.7
TOL = 1e-5


def r6(v):
    return round(v, 6)


def phash(s):
    h = 0
    for b in s.encode():
        h = (h * 33 + b) % PRIME
    return h


def reference(data):
    sess, sigs = data["signing_sessions"], data["issued_signatures"]
    md = data["parameters"]["max_timing_delta"]
    pairs = []
    for i, s in enumerate(sess):
        for j, g in enumerate(sigs):
            corr = r6(1.0 - abs(phash(s["blinded_msg"]) - phash(g["message"])) / (PRIME - 1))
            timing = r6(max(0.0, 1.0 - abs(s["timestamp"] - g["timestamp"]) / md))
            combined = r6((1 - TIMING_W) * corr + TIMING_W * timing)
            pairs.append(dict(i=i, j=j, sid=s["id"], gid=g["id"], corr=corr,
                              timing=timing, combined=combined, detected=corr > DETECTION))
    order = sorted(pairs, key=lambda p: (-p["corr"], p["i"], p["j"]))
    us, ug, matched = set(), set(), []
    for p in order:
        if p["i"] in us or p["j"] in ug:
            continue
        us.add(p["i"])
        ug.add(p["j"])
        matched.append(p)
        if len(matched) >= min(len(sess), len(sigs)):
            break
    adv = r6(sum(p["corr"] for p in matched) / len(matched))
    bins = [0] * 10
    for p in pairs:
        bins[min(int(p["corr"] * 10), 9)] += 1
    ent = -sum((c / len(pairs)) * math.log2(c / len(pairs)) for c in bins if c > 0)
    smax = [r6(max(p["corr"] for p in pairs if p["i"] == i)) for i in range(len(sess))]
    mean_smax = sum(smax) / len(smax)
    std = math.sqrt(sum((x - mean_smax) ** 2 for x in smax) / len(smax))
    # KS test
    n = len(pairs)
    sorted_corrs = sorted(p["corr"] for p in pairs)
    ks_stat = 0.0
    for idx, sc in enumerate(sorted_corrs):
        emp = (idx + 1) / n
        emp_left = idx / n
        ks_stat = max(ks_stat, abs(emp - sc), abs(emp_left - sc))
    ks_cv = 1.36 / math.sqrt(n)
    # Commitment strength
    matched_scores = sorted(p["corr"] for p in matched)
    matched_mean = sum(p["corr"] for p in matched) / len(matched)
    all_mean = sum(p["corr"] for p in pairs) / len(pairs)
    strength_ratio = matched_mean / all_mean if all_mean > 0 else 0.0
    nm = len(matched_scores)
    p95_idx = math.ceil(0.95 * nm) - 1
    p95_idx = max(0, min(p95_idx, nm - 1))
    p95_corr = matched_scores[p95_idx]
    conf_bound = math.sqrt(strength_ratio * p95_corr)
    return dict(
        pairs=pairs, matched=matched,
        total=len(pairs), flagged=sum(1 for p in pairs if p["detected"]),
        advantage=adv, unlink=r6(1 - 2 * adv),
        avg_combined=r6(sum(p["combined"] for p in pairs) / len(pairs)),
        max_combined=r6(max(p["combined"] for p in pairs)),
        suspicious=sum(1 for p in pairs if p["combined"] > SUSPICIOUS),
        entropy=r6(ent), smax=smax, std=r6(std),
        sec_bits=r6(-math.log2(adv)) if adv > 0 else float(SEC_BITS),
        matched_linkable=sum(1 for p in matched if p["corr"] > DETECTION),
        mean_all=r6(sum(p["corr"] for p in pairs) / len(pairs)),
        ks_stat=r6(ks_stat), ks_cv=r6(ks_cv), ks_uniform=ks_stat <= ks_cv,
        strength_ratio=r6(strength_ratio), p95_corr=r6(p95_corr),
        conf_bound=r6(conf_bound),
    )


def load_report():
    return json.loads(REPORT.read_text())


def transcript():
    return json.loads(TRANSCRIPT.read_text())


# ── Structure ───────────────────────────────────────────────────────────────


def test_report_exists():
    """The verification report must exist."""
    assert REPORT.exists()


def test_report_has_required_keys():
    """Report must contain all required top-level keys."""
    report = load_report()
    required = {"summary", "matching", "pair_analysis", "timing_analysis",
                "entropy_assessment", "batch_consistency", "ks_test",
                "commitment", "security", "settings_used"}
    assert required.issubset(report.keys()), f"Missing: {required - report.keys()}"


def test_total_pairs():
    """total_pairs = sessions * signatures = 30."""
    assert load_report()["summary"]["total_pairs"] == 30


def test_pair_analysis_count():
    """pair_analysis must list every pair."""
    assert len(load_report()["pair_analysis"]) == 30


def test_flagged_pairs():
    """flagged_pairs counts pairs with correlation_score > detection_threshold."""
    assert load_report()["summary"]["flagged_pairs"] == reference(transcript())["flagged"]


# ── Settings authority ──────────────────────────────────────────────────────


def test_detection_threshold_setting():
    """detection_threshold is 0.3 from settings.toml (not a profile value)."""
    assert load_report()["settings_used"]["detection_threshold"] == 0.3


def test_security_level_required():
    """security_level_bits is 8 from settings.toml, not 128 from profiles."""
    assert load_report()["security"]["security_level_required"] == 8


def test_timing_weight_setting():
    """timing_weight is 0.15 from settings.toml, not 0.35 from profiles."""
    assert load_report()["settings_used"]["timing_weight"] == 0.15


def test_entropy_threshold_setting():
    """entropy_threshold is 3.5 from settings.toml, not 4.8 from profiles."""
    assert load_report()["settings_used"]["entropy_threshold"] == 3.5


def test_min_unlinkability_setting():
    """min_unlinkability_score is 0.4 from settings.toml."""
    assert load_report()["settings_used"]["min_unlinkability_score"] == 0.4


# ── Correlation / detection ─────────────────────────────────────────────────


def test_correlation_is_similarity():
    """Correlation is a similarity in (0,1]; the most-correlated pair scores high."""
    report = load_report()
    ref = reference(transcript())
    mx = max(p["correlation_score"] for p in report["pair_analysis"])
    assert math.isclose(mx, max(p["corr"] for p in ref["pairs"]), abs_tol=TOL)
    assert 0.0 < mx <= 1.0


def test_correlation_values_match_reference():
    """Every per-pair correlation matches the polynomial-hash similarity model."""
    report = load_report()
    ref = {(p["sid"], p["gid"]): p["corr"] for p in reference(transcript())["pairs"]}
    for p in report["pair_analysis"]:
        assert math.isclose(p["correlation_score"], ref[(p["session_id"], p["signature_id"])], abs_tol=TOL)


def test_detection_is_strictly_above_threshold():
    """correlation_detected is true exactly when correlation_score > threshold."""
    for p in load_report()["pair_analysis"]:
        assert p["correlation_detected"] == (p["correlation_score"] > DETECTION)


# ── Timing / combined ───────────────────────────────────────────────────────


def test_timing_proximity_clamped_nonnegative():
    """timing_proximity is clamped at 0; with this data some pairs hit exactly 0."""
    proximities = [p["timing_proximity"] for p in load_report()["pair_analysis"]]
    assert all(x >= 0.0 for x in proximities)
    assert any(abs(x) < 1e-9 for x in proximities), "expected at least one clamped (0.0) timing"


def test_combined_score_blend():
    """combined_score = (1-w)*correlation + w*timing for every pair (weights not swapped)."""
    for p in load_report()["pair_analysis"]:
        expected = r6((1 - TIMING_W) * p["correlation_score"] + TIMING_W * p["timing_proximity"])
        assert math.isclose(p["combined_score"], expected, abs_tol=TOL)


def test_combined_weights_not_swapped():
    """The correlation channel must dominate the timing channel (weight 0.85 vs 0.15)."""
    report = load_report()
    p = max(report["pair_analysis"], key=lambda q: abs(q["correlation_score"] - q["timing_proximity"]))
    correct = (1 - TIMING_W) * p["correlation_score"] + TIMING_W * p["timing_proximity"]
    swapped = TIMING_W * p["correlation_score"] + (1 - TIMING_W) * p["timing_proximity"]
    assert abs(p["combined_score"] - r6(correct)) < TOL
    assert abs(p["combined_score"] - r6(swapped)) > TOL


# ── Timing analysis ─────────────────────────────────────────────────────────


def test_max_combined_is_maximum():
    """max_combined_score is the maximum combined score (not the minimum)."""
    report = load_report()
    combined = [p["combined_score"] for p in report["pair_analysis"]]
    assert math.isclose(report["timing_analysis"]["max_combined_score"], max(combined), abs_tol=TOL)
    assert report["timing_analysis"]["max_combined_score"] > min(combined)


def test_average_combined():
    """average_combined_score is the mean over all pairs."""
    report = load_report()
    assert math.isclose(report["timing_analysis"]["average_combined_score"],
                        reference(transcript())["avg_combined"], abs_tol=TOL)


def test_suspicious_uses_combined_not_correlation():
    """timing_suspicious_pairs counts combined_score > 0.7, not correlation_score > 0.7."""
    report = load_report()
    ref = reference(transcript())
    by_combined = sum(1 for p in report["pair_analysis"] if p["combined_score"] > SUSPICIOUS)
    by_corr = sum(1 for p in report["pair_analysis"] if p["correlation_score"] > SUSPICIOUS)
    assert report["timing_analysis"]["timing_suspicious_pairs"] == by_combined == ref["suspicious"]
    assert by_combined != by_corr


# ── Matching ────────────────────────────────────────────────────────────────


def test_matching_one_to_one():
    """matched_pairs must be a one-to-one assignment: distinct sessions AND distinct signatures."""
    matched = load_report()["matching"]["matched_pairs"]
    t = transcript()
    expected_len = min(len(t["signing_sessions"]), len(t["issued_signatures"]))
    assert len(matched) == expected_len
    assert len({m["session_id"] for m in matched}) == expected_len
    assert len({m["signature_id"] for m in matched}) == expected_len


def test_matching_greedy_descending_order():
    """Committed edges are taken in descending correlation order; the first match
    is the globally most-correlated pair."""
    report = load_report()
    matched = report["matching"]["matched_pairs"]
    scores = [m["correlation_score"] for m in matched]
    assert scores == sorted(scores, reverse=True)
    global_max = max(p["correlation_score"] for p in report["pair_analysis"])
    assert math.isclose(matched[0]["correlation_score"], global_max, abs_tol=TOL)


def test_matching_pairs_match_reference():
    """The committed edges (ids and scores, in order) match the greedy reference."""
    report = load_report()
    ref = reference(transcript())["matched"]
    got = report["matching"]["matched_pairs"]
    assert len(got) == len(ref)
    for g, e in zip(got, ref):
        assert g["session_id"] == e["sid"]
        assert g["signature_id"] == e["gid"]
        assert math.isclose(g["correlation_score"], e["corr"], abs_tol=TOL)


def test_advantage_is_mean_of_matched_not_all_pairs():
    """distinguishing_advantage is the mean over matched edges, NOT the mean over
    all pairs, and not the global maximum."""
    report = load_report()
    ref = reference(transcript())
    assert math.isclose(report["summary"]["distinguishing_advantage"], ref["advantage"], abs_tol=TOL)
    assert abs(ref["advantage"] - ref["mean_all"]) > 1e-3
    assert not math.isclose(report["summary"]["distinguishing_advantage"], ref["mean_all"], abs_tol=1e-3)


def test_matched_linkable():
    """matched_linkable counts committed edges above the detection threshold."""
    report = load_report()
    assert report["matching"]["matched_linkable"] == reference(transcript())["matched_linkable"]


# ── Summary / security ──────────────────────────────────────────────────────


def test_unlinkability_score():
    """unlinkability_score = 1 - 2 * distinguishing_advantage."""
    report = load_report()
    adv = report["summary"]["distinguishing_advantage"]
    assert math.isclose(report["summary"]["unlinkability_score"], r6(1 - 2 * adv), abs_tol=TOL)


def test_is_unlinkable():
    """is_unlinkable iff unlinkability_score >= min_unlinkability_score (0.4)."""
    report = load_report()
    assert report["summary"]["is_unlinkable"] == (report["summary"]["unlinkability_score"] >= MIN_UNLINK)


def test_security_bits_achieved():
    """security_bits_achieved = -log2(distinguishing_advantage)."""
    report = load_report()
    assert math.isclose(report["security"]["security_bits_achieved"],
                        reference(transcript())["sec_bits"], abs_tol=TOL)


def test_security_bits_positive_when_advantage_below_one():
    """With advantage in (0,1), -log2(advantage) is positive."""
    report = load_report()
    assert report["security"]["security_bits_achieved"] > 0.0


def test_meets_security_level():
    """meets_security_level iff security_bits_achieved >= security_level_bits."""
    report = load_report()
    bits = report["security"]["security_bits_achieved"]
    assert report["security"]["meets_security_level"] == (bits >= SEC_BITS)


# ── Entropy ─────────────────────────────────────────────────────────────────


def test_correlation_entropy_bits():
    """correlation_entropy uses base-2 logarithm (bits), 10 equal-width bins."""
    report = load_report()
    assert math.isclose(report["entropy_assessment"]["correlation_entropy"],
                        reference(transcript())["entropy"], abs_tol=TOL)


def test_entropy_sufficient():
    """entropy_sufficient iff entropy >= threshold."""
    report = load_report()
    e = report["entropy_assessment"]
    assert e["entropy_sufficient"] == (e["correlation_entropy"] >= ENTROPY_THRESH)


# ── Batch consistency ───────────────────────────────────────────────────────


def test_session_max_scores_use_max():
    """session_max_scores are per-session MAXIMUM correlations, ordered by session."""
    report = load_report()
    assert report["batch_consistency"]["session_max_scores"] == reference(transcript())["smax"]


def test_batch_std_is_population():
    """batch_std_deviation is the population std (divide by N) of session_max_scores."""
    report = load_report()
    assert math.isclose(report["batch_consistency"]["batch_std_deviation"],
                        reference(transcript())["std"], abs_tol=TOL)


def test_batch_is_consistent():
    """is_consistent iff batch_std_deviation < max_std_deviation (0.25)."""
    report = load_report()
    b = report["batch_consistency"]
    assert b["is_consistent"] == (b["batch_std_deviation"] < MAX_STD)


# ── KS uniformity test ──────────────────────────────────────────────────────


def test_ks_statistic_value():
    """KS statistic must match the reference two-sided KS computation."""
    report = load_report()
    ref = reference(transcript())
    assert math.isclose(report["ks_test"]["ks_statistic"], ref["ks_stat"], abs_tol=TOL)


def test_ks_critical_value_uses_sqrt_n():
    """Critical value is 1.36/sqrt(N) where N=30 pairs, NOT sqrt(N+1)."""
    report = load_report()
    expected_cv = r6(1.36 / math.sqrt(30))
    wrong_cv = r6(1.36 / math.sqrt(31))
    assert math.isclose(report["ks_test"]["critical_value"], expected_cv, abs_tol=TOL)
    assert not math.isclose(report["ks_test"]["critical_value"], wrong_cv, abs_tol=TOL)


def test_ks_is_uniform():
    """is_uniform iff ks_statistic <= critical_value."""
    report = load_report()
    ks = report["ks_test"]
    assert ks["is_uniform"] == (ks["ks_statistic"] <= ks["critical_value"])


# ── Commitment strength ─────────────────────────────────────────────────────


def test_commitment_strength_ratio():
    """strength_ratio = matched_mean / all_pairs_mean."""
    report = load_report()
    ref = reference(transcript())
    assert math.isclose(report["commitment"]["strength_ratio"], ref["strength_ratio"], abs_tol=TOL)


def test_commitment_p95_correlation():
    """p95_correlation uses ceil-based index into sorted matched scores."""
    report = load_report()
    ref = reference(transcript())
    assert math.isclose(report["commitment"]["p95_correlation"], ref["p95_corr"], abs_tol=TOL)


def test_commitment_confidence_bound():
    """confidence_bound = sqrt(strength_ratio * p95_correlation)."""
    report = load_report()
    ref = reference(transcript())
    assert math.isclose(report["commitment"]["confidence_bound"], ref["conf_bound"], abs_tol=TOL)


# ── Whole-report independent recompute ──────────────────────────────────────


def test_full_independent_recompute():
    """All scalar metrics match the independent reference model."""
    report = load_report()
    ref = reference(transcript())
    assert report["summary"]["total_pairs"] == ref["total"]
    assert report["summary"]["flagged_pairs"] == ref["flagged"]
    assert math.isclose(report["summary"]["distinguishing_advantage"], ref["advantage"], abs_tol=TOL)
    assert math.isclose(report["summary"]["unlinkability_score"], ref["unlink"], abs_tol=TOL)
    assert math.isclose(report["timing_analysis"]["average_combined_score"], ref["avg_combined"], abs_tol=TOL)
    assert math.isclose(report["timing_analysis"]["max_combined_score"], ref["max_combined"], abs_tol=TOL)
    assert report["timing_analysis"]["timing_suspicious_pairs"] == ref["suspicious"]
    assert math.isclose(report["entropy_assessment"]["correlation_entropy"], ref["entropy"], abs_tol=TOL)
    assert math.isclose(report["batch_consistency"]["batch_std_deviation"], ref["std"], abs_tol=TOL)
    assert math.isclose(report["security"]["security_bits_achieved"], ref["sec_bits"], abs_tol=TOL)
    assert math.isclose(report["ks_test"]["ks_statistic"], ref["ks_stat"], abs_tol=TOL)
    assert math.isclose(report["commitment"]["strength_ratio"], ref["strength_ratio"], abs_tol=TOL)


# ── CLI / determinism ───────────────────────────────────────────────────────


def test_cli_no_args_nonzero():
    """CLI must exit non-zero when called with no arguments."""
    assert subprocess.run([BINARY], capture_output=True).returncode != 0


def test_deterministic_output():
    """Output must be identical across repeated runs."""
    subprocess.run([BINARY] + ARGS, capture_output=True)
    first = REPORT.read_text()
    subprocess.run([BINARY] + ARGS, capture_output=True)
    assert REPORT.read_text() == first


# ── Dynamic alternate-input test ────────────────────────────────────────────


def test_below_threshold_pair_not_flagged(tmp_path):
    """On a crafted transcript with a low-correlation pair, that pair must NOT be
    flagged, and the report must match the reference model end-to-end."""
    data = {
        "signing_sessions": [
            {"id": "s1", "blinded_msg": "msg_10", "signature": "b1", "timestamp": 1000, "nonce": "n1"},
            {"id": "s2", "blinded_msg": "msg_0", "signature": "b2", "timestamp": 1100, "nonce": "n2"},
        ],
        "issued_signatures": [
            {"id": "g1", "message": "x", "signature": "i1", "timestamp": 1010, "verifier": "v"},
            {"id": "g2", "message": "msg_1", "signature": "i2", "timestamp": 1120, "verifier": "v"},
        ],
        "parameters": {"security_level_bits": 8, "max_advantage": 0.5, "max_timing_delta": 250},
    }
    inp = str(tmp_path / "t.json")
    outp = str(tmp_path / "o.json")
    Path(inp).write_text(json.dumps(data))
    r = subprocess.run([BINARY, "--config-dir", "/app/config", "--data-file", inp, "--output", outp],
                       capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    out = json.loads(Path(outp).read_text())
    ref = reference(data)
    low = next(p for p in out["pair_analysis"] if p["session_id"] == "s1" and p["signature_id"] == "g1")
    assert low["correlation_score"] < DETECTION
    assert low["correlation_detected"] is False
    assert out["summary"]["flagged_pairs"] == ref["flagged"]
    got_matched = [(m["session_id"], m["signature_id"]) for m in out["matching"]["matched_pairs"]]
    exp_matched = [(m["sid"], m["gid"]) for m in ref["matched"]]
    assert got_matched == exp_matched
    assert math.isclose(out["summary"]["distinguishing_advantage"], ref["advantage"], abs_tol=TOL)


def test_ks_on_alternate_input(tmp_path):
    """KS test on a small 2x2 transcript must use sqrt(N) not sqrt(N+1)."""
    data = {
        "signing_sessions": [
            {"id": "s1", "blinded_msg": "abc", "signature": "b1", "timestamp": 100, "nonce": "n1"},
            {"id": "s2", "blinded_msg": "xyz", "signature": "b2", "timestamp": 200, "nonce": "n2"},
        ],
        "issued_signatures": [
            {"id": "g1", "message": "abc", "signature": "i1", "timestamp": 110, "verifier": "v"},
            {"id": "g2", "message": "zzz", "signature": "i2", "timestamp": 210, "verifier": "v"},
        ],
        "parameters": {"security_level_bits": 8, "max_advantage": 0.5, "max_timing_delta": 500},
    }
    inp = str(tmp_path / "t.json")
    outp = str(tmp_path / "o.json")
    Path(inp).write_text(json.dumps(data))
    r = subprocess.run([BINARY, "--config-dir", "/app/config", "--data-file", inp, "--output", outp],
                       capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    out = json.loads(Path(outp).read_text())
    # 4 pairs -> cv = 1.36/sqrt(4) = 0.68, NOT 1.36/sqrt(5) = 0.608...
    expected_cv = r6(1.36 / math.sqrt(4))
    wrong_cv = r6(1.36 / math.sqrt(5))
    assert math.isclose(out["ks_test"]["critical_value"], expected_cv, abs_tol=TOL)
    assert not math.isclose(out["ks_test"]["critical_value"], wrong_cv, abs_tol=TOL)
