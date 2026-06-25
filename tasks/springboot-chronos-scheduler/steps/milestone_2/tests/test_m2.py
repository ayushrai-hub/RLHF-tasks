"""Milestone 2 verifier — exercises job CRUD, scheduler loop, dispatch, and misfire policies over HTTP."""
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


def _advance(seconds):
    return requests.post(f"{BASE}/api/_test/advance-clock", params={"seconds": seconds}, timeout=10)


def _reset_clock():
    return requests.post(f"{BASE}/api/_test/reset-clock", timeout=10)


def test_create_job_returns_id_and_next_fire_time():
    """POSTing a valid job returns an id and a computed next_fire_time."""
    name = _u("hourly")
    r = _create_job(name, "LoggingJob", "0 0 * * * ?")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] > 0
    assert body["nextFireTime"] is not None
    assert body["state"] == "ACTIVE"


def test_create_job_with_unknown_job_class_rejected():
    """An unknown jobClass yields a 400 with an explanatory error."""
    r = _create_job(_u("bad"), "TotallyMadeUpJob", "0 0 * * * ?")
    assert r.status_code == 400


def test_create_job_with_invalid_cron_rejected():
    """An invalid cron expression yields a 400."""
    r = _create_job(_u("badcron"), "LoggingJob", "totally not a cron")
    assert r.status_code == 400


def test_trigger_now_records_execution_and_runs():
    """POST /trigger-now inserts a PENDING execution which the dispatcher runs."""
    _reset_clock()
    name = _u("trig")
    r = _create_job(name, "LoggingJob", "0 0 12 * * ?")
    jid = r.json()["id"]

    tr = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10)
    assert tr.status_code == 200
    exec_id = tr.json()["id"]

    # Poll for completion up to 10s
    deadline = time.time() + 10
    final = None
    while time.time() < deadline:
        ex = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
        row = next((e for e in ex if e["id"] == exec_id), None)
        if row and row["status"] in ("SUCCEEDED", "FAILED"):
            final = row
            break
        time.sleep(0.5)
    assert final is not None, "execution never finalised"
    assert final["status"] == "SUCCEEDED"
    assert "logged-at" in (final["errorMessage"] or "")


def test_failing_job_marked_failed():
    """A FailingJob run via trigger-now is marked FAILED with the exception message."""
    _reset_clock()
    name = _u("fail")
    r = _create_job(name, "FailingJob", "0 0 12 * * ?")
    jid = r.json()["id"]
    tr = requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10)
    exec_id = tr.json()["id"]

    deadline = time.time() + 10
    final = None
    while time.time() < deadline:
        ex = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
        row = next((e for e in ex if e["id"] == exec_id), None)
        if row and row["status"] in ("SUCCEEDED", "FAILED"):
            final = row
            break
        time.sleep(0.5)
    assert final is not None
    assert final["status"] == "FAILED"
    assert "intentional failure" in (final["errorMessage"] or "")


def test_pause_then_resume_preserves_job():
    """Pause moves a job to PAUSED state; resume returns it to ACTIVE."""
    _reset_clock()
    name = _u("pr")
    r = _create_job(name, "LoggingJob", "0 0 * * * ?")
    jid = r.json()["id"]
    p = requests.post(f"{BASE}/api/jobs/{jid}/pause", timeout=10).json()
    assert p["state"] == "PAUSED"
    rs = requests.post(f"{BASE}/api/jobs/{jid}/resume", timeout=10).json()
    assert rs["state"] == "ACTIVE"


def test_resume_after_missed_fire_applies_fire_now_misfire():
    """Pause, advance the clock past a scheduled fire, then resume — FIRE_NOW must execute the missed fire on resume (not just flip state)."""
    _reset_clock()
    name = _u("pr-fn")
    r = _create_job(name, "LoggingJob", "0 */5 * * * ?", misfire="FIRE_NOW")
    jid = r.json()["id"]
    # Pause before any scheduled fire could happen.
    p = requests.post(f"{BASE}/api/jobs/{jid}/pause", timeout=10).json()
    assert p["state"] == "PAUSED"
    # Push the clock far past the next fire time while paused.
    _advance(6000)
    # Sanity: while paused + advanced, no execution rows should appear.
    time.sleep(2)
    pre = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
    assert not [e for e in pre if e["status"] == "SUCCEEDED"], \
        f"paused job must not run while paused; got {pre}"
    # Resume — the resume handler must consult the misfire policy and run the missed fire.
    rs = requests.post(f"{BASE}/api/jobs/{jid}/resume", timeout=10).json()
    assert rs["state"] == "ACTIVE"
    deadline = time.time() + 15
    succeeded = None
    while time.time() < deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
        succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
        if succeeded:
            break
        time.sleep(0.5)
    assert succeeded, \
        "resume on a FIRE_NOW job with a missed fire must produce a SUCCEEDED execution, proving handleResume invoked the misfire policy"


