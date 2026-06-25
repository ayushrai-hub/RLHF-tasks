"""Verifier for the Perl Marisol-inquiry CLI.

The agent ships inquire.pl and inquire.sh under /app/build, drives a Rails JSON
API to work the case of the lost steamship Marisol, draws the required records
across at least one full pass of the file, and enters a finding of four
particulars (party, means, place, minute).

The case answer is reasoned from the record, not read from the database or
fished from the API: the shipped image has no solution loaded, and the live
finding endpoint returns a "pending" verdict with no per-particular feedback.
The sealed conclusion is injected only at verification time (see conftest.py),
so the adjudicated verdict reflects the agent's reasoning.
"""
from __future__ import annotations

import json
import re
import socket
import subprocess
from pathlib import Path

import pytest


BUILD = Path("/app/build")
OUTPUT = Path("/app/output")
INQUIRE_PL = BUILD / "inquire.pl"
INQUIRE_SH = BUILD / "inquire.sh"
FINDING = OUTPUT / "finding.json"
WRONG_OUT = OUTPUT / "wrong_finding.json"

# The records the office requires in the working file at the moment of finding.
REQUIRED_RECORDS = {
    "rec-salvage-diver",
    "rec-cargo-tally",
    "rec-policy",
    "rec-owner-letters",
    "rec-manifest",
}

# The case truth. The surface of the file presses an accident with the master at
# fault; the record bears the owner's deliberate scuttling.
EXPECTED_FINDING = {
    "party": "par-veil",
    "means": "scuttle-seacock",
    "place": "loc-engine-room",
    "minute": "23:15",
}

VALID_SECTIONS = {
    "sec-records-room", "sec-surveyors-office", "sec-owners-office",
    "sec-salvage-store", "sec-survivors-hall",
}


# ---------------------------------------------------------------------------
# Delivery shape
# ---------------------------------------------------------------------------

def test_inquire_sh_present():
    assert INQUIRE_SH.exists(), f"missing entry point at {INQUIRE_SH}"
    assert INQUIRE_SH.stat().st_mode & 0o111, "inquire.sh must be executable"


def test_inquire_pl_present_and_parses():
    assert INQUIRE_PL.exists(), f"missing client at {INQUIRE_PL}"
    rc = subprocess.run(
        ["perl", "-c", str(INQUIRE_PL)], capture_output=True, text=True, timeout=30
    )
    assert rc.returncode == 0, f"inquire.pl is not valid Perl:\n{rc.stderr}"


def test_inquire_sh_invokes_inquire_pl():
    sh = INQUIRE_SH.read_text()
    assert re.search(r"\bperl\b[^\n]*inquire\.pl", sh), (
        "inquire.sh must invoke 'perl ... inquire.pl'"
    )


def test_inquire_pl_holds_the_logic():
    """The HTTP calls, record handling, and finding submission must live in Perl,
    not in bash/curl. inquire.pl must contain an HTTP client and enter the finding."""
    pl = INQUIRE_PL.read_text()
    assert re.search(r"HTTP::Tiny|LWP::|HTTP::Request|Net::HTTP|IO::Socket", pl), (
        "inquire.pl must contain HTTP client logic (e.g. HTTP::Tiny)"
    )
    assert "finding" in pl, "inquire.pl must enter the finding (POST .../finding) from Perl"
    assert re.search(r"retrieve", pl), "inquire.pl must draw records via the retrieve endpoint"


def test_finding_json_present():
    assert FINDING.exists(), f"missing finding output at {FINDING}"


# ---------------------------------------------------------------------------
# Finding contents
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def finding(clean_room):
    return json.loads(FINDING.read_text())


def test_finding_has_inquiry_id(finding):
    iid = finding.get("inquiry_id")
    assert isinstance(iid, str) and iid, f"inquiry_id missing or empty: {iid!r}"


def test_finding_echoes_schema_version(finding):
    val = finding.get("config_schema_version")
    assert isinstance(val, str) and val, f"missing config_schema_version: {val!r}"


def test_finding_echoes_required_records(finding):
    val = finding.get("required_record_ids")
    assert isinstance(val, list), f"required_record_ids must be a list; got {type(val).__name__}"
    missing = REQUIRED_RECORDS - set(val)
    assert not missing, f"required_record_ids missing case-required ids: {sorted(missing)}"


