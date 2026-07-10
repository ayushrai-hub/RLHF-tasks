"""Tests for pub/sub delivery validator correctness.

Tests independently compute expected results and verify all aspects of the
output. The tests form an interdependent hierarchy: violation detection
cascades to metrics, dead-letter interacts with retention, priority scoring
depends on violation counts, and backpressure depends on latency computation.
"""
import json
import os
import subprocess
from collections import defaultdict

BINARY = "/app/bin/pubsub-validator"
OUTPUT = "/app/output/results.json"
DATA = "/app/data/delivery_log.json"
CONFIG = "/app/config/pubsub.toml"


def _load():
    with open(OUTPUT) as f:
        return json.load(f)


def _load_data():
    with open(DATA) as f:
        return json.load(f)


def _compute_violations():
    """Independent computation of all expected violations."""
    data = _load_data()
    subs = data["subscriptions"]
    deliveries = sorted(data["deliveries"], key=lambda x: x["timestamp"])

    sub_map = {}
    for s in subs:
        key = s["client_id"] + "|" + s["topic"]
        sub_map[key] = (s["subscribe_ts"], s["unsub_ts"])

    unsub_viols = []
    dup_viols = []
    order_viols = []

    for d in deliveries:
        key = d["client_id"] + "|" + d["topic"]
        if key not in sub_map:
            unsub_viols.append(d)
        else:
            sub_ts, unsub_ts = sub_map[key]
            if d["timestamp"] < sub_ts or d["timestamp"] >= unsub_ts:
                unsub_viols.append(d)

    seen = {}
    for d in deliveries:
        dup_key = d["msg_id"] + "|" + d["client_id"]
        if dup_key in seen:
            dup_viols.append(d)
        else:
            seen[dup_key] = d["delivery_id"]

    groups = defaultdict(list)
    for d in deliveries:
        groups[(d["client_id"], d["topic"])].append(d)
    for key, group in groups.items():
        group.sort(key=lambda x: x["timestamp"])
        for i in range(1, len(group)):
            if group[i]["seq_num"] <= group[i - 1]["seq_num"]:
                order_viols.append(group[i])

    return unsub_viols, dup_viols, order_viols


def _compute_deadletter():
    """Independent dead letter computation using >= for retry threshold."""
    data = _load_data()
    dlcfg = data["deadletter_config"]
    deliveries = data["deliveries"]

    msg_first = {}
    for d in deliveries:
        if d["msg_id"] not in msg_first:
            msg_first[d["msg_id"]] = d["timestamp"]

    by_retry = 0
    by_ttl = 0
    dl_ids = set()

    for d in deliveries:
        if d["delivery_id"] in dl_ids:
            continue
        if d["retry_count"] >= dlcfg["max_retry_count"]:
            by_retry += 1
            dl_ids.add(d["delivery_id"])
            continue
        age = d["timestamp"] - msg_first[d["msg_id"]]
        if age > dlcfg["ttl_ms"]:
            by_ttl += 1
            dl_ids.add(d["delivery_id"])

    return by_retry + by_ttl, by_retry, by_ttl, dl_ids


def _compute_retention():
    """Independent retention computation using strict > for TTL."""
    data = _load_data()
    dlcfg = data["deadletter_config"]
    ttl = dlcfg["ttl_ms"]
    deliveries = data["deliveries"]

    msg_first = {}
    for d in deliveries:
        if d["msg_id"] not in msg_first:
            msg_first[d["msg_id"]] = d["timestamp"]

    expired = 0
    for d in deliveries:
        age = d["timestamp"] - msg_first[d["msg_id"]]
        if age > ttl:
            expired += 1

    return expired


def _compute_latency():
    """Independent per-topic latency with floating-point division."""
    data = _load_data()
    topic_ts = defaultdict(list)
    for d in data["deliveries"]:
        topic_ts[d["topic"]].append(d["timestamp"])

    results = {}
    for topic, timestamps in topic_ts.items():
        timestamps.sort()
        if len(timestamps) < 2:
            results[topic] = {"mean_interval": 0.0, "max_gap": 0}
            continue
        gaps = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
        mean_val = sum(gaps) / len(gaps)
        results[topic] = {
            "mean_interval": round(mean_val, 4),
            "max_gap": max(gaps),
        }
    return results


