"""Tests for sliding window rate limiter."""
import json
import subprocess
from pathlib import Path

import pytest

OUTPUT = Path("/app/output")
RJ = OUTPUT / "limiter_report.json"
RT = OUTPUT / "limiter_report.txt"


@pytest.fixture(scope="module")
def report():
    """Load the JSON report."""
    return json.loads(RJ.read_text())


def test_json_exists():
    """JSON report must exist."""
    assert RJ.exists()


def test_text_exists():
    """Text report must exist."""
    assert RT.exists()


def test_total_requests(report):
    """Must process all 16 requests."""
    assert report["total_requests"] == 16


def test_allowed_count(report):
    """With correct settings (window=1000, max=5), exactly 11 allowed."""
    assert report["allowed_count"] == 11


def test_denied_count(report):
    """5 requests denied."""
    assert report["denied_count"] == 5


def test_deny_rate(report):
    """Deny rate = 5/16 = 0.3125."""
    assert report["overall_deny_rate"] == 0.3125


def test_window_violations(report):
    """1 burst event triggers a window violation."""
    assert report["window_violations"] == 1


def test_burst_events(report):
    """1 burst event (client-A exceeds burst_limit=3 in grace_period).
    Event at timestamp_ms=200, count=3, limit=3."""
    assert len(report["burst_events"]) == 1
    be = report["burst_events"][0]
    assert be["client_id"] == "client-A"
    assert be["timestamp_ms"] == 200
    assert be["count"] == 3
    assert be["limit"] == 3


def test_burst_request_reason(report):
    """R04 triggers burst detection and must have reason burst_exceeded."""
    r04 = next(d for d in report["decisions"] if d["request_id"] == "R04")
    assert r04["allowed"] is False
    assert r04["reason"] == "burst_exceeded"


def test_client_stats_count(report):
    """2 clients: client-A and client-B."""
    assert len(report["client_stats"]) == 2


def test_client_a_stats(report):
    """client-A stats with correct window settings."""
    ca = next(c for c in report["client_stats"] if c["client_id"] == "client-A")
    assert ca["total"] == 10
    assert ca["allowed"] == 6
    assert ca["denied"] == 4
    assert ca["deny_rate"] == 0.4
    assert ca["burst_events"] == 1
    assert ca["penalty_ms"] == 500


def test_client_b_stats(report):
    """client-B stats."""
    cb = next(c for c in report["client_stats"] if c["client_id"] == "client-B")
    assert cb["total"] == 6
    assert cb["allowed"] == 5
    assert cb["denied"] == 1
    assert cb["deny_rate"] == 0.1667
    assert cb["burst_events"] == 0
    assert cb["penalty_ms"] == 0


def test_settings_not_overridden(report):
    """Profile would set max_requests=20, allowing all 16. Correct (max=5): 11 allowed."""
    assert report["allowed_count"] == 11
    assert report["denied_count"] == 5


def test_env_var_not_applied(report):
    """RATELIMIT_WINDOW_MS env var must not override settings."""
    assert report["allowed_count"] == 11


def test_client_deny_rate_4dp(report):
    """Client-level deny_rate must use 4dp.
    client-A: denied/total at 4dp precision."""
    ca = next(c for c in report["client_stats"] if c["client_id"] == "client-A")
    # Verify it's 4dp (not 2dp)
    assert ca["deny_rate"] == round(ca["deny_rate"], 4)
    # With 2dp would be different for some values
    assert isinstance(ca["deny_rate"], float)


def test_first_request_allowed(report):
    """R01 must be allowed (first request, empty window)."""
    r01 = next(d for d in report["decisions"] if d["request_id"] == "R01")
    assert r01["allowed"] is True
    assert r01["reason"] == "allowed"


def test_penalty_boundary_request(report):
    """R12 at ts=750 must be ALLOWED. Burst at R04 (ts=200), penalty_end=200+500=700.
    With correct strict < check: 750 < 700 is false -> penalty expired -> ALLOWED."""
    r12 = next(d for d in report["decisions"] if d["request_id"] == "R12")
    assert r12["allowed"] is True, (
        "R12 at ts=750 should be ALLOWED. penalty_end=700, strict < means "
        "750 < 700 is false (penalty expired). If denied, penalty logic is wrong.")


def test_penalized_request_denied(report):
    """R07 at ts=300 must be DENIED with reason penalty_active (300 < 700)."""
    r07 = next(d for d in report["decisions"] if d["request_id"] == "R07")
    assert r07["allowed"] is False
    assert r07["reason"] == "penalty_active"


def test_penalized_request_r10(report):
    """R10 at ts=600 must be DENIED (penalty active: 600 < 750)."""
    r10 = next(d for d in report["decisions"] if d["request_id"] == "R10")
    assert r10["allowed"] is False


def test_burst_trigger_denied(report):
    """R06 at ts=250 must be DENIED due to active penalty (penalty_end=700, 250 < 700)."""
    r06 = next(d for d in report["decisions"] if d["request_id"] == "R06")
    assert r06["allowed"] is False
    assert r06["reason"] == "penalty_active"


def test_window_boundary_inclusive(report):
    """With inclusive start (>=), requests at window boundary are counted."""
    assert report["denied_count"] == 5


def test_file_ordering(report):
    """Traffic files must be loaded in ascending lexicographic order.
    R01 (batch_001) must be processed before R06 (batch_002). If loaded in
    reverse, R01 would see a filled window and be denied."""
    r01 = next(d for d in report["decisions"] if d["request_id"] == "R01")
    assert r01["allowed"] is True
    assert r01["window_count"] == 0, "R01 should see empty window (processed first)"


def test_rate_exceeded_reason(report):
    """R15 (client-B ts=950) must be denied with reason rate_exceeded."""
    r15 = next(d for d in report["decisions"] if d["request_id"] == "R15")
    assert r15["allowed"] is False
    assert r15["reason"] == "rate_exceeded"


def test_text_report_content():
    """Text report must have required headers."""
    text = RT.read_text()
    assert "Sliding Window Rate Limiter Report" in text
    assert "Total requests:" in text
    assert "Denied:" in text
    assert "Deny rate:" in text
    assert "Window violations:" in text


def test_binary_no_args():
    """Binary must exit non-zero with no arguments."""
    r = subprocess.run(["/app/bin/rate-limiter"], capture_output=True)
    assert r.returncode != 0


def test_binary_compiles():
    """Project must compile."""
    import os
    env = os.environ.copy()
    env["PATH"] = "/usr/local/go/bin:" + env.get("PATH", "")
    r = subprocess.run(["go", "build", "-o", "/tmp/test-rl", "./cmd/limiter"],
                       capture_output=True, cwd="/app", env=env)
    assert r.returncode == 0


def test_deterministic():
    """Re-running must produce identical output."""
    import os
    env = os.environ.copy()
    env["PATH"] = "/usr/local/go/bin:" + env.get("PATH", "")
    subprocess.run(["/app/bin/rate-limiter", "analyze",
                    "--traffic", "/app/data/traffic",
                    "--output", "/tmp/rerun_rl", "--format", "json"],
                   capture_output=True, env=env)
    rerun = json.loads(Path("/tmp/rerun_rl/limiter_report.json").read_text())
    original = json.loads(RJ.read_text())
    assert original == rerun
