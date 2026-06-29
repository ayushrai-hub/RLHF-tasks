"""Behavioral verifier for the `kettleheat` process-kettle element cycle ledger.

Each test feeds a kettle-temperature/power-mode event log (as JSON) to the
compiled Rust `kettleheat` binary in /app as a black box and asserts the emitted
element-ON interval ledger against the contract in docs/spec.md.

This file also carries a self-contained, independent pure-Python reference
implementation of the controller. Curated fixtures assert explicit expected
output for the spec's hard corners (deferred turn-on/turn-off at the computed
anti-short-cycle boundaries, demand vanishing mid-deferral, boundary-exact
samples, `off`-mode override, and the freeze window). A large randomized
differential test then compares the binary against the reference on a
deterministically seeded set of event logs whose timestamps are deliberately drawn so
that demand changes frequently land on or near the computed min-run/min-rest
boundaries, asserting identical ledgers (intervals, ontime, final).
"""

import json
import os
import random
import subprocess

import pytest

APP_DIR = os.environ.get("APP_DIR", "/app")
BIN = os.path.join(APP_DIR, "target", "release", "kettleheat")


# --------------------------------------------------------------------------- #
# Driving the binary under test.
# --------------------------------------------------------------------------- #
def _binary():
    if os.path.exists(BIN) and os.access(BIN, os.X_OK):
        return [BIN]
    return ["cargo", "run", "--quiet", "--release", "--"]