def _compute_priority(violations):
    """Independent priority scoring normalized by total deliveries."""
    data = _load_data()
    deliveries = data["deliveries"]
    del_priority = {d["delivery_id"]: d["priority"] for d in deliveries}

    raw_score = 0.0
    high_prio = 0
    for v_type, v_did in violations:
        if v_type == "unsub_delivery":
            weight = 5.0
        elif v_type in ("duplicate_delivery", "ordering_violation"):
            weight = 3.0
        else:
            weight = 1.0
        prio = del_priority.get(v_did, 1)
        raw_score += weight * prio
        if prio >= 3:
            high_prio += 1

    total = len(deliveries)
    score = round(raw_score / total, 4) if total > 0 else 0.0
    return score, high_prio


def _compute_backpressure():
    """Independent backpressure with float mean interval for threshold."""
    data = _load_data()
    topic_ts = defaultdict(list)
    for d in data["deliveries"]:
        topic_ts[d["topic"]].append(d["timestamp"])

    results = {}
    for topic, timestamps in topic_ts.items():
        timestamps.sort()
        if len(timestamps) < 3:
            results[topic] = {"burst_windows": 0, "max_burst_size": 0, "backpressure_index": 0.0}
            continue

        total_gap = sum(timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps)))
        mean_interval = total_gap / (len(timestamps) - 1)
        threshold = int(mean_interval / 2)

        burst_windows = 0
        max_burst = 0
        current_burst = 1
        in_burst = False
        burst_deliveries = 0

        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i-1]
            if gap < threshold:
                current_burst += 1
                if not in_burst:
                    in_burst = True
                    burst_windows += 1
                    burst_deliveries += 1
                burst_deliveries += 1
            else:
                if current_burst > max_burst:
                    max_burst = current_burst
                current_burst = 1
                in_burst = False
        if current_burst > max_burst:
            max_burst = current_burst

        bp_index = round(burst_deliveries / len(timestamps), 4)
        results[topic] = {"burst_windows": burst_windows, "max_burst_size": max_burst, "backpressure_index": bp_index}

    return results


def _compute_throttle():
    """Independent throttle with floor division for bucket size."""
    data = _load_data()
    topic_dels = defaultdict(list)
    for d in data["deliveries"]:
        topic_dels[d["topic"]].append(d["timestamp"])

    results = {}
    for topic, timestamps in topic_dels.items():
        timestamps.sort()
        if len(timestamps) < 2:
            results[topic] = {"delivery_rate": 0.0, "throttle_events": 0, "peak_rate": 0.0}
            continue

        min_ts = timestamps[0]
        max_ts = timestamps[-1]
        span = max_ts - min_ts
        if span == 0:
            span = 1

        bucket_size = span // len(timestamps)
        if bucket_size == 0:
            bucket_size = 1

        buckets = defaultdict(int)
        for ts in timestamps:
            idx = (ts - min_ts) // bucket_size
            buckets[idx] += 1

        overall_rate = round(len(timestamps) / span, 4)
        throttle_events = sum(1 for c in buckets.values() if c > 2)
        peak_count = max(buckets.values())
        peak_rate = round(peak_count / bucket_size, 4)

        results[topic] = {"delivery_rate": overall_rate, "throttle_events": throttle_events, "peak_rate": peak_rate}

    return results


# ============ Structure Tests ============


def test_binary_exists():
    """Binary must be valid ELF over 500KB."""
    assert os.path.isfile(BINARY)
    with open(BINARY, "rb") as f:
        assert f.read(4) == b"\x7fELF"
    assert os.stat(BINARY).st_size > 500000


def test_output_schema():
    """Output must have all required top-level keys including new modules."""
    d = _load()
    required = ["summary", "violations", "topic_stats", "metrics", "latency",
                "fanout", "ack_stats", "dead_letter", "priority", "backpressure",
                "throttle", "retention"]
    for key in required:
        assert key in d, f"Missing key: {key}"


