import hashlib
import json
import os
import subprocess

OUTPUT_PATH = "/app/output/expected.json"
BINARY_PATH = "/app/bin/keyshare_witness"
SHARD_PATHS = [
    "/app/data/handshake_capture/h_pre_rollout.ndjson",
    "/app/data/handshake_capture/h_mid_rollout.ndjson",
    "/app/data/handshake_capture/h_late_rollout.ndjson",
]

VERDICT_SET = [
    "HYBRID_PQ_OK",
    "CLASSIC_OK",
    "DEPRECATED_GRACE",
    "PRE_ROLLOUT_PASS",
    "SEAL_RESCUED",
    "POLICY_DOWNGRADE_BLOCKED",
    "GROUP_BANNED",
    "RATE_LIMITED",
    "QUOTA_EXHAUSTED",
    "REJECTED_TYPE",
    "UNKNOWN_SERVICE",
    "INVALID",
]

VERDICT_SEVERITY_HIGH_TO_LOW = [
    "REJECTED_TYPE",
    "INVALID",
    "UNKNOWN_SERVICE",
    "GROUP_BANNED",
    "QUOTA_EXHAUSTED",
    "POLICY_DOWNGRADE_BLOCKED",
    "RATE_LIMITED",
    "SEAL_RESCUED",
    "DEPRECATED_GRACE",
    "CLASSIC_OK",
    "HYBRID_PQ_OK",
    "PRE_ROLLOUT_PASS",
]


def _load():
    with open(OUTPUT_PATH) as fh:
        return json.load(fh)


def _decision_for(obs_id):
    report = _load()
    for d in report["decisions"]:
        if d["observation_id"] == obs_id:
            return d
    raise AssertionError(f"missing decision for {obs_id}")


def test_output_file_exists_at_pinned_path():
    """The witness writes /app/output/expected.json and the file is non-empty."""
    assert os.path.exists(OUTPUT_PATH)
    assert os.path.getsize(OUTPUT_PATH) > 0


def test_envelope_has_four_top_level_keys():
    """Envelope carries exactly four top-level keys: decisions, by_service, by_verdict, summary."""
    report = _load()
    assert set(report.keys()) == {"decisions", "by_service", "by_verdict", "summary"}


def test_total_observations_equals_input_line_count():
    """Every NDJSON line across the three handshake shards becomes one decision row; the three shards together carry 36 lines."""
    assert _load()["summary"]["total_observations"] == 36


def test_decisions_array_length_matches_summary_total():
    """The decisions array length matches summary.total_observations exactly across the merged shards."""
    report = _load()
    assert len(report["decisions"]) == report["summary"]["total_observations"]


def test_by_verdict_contains_full_closed_enum():
    """by_verdict carries exactly the twelve verdict keys defined by the output envelope, zero-filled where unused."""
    report = _load()
    assert set(report["by_verdict"].keys()) == set(VERDICT_SET)


def test_verdict_counts_match_expected_oracle_tallies():
    """Each verdict bucket holds the count derived from chronological replay across all three shards with every gate applied."""
    counts = _load()["by_verdict"]
    assert counts["HYBRID_PQ_OK"] == 7
    assert counts["CLASSIC_OK"] == 8
    assert counts["DEPRECATED_GRACE"] == 3
    assert counts["PRE_ROLLOUT_PASS"] == 2
    assert counts["SEAL_RESCUED"] == 1
    assert counts["POLICY_DOWNGRADE_BLOCKED"] == 6
    assert counts["GROUP_BANNED"] == 4
    assert counts["RATE_LIMITED"] == 1
    assert counts["QUOTA_EXHAUSTED"] == 1
    assert counts["REJECTED_TYPE"] == 1
    assert counts["UNKNOWN_SERVICE"] == 1
    assert counts["INVALID"] == 1


def test_successful_and_rejected_sum_to_total():
    """successful counts the five admit-class verdicts (hybrid, classic, deprecated_grace, pre_rollout_pass, seal_rescued); rejected is everything else; both sum to total_observations."""
    summary = _load()["summary"]
    assert summary["successful"] == 21
    assert summary["rejected"] == 15
    assert summary["successful"] + summary["rejected"] == summary["total_observations"]


