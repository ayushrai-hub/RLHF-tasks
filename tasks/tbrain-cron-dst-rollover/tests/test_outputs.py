"""Behavioral checks for the dstcron daily-schedule resolver.

`dstcron` reads a small timezone description and a daily wall-clock schedule and,
for each query instant, prints the next UTC second at which the local wall clock
will next read the scheduled time. The timezone has a standard offset and a
daylight offset and two transition instants given directly in the input, so the
result is fully determined by the file and needs no external timezone database.

The reference below is an independent implementation of the documented contract:
local time is UTC plus the offset in force at that UTC instant; the daylight
offset is in force from the spring instant up to (but not including) the fall
instant. The next fire after a query is the earliest UTC second strictly after it
whose local reading equals the scheduled time of day, with a wall-clock time that
is skipped on the spring day resolving to the instant the clock advances and a
wall-clock time that recurs on the fall day resolving to its earlier occurrence.
None of this is part of the shipped program; every assertion reads `dstcron`
stdout only.
"""

import os
import subprocess
import tempfile

import pytest

APP = "/app"
BIN = "/app/dstcron"


def _build():
    r = subprocess.run(
        ["go", "build", "-o", BIN, "./cmd/dstcron"],
        cwd=APP,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, f"go build failed:\n{r.stdout}\n{r.stderr}"


@pytest.fixture(scope="module", autouse=True)
def built():
    _build()


# ---------------------------------------------------------------------------
# Independent reference implementation of the documented contract.
# ---------------------------------------------------------------------------

DAY = 86400


def offset_at(utc, std, dst, spring, fall):
    """Minutes east of UTC in force at the given UTC second."""
    if spring <= utc < fall:
        return dst
    return std


def to_local(utc, std, dst, spring, fall):
    return utc + offset_at(utc, std, dst, spring, fall) * 60


def expected_fire(now, target, std, dst, spring, fall):
    """Earliest UTC second strictly after `now` whose local reading is `target`
    seconds of the local day, honoring the spring gap and fall overlap.

    For each candidate, the local time is rendered for both the standard and the
    daylight offset; a candidate UTC instant is the genuine fire only if the
    offset that actually applies at that instant reproduces the target reading.
    The skipped spring interval has no such instant, so the fire is clamped to
    the moment the clock jumps; the repeated fall interval has two, so the
    earlier one wins. Scanning instants in increasing UTC order yields exactly
    this without special-casing either boundary explicitly.
    """
    candidates = set()
    # A local day's target maps to utc = local_midnight - off + target. Try every
    # offset on a wide band of days around the query so both transitions are
    # covered, then keep only the instants that truly read `target` locally and
    # land strictly after now.
    base_day = (now // DAY) - 2
    for d in range(base_day, base_day + 8):
        local_midnight = d * DAY
        for off in (std, dst):
            utc = local_midnight + target - off * 60
            candidates.add(utc)
    # Also include the exact transition instants as spring-gap landing points.
    candidates.add(spring)
    valid = []
    for utc in candidates:
        if utc <= now:
            continue
        loc = to_local(utc, std, dst, spring, fall)
        if loc % DAY == target:
            valid.append(utc)
    # Spring-gap: if the target reading is skipped on the spring day, the
    # transition instant itself is the fire. Detect by checking whether the
    # target falls in the skipped local interval just after the spring instant.
    gap = (dst - std) * 60
    if gap > 0:
        # local time just before the jump:
        local_before = to_local(spring - 1, std, dst, spring, fall)
        # the skipped local readings are (local_before+1 .. local_before+gap)
        for k in range(1, gap + 1):
            skipped = (local_before + k) % DAY
            if skipped == target and spring > now:
                valid.append(spring)
    if not valid:
        return None
    return min(valid)


def write_spec(path, std, dst, spring, fall, fire_hhmm, queries):
    lines = [
        f"offset_std {std}",
        f"offset_dst {dst}",
        f"spring_forward {spring}",
        f"fall_back {fall}",
        f"fire_at {fire_hhmm}",
    ]
    for q in queries:
        lines.append(f"next {q}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def run_spec(std, dst, spring, fall, fire_hhmm, queries):
    """Write a spec to a tempfile, run dstcron, return the list of int outputs."""
    hh, mm = fire_hhmm.split(":")
    target = int(hh) * 3600 + int(mm) * 60
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "spec.txt")
        write_spec(path, std, dst, spring, fall, fire_hhmm, queries)
        r = subprocess.run(
            [BIN, path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert r.returncode == 0, f"dstcron failed (rc={r.returncode}):\n{r.stderr}"
        out = [int(x) for x in r.stdout.split()]
    want = [expected_fire(q, target, std, dst, spring, fall) for q in queries]
    return out, want


# A fixed, self-consistent timezone for most cases: std=+60, dst=+120, with a
# spring instant and a fall instant placed on round local-day boundaries.
STD = 60
DST = 120
# spring at local 1970-... arbitrary large UTC second; fall well after.
SPRING = 8_553_600   # UTC second of the spring-forward jump
FALL = 26_697_600    # UTC second of the fall-back


# ---------------------------------------------------------------------------
# Group A -- ordinary days (the visible symptom).
# ---------------------------------------------------------------------------

def test_normal_day_single_query():
    """Far from any transition, the next fire is just the scheduled wall-clock
    time converted with the offset actually in force."""
    out, want = run_spec(STD, DST, SPRING, FALL, "09:00", [SPRING + 5 * DAY])
    assert out == want


def test_normal_day_before_spring_uses_standard_offset():
    """A query a few days before the spring jump fires with the standard offset
    (clock not yet advanced)."""
    out, want = run_spec(STD, DST, SPRING, FALL, "06:30", [SPRING - 5 * DAY])
    assert out == want


def test_normal_day_multiple_queries():
    """A batch of ordinary queries on both sides of the year resolves each to its
    own next fire."""
    qs = [SPRING - 9 * DAY, SPRING + 4 * DAY, FALL + 6 * DAY]
    out, want = run_spec(STD, DST, SPRING, FALL, "12:15", qs)
    assert out == want


# ---------------------------------------------------------------------------
# Group B -- the load-bearing transition behavior (no symptom names this).
# ---------------------------------------------------------------------------

def test_spring_gap_fires_at_transition_instant():
    """A scheduled wall-clock time that lands inside the interval the clock skips
    on the spring day does not exist; it must fire at the instant the clock
    advances. The scheduled time here sits one minute into the skipped hour."""
    # local just before jump = to_local(spring-1) ; pick a target inside the gap.
    local_before = to_local(SPRING - 1, STD, DST, SPRING, FALL) % DAY
    gap_target = (local_before + 30 * 60) % DAY  # 30 min into a 60-min gap
    hh = gap_target // 3600
    mm = (gap_target % 3600) // 60
    fire = f"{hh:02d}:{mm:02d}"
    # Query late on the day before the jump so the next fire lands on the spring
    # day, inside the skipped interval.
    out, want = run_spec(STD, DST, SPRING, FALL, fire, [SPRING - 1000])
    assert want[0] == SPRING, "fixture sanity: spring-gap target should clamp to jump"
    assert out == want


def test_fall_overlap_fires_at_first_occurrence():
    """A scheduled wall-clock time that recurs inside the interval repeated on the
    fall day occurs twice; it must fire at the earlier occurrence (the one still
    on the daylight offset)."""
    # local readings repeated are (to_local(fall, std) .. ) -- pick inside overlap.
    gap = (DST - STD) * 60
    local_after_fall = to_local(FALL, STD, DST, SPRING, FALL) % DAY
    over_target = (local_after_fall + 20 * 60) % DAY  # 20 min into repeated hour
    hh = over_target // 3600
    mm = (over_target % 3600) // 60
    fire = f"{hh:02d}:{mm:02d}"
    # First query sits before either occurrence, so the earlier (daylight) one
    # wins; the second sits between them, so the next fire is the later
    # (standard) occurrence on the same wall-clock day.
    qs = [FALL - 3600, FALL - 1000]
    out, want = run_spec(STD, DST, SPRING, FALL, fire, qs)
    # sanity: the two occurrences differ by `gap`; the earlier one is selected
    # first, and both read the same wall-clock time.
    earlier = want[0]
    later = earlier + gap
    assert to_local(earlier, STD, DST, SPRING, FALL) % DAY == over_target
    assert to_local(later, STD, DST, SPRING, FALL) % DAY == over_target
    assert earlier < later
    assert want[1] == later
    assert out == want


def test_query_just_before_spring_forward():
    """A query placed seconds before the spring jump, scheduled for a time that
    exists right after the jump, fires with the daylight offset already applied."""
    out, want = run_spec(STD, DST, SPRING, FALL, "04:00", [SPRING - 30])
    assert out == want


def test_query_crossing_fall_back():
    """A query just after the fall instant, scheduled for an ordinary time later
    that day, fires with the standard offset that is now back in force."""
    out, want = run_spec(STD, DST, SPRING, FALL, "23:30", [FALL + 60])
    assert out == want


def test_offset_chosen_correctly_each_side():
    """The same scheduled time resolves with different offsets depending on which
    side of the transitions the next fire lands on; both must be right."""
    qs = [SPRING - 1, FALL - 1]
    out, want = run_spec(STD, DST, SPRING, FALL, "15:45", qs)
    assert out == want


# ---------------------------------------------------------------------------
# Group C -- preservation (must stay correct on any valid build).
# ---------------------------------------------------------------------------

def test_far_from_transitions_batch():
    qs = [SPRING + 30 * DAY, SPRING + 31 * DAY, FALL + 40 * DAY]
    out, want = run_spec(STD, DST, SPRING, FALL, "08:00", qs)
    assert out == want


def test_same_day_later_fire():
    """A query earlier on a day than the scheduled time fires later the same local
    day, not the next."""
    # pick a query at local 00:10 of some day, fire at 07:00 same day.
    day = (SPRING + 10 * DAY)
    q = day  # arbitrary instant well inside DST
    out, want = run_spec(STD, DST, SPRING, FALL, "07:00", [q])
    assert out == want


def test_next_day_fire():
    """A query after the scheduled time on its day fires the next local day."""
    day = (FALL + 12 * DAY)
    out, want = run_spec(STD, DST, SPRING, FALL, "00:05", [day + 12 * 3600])
    assert out == want