def test_summary_schema():
    """Summary must have all required fields with correct types."""
    s = _load()["summary"]
    for key in ["total_deliveries", "unsub_violations", "duplicate_violations",
                "ordering_violations", "dead_lettered", "num_violations",
                "num_topics", "all_valid"]:
        assert key in s, f"Missing summary field: {key}"
    assert isinstance(s["all_valid"], bool)


# ============ Violation Detection Tests ============


def test_total_deliveries():
    """Must process all 45 deliveries from the log."""
    assert _load()["summary"]["total_deliveries"] == 45


def test_unsub_violations_count():
    """Unsub violations use exclusive end window and config override removal."""
    unsub, _, _ = _compute_violations()
    r = _load()
    assert r["summary"]["unsub_violations"] == len(unsub), (
        f"Expected {len(unsub)} unsub violations, got {r['summary']['unsub_violations']}"
    )


def test_unsub_boundary_exclusive():
    """Delivery at exactly unsub_ts must be flagged - exclusive end semantics."""
    r = _load()
    unsub = [v for v in r["violations"] if v["type"] == "unsub_delivery"]
    d05 = [v for v in unsub if v["delivery_id"] == "d05"]
    assert len(d05) == 1, "d05 at exactly unsub_ts=500 must be flagged"
    assert d05[0]["severity"] == "critical"


def test_unsub_no_subscription():
    """d16: c2 never subscribed to alerts, must be flagged critical."""
    r = _load()
    unsub = [v for v in r["violations"] if v["type"] == "unsub_delivery"]
    d16 = [v for v in unsub if v["delivery_id"] == "d16"]
    assert len(d16) == 1
    assert d16[0]["severity"] == "critical"


def test_duplicate_violations_per_client():
    """Duplicates are per-client: same msg_id to same client is dup, cross-client is fan-out."""
    _, dup, _ = _compute_violations()
    r = _load()
    assert r["summary"]["duplicate_violations"] == len(dup), (
        f"Expected {len(dup)} duplicates, got {r['summary']['duplicate_violations']}"
    )


def test_duplicate_not_cross_client():
    """m6 delivered to c1 and c3 is valid fan-out, NOT a duplicate."""
    r = _load()
    dup = [v for v in r["violations"] if v["type"] == "duplicate_delivery"]
    m6_dups = [v for v in dup if "m6" in v["details"]]
    assert len(m6_dups) == 0, "Cross-client same msg_id is fan-out, not duplicate"


def test_ordering_violations_strict():
    """Ordering requires strictly increasing seq: seq <= prev is violation."""
    _, _, order = _compute_violations()
    r = _load()
    assert r["summary"]["ordering_violations"] == len(order), (
        f"Expected {len(order)} ordering violations, got {r['summary']['ordering_violations']}"
    )


def test_ordering_d04_regression():
    """d04: seq 2 after seq 3 in c1/orders must be flagged as ordering violation."""
    r = _load()
    order = [v for v in r["violations"] if v["type"] == "ordering_violation"]
    d04 = [v for v in order if v["delivery_id"] == "d04"]
    assert len(d04) == 1
    assert d04[0]["severity"] == "error"


# ============ Dead Letter & Retention Tests ============


def test_deadletter_retry_exhaustion():
    """Dead letter must use >= for retry threshold (retry_count >= max_retry_count).

    With max_retry_count=2: d31 (retry=2), d40 (retry=1 — no), d04 (retry=1 — no),
    d15 (retry=1 — no), d21 (retry=1 — no). Only d31 qualifies by retry."""
    total, by_retry, by_ttl, _ = _compute_deadletter()
    r = _load()
    assert r["dead_letter"]["by_retry_exhaustion"] == by_retry, (
        f"Expected {by_retry} retry exhaustion, got {r['dead_letter']['by_retry_exhaustion']}"
    )


def test_deadletter_ttl_expiry():
    """Dead letter TTL uses strict >: age > 500 means expired."""
    total, by_retry, by_ttl, _ = _compute_deadletter()
    r = _load()
    assert r["dead_letter"]["by_ttl_expiry"] == by_ttl, (
        f"Expected {by_ttl} TTL expiry, got {r['dead_letter']['by_ttl_expiry']}"
    )