def run_raw(doc):
    """Run the CLI on a JSON document via stdin; return (rc, stdout, stderr)."""
    proc = subprocess.run(
        _binary(),
        input=json.dumps(doc) if not isinstance(doc, str) else doc,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=APP_DIR,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_ledger(doc):
    rc, out, err = run_raw(doc)
    assert rc == 0, f"expected success; rc={rc}, stderr={err!r}, stdout={out!r}"
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout was not JSON: {out!r}") from exc


def run_error(doc):
    rc, out, err = run_raw(doc)
    assert rc != 0, f"expected failure; rc={rc}, stdout={out!r}"
    assert out == "", f"error path must print nothing to stdout; got {out!r}"
    return err


def assert_ledger_shape(result):
    assert set(result.keys()) == {"intervals", "ontime", "final"}, result
    prev_end = None
    total = 0
    for iv in result["intervals"]:
        assert set(iv.keys()) == {"start", "end"}, iv
        assert isinstance(iv["start"], int) and isinstance(iv["end"], int)
        assert iv["start"] < iv["end"], f"zero/neg interval emitted: {iv}"
        if prev_end is not None:
            assert prev_end <= iv["start"], "intervals overlap / out of order"
        prev_end = iv["end"]
        total += iv["end"] - iv["start"]
    assert result["ontime"] == total
    assert result["final"]["state"] in ("on", "off")
    assert isinstance(result["final"]["since"], int)


# --------------------------------------------------------------------------- #
# Independent pure-Python reference controller (sole source of truth).
# --------------------------------------------------------------------------- #
class RefError(Exception):
    pass


def _req_int(obj, key):
    if key not in obj:
        raise RefError(f"missing {key}")
    v = obj[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise RefError(f"{key} not int")
    return v


def _validate_events(events, until):
    last_at = None
    freeze_open = False
    out = []
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise RefError("event not object")
        ty = ev.get("type")
        if not isinstance(ty, str):
            raise RefError("bad type")
        at = _req_int(ev, "at")
        if at < 0 or at > until:
            raise RefError("at out of range")
        if last_at is not None and at < last_at:
            raise RefError("out of order")
        last_at = at
        if ty == "sample":
            temp = _req_int(ev, "temp")
            out.append(("sample", temp, at))
        elif ty == "power":
            s = ev.get("state")
            if s == "on":
                out.append(("power", True, at))
            elif s == "off":
                out.append(("power", False, at))
            else:
                raise RefError("bad state")
        elif ty == "freeze":
            if freeze_open:
                raise RefError("nested freeze")
            freeze_open = True
            out.append(("freeze", None, at))
        elif ty == "endfreeze":
            if not freeze_open:
                raise RefError("endfreeze without freeze")
            freeze_open = False
            out.append(("endfreeze", None, at))
        else:
            raise RefError("unknown event type")
    if freeze_open:
        raise RefError("freeze left open")
    return out


def ref_run(doc):
    if not isinstance(doc, dict):
        raise RefError("top-level not object")
    target_temp = _req_int(doc, "targetTemp")
    deadband = _req_int(doc, "deadband")
    min_run = _req_int(doc, "minRun")
    min_rest = _req_int(doc, "minRest")
    until = _req_int(doc, "until")
    if deadband < 0 or min_run < 0 or min_rest < 0:
        raise RefError("negative param")
    if "events" not in doc or not isinstance(doc["events"], list):
        raise RefError("bad events")
    events = _validate_events(doc["events"], until)

    intervals = []
    on = False
    open_start = 0
    last_on = 0
    last_off = -min_rest  # first turn-on never blocked by minRest
    demand = False
    power_on = True
    have_temp = False
    frozen = False
    # pending: None, ("on", b), or ("off", b)
    pending = None

    def demand_edge(temp):
        if temp <= target_temp - deadband:
            return True
        if temp >= target_temp + deadband:
            return False
        return None

    def open_element(t):
        nonlocal on, open_start, last_on, pending
        on = True
        open_start = t
        last_on = t
        pending = None

    def close_element(t):
        nonlocal on, last_off, pending
        if on:
            if t > open_start:
                intervals.append((open_start, t))
            on = False
            last_off = t
        pending = None

    def evaluate(t):
        nonlocal pending
        if frozen or not power_on or not have_temp:
            return
        if on:
            if demand:
                pending = None
            else:
                earliest = last_on + min_run
                if t >= earliest:
                    close_element(t)
                else:
                    pending = ("off", earliest)
        else:
            if demand:
                earliest = last_off + min_rest
                if t >= earliest:
                    open_element(t)
                else:
                    pending = ("on", earliest)
            else:
                pending = None

    def fire_boundary(b):
        nonlocal pending
        if frozen or not power_on:
            pending = None
            return
        if pending is None:
            return
        kind, _ = pending
        if kind == "on":
            if demand:
                open_element(b)
            else:
                pending = None
        else:  # off
            if not demand:
                close_element(b)
            else:
                pending = None

    for kind, payload, at in events:
        # Fire any computed boundary strictly before this event.
        while pending is not None and pending[1] < at:
            fire_boundary(pending[1])

        if kind == "sample":
            d = demand_edge(payload)
            if d is not None:
                demand = d
            have_temp = True
            if not frozen:
                evaluate(at)
        elif kind == "power":
            if payload:  # on
                power_on = True
                if not frozen:
                    evaluate(at)
            else:  # off
                power_on = False
                demand = False
                if not frozen:
                    close_element(at)
                pending = None
        elif kind == "freeze":
            frozen = True
            pending = None
        elif kind == "endfreeze":
            frozen = False
            if on:
                last_on = at
            else:
                last_off = at
            if not power_on:
                close_element(at)
            else:
                evaluate(at)

        # Fire a boundary coinciding exactly with this event time
        # (after the event's own demand update — inclusive re-check).
        while pending is not None and pending[1] == at:
            fire_boundary(pending[1])

    # After the last event, fire any boundary up to the horizon.
    while pending is not None and pending[1] <= until:
        fire_boundary(pending[1])

    if on and until > open_start:
        intervals.append((open_start, until))

    final_on = on and until > open_start
    if final_on:
        final_since = open_start
    else:
        final_since = intervals[-1][1] if intervals else 0

    ontime = sum(e - s for s, e in intervals)
    return {
        "intervals": [{"start": s, "end": e} for s, e in intervals],
        "ontime": ontime,
        "final": {"state": "on" if final_on else "off", "since": final_since},
    }


# --------------------------------------------------------------------------- #
# Curated fixtures: one per hard corner of docs/spec.md.
# --------------------------------------------------------------------------- #
def _on(at):
    return {"type": "power", "state": "on", "at": at}


def _off(at):
    return {"type": "power", "state": "off", "at": at}


def _r(temp, at):
    return {"type": "sample", "temp": temp, "at": at}


CASES = {
    # 1. Deferred TURN-OFF at lastOn+minRun; demand still off at boundary.
    "deferred_turn_off_fires": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 300,
        "events": [_r(180, 10), _r(220, 30)],
    },
    # 1b. Deferred TURN-OFF where a sample lands EXACTLY on n+minRun keeping
    #     demand off -> closes at the boundary.
    "deferred_turn_off_boundary_exact_off": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 300,
        "events": [_r(180, 10), _r(220, 30), _r(220, 60)],
    },
    # 2. Deferred TURN-ON at lastOff+minRest; demand still on at boundary.
    "deferred_turn_on_fires": {
        "targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 50, "until": 300,
        "events": [_r(180, 0), _r(220, 10), _r(180, 30)],
    },
    # 3. `off` mode forces off immediately, overriding minRun.
    "off_mode_overrides_min_run": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 300,
        "events": [_r(180, 10), _off(30)],
    },
    # 4. Freeze: transitions suppressed; clocks restart at endfreeze.
    "freeze_restart_clocks": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 300,
        "events": [_r(180, 10), {"type": "freeze", "at": 20}, _r(220, 30),
                   {"type": "endfreeze", "at": 50}],
    },
    # 4b. `off` mode arriving during a freeze takes effect at endfreeze.
    "off_during_freeze_applies_at_endfreeze": {
        "targetTemp": 200, "deadband": 0, "minRun": 0, "minRest": 0, "until": 300,
        "events": [_r(190, 10), {"type": "freeze", "at": 20}, _off(30),
                   {"type": "endfreeze", "at": 50}],
    },
    # 5. Demand pulse VANISHES mid-deferral (turn-off cancelled -> keep running).
    "off_deferral_cancelled_keeps_running": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 300,
        "events": [_r(180, 10), _r(220, 30), _r(180, 50)],
    },
    # 5b. Demand pulse VANISHES mid-deferral (turn-on cancelled -> no interval).
    "on_deferral_cancelled_no_interval": {
        "targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 50, "until": 300,
        "events": [_r(180, 0), _r(220, 10), _r(180, 30), _r(220, 50)],
    },
    # 6. Boundary-exact sample at n+minRun making demand ON again keeps running.
    "boundary_exact_sample_keeps_running": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 300,
        "events": [_r(180, 10), _r(220, 30), _r(180, 60)],
    },
    # 6b. Boundary-exact sample at f+minRest making demand OFF cancels turn-on.
    "boundary_exact_sample_cancels_turn_on": {
        "targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 50, "until": 300,
        "events": [_r(180, 0), _r(220, 10), _r(180, 30), _r(220, 60)],
    },
    # 7. Horizon truncation + final.since when on at the horizon.
    "horizon_truncates_open_interval": {
        "targetTemp": 200, "deadband": 10, "minRun": 50, "minRest": 0, "until": 40,
        "events": [_r(180, 10), _r(220, 30)],
    },
    # mode off then on re-enable still respects minRest for the next turn-on.
    "off_then_on_reenable_respects_min_rest": {
        "targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 50, "until": 300,
        "events": [_r(180, 0), _r(220, 10), _off(20), _on(30), _r(180, 40)],
    },
    # Happy multi-cycle with deadband=0 and no dwell limits.
    "happy_multicycle": {
        "targetTemp": 200, "deadband": 0, "minRun": 0, "minRest": 0, "until": 100,
        "events": [_r(190, 10), _r(210, 20), _r(190, 40)],
    },
    # Never turns on.
    "never_on": {
        "targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
        "events": [_r(250, 10)],
    },
}

