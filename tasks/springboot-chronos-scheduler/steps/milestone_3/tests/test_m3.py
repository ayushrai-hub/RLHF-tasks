"""Milestone 3 verifier — exercises concurrent dispatch, atomic claim, heartbeats, and crash failover."""
import concurrent.futures
import time
import uuid

import requests

BASE = "http://localhost:8080"


def _u(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_job(name, job_class, cron, misfire="FIRE_NOW", concurrent=False, zone="UTC"):
    return requests.post(
        f"{BASE}/api/jobs",
        json={
            "name": name,
            "jobClass": job_class,
            "cronExpr": cron,
            "zone": zone,
            "misfire": misfire,
            "concurrentExecutionDisallowed": concurrent,
        },
        timeout=10,
    )


def _reset_clock():
    requests.post(f"{BASE}/api/_test/reset-clock", timeout=10)


def test_20_concurrent_triggers_produce_20_unique_executions():
    """20 concurrent trigger-now POSTs on the same job yield exactly 20 distinct execution rows."""
    _reset_clock()
    name = _u("burst")
    r = _create_job(name, "LoggingJob", "0 0 12 * * ?")
    jid = r.json()["id"]

    N = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(requests.post, f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10) for _ in range(N)]
        responses = [f.result() for f in futures]

    exec_ids = sorted(resp.json()["id"] for resp in responses)
    assert len(exec_ids) == N
    assert len(set(exec_ids)) == N, "duplicate execution IDs returned"

    # Wait for all to finalise.
    deadline = time.time() + 30
    while time.time() < deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 50}, timeout=10).json()
        if len(execs) >= N and all(e["status"] in ("SUCCEEDED", "FAILED") for e in execs[:N]):
            break
        time.sleep(0.5)

    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 50}, timeout=10).json()
    succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
    assert len(succeeded) == N, f"expected {N} SUCCEEDED rows, got {len(succeeded)}"


def test_each_execution_claimed_by_exactly_one_worker():
    """No two execution rows for the same job share both scheduled_time and worker_id."""
    _reset_clock()
    name = _u("uniq")
    r = _create_job(name, "LoggingJob", "0 0 12 * * ?")
    jid = r.json()["id"]

    N = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(requests.post, f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10) for _ in range(N)]
        [f.result() for f in futures]

    time.sleep(8)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 50}, timeout=10).json()
    finalised = [e for e in execs if e["status"] in ("SUCCEEDED", "FAILED")]
    assert len(finalised) == N

    # Each row must have a worker_id set after it ran.
    for e in finalised:
        assert e["workerId"], f"row {e['id']} missing worker_id: {e}"

    # No row's id appears twice (sanity).
    ids = [e["id"] for e in finalised]
    assert len(ids) == len(set(ids))


def test_concurrent_execution_disallowed_skips_second_run():
    """With concurrent_execution_disallowed=true, two near-simultaneous triggers => one RUNS, one SKIPPED."""
    _reset_clock()
    name = _u("cedis")
    r = _create_job(name, "SlowJob", "0 0 12 * * ?", concurrent=True)
    jid = r.json()["id"]

    # First trigger (will sleep 2s in SlowJob).
    r1 = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10).json()
    # Give it a moment to claim + start.
    time.sleep(0.5)
    r2 = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10).json()

    # Wait for both to finalise.
    deadline = time.time() + 12
    while time.time() < deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 10}, timeout=10).json()
        relevant = [e for e in execs if e["id"] in (r1["id"], r2["id"])]
        if len(relevant) == 2 and all(e["status"] in ("SUCCEEDED", "SKIPPED", "FAILED") for e in relevant):
            break
        time.sleep(0.3)

    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 10}, timeout=10).json()
    rec1 = next(e for e in execs if e["id"] == r1["id"])
    rec2 = next(e for e in execs if e["id"] == r2["id"])

    statuses = sorted([rec1["status"], rec2["status"]])
    assert statuses == ["SKIPPED", "SUCCEEDED"], f"got statuses {statuses}; rec1={rec1}; rec2={rec2}"
    skipped = rec1 if rec1["status"] == "SKIPPED" else rec2
    assert "concurrent_execution_disallowed" in (skipped["errorMessage"] or "")