def test_deadletter_total():
    """Total dead-lettered = retry exhaustion + TTL expiry."""
    total, _, _, _ = _compute_deadletter()
    r = _load()
    assert r["dead_letter"]["total_dead_lettered"] == total
    assert r["summary"]["dead_lettered"] == total


def test_retention_strict_boundary():
    """Retention uses strict >: age == ttl is NOT expired, age > ttl IS expired.

    With ttl=500: messages with age exactly 500 must NOT be flagged.
    This interacts with deadletter (both check TTL but with different semantics)."""
    expected = _compute_retention()
    r = _load()
    assert r["retention"]["total_expired"] == expected, (
        f"Expected {expected} retention expired, got {r['retention']['total_expired']}"
    )


def test_retention_deadletter_interaction():
    """Retention and deadletter both check TTL but must agree on boundary.

    Retention: age > ttl (strict). Deadletter TTL: age > ttl (strict).
    Both must produce consistent expiry counts for the same messages."""
    _, _, dl_ttl, _ = _compute_deadletter()
    ret_expired = _compute_retention()
    assert dl_ttl == ret_expired, (
        f"Deadletter TTL ({dl_ttl}) and retention ({ret_expired}) must agree"
    )


def test_retention_expiry_rate():
    """Retention expiry_rate is total_expired / total_deliveries rounded to 4dp."""
    data = _load_data()
    total = len(data["deliveries"])
    expired = _compute_retention()
    expected_rate = round(expired / total, 4)
    r = _load()
    assert abs(r["retention"]["expiry_rate"] - expected_rate) < 0.001, (
        f"Expected expiry_rate={expected_rate}, got {r['retention']['expiry_rate']}"
    )


def test_retention_age_fields():
    """Retention max_age and avg_age computed from message ages (age > 0 only)."""
    data = _load_data()
    dlcfg = data["deadletter_config"]
    ttl = dlcfg["ttl_ms"]
    deliveries = data["deliveries"]

    msg_first = {}
    for d in deliveries:
        if d["msg_id"] not in msg_first:
            msg_first[d["msg_id"]] = d["timestamp"]

    ages = []
    for d in deliveries:
        age = d["timestamp"] - msg_first[d["msg_id"]]
        if age > ttl:
            ages.append(age)

    r = _load()
    if ages:
        expected_max = max(ages)
        expected_avg = round(sum(ages) / len(ages), 4)
        assert r["retention"]["max_age"] == expected_max, (
            f"Expected max_age={expected_max}, got {r['retention']['max_age']}"
        )
        assert abs(r["retention"]["avg_age"] - expected_avg) < 0.01, (
            f"Expected avg_age={expected_avg}, got {r['retention']['avg_age']}"
        )


# ============ Priority Scoring Tests ============


def test_priority_normalization():
    """weighted_violation_score normalizes by total_deliveries, not violation count.

    This is the key interaction: if normalized by violations, the score is much
    higher because the denominator is smaller. Only total_deliveries normalization
    gives the correct per-delivery severity index."""
    unsub, dup, order = _compute_violations()
    all_viols = []
    for d in unsub:
        all_viols.append(("unsub_delivery", d["delivery_id"]))
    for d in dup:
        all_viols.append(("duplicate_delivery", d["delivery_id"]))
    for d in order:
        all_viols.append(("ordering_violation", d["delivery_id"]))

    expected_score, _ = _compute_priority(all_viols)
    r = _load()
    assert abs(r["priority"]["weighted_violation_score"] - expected_score) < 0.01, (
        f"Expected score {expected_score}, got {r['priority']['weighted_violation_score']}"
    )


def test_priority_high_violations():
    """High priority violations count deliveries with priority >= 3."""
    unsub, dup, order = _compute_violations()
    all_viols = []
    for d in unsub:
        all_viols.append(("unsub_delivery", d["delivery_id"]))
    for d in dup:
        all_viols.append(("duplicate_delivery", d["delivery_id"]))
    for d in order:
        all_viols.append(("ordering_violation", d["delivery_id"]))

    _, expected_high = _compute_priority(all_viols)
    r = _load()
    assert r["priority"]["high_priority_violations"] == expected_high


# ============ Latency Tests ============