def test_required_records_drawn(finding):
    """Final working file must hold the required records. The API only adds a
    record when the assessor is in its section, so this also proves the archive
    was genuinely worked (including the salvage store and the owners' file room)."""
    have = set(finding.get("final_state", {}).get("retrieved", []))
    missing = REQUIRED_RECORDS - have
    assert not missing, f"final working file missing required records: {sorted(missing)}"


def test_pass_completed(finding):
    day = finding.get("final_state", {}).get("day_number")
    assert isinstance(day, int) and day >= 2, (
        f"day_number must be >= 2 (one full pass completed); got {day!r}"
    )


def test_finding_particulars_correct(finding):
    """The four particulars must match the case truth: the owner's deliberate
    scuttling, not the surface finding of an accident with the master at fault."""
    entered = finding.get("finding")
    assert isinstance(entered, dict), f"missing finding object: {entered!r}"
    for key, expected in EXPECTED_FINDING.items():
        assert entered.get(key) == expected, (
            f"finding {key} = {entered.get(key)!r}, expected {expected!r}"
        )


def test_finding_verdict_sound(finding):
    verdict = finding.get("verdict")
    assert isinstance(verdict, dict), f"missing verdict object: {verdict!r}"
    assert verdict.get("verdict") == "sound", (
        f"expected verdict=sound, got {verdict.get('verdict')!r}; reasons={verdict.get('reasons')!r}"
    )
    assert verdict.get("reasons") in ([], None), (
        f"a sound finding should carry no reasons; got {verdict.get('reasons')!r}"
    )


def test_final_inquiry_status_closed_sound(finding):
    status = finding.get("final_state", {}).get("status")
    assert status == "closed-sound", f"final inquiry status not 'closed-sound': {status!r}"


def test_final_state_shape(finding):
    final = finding.get("final_state")
    assert isinstance(final, dict), f"final_state must be an object: {final!r}"
    expected = {"inquiry_id", "current_section", "day_number", "retrieved", "journal", "status"}
    missing = expected - set(final.keys())
    assert not missing, f"final_state missing fields the GET /api/inquiries/{{id}} response carries: {sorted(missing)}"


def test_actions_recorded(finding):
    actions = finding.get("actions")
    assert isinstance(actions, list) and len(actions) >= 10, (
        f"expected at least 10 logged actions, got {len(actions) if isinstance(actions, list) else 'none'}"
    )
    kinds = {a.get("kind") for a in actions if isinstance(a, dict)}
    for required in ("go", "retrieve", "finding"):
        assert required in kinds, f"action log missing kind={required}: {sorted(kinds)}"
    for a in actions:
        if isinstance(a, dict) and a.get("kind") == "go":
            sec = a.get("to") or a.get("section_id") or a.get("from")
            assert sec in VALID_SECTIONS, f"go action references an unknown section: {sec!r}"
        if isinstance(a, dict) and a.get("kind") == "retrieve":
            assert re.match(r"^rec-[a-z0-9-]+$", str(a.get("record_id"))), (
                f"retrieve action lacks a real record id: {a.get('record_id')!r}"
            )


def test_actions_exactly_one_finding(finding):
    actions = finding.get("actions") or []
    fins = [a for a in actions if isinstance(a, dict) and a.get("kind") == "finding"]
    assert len(fins) == 1, f"expected exactly one finding in actions, got {len(fins)}"


# ---------------------------------------------------------------------------
# Losing path
# ---------------------------------------------------------------------------

def test_wrong_finding_unsound():
    result = subprocess.run(
        [str(INQUIRE_SH), "wrong"], capture_output=True, text=True, timeout=400
    )
    assert result.returncode == 0, f"inquire.sh wrong failed: {result.stderr[:400]}"
    assert WRONG_OUT.exists(), f"inquire.sh wrong did not write {WRONG_OUT}"
    payload = json.loads(WRONG_OUT.read_text())
    verdict = payload.get("verdict", {})
    assert verdict.get("verdict") == "unsound", (
        f"wrong finding should be unsound; got {verdict.get('verdict')!r}, reasons={verdict.get('reasons')!r}"
    )
    reasons = verdict.get("reasons") or []
    bad = {"party_wrong", "means_wrong", "place_wrong", "minute_wrong"}
    assert bad & set(reasons), (
        f"unsound finding must list at least one wrong particular; got {reasons!r}"
    )