def test_resume_after_missed_fire_applies_fire_next_summary():
    """Pause, advance past several missed fires, then resume — FIRE_NEXT must insert exactly one MISFIRED summary row on resume."""
    _reset_clock()
    name = _u("pr-fn-summary")
    r = _create_job(name, "LoggingJob", "0 */5 * * * ?", misfire="FIRE_NEXT_WITH_REMAINING_COUNT")
    jid = r.json()["id"]
    p = requests.post(f"{BASE}/api/jobs/{jid}/pause", timeout=10).json()
    assert p["state"] == "PAUSED"
    _advance(6000)
    time.sleep(2)
    pre = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
    assert not pre, f"paused job must not produce any execution rows while paused; got {pre}"
    rs = requests.post(f"{BASE}/api/jobs/{jid}/resume", timeout=10).json()
    assert rs["state"] == "ACTIVE"
    # Give resume + scheduler ticks time to settle.
    time.sleep(4)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
    statuses = [e["status"] for e in execs]
    misfired = [e for e in execs if e["status"] == "MISFIRED"]
    succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
    assert len(misfired) == 1, \
        f"resume with FIRE_NEXT must produce exactly one MISFIRED summary row; got {statuses}"
    assert not succeeded, \
        f"FIRE_NEXT on resume must not run missed bodies; got SUCCEEDED rows {succeeded}"


def test_misfire_fire_now_produces_execution_after_advance():
    """A FIRE_NOW job whose next_fire_time slips behind runs the missed fire to completion."""
    _reset_clock()
    name = _u("mfn")
    r = _create_job(name, "LoggingJob", "0 */5 * * * ?", misfire="FIRE_NOW")
    jid = r.json()["id"]
    # Advance the clock far past the next fire time.
    _advance(6000)  # +100 minutes
    # Poll for a SUCCEEDED row produced by the misfire path — proves the body actually ran.
    deadline = time.time() + 15
    succeeded = None
    while time.time() < deadline:
        execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
        succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
        if succeeded:
            break
        time.sleep(0.5)
    assert succeeded, (
        "FIRE_NOW misfire must produce at least one SUCCEEDED execution, "
        "not just a queued PENDING row"
    )
    assert "logged-at" in (succeeded[0]["errorMessage"] or ""), \
        f"expected LoggingJob marker in errorMessage; got {succeeded[0]}"


def test_misfire_do_nothing_skips_missed_fires():
    """A DO_NOTHING job advanced past its fire time produces zero execution rows."""
    _reset_clock()
    name = _u("mdn")
    r = _create_job(name, "LoggingJob", "0 */5 * * * ?", misfire="DO_NOTHING")
    jid = r.json()["id"]
    _advance(6000)
    time.sleep(3)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
    statuses = [e["status"] for e in execs]
    # DO_NOTHING silently drops every missed fire, so no execution rows of any kind.
    assert not execs, \
        f"DO_NOTHING must drop missed fires silently; expected zero execution rows, got {statuses}"


def test_misfire_summary_writes_one_misfired_row():
    """A FIRE_NEXT_WITH_REMAINING_COUNT job advanced past N missed fires writes exactly one MISFIRED summary row and no SUCCEEDED row."""
    _reset_clock()
    name = _u("msu")
    r = _create_job(name, "LoggingJob", "0 */5 * * * ?", misfire="FIRE_NEXT_WITH_REMAINING_COUNT")
    jid = r.json()["id"]
    # Advance well past many missed fires (100 minutes ≈ 20 missed 5-min fires).
    _advance(6000)
    # Give the scheduler loop several ticks to be sure no follow-on rows appear.
    time.sleep(4)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=5).json()
    statuses = [e["status"] for e in execs]
    misfired = [e for e in execs if e["status"] == "MISFIRED"]
    succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
    assert len(misfired) == 1, \
        f"FIRE_NEXT must collapse all missed fires into exactly one MISFIRED summary row; got {statuses}"
    assert not succeeded, \
        f"FIRE_NEXT must not run any missed body; got SUCCEEDED rows {succeeded}"


def test_get_job_includes_last_executions():
    """GET /api/jobs/{id} returns the job plus its most recent executions array."""
    _reset_clock()
    name = _u("get")
    r = _create_job(name, "LoggingJob", "0 0 12 * * ?")
    jid = r.json()["id"]
    requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10)
    time.sleep(3)
    g = requests.get(f"{BASE}/api/jobs/{jid}", timeout=10).json()
    assert g["id"] == jid
    assert isinstance(g["executions"], list)
    assert len(g["executions"]) >= 1


def test_get_executions_supports_limit():
    """GET /api/jobs/{id}/executions?limit=N respects the limit parameter."""
    _reset_clock()
    name = _u("lim")
    r = _create_job(name, "LoggingJob", "0 0 12 * * ?")
    jid = r.json()["id"]
    for _ in range(5):
        requests.post(f"{BASE}/api/jobs/{jid}/trigger-now", timeout=10)
    time.sleep(4)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", params={"limit": 3}, timeout=10).json()
    assert len(execs) <= 3


def test_unknown_job_id_returns_404():
    """GET on a non-existent job id returns 404 with a structured error."""
    r = requests.get(f"{BASE}/api/jobs/99999999", timeout=10)
    assert r.status_code == 404
    assert "job_not_found" in r.text


def test_pause_prevents_scheduler_loop_from_firing():
    """A paused job whose next_fire_time elapses does not get a SUCCEEDED execution row."""
    _reset_clock()
    name = _u("pause-skip")
    r = _create_job(name, "LoggingJob", "0 */5 * * * ?", misfire="FIRE_NOW")
    jid = r.json()["id"]
    requests.post(f"{BASE}/api/jobs/{jid}/pause", timeout=10)
    _advance(6000)
    time.sleep(3)
    execs = requests.get(f"{BASE}/api/jobs/{jid}/executions", timeout=10).json()
    succeeded = [e for e in execs if e["status"] == "SUCCEEDED"]
    assert not succeeded, f"paused job should not produce SUCCEEDED rows; got {execs}"