def test_latency_float_division():
    """Mean interval must use floating-point division, not integer truncation.

    Integer division truncates fractional results, cascading errors to
    avg_mean_interval and backpressure threshold computation."""
    expected = _compute_latency()
    r = _load()
    for entry in r["latency"]:
        topic = entry["topic"]
        assert topic in expected, f"Unexpected topic: {topic}"
        exp_mean = expected[topic]["mean_interval"]
        assert abs(entry["mean_interval"] - exp_mean) < 0.01, (
            f"{topic}: mean_interval={entry['mean_interval']}, expected={exp_mean}"
        )
        assert entry["max_gap"] == expected[topic]["max_gap"]


def test_latency_sorted():
    """Latency array must be sorted by topic name."""
    topics = [e["topic"] for e in _load()["latency"]]
    assert topics == sorted(topics)


def test_avg_mean_interval():
    """avg_mean_interval = mean of per-topic mean_intervals to 4dp."""
    expected = _compute_latency()
    avg = round(sum(v["mean_interval"] for v in expected.values()) / len(expected), 4)
    r = _load()
    assert abs(r["metrics"]["avg_mean_interval"] - avg) < 0.1


# ============ Backpressure Tests ============


def test_backpressure_float_threshold():
    """Backpressure threshold must use float mean interval (not integer division).

    This cascades from latency fix: if latency uses integer division, the
    threshold is too coarse and produces wrong burst window detection."""
    expected = _compute_backpressure()
    r = _load()
    for entry in r["backpressure"]:
        topic = entry["topic"]
        if topic in expected:
            exp = expected[topic]
            assert entry["burst_windows"] == exp["burst_windows"], (
                f"{topic}: burst_windows={entry['burst_windows']}, expected={exp['burst_windows']}"
            )
            assert abs(entry["backpressure_index"] - exp["backpressure_index"]) < 0.01, (
                f"{topic}: bp_index={entry['backpressure_index']}, expected={exp['backpressure_index']}"
            )


def test_backpressure_sorted():
    """Backpressure array must be sorted by topic name."""
    topics = [e["topic"] for e in _load()["backpressure"]]
    assert topics == sorted(topics)


def test_backpressure_max_burst_size():
    """max_burst_size tracks the largest consecutive burst window per topic."""
    expected = _compute_backpressure()
    r = _load()
    for entry in r["backpressure"]:
        topic = entry["topic"]
        if topic in expected:
            exp = expected[topic]
            assert entry["max_burst_size"] == exp["max_burst_size"], (
                f"{topic}: max_burst_size={entry['max_burst_size']}, expected={exp['max_burst_size']}"
            )


# ============ Throttle Tests ============


def test_throttle_floor_division():
    """Throttle bucket_size must use floor division (not ceiling).

    Ceiling division produces larger buckets → fewer throttle events detected.
    Floor division produces smaller buckets → correct granularity for rate detection."""
    expected = _compute_throttle()
    r = _load()
    for entry in r["throttle"]:
        topic = entry["topic"]
        if topic in expected:
            exp = expected[topic]
            assert entry["throttle_events"] == exp["throttle_events"], (
                f"{topic}: throttle_events={entry['throttle_events']}, expected={exp['throttle_events']}"
            )


def test_throttle_sorted():
    """Throttle array must be sorted by topic name."""
    topics = [e["topic"] for e in _load()["throttle"]]
    assert topics == sorted(topics)


def test_throttle_delivery_rate():
    """Throttle delivery_rate is count/span for each topic."""
    expected = _compute_throttle()
    r = _load()
    for entry in r["throttle"]:
        topic = entry["topic"]
        if topic in expected:
            exp = expected[topic]
            assert abs(entry["delivery_rate"] - exp["delivery_rate"]) < 0.001, (
                f"{topic}: delivery_rate={entry['delivery_rate']}, expected={exp['delivery_rate']}"
            )


def test_throttle_peak_rate():
    """Throttle peak_rate is max bucket count / bucket_size."""
    expected = _compute_throttle()
    r = _load()
    for entry in r["throttle"]:
        topic = entry["topic"]
        if topic in expected:
            exp = expected[topic]
            assert abs(entry["peak_rate"] - exp["peak_rate"]) < 0.001, (
                f"{topic}: peak_rate={entry['peak_rate']}, expected={exp['peak_rate']}"
            )