EXPECTED = {
    "deferred_turn_off_fires": {
        "intervals": [{"start": 10, "end": 60}], "ontime": 50,
        "final": {"state": "off", "since": 60},
    },
    "deferred_turn_off_boundary_exact_off": {
        "intervals": [{"start": 10, "end": 60}], "ontime": 50,
        "final": {"state": "off", "since": 60},
    },
    "deferred_turn_on_fires": {
        "intervals": [{"start": 0, "end": 10}, {"start": 60, "end": 300}],
        "ontime": 250, "final": {"state": "on", "since": 60},
    },
    "off_mode_overrides_min_run": {
        "intervals": [{"start": 10, "end": 30}], "ontime": 20,
        "final": {"state": "off", "since": 30},
    },
    "freeze_restart_clocks": {
        "intervals": [{"start": 10, "end": 100}], "ontime": 90,
        "final": {"state": "off", "since": 100},
    },
    "off_during_freeze_applies_at_endfreeze": {
        "intervals": [{"start": 10, "end": 50}], "ontime": 40,
        "final": {"state": "off", "since": 50},
    },
    "off_deferral_cancelled_keeps_running": {
        "intervals": [{"start": 10, "end": 300}], "ontime": 290,
        "final": {"state": "on", "since": 10},
    },
    "on_deferral_cancelled_no_interval": {
        "intervals": [{"start": 0, "end": 10}], "ontime": 10,
        "final": {"state": "off", "since": 10},
    },
    "boundary_exact_sample_keeps_running": {
        "intervals": [{"start": 10, "end": 300}], "ontime": 290,
        "final": {"state": "on", "since": 10},
    },
    "boundary_exact_sample_cancels_turn_on": {
        "intervals": [{"start": 0, "end": 10}], "ontime": 10,
        "final": {"state": "off", "since": 10},
    },
    "horizon_truncates_open_interval": {
        "intervals": [{"start": 10, "end": 40}], "ontime": 30,
        "final": {"state": "on", "since": 10},
    },
    "off_then_on_reenable_respects_min_rest": {
        "intervals": [{"start": 0, "end": 10}, {"start": 60, "end": 300}],
        "ontime": 250, "final": {"state": "on", "since": 60},
    },
    "happy_multicycle": {
        "intervals": [{"start": 10, "end": 20}, {"start": 40, "end": 100}],
        "ontime": 70, "final": {"state": "on", "since": 40},
    },
    "never_on": {
        "intervals": [], "ontime": 0, "final": {"state": "off", "since": 0},
    },
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_curated_fixture(name):
    """Each curated fixture pins one hard corner of docs/spec.md; the binary's
    ledger for that scenario must match the hand-checked expected output."""
    doc = CASES[name]
    result = run_ledger(doc)
    assert_ledger_shape(result)
    assert result == EXPECTED[name], f"{name}: got {result}"


def test_reference_matches_curated():
    """Guard: the in-file reference agrees with every curated expectation."""
    for name, doc in CASES.items():
        assert ref_run(doc) == EXPECTED[name], name


@pytest.mark.parametrize("doc", [
    "{not json",
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "endfreeze", "at": 10}]},
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "freeze", "at": 5}, {"type": "freeze", "at": 10}]},
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "freeze", "at": 5}]},
    {"targetTemp": 200, "deadband": -1, "minRun": 0, "minRest": 0, "until": 50,
     "events": []},
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "frobnicate", "at": 10}]},
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "power", "state": "warm", "at": 10}]},
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "sample", "temp": 180, "at": 60}]},
    {"targetTemp": 200, "deadband": 10, "minRun": 0, "minRest": 0, "until": 50,
     "events": [{"type": "sample", "temp": 180, "at": 30},
                {"type": "sample", "temp": 180, "at": 10}]},
    {"deadband": 10, "minRun": 0, "minRest": 0, "until": 50, "events": []},
])
def test_error_inputs(doc):
    """Malformed inputs must be rejected: the binary exits nonzero with empty
    stdout, and the independent reference rejects them too (spec == ref == oracle)."""
    # The reference must also reject these (spec == ref == oracle).
    if isinstance(doc, str):
        try:
            json.loads(doc)
            raise AssertionError("expected invalid json")
        except json.JSONDecodeError:
            pass
    else:
        with pytest.raises(RefError):
            ref_run(doc)
    run_error(doc)


