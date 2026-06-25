"""Milestone 1 verifier — exercises the Quartz-dialect cron parser + nextExecutionTime over HTTP."""
import datetime
import subprocess
import requests

BASE = "http://localhost:8080"


def _parse(expression):
    return requests.post(f"{BASE}/api/cron/parse", json={"expression": expression}, timeout=10)


def _next(expression, frm, zone="UTC", count=1):
    return requests.post(
        f"{BASE}/api/cron/next",
        json={"expression": expression, "from": frm, "zone": zone, "count": count},
        timeout=10,
    )


def test_parse_canonical_quartz_daily_noon():
    """A canonical Quartz daily-at-noon expression parses as valid."""
    r = _parse("0 0 12 * * ?")
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    field_names = [f["name"] for f in body["fields"]]
    assert field_names == ["SECONDS", "MINUTES", "HOURS", "DAY_OF_MONTH", "MONTH", "DAY_OF_WEEK"]


def test_parse_with_named_dow_and_month():
    """Named DOW (MON-FRI) and named months (JAN-DEC) are normalised correctly."""
    r = _parse("0 15 10 ? * MON-FRI")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is True
    dow_field = next(f for f in body["fields"] if f["name"] == "DAY_OF_WEEK")
    # Quartz convention: 1=SUN..7=SAT, so MON-FRI is 2..6
    assert dow_field["values"] == [2, 3, 4, 5, 6]


def test_parse_mutual_exclusion_both_question_rejected():
    """Both dayOfMonth=? and dayOfWeek=? is rejected (exactly one must be ?)."""
    r = _parse("0 0 12 ? * ?")
    body = r.json()
    assert body["valid"] is False
    assert body.get("error")


def test_parse_mutual_exclusion_neither_question_rejected():
    """Neither dayOfMonth=? nor dayOfWeek=? is rejected (exactly one must be ?)."""
    r = _parse("0 0 12 * * *")
    body = r.json()
    assert body["valid"] is False


def test_parse_invalid_field_count():
    """Wrong field count yields valid=false with an explanatory error."""
    r = _parse("0 12 * * ?")
    body = r.json()
    assert body["valid"] is False
    assert "fields" in body.get("error", "")


def test_parse_step_syntax():
    """Step syntax */15 expands to {0, 15, 30, 45} for a 0-59 field."""
    r = _parse("0 */15 * * * ?")
    body = r.json()
    assert body["valid"] is True
    minutes = next(f for f in body["fields"] if f["name"] == "MINUTES")["values"]
    assert minutes == [0, 15, 30, 45]


def test_parse_last_day_of_month_marker():
    """The 'L' marker on dayOfMonth parses without throwing."""
    r = _parse("0 0 12 L * ?")
    body = r.json()
    assert body["valid"] is True
    dom = next(f for f in body["fields"] if f["name"] == "DAY_OF_MONTH")
    assert dom["special"] == "L"


def test_next_at_exact_minute_boundary():
    """next('0 15 10 ? * MON-FRI', 2026-06-15T10:00Z) yields 2026-06-15T10:15Z (Monday)."""
    r = _next("0 15 10 ? * MON-FRI", "2026-06-15T10:00:00Z", "UTC", 1)
    body = r.json()
    assert body["executions"] == ["2026-06-15T10:15:00Z"]


def test_next_five_weekdays():
    """Asking for the next 5 fires of a MON-FRI rule yields 5 distinct weekday timestamps."""
    r = _next("0 15 10 ? * MON-FRI", "2026-06-15T08:00:00Z", "UTC", 5)
    body = r.json()
    assert len(body["executions"]) == 5
    days = [datetime.datetime.fromisoformat(e.replace("Z", "+00:00")).weekday() for e in body["executions"]]
    assert days == [0, 1, 2, 3, 4]


def test_next_last_friday_of_june_2026():
    """'0 15 10 ? * 6L' fires on the last Friday of June 2026 = 2026-06-26."""
    r = _next("0 15 10 ? * 6L", "2026-06-01T00:00:00Z", "UTC", 1)
    body = r.json()
    assert body["executions"][0] == "2026-06-26T10:15:00Z"


def test_next_third_friday_pound_syntax():
    """'0 15 10 ? * 6#3' fires on the third Friday of the next month."""
    r = _next("0 15 10 ? * 6#3", "2026-06-01T00:00:00Z", "UTC", 1)
    body = r.json()
    # Third Friday of June 2026 = 2026-06-19
    assert body["executions"][0] == "2026-06-19T10:15:00Z"