# ============ Fanout & Topic Stats Tests ============


def test_fanout_ratio():
    """Fan-out ratio = total_deliveries / unique_messages per topic (float division)."""
    data = _load_data()
    r = _load()
    for entry in r["fanout"]:
        topic = entry["topic"]
        topic_dels = [d for d in data["deliveries"] if d["topic"] == topic]
        unique_msgs = len(set(d["msg_id"] for d in topic_dels))
        expected_ratio = round(len(topic_dels) / unique_msgs, 4)
        assert abs(entry["fanout_ratio"] - expected_ratio) < 0.001, (
            f"{topic}: ratio={entry['fanout_ratio']}, expected={expected_ratio}"
        )


def test_fanout_sorted():
    """Fanout array must be sorted by topic name."""
    topics = [e["topic"] for e in _load()["fanout"]]
    assert topics == sorted(topics)


def test_topic_stats_sorted():
    """topic_stats must be sorted by topic name."""
    stats = _load()["topic_stats"]
    names = [s["topic"] for s in stats]
    assert names == sorted(names)


def test_topic_stats_violations_sum():
    """Sum of per-topic violations must equal total num_violations."""
    r = _load()
    topic_total = sum(ts["violations"] for ts in r["topic_stats"])
    assert topic_total == r["summary"]["num_violations"]


def test_num_topics():
    """num_topics counts distinct topics across all deliveries."""
    data = _load_data()
    topics = set(d["topic"] for d in data["deliveries"])
    assert _load()["summary"]["num_topics"] == len(topics)


# ============ Metrics & Cross-Section Tests ============


def test_violation_rates():
    """All rates = count / total_deliveries rounded to 4dp."""
    unsub, dup, order = _compute_violations()
    total = 45
    r = _load()["metrics"]
    assert abs(r["unsub_rate"] - round(len(unsub) / total, 4)) < 0.0001
    assert abs(r["duplicate_rate"] - round(len(dup) / total, 4)) < 0.0001
    assert abs(r["ordering_rate"] - round(len(order) / total, 4)) < 0.0001


def test_ack_stats():
    """ack_rate = total_acked / total_deliveries to 4dp."""
    data = _load_data()
    acked = sum(1 for d in data["deliveries"] if d["acked"])
    total = len(data["deliveries"])
    r = _load()
    assert r["ack_stats"]["total_acked"] == acked
    assert r["ack_stats"]["total_unacked"] == total - acked
    assert abs(r["ack_stats"]["ack_rate"] - round(acked / total, 4)) < 0.0001


def test_cross_section_consistency():
    """num_violations == len(violations) == sum(topic_stats[*].violations).

    This integration test cascades from ALL violation detection: core violations,
    deadletter violations, and retention violations all contribute."""
    r = _load()
    assert r["summary"]["num_violations"] == len(r["violations"])
    topic_total = sum(ts["violations"] for ts in r["topic_stats"])
    assert topic_total == r["summary"]["num_violations"]
    expected_rate = round(r["summary"]["num_violations"] / r["summary"]["total_deliveries"], 4)
    assert abs(r["metrics"]["violation_rate"] - expected_rate) < 0.0001


def test_all_valid_false():
    """all_valid must be false when any violations exist."""
    assert _load()["summary"]["all_valid"] is False


def test_violations_sorted():
    """Violations sorted by type then delivery_id."""
    vs = _load()["violations"]
    for i in range(1, len(vs)):
        prev = (vs[i - 1]["type"], vs[i - 1]["delivery_id"])
        curr = (vs[i]["type"], vs[i]["delivery_id"])
        assert prev <= curr, f"Not sorted: {prev} > {curr}"


# ============ Anti-Cheating & Determinism ============