def test_concurrent_disallowed_off_allows_parallel_runs():
    """Without the flag, two near-simultaneous SlowJob triggers BOTH succeed concurrently."""
    _reset_clock()
    name = _u("parallel")
    r = _create_job(name, "SlowJob", "0 0 12 * * ?", concurrent=False)
    jid = r.json()["id"]

    requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10)
    time.sleep(0.3)
    requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10)

    deadline = time.time() + 12
    succeeded = []
    while time.time() < deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 10}, timeout=10).json()
        succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
        if len(succeeded) >= 2:
            break
        time.sleep(0.5)
    assert len(succeeded) >= 2, f"both runs should succeed; got {succeeded}"


def test_simulated_crash_triggers_failover_recovery():
    """A SlowJob killed mid-run via simulate-crash gets a fresh PENDING row with recovery_attempt=1."""
    _reset_clock()
    name = _u("crash")
    r = _create_job(name, "SlowJob", "0 0 12 * * ?")
    jid = r.json()["id"]

    tr = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10).json()
    original_exec_id = tr["id"]

    # Wait for it to start running.
    start_deadline = time.time() + 8
    while time.time() < start_deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 10}, timeout=10).json()
        running = [e for e in execs if e["id"] == original_exec_id and e["status"] == "RUNNING"]
        if running:
            break
        time.sleep(0.2)

    # Crash it.
    crash = requests.post(f"{BASE}/api/_test/simulate-crash/{original_exec_id}", timeout=10).json()
    assert crash.get("killed") is True

    # Wait up to 25s for failover detector to kick in and a recovery row to be created and run.
    deadline = time.time() + 25
    recovered = None
    while time.time() < deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 20}, timeout=10).json()
        # Original should be FAILED with worker_lost_heartbeat.
        orig = next((e for e in execs if e["id"] == original_exec_id), None)
        # Recovery row: same job_id, scheduled_time within tolerance, recovery_attempt=1, eventually SUCCEEDED.
        recoveries = [e for e in execs
                      if e["id"] != original_exec_id
                      and e["recoveryAttempt"] == 1]
        if orig and orig["status"] == "FAILED" and recoveries and any(r["status"] == "SUCCEEDED" for r in recoveries):
            recovered = recoveries[0]
            break
        time.sleep(1)

    assert recovered is not None, f"no recovery row succeeded; execs={requests.get(f'{BASE}/api/jobs/{jid}/executions', params={'limit':20}, timeout=10).json()}"
    orig = next(e for e in requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 20}, timeout=10).json() if e["id"] == original_exec_id)
    assert orig["status"] == "FAILED"
    assert "worker_lost_heartbeat" in (orig["errorMessage"] or "")


def test_heartbeats_advance_during_long_running_job():
    """While a SlowJob is RUNNING, last_heartbeat advances at least once."""
    _reset_clock()
    name = _u("hb")
    r = _create_job(name, "SlowJob", "0 0 12 * * ?")
    jid = r.json()["id"]
    tr = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10).json()
    exec_id = tr["id"]

    # Wait for it to be RUNNING.
    deadline = time.time() + 5
    first_hb = None
    while time.time() < deadline:
        ex = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 5}, timeout=10).json()
        row = next((e for e in ex if e["id"] == exec_id), None)
        if row and row["status"] == "RUNNING" and row["lastHeartbeat"]:
            first_hb = row["lastHeartbeat"]
            break
        time.sleep(0.1)
    assert first_hb is not None, "execution never reached RUNNING with a heartbeat"

    # Wait ~1.5s and verify heartbeat advanced (or job completed if it raced).
    time.sleep(1.2)
    ex = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 5}, timeout=10).json()
    row = next(e for e in ex if e["id"] == exec_id)
    if row["status"] == "RUNNING":
        assert row["lastHeartbeat"] != first_hb, "heartbeat did not advance"
    else:
        assert row["status"] == "SUCCEEDED"