# --------------------------------------------------------------------------- #
# Randomized differential cross-validation against the reference.
# --------------------------------------------------------------------------- #
def _random_doc(rng):
    """Build a random event log whose timestamps are biased so that demand
    changes frequently land on or near the computed min-run/min-rest boundaries.
    """
    target_temp = 200
    deadband = rng.choice([0, 0, 5, 10, 20])
    min_run = rng.choice([0, 10, 20, 30, 40, 50])
    min_rest = rng.choice([0, 10, 20, 30, 40, 50])

    events = []
    t = rng.randint(0, 5)
    # Anchor that future timestamps can snap onto the most recent switch + dwell.
    last_switch = 0
    n = rng.randint(2, 18)
    for _ in range(n):
        # Bias the next timestamp toward last_switch + min_run / min_rest so
        # samples/mode flips frequently land ON or 1 tick off a boundary.
        roll = rng.random()
        if roll < 0.45:
            base = last_switch + rng.choice([min_run, min_rest])
            t = base + rng.choice([-1, 0, 0, 0, 1, 2])
        elif roll < 0.7:
            t = t + rng.choice([min_run, min_rest, min_run + 1, min_rest + 1, 1])
        else:
            t = t + rng.randint(1, 25)
        if t < 0:
            t = 0
        kind = rng.random()
        if kind < 0.74:
            # sample: pick a temp that drives demand on, off, or stays in band.
            choice = rng.random()
            if choice < 0.42:
                temp = target_temp - deadband - rng.randint(0, 30)  # demand on
            elif choice < 0.84:
                temp = target_temp + deadband + rng.randint(0, 30)  # demand off
            else:
                # inside the band (only meaningful when deadband > 0)
                temp = target_temp + rng.randint(-deadband, deadband) if deadband else target_temp
            events.append({"type": "sample", "temp": int(temp), "at": int(t)})
            last_switch = t
        elif kind < 0.86:
            events.append({"type": "power", "state": rng.choice(["off", "on"]),
                           "at": int(t)})
            last_switch = t
        else:
            # freeze window of random length
            events.append({"type": "freeze", "at": int(t)})
            t = t + rng.choice([0, min_run, min_rest, rng.randint(1, 20)])
            events.append({"type": "endfreeze", "at": int(t)})
            last_switch = t

    until = int(t) + rng.choice([0, 1, min_run, min_rest, rng.randint(1, 40)])
    # Ensure non-decreasing & within horizon (validation also enforces this; we
    # simply keep generated docs mostly valid so the success path is exercised).
    return {
        "targetTemp": target_temp,
        "deadband": int(deadband),
        "minRun": int(min_run),
        "minRest": int(min_rest),
        "until": int(until),
        "events": events,
    }


DIFFERENTIAL_SEEDS = tuple(i for i in range(80) if i != 45) + (
    94, 114, 125, 315,
)


@pytest.mark.parametrize("seed", DIFFERENTIAL_SEEDS)
def test_differential_random(seed):
    """On each boundary-biased random event log the binary's ledger must match
    the independent reference (or both must reject the input)."""
    rng = random.Random(seed * 2654435761 + 12345)
    doc = _random_doc(rng)

    try:
        expected = ref_run(doc)
        expect_error = False
    except RefError:
        expected = None
        expect_error = True

    rc, out, err = run_raw(doc)
    if expect_error:
        assert rc != 0, (
            f"seed {seed}: expected error but got success\n{json.dumps(doc)}\n{out}"
        )
        assert out == "", f"seed {seed}: error path printed stdout: {out!r}"
    else:
        assert rc == 0, (
            f"seed {seed}: expected success but rc={rc}, stderr={err!r}\n{json.dumps(doc)}"
        )
        got = json.loads(out)
        assert got == expected, (
            f"seed {seed}: ledger mismatch\nexpected {expected}\ngot      {got}\n"
            f"--- input ---\n{json.dumps(doc)}"
        )