def test_next_nearest_weekday_no_shift_when_target_is_weekday():
    """'0 0 12 15W * ?' picks the nearest weekday to the 15th. June 2026 15th = Mon, no shift."""
    r = _next("0 0 12 15W * ?", "2026-06-01T00:00:00Z", "UTC", 1)
    body = r.json()
    assert body["executions"][0] == "2026-06-15T12:00:00Z"


def test_next_nearest_weekday_sunday_shifts_to_monday():
    """'0 0 12 15W * ?' on Nov 2026 (15th = Sunday) shifts forward to Mon Nov 16."""
    r = _next("0 0 12 15W * ?", "2026-11-01T00:00:00Z", "UTC", 1)
    body = r.json()
    assert body["executions"][0] == "2026-11-16T12:00:00Z"


def test_next_last_weekday_of_month():
    """'0 0 12 LW * ?' picks the last weekday; May 2026 ends on Sun the 31st => Fri May 29."""
    r = _next("0 0 12 LW * ?", "2026-05-01T00:00:00Z", "UTC", 1)
    body = r.json()
    assert body["executions"][0] == "2026-05-29T12:00:00Z"


def test_next_leap_year_feb_29():
    """A '0 0 0 29 FEB ?' rule yields a leap year (2028) on the next eligible Feb 29."""
    r = _next("0 0 0 29 FEB ?", "2026-03-01T00:00:00Z", "UTC", 1)
    body = r.json()
    assert body["executions"][0] == "2028-02-29T00:00:00Z"


def test_next_dst_spring_forward_skipped_hour():
    """A 2:30am rule in America/New_York on the DST-skip day jumps past the skipped hour."""
    # 2026 US DST spring-forward: March 8, 2026. Local 02:00-02:59 doesn't exist.
    # Two valid behaviours: fire at the first post-gap instant (>= 03:00 EDT = 07:00Z)
    # OR skip to the next day's 02:30 EDT (= 06:30Z March 9). Both qualify as "did not
    # fire at the non-existent 02:30 EST" — assert the result is NOT in the gap.
    r = _next("0 30 2 * * ?", "2026-03-08T05:00:00Z", "America/New_York", 1)
    body = r.json()
    got = datetime.datetime.fromisoformat(body["executions"][0].replace("Z", "+00:00"))
    # Strictly after the non-existent 06:30Z March 8 (i.e. >= 07:00Z March 8),
    # and not later than 07:00Z March 9 (the next day's normal 02:00 EDT).
    assert got >= datetime.datetime.fromisoformat("2026-03-08T07:00:00+00:00")
    assert got <= datetime.datetime.fromisoformat("2026-03-09T07:00:00+00:00")


def test_next_dst_fall_back_fires_once():
    """A 1:30am rule in America/New_York on the DST-fall-back day fires at the earlier offset."""
    # 2026 US DST fall-back: November 1, 2026. Local 01:30 happens twice.
    r = _next("0 30 1 * * ?", "2026-11-01T04:00:00Z", "America/New_York", 1)
    body = r.json()
    # Earlier 01:30 occurrence = 01:30 EDT = 05:30Z.
    assert body["executions"][0] == "2026-11-01T05:30:00Z"


def test_no_quartz_dependency_in_image():
    """The compiled jar must not link against the org.quartz library or spring-quartz packages."""
    result = subprocess.run(
        ["jar", "tf", "/app/chronos.jar"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    # Filter for the actual third-party quartz packages, not the project's own
    # "QuartzCronExpression" class which references quartz by name only.
    forbidden = [
        line for line in result.stdout.splitlines()
        if "org/quartz/" in line.lower()
        or "spring-quartz" in line.lower()
        or line.lower().startswith("boot-inf/lib/quartz")
    ]
    assert not forbidden, f"quartz dependency classes leaked into the jar: {forbidden[:5]}"


def test_no_quartz_in_pom():
    """The Maven pom.xml must not declare a quartz dependency."""
    with open("/app/pom.xml") as f:
        pom = f.read().lower()
    assert "quartz" not in pom, "quartz dependency found in pom.xml"


def test_parse_invalid_field_value():
    """Field values outside the legal range yield valid=false."""
    r = _parse("0 0 25 * * ?")  # hour=25
    body = r.json()
    assert body["valid"] is False
