"""Verifier for the Cargo inference config reconciliation task.

Each test maps to a requirement stated in instruction.md and the dossier's
normative appendices: model identity, quantization mode, the crate feature set,
evaluation thresholds, serving limits, and the exact output contract for
/app/release-plan.yaml.
"""
import hashlib
import json
import os
import subprocess

import pytest
import yaml

DOSSIER = "/app/dossier.md"
ENTRY = "/app/dist/reconcile.js"
PLAN = "/app/release-plan.yaml"
DEPLOY = "/app/deploy.json"
LOCK = "/app/lock.json"

EXPECTED_TOP_ORDER = [
    "apiVersion",
    "kind",
    "model",
    "quantization",
    "features",
    "thresholds",
    "serving",
]
EXPECTED_FEATURES = [
    "cpu-avx2",
    "quantized-int8",
]


@pytest.fixture(scope="session", autouse=True)
def regenerated_plan():
    """Regenerate all three artifacts by running the pipeline the task mandates.

    Any pre-existing outputs are deleted and the pipeline is re-run with the
    dossier piped on stdin, so a passing run must come from a working TypeScript
    pipeline rather than hand-written static files left in place.
    """
    for path in (PLAN, DEPLOY, LOCK):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    assert os.path.exists(ENTRY), f"pipeline entrypoint {ENTRY} is missing"
    with open(DOSSIER, "rb") as fh:
        proc = subprocess.run(
            ["node", ENTRY], stdin=fh, capture_output=True, timeout=120
        )
    assert proc.returncode == 0, (
        f"pipeline exited {proc.returncode}: {proc.stderr.decode()[:800]}"
    )
    for path in (PLAN, DEPLOY, LOCK):
        assert os.path.exists(path), f"pipeline did not write {path}"
    yield


def _raw():
    with open(PLAN, "r") as fh:
        return fh.read()


def _doc():
    return yaml.safe_load(_raw())


def _deploy():
    with open(DEPLOY) as fh:
        return json.load(fh)


def _lock():
    with open(LOCK) as fh:
        return json.load(fh)


def _block_subkeys(raw, top_key):
    """Return the ordered 2-space-indented sub-keys under a top-level mapping."""
    lines = raw.splitlines()
    out = []
    inside = False
    for line in lines:
        if not line:
            continue
        if not line[0].isspace():
            inside = line.split(":", 1)[0] == top_key
            continue
        if inside and line.startswith("  ") and not line.startswith("    "):
            stripped = line.strip()
            if ":" in stripped:
                out.append(stripped.split(":", 1)[0])
    return out


def test_valid_yaml():
    """The plan parses as a YAML mapping."""
    doc = _doc()
    assert isinstance(doc, dict)


def test_top_level_key_order_and_set():
    """Top-level keys appear in the exact contract order with no extras."""
    raw = _raw()
    keys = [
        ln.split(":", 1)[0]
        for ln in raw.splitlines()
        if ln and not ln[0].isspace() and ":" in ln
    ]
    assert keys == EXPECTED_TOP_ORDER


def test_api_version_and_kind():
    """apiVersion and kind carry the literal contract values."""
    doc = _doc()
    assert doc["apiVersion"] == "release.mlops/v1"
    assert doc["kind"] == "ReleasePlan"


def test_model_name_from_tracker():
    """Model name is the tracker's model name, not the crate package name."""
    assert _doc()["model"]["name"] == "sentiment-transformer"


def test_model_version_pinning():
    """Version pins MLflow major.minor (4.2) onto the crate patch (1) -> 4.2.1."""
    assert _doc()["model"]["version"] == "4.2.1"


def test_model_run_id_from_manifest():
    """run_id is the authoritative manifest value from the dossier, not MLflow's."""
    assert str(_doc()["model"]["run_id"]) == "5d8e02b4"


def test_model_evaluated_at_utc_selection():
    """evaluated_at is the UTC-normalized timestamp of the latest valid CSV row.

    The winning row (2026-05-14T20:10:00-04:00 -> 2026-05-15T00:10:00Z) is later
    in UTC than the Berlin-tz row whose local wall-clock looks later, and its
    quoted-comma notes field must be parsed as RFC-4180. Both are required to get
    this value right.
    """
    assert _doc()["model"]["evaluated_at"] == "2026-05-15T00:10:00Z"
    assert '  evaluated_at: "2026-05-15T00:10:00Z"\n' in _raw()


def test_model_subkey_order():
    """model sub-keys appear in the order name, version, run_id, evaluated_at."""
    assert _block_subkeys(_raw(), "model") == [
        "name",
        "version",
        "run_id",
        "evaluated_at",
    ]


def test_quantization_mode():
    """Quantization resolves to int8 for the certified CPU serving path."""
    assert _doc()["quantization"] == "int8"


def test_quantization_is_scalar_not_mapping():
    """quantization is a plain top-level scalar string, not a nested mapping."""
    assert isinstance(_doc()["quantization"], str)


def test_features_exact_set_sorted_dedup():
    """Feature list is the reconciled set, deduplicated and lexicographically sorted."""
    feats = _doc()["features"]
    assert feats == EXPECTED_FEATURES
    assert feats == sorted(feats)
    assert len(feats) == len(set(feats))


def test_features_exclusions():
    """Telemetry and gpu-cuda are excluded; no bf16 quantization feature leaks in."""
    feats = set(_doc()["features"])
    assert "telemetry" not in feats
    assert "gpu-cuda" not in feats
    assert "quantized-bf16" not in feats