def test_wrong_finding_has_inquiry_id():
    assert WRONG_OUT.exists(), "test_wrong_finding_unsound must run first"
    payload = json.loads(WRONG_OUT.read_text())
    iid = payload.get("inquiry_id")
    assert isinstance(iid, str) and iid, f"wrong_finding.json missing inquiry_id: {iid!r}"


def test_wrong_finding_submitted_shape():
    assert WRONG_OUT.exists(), "test_wrong_finding_unsound must run first"
    payload = json.loads(WRONG_OUT.read_text())
    submitted = payload.get("submitted")
    assert isinstance(submitted, dict), f"wrong_finding.json: 'submitted' must be an object; got {submitted!r}"
    for key in ("party", "means", "place", "minute"):
        assert key in submitted, f"wrong_finding.json: submitted missing required field {key!r}"


def test_wrong_inquiry_differs_from_play(finding):
    assert WRONG_OUT.exists(), "test_wrong_finding_unsound must run first"
    wrong_id = json.loads(WRONG_OUT.read_text()).get("inquiry_id")
    play_id = finding.get("inquiry_id")
    assert wrong_id and play_id, f"missing inquiry_id (play={play_id!r}, wrong={wrong_id!r})"
    assert wrong_id != play_id, "the wrong run reused the play inquiry; the spec requires a fresh inquiry"


# ---------------------------------------------------------------------------
# API-driven behaviour and anti-cheat
# ---------------------------------------------------------------------------

def _client_blob() -> str:
    parts = []
    for p in (INQUIRE_PL, INQUIRE_SH):
        if p.exists():
            parts.append(p.read_text())
    return "\n".join(parts)


def test_client_drove_api_at_runtime(play_audit):
    assert play_audit, "no API requests recorded; the client never drove the Rails API at runtime"
    haystack = "\n".join(play_audit)
    for path in ("/healthz", "/api/config", "/api/sections", "/api/parties", "/api/records", "/api/inquiries"):
        assert path in haystack, f"no request to {path} recorded; the client did not call this endpoint at runtime"
    for action in ("retrieve", "finding", "go"):
        assert action in haystack, f"no {action} request recorded; the play run did not drive this action via the API"


def test_play_made_single_finding(play_audit):
    """A single play run must enter exactly one finding. More than one means the
    client is fishing for the answer rather than reasoning it from the record."""
    calls = [r for r in play_audit if "finding" in r and "POST" in r.upper()]
    assert len(calls) == 1, (
        f"the play run entered {len(calls)} findings; exactly one is expected. "
        f"Entering several is fishing, not reasoning."
    )


def test_play_did_not_brute_force_inquiries(play_audit):
    creates = [
        r for r in play_audit
        if r.strip().upper().startswith("POST") and re.search(r"/api/inquiries/?$", r)
    ]
    assert len(creates) <= 2, (
        f"the play run opened {len(creates)} inquiries; a reasoning client needs one. "
        f"Many inquiries indicate brute-forcing the finding across fresh passes."
    )


def test_client_does_not_bypass_db():
    blob = _client_blob()
    for forbidden in ("/app/api/db", "case.sqlite3", "FROM truth", "from truth"):
        assert forbidden not in blob, (
            f"client references the API's private database ({forbidden!r}); the answer "
            "must come from the record and the HTTP API only"
        )


def test_outputs_deterministic_on_rerun(finding):
    initial_finding = finding.get("finding")
    initial_retrieved = set(finding.get("final_state", {}).get("retrieved", []))
    result = subprocess.run(
        [str(INQUIRE_SH), "play"], capture_output=True, text=True, timeout=400
    )
    assert result.returncode == 0, f"rerun failed: {result.stderr[:400]}"
    rerun = json.loads(FINDING.read_text())
    assert rerun.get("verdict", {}).get("verdict") == "sound", "rerun verdict was not sound"
    rerun_retrieved = set(rerun.get("final_state", {}).get("retrieved", []))
    assert REQUIRED_RECORDS.issubset(rerun_retrieved), "rerun did not re-draw the required records"
    assert rerun_retrieved == initial_retrieved, (
        f"drawn records changed between runs: initial={sorted(initial_retrieved)} rerun={sorted(rerun_retrieved)}"
    )
    assert rerun.get("finding") == initial_finding, (
        f"finding changed between runs: initial={initial_finding} rerun={rerun.get('finding')}"
    )


def test_api_server_not_lingering():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", 3000))
    except OSError as e:
        pytest.fail(f"Port 3000 still bound after inquire.sh exit: {e}")
    finally:
        sock.close()
