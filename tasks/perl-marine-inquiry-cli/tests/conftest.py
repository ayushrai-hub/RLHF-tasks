"""Verifier session fixtures for the Marisol inquiry.

The case answer is NOT present in the agent's environment. The shipped
case.sqlite3 has an empty `truth` table, so an agent can neither read the sealed
finding from the database nor fish it out of the live API: with no solution
loaded, POST /finding returns a "pending" verdict with no per-particular
feedback, so there is nothing to brute-force against.

At verification time this module rebuilds the case database from a pristine seed
that ships with the tests (so an agent who tampered with /app/api/db cannot
influence grading), injects the case office's sealed conclusion into the `truth`
table, and runs the agent's inquire.sh in a clean room. Only then is the finding
adjudicated. Reasoning the answer out of the record is the only path that yields
a sound finding; reading a database or probing the API does not.
"""
from __future__ import annotations

import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

FIXTURE_SEED = Path(__file__).resolve().parent / "fixtures" / "seed.sql"
CASE_DB = Path("/app/api/db/case.sqlite3")
AUDIT_DB = Path("/app/state/api-audit.sqlite3")
RAILS_LOG = Path("/app/state/rails.log")
INQUIRE_SH = Path("/app/build/inquire.sh")

# The case office's sealed finding, supplied only at submission review. It lives
# with the tests, never in the agent image.
TRUTH = {
    "party": "par-veil",
    "means": "scuttle-seacock",
    "place": "loc-engine-room",
    "minute": "23:15",
}


def _pkill_puma() -> None:
    subprocess.run(
        ["pkill", "-KILL", "-f", "puma .*config.ru"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _rebuild_db_with_truth() -> None:
    """Rebuild every static table from the pristine test seed, then inject the
    sealed finding. Immune to any agent edits of /app/api/db/case.sqlite3."""
    _pkill_puma()
    time.sleep(0.4)
    CASE_DB.parent.mkdir(parents=True, exist_ok=True)
    if CASE_DB.exists():
        CASE_DB.unlink()
    proc = subprocess.run(
        ["sqlite3", str(CASE_DB)],
        input=FIXTURE_SEED.read_bytes(),
        capture_output=True,
    )
    assert proc.returncode == 0, (
        f"seed rebuild failed: {proc.stderr.decode(errors='ignore')}"
    )
    conn = sqlite3.connect(str(CASE_DB))
    try:
        conn.execute("DELETE FROM truth")
        conn.execute(
            "INSERT INTO truth (id, party, means, place, minute) VALUES (1, ?, ?, ?, ?)",
            (TRUTH["party"], TRUTH["means"], TRUTH["place"], TRUTH["minute"]),
        )
        conn.commit()
    finally:
        conn.close()


def _as_text(v) -> str:
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", "ignore")
    return str(v)


def _read_audit() -> list[str]:
    rows: list[str] = []
    if AUDIT_DB.exists():
        try:
            conn = sqlite3.connect(str(AUDIT_DB))
            try:
                rows.extend(
                    f"{_as_text(m)} {_as_text(p)}" for m, p in conn.execute(
                        "SELECT method, path FROM audit_requests"
                    )
                )
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    if not rows and RAILS_LOG.exists():
        rows.extend(RAILS_LOG.read_text(encoding="utf-8", errors="ignore").splitlines())
    return rows


_PLAY_AUDIT: list[str] = []


@pytest.fixture(scope="session", autouse=True)
def clean_room():
    """Inject the sealed finding and re-run inquire.sh play in a clean room.

    The agent's own run (in an environment without the solution) produces only a
    'pending' verdict; grading does not trust it. We rebuild the database, inject
    the truth, clear the request audit, and run the deliverable so the finding is
    adjudicated against the real conclusion and the audit reflects only this run.
    """
    assert INQUIRE_SH.exists(), f"missing deliverable at {INQUIRE_SH}"
    _rebuild_db_with_truth()
    if AUDIT_DB.exists():
        AUDIT_DB.unlink()
    if RAILS_LOG.exists():
        RAILS_LOG.unlink()
    proc = subprocess.run(
        [str(INQUIRE_SH), "play"],
        capture_output=True,
        text=True,
        timeout=400,
    )
    assert proc.returncode == 0, (
        "inquire.sh play failed in clean room:\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )
    _PLAY_AUDIT.clear()
    _PLAY_AUDIT.extend(_read_audit())
    yield
    _pkill_puma()


@pytest.fixture(scope="session")
def play_audit(clean_room) -> list[str]:
    """The (METHOD PATH) strings recorded during the clean-room play run only."""
    return list(_PLAY_AUDIT)


@pytest.fixture(scope="session")
def api_request_audit() -> list[str]:
    """Live request audit (accumulates across play plus any wrong/rerun runs)."""
    return _read_audit()