def test_decisions_sorted_severity_then_service_then_ts_then_observation():
    """Decisions are sorted by verdict severity descending, then service_id ascending, then observed_ts_ns ascending, then observation_id ascending."""
    report = _load()
    sev_idx = {v: i for i, v in enumerate(VERDICT_SEVERITY_HIGH_TO_LOW)}
    decisions = report["decisions"]
    for a, b in zip(decisions, decisions[1:]):
        ka = (sev_idx[a["verdict"]], a["service_id"], a["observation_id"])
        kb = (sev_idx[b["verdict"]], b["service_id"], b["observation_id"])
        assert ka <= kb, f"sort violation between {a} and {b}"


def test_rejected_type_on_stringy_timestamp():
    """obs-003 carries observed_ts_ns as a JSON string literal instead of a number; the type-strict gate maps it to REJECTED_TYPE."""
    decision = _decision_for("obs-003")
    assert decision["verdict"] == "REJECTED_TYPE"
    assert decision["matched_group"] == ""


def test_invalid_when_offered_groups_field_missing():
    """obs-004 omits the offered_groups field entirely; the required-fields gate emits INVALID."""
    assert _decision_for("obs-004")["verdict"] == "INVALID"


def test_unknown_service_for_unregistered_service_id():
    """obs-014 names phantom-svc which is absent from the service inventory; the lookup gate emits UNKNOWN_SERVICE."""
    assert _decision_for("obs-014")["verdict"] == "UNKNOWN_SERVICE"


def test_group_banned_short_circuits_phase_and_rate_without_seal():
    """obs-017 offers a banned ffdhe1024 plus a classic x25519; with no seal pin entry the banned gate fires and emits GROUP_BANNED, naming the banned group in matched_group."""
    decision = _decision_for("obs-017")
    assert decision["verdict"] == "GROUP_BANNED"
    assert decision["matched_group"] == "ffdhe1024"


def test_group_banned_for_binary_curve():
    """obs-022 offers the banned binary curve sect283k1 on billing-rpc; the banned gate emits GROUP_BANNED."""
    decision = _decision_for("obs-022")
    assert decision["verdict"] == "GROUP_BANNED"
    assert decision["matched_group"] == "sect283k1"


def test_seal_rescued_overrides_group_banned_with_valid_hmac_pin():
    """obs-030 offers banned ffdhe1024 but carries a valid HMAC seal pin; the rescue override demotes the banned verdict to SEAL_RESCUED while keeping matched_group set to the originally banned group."""
    decision = _decision_for("obs-030")
    assert decision["verdict"] == "SEAL_RESCUED"
    assert decision["matched_group"] == "ffdhe1024"


def test_invalid_seal_pin_still_yields_group_banned():
    """obs-032 has a pin entry but the HMAC mismatches the computed value over observation_id pipe service_id pipe client_id; the rescue does not apply and the verdict stays GROUP_BANNED."""
    decision = _decision_for("obs-032")
    assert decision["verdict"] == "GROUP_BANNED"
    assert decision["matched_group"] == "ffdhe1024"


def test_quota_exhausted_when_service_month_cap_reached():
    """obs-036 is the third gateway-prod admit candidate in the M02 monthly window where the cap is set to two; the quota gate fires before rate or phase and emits QUOTA_EXHAUSTED."""
    decision = _decision_for("obs-036")
    assert decision["verdict"] == "QUOTA_EXHAUSTED"
    assert decision["matched_group"] == ""


def test_seal_rescued_does_not_consume_quota_slot():
    """obs-030 is SEAL_RESCUED so it must not consume a slot in gateway-prod's M02 quota; obs-035 still admits as HYBRID_PQ_OK as the second slot and obs-036 only then exhausts."""
    obs_035 = _decision_for("obs-035")
    obs_036 = _decision_for("obs-036")
    assert obs_035["verdict"] == "HYBRID_PQ_OK"
    assert obs_036["verdict"] == "QUOTA_EXHAUSTED"


def test_client_override_flips_legacy_proxy_to_pq_mandatory():
    """obs-034 is on legacy-proxy whose base policy is classic_only, but client-uu34 carries a pq_mandatory override; post-grace with no hybrid offered the effective tier yields POLICY_DOWNGRADE_BLOCKED."""
    decision = _decision_for("obs-034")
    assert decision["verdict"] == "POLICY_DOWNGRADE_BLOCKED"