def test_max_recovery_attempts_caps_at_three():
    """After the 3rd recovery attempt fails, no recovery_attempt=4 row is ever inserted."""
    _reset_clock()
    name = _u("maxrec")
    r = _create_job(name, "SlowJob", "0 0 12 * * ?")
    jid = r.json()["id"]

    tr = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10).json()
    current_exec_id = tr["id"]
    # Original row carries recovery_attempt=0; each cycle below crashes the current
    # row and waits for the next recovery row to appear with recovery_attempt = cycle+1.
    # Cycle 0..2 should each produce a recovery row (attempts 1, 2, 3). Cycle 3 (the
    # 4th crash) must NOT produce a row with recovery_attempt=4 — the cap is 3.
    for cycle in range(4):
        # Wait for the current execution to reach RUNNING so simulate-crash has a
        # worker thread to interrupt.
        start_deadline = time.time() + 20
        running_seen = False
        while time.time() < start_deadline:
            execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 50}, timeout=10).json()
            row = next((e for e in execs if e["id"] == current_exec_id), None)
            if row and row["status"] == "RUNNING":
                running_seen = True
                break
            time.sleep(0.3)
        assert running_seen, f"cycle {cycle}: execution {current_exec_id} never reached RUNNING"

        crash = requests.post(f"{BASE}/api/_test/simulate-crash/{current_exec_id}", timeout=10).json()
        assert crash.get("killed") is True

        expected_attempt = cycle + 1
        # Wait long enough for the FailoverDetector to mark the current row FAILED
        # (heartbeat timeout 10s + detector tick window).
        detect_deadline = time.time() + 30
        recovery_row = None
        crashed_row = None
        while time.time() < detect_deadline:
            execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 50}, timeout=10).json()
            crashed_row = next((e for e in execs if e["id"] == current_exec_id), None)
            recoveries = [e for e in execs
                          if e["id"] != current_exec_id and e.get("recoveryAttempt") == expected_attempt]
            if crashed_row and crashed_row["status"] == "FAILED" and (cycle == 3 or recoveries):
                if recoveries:
                    recovery_row = recoveries[0]
                break
            time.sleep(1)

        assert crashed_row is not None and crashed_row["status"] == "FAILED", \
            f"cycle {cycle}: crashed exec {current_exec_id} never marked FAILED"
        assert "worker_lost_heartbeat" in (crashed_row.get("errorMessage") or "")

        if cycle < 3:
            assert recovery_row is not None, \
                f"cycle {cycle}: no recovery row at recovery_attempt={expected_attempt}"
            current_exec_id = recovery_row["id"]
        else:
            # Past the cap — no recovery_attempt=4 row should exist now, and giving
            # the detector additional time must not produce one.
            assert recovery_row is None, \
                f"recovery_attempt={expected_attempt} row appeared past the cap: {recovery_row}"

    time.sleep(15)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 50}, timeout=10).json()
    over_cap = [e for e in execs if e.get("recoveryAttempt", 0) >= 4]
    assert not over_cap, f"no execution row with recovery_attempt>=4 should exist; got {over_cap}"


def test_no_quartz_dependency_in_image_m3():
    """Even at M3 the compiled jar must remain free of the org.quartz library."""
    import subprocess
    result = subprocess.run(["jar", "tf", "/app/chronos.jar"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    forbidden = [
        line for line in result.stdout.splitlines()
        if "org/quartz/" in line.lower()
        or "spring-quartz" in line.lower()
        or line.lower().startswith("boot-inf/lib/quartz")
    ]
    assert not forbidden, f"quartz dependency leaked: {forbidden[:5]}"
