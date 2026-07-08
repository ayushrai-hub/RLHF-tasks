"""Verifier for C++ Polars inference endpoint batch audit."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import pytest
import requests

APP = Path("/app")
ENV = APP / "environment"
AUDIT = APP / "output" / "batch_audit.json"
API = "http://127.0.0.1:19091/v1/batch-score"
LOCK = ENV / "sidecar" / "poetry.lock"

WEIGHTS = json.loads((ENV / "config/model_weights.json").read_text(encoding="utf-8"))

BUNDLED_ROWS = json.loads((ENV / "seed/bundled_rows.json").read_text(encoding="utf-8"))["rows"]

REGIONS = ("west", "east", "north", "south")
CHANNELS = ("web", "phone", "retail")

POLICY = {
    "max_batch_rows": 32,
    "null_fill": "forward",
    "unknown_category": "reject",
    "polars_pin": "1.12.0",
    "score_precision": 6,
}


def policy_seq() -> str:
    canonical = json.dumps(POLICY, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def lock_digest() -> str:
    payload = f"polars=={POLICY['polars_pin']}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def forward_fill(rows: list[dict]) -> list[dict]:
    last_age = None
    last_tenure = None
    filled = []
    for row in rows:
        age = row["age"] if row["age"] is not None else last_age
        tenure = row["tenure_months"] if row["tenure_months"] is not None else last_tenure
        if age is not None:
            last_age = age
        if tenure is not None:
            last_tenure = tenure
        filled.append({**row, "age": age, "tenure_months": tenure})
    return filled


def build_features(row: dict) -> dict[str, float]:
    region = row["region"]
    channel = row["channel"]
    features: dict[str, float] = {
        "age_ff": float(row["age"]) / 100.0,
        "tenure_ff": float(row["tenure_months"]) / 60.0,
    }
    for name in REGIONS:
        features[f"region_{name}"] = 1.0 if region == name else 0.0
    for name in CHANNELS:
        features[f"channel_{name}"] = 1.0 if channel == name else 0.0
    return features


def feature_digest(features: dict[str, float]) -> str:
    keys = sorted(features)
    parts = [f'"{k}":{round(features[k], 6):.6f}' for k in keys]
    payload = "{" + ",".join(parts) + "}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def expected_score(features: dict[str, float]) -> float:
    total = WEIGHTS["bias"]
    for key, value in features.items():
        total += WEIGHTS[key] * value
    return round(total, POLICY["score_precision"])


def expected_audit_rows() -> dict[str, tuple[float, str]]:
    rows = forward_fill(BUNDLED_ROWS)
    out: dict[str, tuple[float, str]] = {}
    for row in rows:
        features = build_features(row)
        out[row["row_id"]] = (expected_score(features), feature_digest(features))
    return out


def _kill_server() -> None:
    subprocess.run(["pkill", "-f", "score-server"], check=False)


def _rebuild_and_start() -> None:
    _kill_server()
    subprocess.run(["make", "-C", "/app/environment", "install"], check=True, timeout=300)
    subprocess.run(["bash", str(ENV / "ci/start-score-server.sh")], check=True, timeout=120)


def _post(payload: dict) -> dict:
    resp = requests.post(API, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _run_audit() -> dict:
    if AUDIT.exists():
        AUDIT.unlink()
    subprocess.run(["bash", str(ENV / "scripts/run-batch-audit.sh")], check=True, timeout=120)
    return json.loads(AUDIT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def prepare_server():
    _rebuild_and_start()
    yield
    _kill_server()


class TestBatchAudit:
    def test_audit_regenerates(self):
        """Bundled audit accepts every seed row with zero rejections."""
        report = _run_audit()
        assert report["api_version"] == "1"
        assert report["accepted"] == len(BUNDLED_ROWS)
        assert report["rejected"] == 0

    def test_policy_seq_matches_dossier(self):
        """policy_seq reflects Section 12 ratified preprocessing defaults."""
        report = _run_audit()
        assert report["policy_seq"] == policy_seq()

    def test_lock_digest_matches_pin(self):
        """lock_digest matches the ratified polars pin string."""
        report = _run_audit()
        assert report["lock_digest"] == lock_digest()

    def test_scores_match_reference(self):
        """Each bundled row score and feature_digest match ridge reference math."""
        report = _run_audit()
        expected = expected_audit_rows()
        by_id = {row["row_id"]: row for row in report["scores"]}
        for row_id, (score, digest) in expected.items():
            entry = by_id[row_id]
            assert entry["status"] == "ok"
            assert entry["score"] == score
            assert entry["feature_digest"] == digest

    def test_scores_sorted_by_row_id(self):
        """Audit scores array is sorted ascending by row_id."""
        report = _run_audit()
        ids = [row["row_id"] for row in report["scores"]]
        assert ids == sorted(ids)

    def test_idempotent_rerun(self):
        """Back-to-back audits with unchanged fixtures yield identical JSON."""
        first = _run_audit()
        second = _run_audit()
        assert second == first

    def test_oversize_batch_rejected(self):
        """Batches above the dossier row limit are fully rejected."""
        rows = [
            {
                "row_id": f"pad-{i:02d}",
                "age": 25.0,
                "tenure_months": 12,
                "region": "west",
                "channel": "web",
            }
            for i in range(POLICY["max_batch_rows"] + 1)
        ]
        body = _post({"batch_id": "mut-oversize", "rows": rows})
        assert body["accepted"] == 0
        assert body["rejected"] == len(rows)
        assert all(row["status"] == "rejected" for row in body["scores"])

    def test_unknown_region_rejected(self):
        """Unknown categorical region values reject the batch."""
        body = _post(
            {
                "batch_id": "mut-region",
                "rows": [
                    {
                        "row_id": "x1",
                        "age": 20.0,
                        "tenure_months": 3,
                        "region": "atlantis",
                        "channel": "web",
                    }
                ],
            }
        )
        assert body["accepted"] == 0
        assert body["rejected"] == 1
        assert body["scores"][0]["status"] == "rejected"

    def test_missing_column_rejected(self):
        """Rows missing required keys reject the batch."""
        body = _post(
            {
                "batch_id": "mut-missing",
                "rows": [
                    {"row_id": "x2", "age": 20.0, "tenure_months": 3, "channel": "web"}
                ],
            }
        )
        assert body["accepted"] == 0
        assert body["rejected"] == 1

    def test_tampered_lock_fail_closed(self):
        """A mismatched poetry.lock polars pin fails the batch closed."""
        original = LOCK.read_text(encoding="utf-8")
        backup = Path(tempfile.gettempdir()) / "ridge-poetry-lock-backup"
        backup.write_text(original, encoding="utf-8")
        try:
            tampered = original.replace(POLICY["polars_pin"], "0.20.31")
            LOCK.write_text(tampered, encoding="utf-8")
            _rebuild_and_start()
            payload = json.loads((ENV / "seed/bundled_rows.json").read_text(encoding="utf-8"))
            body = _post(payload)
            assert body["accepted"] == 0
            assert body["rejected"] == len(payload["rows"])
        finally:
            LOCK.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
            backup.unlink(missing_ok=True)
            _rebuild_and_start()