def test_group_alias_resolves_to_canonical_in_matched_group():
    """obs-033 offers the alias x25519_kyber768 which the catalog maps to canonical x25519_mlkem768; the verdict is HYBRID_PQ_OK and matched_group surfaces the canonical name, not the alias."""
    decision = _decision_for("obs-033")
    assert decision["verdict"] == "HYBRID_PQ_OK"
    assert decision["matched_group"] == "x25519_mlkem768"


def test_pre_rollout_pass_when_policy_not_yet_active():
    """obs-001 is on gateway-prod before its rollout window opens; the policy is not yet active so the verdict is PRE_ROLLOUT_PASS."""
    decision = _decision_for("obs-001")
    assert decision["verdict"] == "PRE_ROLLOUT_PASS"
    assert decision["matched_group"] == ""


def test_hybrid_pq_ok_inside_rollout_window():
    """obs-002 falls inside gateway-prod's rollout window and offers x25519_mlkem768 plus a classic; the verdict is HYBRID_PQ_OK and matched_group is the hybrid that matched."""
    decision = _decision_for("obs-002")
    assert decision["verdict"] == "HYBRID_PQ_OK"
    assert decision["matched_group"] == "x25519_mlkem768"


def test_pq_mandatory_grace_blocks_classic_only_offering():
    """obs-006 lies inside gateway-prod's grace stretch which is pq_mandatory; classic-only offering yields POLICY_DOWNGRADE_BLOCKED — grace counts as enforcement, not as a permissive tail."""
    assert _decision_for("obs-006")["verdict"] == "POLICY_DOWNGRADE_BLOCKED"


def test_pq_mandatory_post_grace_deprecated_alone_blocked():
    """obs-010 is for ledger-api past the grace stretch; pq_mandatory with only deprecated ffdhe2048 yields POLICY_DOWNGRADE_BLOCKED."""
    assert _decision_for("obs-010")["verdict"] == "POLICY_DOWNGRADE_BLOCKED"


def test_hybrid_preferred_classic_admitted_post_grace():
    """obs-019 is on cdn-edge past the grace stretch; hybrid_preferred still admits a classic x25519 offering as CLASSIC_OK."""
    decision = _decision_for("obs-019")
    assert decision["verdict"] == "CLASSIC_OK"
    assert decision["matched_group"] == "x25519"


def test_hybrid_preferred_deprecated_alone_blocked_post_grace():
    """obs-020 is on cdn-edge past the grace stretch and offers only deprecated ffdhe3072; deprecated is no longer acceptable for hybrid_preferred after grace closes so the verdict is POLICY_DOWNGRADE_BLOCKED."""
    assert _decision_for("obs-020")["verdict"] == "POLICY_DOWNGRADE_BLOCKED"


def test_deprecated_grace_inside_rollout_window():
    """obs-011 offers ffdhe2048 alone inside cdn-edge's rollout window; deprecated groups are tolerated as DEPRECATED_GRACE with the deprecated group named in matched_group."""
    decision = _decision_for("obs-011")
    assert decision["verdict"] == "DEPRECATED_GRACE"
    assert decision["matched_group"] == "ffdhe2048"


def test_classic_only_service_still_accepts_hybrid_offering():
    """obs-024 is on legacy-proxy which is classic_only; a hybrid_pq group is still acceptable for that tier so the verdict is HYBRID_PQ_OK."""
    decision = _decision_for("obs-024")
    assert decision["verdict"] == "HYBRID_PQ_OK"
    assert decision["matched_group"] == "x25519_mlkem768"


def test_rate_limited_seventh_handshake_in_window():
    """obs-029 is the seventh legacy-proxy handshake within a single sliding window where the tier_b cap is six; the rate gate emits RATE_LIMITED after six prior admits saturate."""
    assert _decision_for("obs-029")["verdict"] == "RATE_LIMITED"


def test_by_service_lists_only_registered_services():
    """by_service contains exactly the five registered services and never includes phantom-svc from the unknown-service observation."""
    report = _load()
    ids = [bs["service_id"] for bs in report["by_service"]]
    assert "phantom-svc" not in ids
    assert sorted(ids) == ["billing-rpc", "cdn-edge", "gateway-prod", "ledger-api", "legacy-proxy"]