def test_experimental_simd_excluded_non_power_of_two():
    """The resolved batch size 12 is not a power of two, so experimental-simd is excluded.

    An agent that misses the 2026-06-12 batch revision keeps batch 16 (a power of
    two) and wrongly includes experimental-simd.
    """
    assert "experimental-simd" not in set(_doc()["features"])


def test_dynamic_batching_dropped_after_concurrency_revision():
    """The 2026-06-12 concurrency revision to 12 (< 16) drops dynamic-batching."""
    assert "dynamic-batching" not in set(_doc()["features"])


def test_thresholds_values():
    """From the selected CSV row (acc 0.918, lat 47): gate 0.918, ceiling ceil(47*1.2)=57."""
    thr = _doc()["thresholds"]
    assert abs(float(thr["min_accuracy"]) - 0.918) < 1e-9
    assert thr["max_latency_ms"] == 57


def test_min_accuracy_three_decimal_literal():
    """min_accuracy is written with exactly three decimal places (0.918)."""
    assert "  min_accuracy: 0.918\n" in _raw()


def test_thresholds_subkey_order():
    """thresholds sub-keys are min_accuracy then max_latency_ms."""
    assert _block_subkeys(_raw(), "thresholds") == ["min_accuracy", "max_latency_ms"]


def test_serving_limits():
    """After the revisions: batch 12, concurrency 12, request timeout 1200 (2026-06-20)."""
    srv = _doc()["serving"]
    assert srv["max_batch_size"] == 12
    assert srv["max_concurrency"] == 12
    assert srv["request_timeout_ms"] == 1200


def test_queue_capacity_derived():
    """queue_capacity is resolved max_batch_size * max_concurrency = 12 * 12 = 144."""
    assert _doc()["serving"]["queue_capacity"] == 144


def test_serving_subkey_order():
    """serving sub-keys are batch, concurrency, timeout, queue_capacity in order."""
    assert _block_subkeys(_raw(), "serving") == [
        "max_batch_size",
        "max_concurrency",
        "request_timeout_ms",
        "queue_capacity",
    ]


def test_formatting_contract():
    """File ends with exactly one trailing newline and has no trailing whitespace."""
    raw = _raw()
    assert raw.endswith("\n")
    assert not raw.endswith("\n\n")
    for line in raw.splitlines():
        assert line == line.rstrip(), f"trailing whitespace on line: {line!r}"


def test_deploy_replicas():
    """deploy.json replicas = ceil(resolved concurrency 12 / 4) = 3."""
    assert _deploy()["replicas"] == 3


def test_deploy_cpu_millicores():
    """deploy.json cpu_millicores = 250 * resolved batch 12 = 3000."""
    assert _deploy()["cpu_millicores"] == 3000


def test_deploy_memory_mb():
    """deploy.json memory_mb = 8 * resolved queue_capacity 144 = 1152."""
    assert _deploy()["memory_mb"] == 1152


def test_deploy_request_deadline_mirrors_plan():
    """deploy.json request_deadline_ms mirrors the resolved request timeout (1200)."""
    assert _deploy()["request_deadline_ms"] == 1200


def test_deploy_warmup_batches():
    """warmup_batches is the latest-dated value 8 (2026-06-14), not the older 16 (2026-06-01)."""
    assert _deploy()["warmup_batches"] == 8


def test_deploy_shutdown_grace_seconds():
    """shutdown_grace_seconds is the latest-dated 25 (2026-06-19), not the older 40 (2026-06-04)."""
    assert _deploy()["shutdown_grace_seconds"] == 25


def test_deploy_canary_percent():
    """canary_percent is the latest-dated 15 (2026-06-16), not the older 30 (2026-06-02)."""
    assert _deploy()["canary_percent"] == 15


def test_deploy_env_consistent_with_plan():
    """deploy.json env mirrors the plan: quant mode, comma-joined sorted features, concurrency."""
    env = _deploy()["env"]
    doc = _doc()
    assert env["QUANT_MODE"] == doc["quantization"]
    assert env["FEATURES"] == ",".join(doc["features"])
    assert env["MAX_INFLIGHT"] == str(doc["serving"]["max_concurrency"])


def test_lock_run_id_matches_plan():
    """lock.json run_id equals the plan's authoritative run_id."""
    assert _lock()["run_id"] == str(_doc()["model"]["run_id"])


def test_lock_counts_consistent():
    """lock.json feature_count and replica_count match the plan and deploy descriptor."""
    lock = _lock()
    assert lock["feature_count"] == len(_doc()["features"])
    assert lock["replica_count"] == _deploy()["replicas"]


def test_lock_plan_digest_matches_bytes():
    """lock.json plan_sha256 is the lowercase-hex SHA-256 of the actual plan bytes."""
    with open(PLAN, "rb") as fh:
        expected = hashlib.sha256(fh.read()).hexdigest()
    assert _lock()["plan_sha256"] == expected


def test_lock_deploy_digest_matches_bytes():
    """lock.json deploy_sha256 is the lowercase-hex SHA-256 of the actual deploy.json bytes."""
    with open(DEPLOY, "rb") as fh:
        expected = hashlib.sha256(fh.read()).hexdigest()
    assert _lock()["deploy_sha256"] == expected


def test_lock_binding_digest():
    """lock.json binding = SHA-256 of 'plan_sha256:deploy_sha256'."""
    lock = _lock()
    combined = f"{lock['plan_sha256']}:{lock['deploy_sha256']}".encode("ascii")
    assert lock["binding"] == hashlib.sha256(combined).hexdigest()
