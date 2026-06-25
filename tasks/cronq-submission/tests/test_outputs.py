"""End-to-end tests for the cronq CLI.

Each test shells out to `java -jar /app/cronq.jar next ...`, parses the
JSON it prints, and checks the fire times against values worked out by
hand from the rules in docs/PROTOCOL.md. The bundled manifest carries
reference times for a subset of the cases; the rest are kept here only
so a fix that happens to satisfy the published cases still has to hold
up on the ones it can't see.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

APP = Path("/app")
JAR = APP / "cronq.jar"
DATA = APP / "data"
DOCS = APP / "docs"

# Combined SHA-256 of everything under /app/data/ (the cases plus the
# manifest). The expected fire times below are tied to these exact
# inputs, so if a case file or the manifest changes the comparison
# stops meaning anything -- this guard makes that loud instead of
# silent.
DATA_SHA256 = "8e82a85534dbd29432698045745ff938542e93cab04fcf692c66426941a4f915"

# Combined SHA-256 of the docs under /app/docs/. These spell out the
# contract the implementation has to meet; the instruction says to
# leave them alone, and this checks that they were.
DOCS_SHA256 = "a8966f0c6aa016f47285196732f7e25de8ddf07e62088b711760d344feeff401"


#  Expected fire times for every bundled case, keyed by case id. Worked
# out from PROTOCOL.md by hand. The six cases also present in the
# manifest are repeated here on purpose so the two never drift apart.
EXPECTED = {
    "c1_daily_midnight": [
        "2026-03-02T00:00:00Z", "2026-03-03T00:00:00Z", "2026-03-04T00:00:00Z",
    ],
    "c2_quarter_hour_boundary": [
        "2026-03-01T12:15:00Z", "2026-03-01T12:30:00Z",
        "2026-03-01T12:45:00Z", "2026-03-01T13:00:00Z",
    ],
    "c3_quarter_hour_offset": [
        "2026-03-01T12:15:00Z", "2026-03-01T12:30:00Z", "2026-03-01T12:45:00Z",
    ],
    "c4_business_hours_step": [
        "2026-03-01T09:00:00Z", "2026-03-01T12:00:00Z", "2026-03-01T15:00:00Z",
        "2026-03-01T18:00:00Z", "2026-03-01T21:00:00Z", "2026-03-02T09:00:00Z",
    ],
    "c5_dom_step": [
        "2026-03-05T00:00:00Z", "2026-03-15T00:00:00Z",
        "2026-03-25T00:00:00Z", "2026-04-05T00:00:00Z",
    ],
    "c6_friday_thirteenth": [
        "2026-02-06T00:00:00Z", "2026-02-13T00:00:00Z", "2026-02-20T00:00:00Z",
        "2026-02-27T00:00:00Z", "2026-03-06T00:00:00Z", "2026-03-13T00:00:00Z",
    ],
    "c7_first_and_fifteenth_monday": [
        "2026-01-05T00:00:00Z", "2026-01-12T00:00:00Z", "2026-01-15T00:00:00Z",
        "2026-01-19T00:00:00Z", "2026-01-26T00:00:00Z", "2026-02-01T00:00:00Z",
    ],
    "c8_march_noon": [
        "2026-03-01T12:00:00Z", "2026-03-02T12:00:00Z", "2026-03-03T12:00:00Z",
    ],
    "c9_leap_day": [
        "2028-02-29T00:00:00Z", "2032-02-29T00:00:00Z",
    ],
}


def _case(name):
    with open(DATA / "cases" / (name + ".json")) as f:
        return json.load(f)


def _manifest():
    with open(DATA / "manifest.json") as f:
        return json.load(f)


def _combined_sha256(root):
    h = hashlib.sha256()
    files = []
    for dirpath, _dirs, filenames in os.walk(root):
        for name in filenames:
            files.append(os.path.join(dirpath, name))
    for path in sorted(files):
        with open(path, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def _run(expr, frm, count):
    cmd = ["java", "-jar", str(JAR), "next",
           "--expr", expr, "--from", frm, "--count", str(count)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (
        f"cronq exited {r.returncode}\ncmd: {' '.join(cmd)}\nstderr:\n{r.stderr}"
    )
    return json.loads(r.stdout)


def _run_case(name):
    c = _case(name)
    return _run(c["expr"], c["from"], c["count"])


# ---- fixture / contract integrity -----------------------------------

def test_data_dir_unchanged():
    """The bundled `/app/data/` (case fixtures plus the manifest) has
    to be byte-identical to what the task shipped. The expected fire
    times baked into this file are tied to those exact inputs; this
    guard makes drift loud instead of silent."""
    actual = _combined_sha256(DATA)
    assert actual == DATA_SHA256, (
        f"/app/data/ has been modified\n"
        f"  expected sha256: {DATA_SHA256}\n"
        f"  actual sha256:   {actual}"
    )


def test_docs_dir_unchanged():
    """The contract docs under `/app/docs/` define the behaviour
    being verified; the instruction asks for them to stay untouched
    and this checks that."""
    actual = _combined_sha256(DOCS)
    assert actual == DOCS_SHA256, (
        f"/app/docs/ has been modified\n"
        f"  expected sha256: {DOCS_SHA256}\n"
        f"  actual sha256:   {actual}"
    )


# ---- output shape ---------------------------------------------------

def test_output_shape():
    """A successful run reports ok=true, echoes the expression and the
    start time back, and returns a list of matches. Everything else
    keys off this, so check it first."""
    out = _run_case("c1_daily_midnight")
    assert out["ok"] is True
    assert out["expr"] == "0 0 * * *"
    assert out["from"] == "2026-03-01T00:00:00Z"
    assert isinstance(out["matches"], list)


def test_count_is_honoured():
    """The number of times returned matches --count for a few cases
    with different counts, so a fix can't quietly return short or long
    lists."""
    for name in ("c3_quarter_hour_offset", "c4_business_hours_step", "c9_leap_day"):
        c = _case(name)
        out = _run_case(name)
        assert len(out["matches"]) == c["count"], (
            f"{name}: asked for {c['count']} times, got {len(out['matches'])}"
        )


def test_times_are_iso_utc_on_the_minute():
    """Fire times are reported in UTC, to the minute, in the
    YYYY-MM-DDTHH:MM:00Z shape the protocol describes."""
    out = _run_case("c4_business_hours_step")
    for t in out["matches"]:
        assert t.endswith(":00Z"), f"not on a whole minute / not UTC: {t}"
        assert t[4] == "-" and t[10] == "T", f"unexpected timestamp shape: {t}"


def test_times_are_strictly_increasing():
    """Successive fire times go forward in time, never repeat or go
    backwards."""
    for name in EXPECTED:
        out = _run_case(name)
        ts = out["matches"]
        assert ts == sorted(ts), f"{name}: times are not in order: {ts}"
        assert len(ts) == len(set(ts)), f"{name}: duplicate times: {ts}"


# ---- the published manifest -----------------------------------------

def test_matches_published_manifest():
    """For every case the manifest publishes, the CLI has to reproduce
    the listed times exactly."""
    ref = _manifest()["reference"]
    for name, expected in ref.items():
        out = _run_case(name)
        assert out["matches"] == expected, (
            f"{name}: CLI output disagrees with the manifest\n"
            f"  manifest: {expected}\n"
            f"  cli:      {out['matches']}"
        )


# ---- every bundled case ---------------------------------------------

def test_all_cases_match_expected():
    """Every bundled case, including the ones held back from the
    manifest, has to produce the hand-computed fire times."""
    for name, expected in EXPECTED.items():
        out = _run_case(name)
        assert out["matches"] == expected, (
            f"{name}: wrong fire times\n"
            f"  expected: {expected}\n"
            f"  actual:   {out['matches']}"
        )


# ---- individual cases, one per behaviour ----------------------------

def test_daily_midnight_skips_the_start_minute():
    """`from` lands exactly on a fire minute; the first result has to
    be the next day, not the start minute itself."""
    out = _run_case("c1_daily_midnight")
    assert out["matches"][0] == "2026-03-02T00:00:00Z"


def test_quarter_hour_offset_rounds_up():
    """Starting at :07 with a */15 schedule, the next fire is :15."""
    out = _run_case("c3_quarter_hour_offset")
    assert out["matches"][0] == "2026-03-01T12:15:00Z"


def test_stepped_hours_start_at_the_base():
    """`9/3` in the hour field means 9, 12, 15, ... -- the step counts
    up from 9, not from the bottom of the hour range."""
    out = _run_case("c4_business_hours_step")
    hours = [t[11:13] for t in out["matches"]]
    assert hours[:5] == ["09", "12", "15", "18", "21"], hours


def test_stepped_dom_starts_at_the_base():
    """`5/10` in the day-of-month field means the 5th, 15th, 25th, ..."""
    out = _run_case("c5_dom_step")
    days = [t[8:10] for t in out["matches"]]
    assert days == ["05", "15", "25", "05"], days


def test_friday_thirteenth_is_a_union():
    """`0 0 13 * FRI` fires on the 13th OR on any Friday, not only on
    Fridays that happen to be the 13th."""
    out = _run_case("c6_friday_thirteenth")
    assert out["matches"] == EXPECTED["c6_friday_thirteenth"]


def test_first_and_fifteenth_or_monday():
    """`0 0 1,15 * MON` fires on the 1st, the 15th, or any Monday."""
    out = _run_case("c7_first_and_fifteenth_monday")
    assert out["matches"] == EXPECTED["c7_first_and_fifteenth_monday"]


def test_month_name_is_honoured():
    """`MAR` in the month field restricts firing to March."""
    out = _run_case("c8_march_noon")
    assert all(t[5:7] == "03" for t in out["matches"]), out["matches"]


def test_leap_day_only():
    """Feb 29 only exists on leap years, so the next two fires are four
    years apart."""
    out = _run_case("c9_leap_day")
    assert out["matches"] == ["2028-02-29T00:00:00Z", "2032-02-29T00:00:00Z"]


# ---- error handling -------------------------------------------------

def test_bad_expression_exits_2():
    """A malformed expression is a usage error on the input, reported
    with exit code 2."""
    r = subprocess.run(
        ["java", "-jar", str(JAR), "next",
         "--expr", "0 0 99 * *", "--from", "2026-03-01T00:00:00Z", "--count", "1"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stderr}"


def test_missing_argument_exits_2():
    """Leaving off a required flag is a usage error, exit code 2."""
    r = subprocess.run(
        ["java", "-jar", str(JAR), "next", "--expr", "0 0 * * *"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stderr}"


def test_unsatisfiable_expression_exits_3():
    """A valid expression that can never fire (Feb 30 never exists)
    parses fine but finds nothing inside the search bound -- exit 3."""
    r = subprocess.run(
        ["java", "-jar", str(JAR), "next",
         "--expr", "0 0 30 2 *", "--from", "2026-03-01T00:00:00Z", "--count", "1"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 3, f"expected exit 3, got {r.returncode}: {r.stderr}"


# ---- verifier-only expressions (not in data/cases or the manifest) --
# These exercise the documented rules with values that appear nowhere in
# the bundled fixtures, so a fix has to be general, not case-matched.

def test_strictly_after_excludes_exact_start_offgrid():
    """`30 14 * * *` started exactly on a 14:30 fire minute must skip
    that instant and begin the next day; an off-by-one would echo the
    start time back."""
    out = _run("30 14 * * *", "2026-03-01T14:30:00Z", 3)
    assert out["matches"] == [
        "2026-03-02T14:30:00Z",
        "2026-03-03T14:30:00Z",
        "2026-03-04T14:30:00Z",
    ]


def test_dom_dow_union_first_or_wednesday():
    """`0 0 1 * WED` with both day fields restricted fires on the 1st
    OR on any Wednesday. AND semantics would demand the 1st itself be a
    Wednesday and collapse to the wrong, far-apart dates."""
    out = _run("0 0 1 * WED", "2026-04-01T12:00:00Z", 4)
    assert out["matches"] == [
        "2026-04-08T00:00:00Z",
        "2026-04-15T00:00:00Z",
        "2026-04-22T00:00:00Z",
        "2026-04-29T00:00:00Z",
    ]


def test_sunday_by_name_offgrid():
    """`15 9 * * SUN` fires 09:15 every Sunday. A Java-to-cron weekday
    mapping that drops Sunday would never match and fail to find any
    future fire."""
    out = _run("15 9 * * SUN", "2026-05-01T00:00:00Z", 3)
    assert out["matches"] == [
        "2026-05-03T09:15:00Z",
        "2026-05-10T09:15:00Z",
        "2026-05-17T09:15:00Z",
    ]


def test_single_value_step_anchors_at_value_offgrid():
    """`0 7/4 * * *` steps every 4 hours starting at hour 7, giving
    7/11/15/19/23. Anchoring the step at the field minimum (0) instead
    of 7 would shift the whole series."""
    out = _run("0 7/4 * * *", "2026-03-01T00:00:00Z", 5)
    assert out["matches"] == [
        "2026-03-01T07:00:00Z",
        "2026-03-01T11:00:00Z",
        "2026-03-01T15:00:00Z",
        "2026-03-01T19:00:00Z",
        "2026-03-01T23:00:00Z",
    ]


def test_hour_jump_resets_minute_to_field_floor_offgrid():
    """`45 6 * * *` fires at 06:45 daily. Reaching hour 6 from an earlier
    hour has to land the minute on the field's value (45), not snap it to
    the top of the hour; a reset to minute 0 would report 06:00, which the
    schedule never fires."""
    out = _run("45 6 * * *", "2026-03-01T00:00:00Z", 3)
    assert out["matches"] == [
        "2026-03-01T06:45:00Z",
        "2026-03-02T06:45:00Z",
        "2026-03-03T06:45:00Z",
    ]


def test_range_step_respects_range_ceiling_offgrid():
    """`0 0 1-25/7 * *` steps every 7 days across days 1..25, giving
    8/15/22 and then rolling into the next month -- day 29 is past the
    written ceiling of 25 and must not appear, even though it sits inside
    the field's own range."""
    out = _run("0 0 1-25/7 * *", "2026-03-01T00:00:00Z", 5)
    assert out["matches"] == [
        "2026-03-08T00:00:00Z",
        "2026-03-15T00:00:00Z",
        "2026-03-22T00:00:00Z",
        "2026-04-01T00:00:00Z",
        "2026-04-08T00:00:00Z",
    ]