def test_by_service_aggregate_for_gateway_prod():
    """gateway-prod aggregates three hybrid_pq_ok, one pre_rollout_pass, one seal_rescued, one policy_downgrade_blocked, one group_banned, one quota_exhausted, one rejected_type, one invalid; total is ten."""
    report = _load()
    row = next(x for x in report["by_service"] if x["service_id"] == "gateway-prod")
    assert row["hybrid_pq_ok"] == 3
    assert row["pre_rollout_pass"] == 1
    assert row["seal_rescued"] == 1
    assert row["policy_downgrade_blocked"] == 1
    assert row["group_banned"] == 1
    assert row["quota_exhausted"] == 1
    assert row["rejected_type"] == 1
    assert row["invalid"] == 1
    assert row["total"] == 10


def test_by_service_aggregate_for_legacy_proxy():
    """legacy-proxy aggregates four classic_ok, one hybrid_pq_ok, one deprecated_grace, one rate_limited, one policy_downgrade_blocked from the client override observation; total is eight."""
    report = _load()
    row = next(x for x in report["by_service"] if x["service_id"] == "legacy-proxy")
    assert row["classic_ok"] == 4
    assert row["hybrid_pq_ok"] == 1
    assert row["deprecated_grace"] == 1
    assert row["rate_limited"] == 1
    assert row["policy_downgrade_blocked"] == 1
    assert row["total"] == 8


def test_report_digest_matches_recomputation_from_emitted_rows():
    """The report_digest is the first sixteen hex characters of SHA-256 over the pipe-separated newline-joined preimage covering every decision row, every by_service row, then the summary triple. Recompute the canonical preimage from the emitted output and assert the witness's digest matches — any deviation from the pinned template, key order, or hash truncation breaks the check."""
    report = _load()
    pre = []
    for d in report["decisions"]:
        pre.append("D|{}|{}|{}|{}".format(
            d["observation_id"], d["service_id"], d["verdict"], d["matched_group"]))
    for bs in report["by_service"]:
        pre.append("S|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(
            bs["service_id"], bs["pre_rollout_pass"], bs["hybrid_pq_ok"], bs["classic_ok"],
            bs["deprecated_grace"], bs["seal_rescued"], bs["policy_downgrade_blocked"],
            bs["group_banned"], bs["rate_limited"], bs["quota_exhausted"],
            bs["rejected_type"], bs["invalid"], bs["total"]))
    s = report["summary"]
    pre.append("T|{}|{}|{}".format(s["total_observations"], s["successful"], s["rejected"]))
    expected = hashlib.sha256("\n".join(pre).encode()).hexdigest()[:16]
    assert s["report_digest"] == expected


def test_report_digest_is_lowercase_hex_sixteen_chars():
    """The digest is exactly sixteen lowercase hex characters with no prefix."""
    digest = _load()["summary"]["report_digest"]
    assert len(digest) == 16
    assert all(c in "0123456789abcdef" for c in digest)


def test_idempotent_rerun_yields_identical_envelope():
    """Re-running the witness binary over the same inputs produces an identical envelope — same decisions, same aggregates, same digest."""
    first = _load()
    subprocess.run([BINARY_PATH], check=True)
    second = _load()
    assert first == second


def test_observation_shards_immutability():
    """The witness never mutates any of the three handshake shards; SHA-256 of each file is identical before and after a re-run."""
    before = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in SHARD_PATHS}
    subprocess.run([BINARY_PATH], check=True)
    after = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in SHARD_PATHS}
    assert before == after


def test_shards_globally_sorted_in_processing_order_implied_by_quota_outcome():
    """Even though the pre-rollout shard ships rows in reverse chronological order, the engine merges and processes by observed_ts_ns ascending; obs-036 only becomes QUOTA_EXHAUSTED because obs-035 was processed first."""
    obs_035 = _decision_for("obs-035")
    obs_036 = _decision_for("obs-036")
    assert obs_035["verdict"] == "HYBRID_PQ_OK"
    assert obs_036["verdict"] == "QUOTA_EXHAUSTED"