def test_source_not_gutted():
    """Core source files must retain implementations."""
    required_files = [
        "pkg/validator/validator.go", "pkg/config/config.go",
        "pkg/report/report.go", "pkg/latency/latency.go",
        "pkg/ack/ack.go", "pkg/fanout/fanout.go",
        "pkg/deadletter/deadletter.go", "pkg/priority/priority.go",
        "pkg/backpressure/backpressure.go", "pkg/throttle/throttle.go",
        "pkg/retention/retention.go",
    ]
    for f in required_files:
        path = f"/app/{f}"
        assert os.path.isfile(path), f"Missing: {f}"
        content = open(path).read()
        lines = [ln for ln in content.splitlines()
                 if ln.strip() and not ln.strip().startswith("//")]
        assert len(lines) >= 8, f"{f} appears gutted ({len(lines)} lines)"


def test_rerun_deterministic():
    """Output must be identical across runs."""
    subprocess.run([BINARY, "--data", DATA, "--config", CONFIG,
                    "--output", "/app/output"], capture_output=True)
    d1 = _load()
    subprocess.run([BINARY, "--data", DATA, "--config", CONFIG,
                    "--output", "/app/output"], capture_output=True)
    d2 = _load()
    assert d1 == d2


def test_config_override_inactive():
    """Config override must not disable validation checks."""
    r = _load()
    assert r["summary"]["unsub_violations"] > 0, (
        "No unsub violations — config override may still be active"
    )
    assert r["summary"]["duplicate_violations"] > 0, (
        "No duplicate violations — config override may still be active"
    )


def test_compound_violation_d31():
    """d31 triggers multiple violation types simultaneously.

    d31: m7 to c1/events at ts=700 with unsub_ts=700 (exclusive -> invalid).
    d31: seq=2 after d12 seq=3 in c1/events (ordering violation).
    d31: m7 to c1 again (duplicate of d11).
    d31: retry_count=2 >= max_retry_count=2 (dead letter).
    Tests that a single delivery can cascade across all detection systems."""
    r = _load()
    d31_viols = [v for v in r["violations"] if v["delivery_id"] == "d31"]
    types = {v["type"] for v in d31_viols}
    assert "unsub_delivery" in types, "d31 at ts=700 with unsub=700 must be flagged"
    assert "ordering_violation" in types, "d31 seq=2 after seq=3 must be flagged"
    assert "duplicate_delivery" in types, "d31 m7 to c1 again must be flagged"
    assert "dead_letter" in types, "d31 retry_count=2 >= max=2 must be dead-lettered"


# ============ Additional Metrics Coverage Tests ============


def test_dead_letter_rate_metric():
    """dead_letter_rate in metrics must equal dead_lettered / total_deliveries to 4dp."""
    r = _load()
    total, _, _, _ = _compute_deadletter()
    expected = round(total / 45, 4)
    assert abs(r["metrics"]["dead_letter_rate"] - expected) < 0.0001


def test_avg_fanout_metric():
    """avg_fanout = mean of per-topic fanout ratios to 4dp."""
    r = _load()
    ratios = [e["fanout_ratio"] for e in r["fanout"]]
    expected = round(sum(ratios) / len(ratios), 4)
    assert abs(r["metrics"]["avg_fanout"] - expected) < 0.001


def test_avg_backpressure_metric():
    """avg_backpressure = mean of per-topic backpressure indices to 4dp."""
    expected = _compute_backpressure()
    indices = [v["backpressure_index"] for v in expected.values()]
    avg = round(sum(indices) / len(indices), 4)
    r = _load()
    assert abs(r["metrics"]["avg_backpressure"] - avg) < 0.01


def test_priority_distribution():
    """priority_distribution must count deliveries by priority bucket."""
    data = _load_data()
    high = sum(1 for d in data["deliveries"] if d["priority"] >= 3)
    medium = sum(1 for d in data["deliveries"] if d["priority"] == 2)
    low = sum(1 for d in data["deliveries"] if d["priority"] < 2)
    r = _load()
    pd = r["priority"]["priority_distribution"]
    assert pd.get("high", 0) == high
    assert pd.get("medium", 0) == medium
    assert pd.get("low", 0) == low


def test_avg_priority():
    """avg_priority = mean of all delivery priority values to 4dp."""
    data = _load_data()
    priorities = [d["priority"] for d in data["deliveries"]]
    expected = round(sum(priorities) / len(priorities), 4)
    r = _load()
    assert abs(r["priority"]["avg_priority"] - expected) < 0.001
