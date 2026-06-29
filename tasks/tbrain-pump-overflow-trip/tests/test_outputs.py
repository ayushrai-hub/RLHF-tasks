"""Behavioral verifier for the pump-station-overflow trip engine.

Each test feeds a JSON scenario to the compiled Go binary in /app as a black box
and asserts the emitted ledger against the contract in /app/docs/spec.md. The
agent edits only the engine source; this verifier supplies its own fixtures and
an independent reference engine for a randomized, boundary-biased differential
cross-check.

The reference models the full state machine: the arm/debounce confirmation, the
reset/recovery dwell and its sub-reset merge, the cumulative over-second budget
with its interpolated one-way lockout latch, the per-line maint window that
PAUSES the dwell and over-second clocks without reseting state, the resolution of
computed confirm/reset boundaries between samples (a boundary that coincides
with an explicit event resolves before that event), and the `final` state at the
horizon. The Go binary and this reference are cross-checked on several thousand
boundary-biased scenarios.

A module-scoped fixture rebuilds the binary once with
`go build -o overflow ./cmd/overflow` so the agent's current source is what is
exercised, even if the agent never rebuilt by hand.
"""

import json
import os
import random
import subprocess

import pytest

APP_DIR = os.environ.get("APP_DIR", "/app")
BIN = os.path.join(APP_DIR, "overflow")


@pytest.fixture(scope="module", autouse=True)
def build_binary():
    proc = subprocess.run(
        ["go", "build", "-o", "overflow", "./cmd/overflow"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, f"go build failed:\n{proc.stderr}"
    assert os.path.exists(BIN), f"binary not found at {BIN}"


def run(doc):
    """Run the binary on a scenario dict; return (rc, parsed_or_None, stderr)."""
    proc = subprocess.run(
        [BIN], input=json.dumps(doc), text=True, capture_output=True, timeout=30
    )
    parsed = None
    if proc.returncode == 0 and proc.stdout.strip():
        parsed = json.loads(proc.stdout)
    return proc.returncode, parsed, proc.stderr


def ledger(doc):
    rc, parsed, err = run(doc)
    assert rc == 0, f"unexpected nonzero exit ({rc}); stderr={err!r}"
    assert parsed is not None, "expected a JSON ledger on stdout"
    return parsed


def prod(name, limit, arm, reset, budget):
    return {"name": name, "limit": limit, "arm": arm, "reset": reset, "budget": budget}


def rd(t, p, lps):
    return {"t": t, "line": p, "lps": lps}


def svc(t, p):
    return {"t": t, "line": p, "type": "maint"}


def endsvc(t, p):
    return {"t": t, "line": p, "type": "endmaint"}


# ---------------------------------------------------------------------------
# Independent reference engine (mirrors docs/spec.md). Kept deliberately
# separate from the Go implementation.
# ---------------------------------------------------------------------------
class _Bad(Exception):
    pass


def _ci(v, what):
    if isinstance(v, bool) or not isinstance(v, int):
        raise _Bad(what)
    return v


IDLE, ARMING, ACTIVE, CLEARING = 0, 1, 2, 3


class _Sim:
    """Per-line trip state machine over its (sample|maint) timeline."""

    def __init__(self, c, horizon):
        self.limit, self.arm, self.reset, self.budget = c
        self.horizon = horizon
        self.mode = IDLE
        self.frozen = False
        self.have_lps = False
        self.cur_lps = 0
        self.cur_start = 0
        self.reset_from = 0
        # remaining non-frozen dwell seconds until the pending boundary fires;
        # -1 means no pending boundary.
        self.remain = -1
        self.cum = 0
        self.locked = False
        self.locked_at = 0
        self.last_end = 0
        self.excs = []

    def over(self):
        return self.have_lps and self.cur_lps > self.limit

    def finalize(self, end):
        if self.cur_start < end:
            self.excs.append({"start": self.cur_start, "end": end})
        self.last_end = end

    def accrue_to(self, frm, to):
        if self.locked or to <= frm:
            return False
        dur = to - frm
        if self.cum + dur >= self.budget:
            self.locked_at = frm + (self.budget - self.cum)
            self.cum = self.budget
            self.locked = True
            self.finalize(self.locked_at)
            return True
        self.cum += dur
        return False

    def fire_boundary(self, b):
        if self.mode == ARMING:
            if self.over():
                self.mode = ACTIVE
                self.remain = -1
                if self.budget == 0:
                    self.locked_at = b
                    self.cum = 0
                    self.locked = True
                    self.finalize(b)
            else:
                self.mode = IDLE
                self.remain = -1
        elif self.mode == CLEARING:
            if not self.over():
                self.finalize(self.reset_from)
                self.mode = IDLE
                self.remain = -1
            else:
                self.remain = -1

    def step(self, frm, to):
        while frm < to and not self.locked:
            nxt = to
            fire_at = -1
            if self.remain >= 0 and not self.frozen:
                b = frm + self.remain
                if b < to:
                    nxt = b
                    fire_at = b
            if self.mode == ACTIVE and self.over() and not self.frozen:
                if self.accrue_to(frm, nxt):
                    return
            if self.remain >= 0 and not self.frozen:
                self.remain -= nxt - frm
            frm = nxt
            if fire_at >= 0:
                self.fire_boundary(fire_at)

    def evaluate(self, t):
        if self.frozen:
            return
        over = self.over()
        if self.mode == IDLE:
            if over:
                self.mode = ARMING
                self.cur_start = t
                self.remain = self.arm
                if self.arm == 0:
                    self.fire_boundary(t)
        elif self.mode == ARMING:
            if not over:
                self.mode = IDLE
                self.remain = -1
        elif self.mode == ACTIVE:
            if not over:
                self.mode = CLEARING
                self.reset_from = t
                self.remain = self.reset
                if self.reset == 0:
                    self.fire_boundary(t)
        elif self.mode == CLEARING:
            if over:
                self.mode = ACTIVE
                self.remain = -1

    def on_sample(self, t, lps):
        self.cur_lps = lps
        self.have_lps = True
        if not self.frozen:
            self.evaluate(t)

    def run(self, evs):
        evs = sorted(evs, key=lambda e: e[0])  # stable; ties keep array order
        clock = evs[0][0]
        for (t, kind, lps) in evs:
            self.step(clock, t)
            clock = t
            if self.locked:
                break
            # A boundary coinciding with this event resolves BEFORE the event,
            # using the over state that holds up to this instant.
            if self.remain == 0 and not self.frozen:
                self.remain = -1
                self.fire_boundary(t)
                if self.locked:
                    break
            if kind == "sample":
                self.on_sample(t, lps)
            elif kind == "maint":
                self.frozen = True
            elif kind == "endmaint":
                self.frozen = False
                self.evaluate(t)
            if self.locked:
                break

        if not self.locked:
            self.step(clock, self.horizon)
            if not self.locked and self.remain == 0 and not self.frozen:
                self.remain = -1
                self.fire_boundary(self.horizon)

        if not self.locked:
            if self.mode == ACTIVE:
                self.finalize(self.horizon)
            elif self.mode == CLEARING:
                self.finalize(self.reset_from)

        if self.locked:
            return (self.excs, self.cum, self.locked_at,
                    {"state": "locked", "since": self.locked_at})
        if self.mode == ACTIVE:
            final = {"state": "tripped", "since": self.cur_start}
        elif self.mode == CLEARING:
            final = {"state": "ok", "since": self.reset_from}
        else:
            final = {"state": "ok", "since": self.last_end}
        return self.excs, self.cum, None, final


def reference(doc):
    if not isinstance(doc, dict):
        raise _Bad("top")
    prods_in, reads_in = doc.get("lines"), doc.get("samples")
    if not isinstance(prods_in, list) or not isinstance(reads_in, list):
        raise _Bad("arrays")
    lines, per = {}, {}
    for p in prods_in:
        if not isinstance(p, dict):
            raise _Bad("p")
        name = p.get("name")
        if not isinstance(name, str) or name == "" or name in lines:
            raise _Bad("name")
        limit = _ci(p.get("limit"), "limit")
        arm = _ci(p.get("arm"), "arm")
        reset = _ci(p.get("reset"), "reset")
        budget = _ci(p.get("budget"), "budget")
        if arm < 0 or reset < 0 or budget < 0:
            raise _Bad("neg")
        lines[name] = (limit, arm, reset, budget)
        per[name] = []
    max_t = None
    for r in reads_in:
        if not isinstance(r, dict):
            raise _Bad("r")
        t = _ci(r.get("t"), "t")
        if t < 0:
            raise _Bad("t<0")
        pn = r.get("line")
        if pn not in lines:
            raise _Bad("unknown")
        ty = r.get("type")
        if ty is None or ty == "sample":
            lps = _ci(r.get("lps"), "lps")
            per[pn].append((t, "sample", lps))
        elif ty in ("maint", "endmaint"):
            if r.get("lps") is not None:
                raise _Bad("maint lps")
            per[pn].append((t, ty, 0))
        else:
            raise _Bad("type")
        max_t = t if max_t is None else max(max_t, t)
    until = doc.get("until")
    if until is not None:
        until = _ci(until, "until")
        if max_t is not None and until < max_t:
            raise _Bad("until")
        horizon, has_h = until, True
    elif max_t is not None:
        horizon, has_h = max_t, True
    else:
        horizon, has_h = None, False

    out = []
    for name in sorted(lines):
        out.append(_one(name, lines[name], per[name], horizon, has_h))
    return {"lines": out}


def _one(name, c, evs, horizon, has_h):
    evs_sorted = sorted(evs, key=lambda e: e[0])
    maint_open = False
    last_read_t = None
    for (t, kind, _lps) in evs_sorted:
        if kind == "maint":
            if maint_open:
                raise _Bad("nested maint")
            maint_open = True
        elif kind == "endmaint":
            if not maint_open:
                raise _Bad("endmaint without maint")
            maint_open = False
        else:
            if last_read_t == t:
                raise _Bad("dup t")
            last_read_t = t
    if maint_open:
        raise _Bad("maint left open")
    if not evs or not has_h:
        return {"name": name, "trips": [], "trip_seconds": 0,
                "locked_at": None, "final": {"state": "ok", "since": 0}}
    excs, cum, locked_at, final = _Sim(c, horizon).run(evs)
    return {"name": name, "trips": excs, "trip_seconds": cum,
            "locked_at": locked_at, "final": final}


# ---------------------------------------------------------------------------
# Output-shape invariants.
# ---------------------------------------------------------------------------
def assert_shape(out):
    assert set(out.keys()) == {"lines"}, out
    for p in out["lines"]:
        assert set(p.keys()) == {
            "name", "trips", "trip_seconds", "locked_at", "final"}, p
        prev_end = None
        total = 0
        for e in p["trips"]:
            assert set(e.keys()) == {"start", "end"}, e
            assert isinstance(e["start"], int) and isinstance(e["end"], int)
            assert e["start"] < e["end"], f"zero/neg trip: {e}"
            if prev_end is not None:
                assert prev_end <= e["start"], "trips overlap/out of order"
            prev_end = e["end"]
            total += e["end"] - e["start"]
        assert isinstance(p["trip_seconds"], int)
        assert p["locked_at"] is None or isinstance(p["locked_at"], int)
        f = p["final"]
        assert set(f.keys()) == {"state", "since"}, f
        assert f["state"] in ("ok", "tripped", "locked")
        assert isinstance(f["since"], int)
        if p["locked_at"] is not None:
            assert f["state"] == "locked" and f["since"] == p["locked_at"]


# ---------------------------------------------------------------------------
# Targeted fixtures, each pinning one rule from the spec. Expected outputs were
# generated by running the reference engine.
# ---------------------------------------------------------------------------
def one(doc):
    out = ledger(doc)
    assert_shape(out)
    return out["lines"][0]


CASES = {
    # original dwell/budget corners
    "subarm_transient_suppressed": {
        "lines": [prod("a", 0, 3, 2, 100)],
        "samples": [rd(0, "a", 5), rd(2, "a", -1), rd(10, "a", 0)],
    },
    "exact_arm_confirms_start_at_crossing": {
        "lines": [prod("a", 0, 3, 2, 100)],
        "samples": [rd(0, "a", 5), rd(3, "a", -1), rd(10, "a", 0)],
    },
    "subreset_dip_merges": {
        "lines": [prod("a", 0, 1, 3, 100)],
        "samples": [rd(0, "a", 5), rd(5, "a", -1), rd(7, "a", 5),
                     rd(9, "a", -1), rd(20, "a", 0)],
    },
    "rebreach_at_full_reset_new_trip": {
        "lines": [prod("a", 0, 1, 3, 100)],
        "samples": [rd(0, "a", 5), rd(5, "a", -1), rd(8, "a", 5),
                     rd(10, "a", -1), rd(20, "a", 0)],
    },
    "end_is_return_not_return_plus_reset": {
        "lines": [prod("a", 0, 2, 5, 100)],
        "samples": [rd(0, "a", 9), rd(10, "a", -1), rd(40, "a", 0)],
    },
    "budget_locks out_interpolated": {
        "lines": [prod("a", 0, 0, 5, 4)],
        "samples": [rd(0, "a", 7), rd(100, "a", 7)],
    },
    "budget_zero_locks out_at_confirm": {
        "lines": [prod("a", 0, 3, 2, 0)],
        "samples": [rd(0, "a", 7), rd(100, "a", 7)],
    },
    "until_truncates_open": {
        "lines": [prod("a", 0, 2, 5, 100)],
        "samples": [rd(0, "a", 9)], "until": 12,
    },
    "return_exactly_at_confirm": {
        "lines": [prod("a", 0, 3, 2, 100)],
        "samples": [rd(0, "a", 7), rd(3, "a", -1), rd(10, "a", 0)],
    },
    # maint-window (freeze) corners
    "maint_pauses_arm_dwell": {
        "lines": [prod("a", 0, 5, 3, 100)],
        "samples": [rd(0, "a", 7), svc(2, "a"), endsvc(8, "a"),
                     rd(20, "a", -1), rd(40, "a", 0)],
    },
    "maint_pauses_reset_dwell": {
        "lines": [prod("a", 0, 2, 10, 100)],
        "samples": [rd(0, "a", 7), rd(5, "a", -1), svc(7, "a"),
                     endsvc(17, "a"), rd(40, "a", 0)],
    },
    "maint_pauses_trip_seconds": {
        "lines": [prod("a", 0, 0, 5, 100)],
        "samples": [rd(0, "a", 7), svc(4, "a"), endsvc(10, "a"), rd(20, "a", -1)],
    },
    "confirm_boundary_at_maint_start": {
        "lines": [prod("a", 0, 5, 3, 100)],
        "samples": [rd(0, "a", 7), svc(5, "a"), endsvc(9, "a"), rd(30, "a", -1)],
    },
    "reset_boundary_at_maint_start": {
        "lines": [prod("a", 0, 3, 5, 100)],
        "samples": [rd(0, "a", 7), rd(3, "a", -1), svc(8, "a"),
                     endsvc(20, "a"), rd(30, "a", 0)],
    },
    "lockout_with_freeze_pause": {
        "lines": [prod("a", 0, 0, 2, 10)],
        "samples": [rd(0, "a", 7), svc(4, "a"), endsvc(9, "a"), rd(30, "a", -1)],
    },
    # final-state corners
    "final_over_at_horizon": {
        "lines": [prod("a", 0, 2, 5, 100)],
        "samples": [rd(0, "a", 9)], "until": 12,
    },
    "final_ok_reseting_at_horizon": {
        "lines": [prod("a", 0, 1, 8, 100)],
        "samples": [rd(0, "a", 9), rd(5, "a", -1)], "until": 9,
    },
    "degenerate_all_zero": {
        "lines": [prod("a", 0, 0, 0, 0)],
        "samples": [rd(0, "a", 7), rd(5, "a", 7)],
    },
}

EXPECTED = {
    "subarm_transient_suppressed": {
        "name": "a", "trips": [], "trip_seconds": 0,
        "locked_at": None, "final": {"state": "ok", "since": 0}},
    "exact_arm_confirms_start_at_crossing": {
        "name": "a", "trips": [{"start": 0, "end": 3}], "trip_seconds": 0,
        "locked_at": None, "final": {"state": "ok", "since": 3}},
    "subreset_dip_merges": {
        "name": "a", "trips": [{"start": 0, "end": 9}], "trip_seconds": 6,
        "locked_at": None, "final": {"state": "ok", "since": 9}},
    "rebreach_at_full_reset_new_trip": {
        "name": "a", "trips": [{"start": 0, "end": 5}, {"start": 8, "end": 10}],
        "trip_seconds": 5, "locked_at": None, "final": {"state": "ok", "since": 10}},
    "end_is_return_not_return_plus_reset": {
        "name": "a", "trips": [{"start": 0, "end": 10}], "trip_seconds": 8,
        "locked_at": None, "final": {"state": "ok", "since": 10}},
    "budget_locks out_interpolated": {
        "name": "a", "trips": [{"start": 0, "end": 4}], "trip_seconds": 4,
        "locked_at": 4, "final": {"state": "locked", "since": 4}},
    "budget_zero_locks out_at_confirm": {
        "name": "a", "trips": [{"start": 0, "end": 3}], "trip_seconds": 0,
        "locked_at": 3, "final": {"state": "locked", "since": 3}},
    "until_truncates_open": {
        "name": "a", "trips": [{"start": 0, "end": 12}], "trip_seconds": 10,
        "locked_at": None, "final": {"state": "tripped", "since": 0}},
    "return_exactly_at_confirm": {
        "name": "a", "trips": [{"start": 0, "end": 3}], "trip_seconds": 0,
        "locked_at": None, "final": {"state": "ok", "since": 3}},
    "maint_pauses_arm_dwell": {
        "name": "a", "trips": [{"start": 0, "end": 20}], "trip_seconds": 9,
        "locked_at": None, "final": {"state": "ok", "since": 20}},
    "maint_pauses_reset_dwell": {
        "name": "a", "trips": [{"start": 0, "end": 5}], "trip_seconds": 3,
        "locked_at": None, "final": {"state": "ok", "since": 5}},
    "maint_pauses_trip_seconds": {
        "name": "a", "trips": [{"start": 0, "end": 20}], "trip_seconds": 14,
        "locked_at": None, "final": {"state": "ok", "since": 20}},
    "confirm_boundary_at_maint_start": {
        "name": "a", "trips": [{"start": 0, "end": 30}], "trip_seconds": 21,
        "locked_at": None, "final": {"state": "ok", "since": 30}},
    "reset_boundary_at_maint_start": {
        "name": "a", "trips": [{"start": 0, "end": 3}], "trip_seconds": 0,
        "locked_at": None, "final": {"state": "ok", "since": 3}},
    "lockout_with_freeze_pause": {
        "name": "a", "trips": [{"start": 0, "end": 15}], "trip_seconds": 10,
        "locked_at": 15, "final": {"state": "locked", "since": 15}},
    "final_over_at_horizon": {
        "name": "a", "trips": [{"start": 0, "end": 12}], "trip_seconds": 10,
        "locked_at": None, "final": {"state": "tripped", "since": 0}},
    "final_ok_reseting_at_horizon": {
        "name": "a", "trips": [{"start": 0, "end": 5}], "trip_seconds": 4,
        "locked_at": None, "final": {"state": "ok", "since": 5}},
    "degenerate_all_zero": {
        "name": "a", "trips": [], "trip_seconds": 0,
        "locked_at": 0, "final": {"state": "locked", "since": 0}},
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_curated_fixture(name):
    assert one(CASES[name]) == EXPECTED[name], name


def test_reference_matches_curated():
    """Guard: the in-file reference agrees with every curated expectation."""
    for name, doc in CASES.items():
        assert reference(doc)["lines"][0] == EXPECTED[name], name


def test_lines_sorted_and_independent():
    doc = {"lines": [prod("b", 0, 1, 1, 100), prod("a", 5, 1, 1, 100)],
           "samples": [rd(0, "b", 9), rd(5, "b", -1),
                        rd(0, "a", 9), rd(5, "a", 1)]}
    out = ledger(doc)
    assert_shape(out)
    assert [p["name"] for p in out["lines"]] == ["a", "b"]
    assert out == reference(doc)


# ---------------------------------------------------------------------------
# Invalid inputs.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("doc", [
    {"lines": [prod("a", 0, 1, 1, 5)]},  # missing samples
    {"lines": [prod("a", 0, 1, 1, 5)], "samples": [rd(0, "zz", 1)]},  # unknown line
    {"lines": [prod("a", 0, -1, 1, 5)], "samples": []},  # negative arm
    {"lines": [prod("a", 0, 1, 1, 5), prod("a", 1, 1, 1, 5)], "samples": []},  # dup
    {"lines": [prod("a", 0, 1, 1, 5)],
     "samples": [rd(3, "a", 1), rd(3, "a", 2)]},  # dup timestamp same line
    {"lines": [prod("a", 0, 1, 1, 5)], "samples": [rd(0, "a", 1)], "until": -1},  # until<last
    {"lines": [prod("a", 0, 1, 1, 5)], "samples": [rd(-2, "a", 1)]},  # negative t
    # maint-window structural errors
    {"lines": [prod("a", 0, 1, 1, 5)],
     "samples": [endsvc(2, "a")]},  # endmaint without maint
    {"lines": [prod("a", 0, 1, 1, 5)],
     "samples": [svc(1, "a"), svc(2, "a"), endsvc(3, "a")]},  # nested maint
    {"lines": [prod("a", 0, 1, 1, 5)],
     "samples": [svc(1, "a")]},  # maint left open
    {"lines": [prod("a", 0, 1, 1, 5)],
     "samples": [{"t": 1, "line": "a", "type": "maint", "lps": 5},
                  endsvc(2, "a")]},  # maint carries lps
    {"lines": [prod("a", 0, 1, 1, 5)],
     "samples": [{"t": 1, "line": "a", "type": "bogus"}]},  # unknown type
])
def test_invalid_inputs_exit_nonzero_with_no_stdout(doc):
    proc = subprocess.run(
        [BIN], input=json.dumps(doc), text=True, capture_output=True, timeout=30
    )
    # Malformed input must exit nonzero...
    assert proc.returncode != 0, f"expected nonzero exit; stdout={proc.stdout!r}"
    # ...print no ledger (nothing at all) on stdout...
    assert proc.stdout.strip() == "", (
        f"expected empty stdout on malformed input; got {proc.stdout!r}"
    )
    # ...and print a diagnostic on stderr.
    assert proc.stderr.strip() != "", "expected a diagnostic on stderr"
    with pytest.raises(_Bad):
        reference(doc)


# ---------------------------------------------------------------------------
# Randomized, boundary-biased differential cross-check.
# ---------------------------------------------------------------------------
def _random_scenario(rng):
    nprod = rng.randint(1, 3)
    names = ["p%d" % i for i in range(nprod)]
    # Degenerate zero-valued params are oversampled to hit the arm=0/reset=0/
    # budget=0 corners.
    lines = [{"name": nm,
                 "limit": rng.randint(-2, 5),
                 "arm": rng.choice([0, 0, 1, 2, 3, 4]),
                 "reset": rng.choice([0, 0, 1, 2, 3, 4]),
                 "budget": rng.choice([0, 0, 1, 2, 3, 4, 6, 8])}
                for nm in names]
    nread = rng.randint(0, 16)
    samples = []
    tpool = {}
    svc_open = {nm: False for nm in names}
    for _ in range(nread):
        nm = rng.choice(names)
        # Bias the next timestamp toward the most recent switch + a dwell so
        # samples and maint edges frequently land exactly on a computed
        # confirm/reset/lockout boundary.
        t = tpool.get(nm, rng.randint(0, 2))
        roll = rng.random()
        if roll < 0.20:
            if svc_open[nm]:
                samples.append({"t": t, "line": nm, "type": "endmaint"})
                svc_open[nm] = False
            else:
                samples.append({"t": t, "line": nm, "type": "maint"})
                svc_open[nm] = True
            tpool[nm] = t + rng.choice([1, 1, 2, 3, 4])
        else:
            samples.append(rd(t, nm, rng.randint(-3, 8)))
            tpool[nm] = t + rng.choice([1, 1, 2, 3, 4])
    # Close any open maint windows so the scenario stays valid.
    for nm in names:
        if svc_open[nm]:
            t = tpool.get(nm, 0)
            samples.append({"t": t, "line": nm, "type": "endmaint"})
            tpool[nm] = t + 1
    doc = {"lines": lines, "samples": samples}
    if rng.random() < 0.5:
        mx = max((r["t"] for r in samples), default=0)
        doc["until"] = mx + rng.choice([0, 1, 2, 3, 5])
    return doc


def test_differential_against_reference():
    """On several thousand boundary-biased scenarios the binary's ledger must
    match the independent reference, exercising the arm/reset dwells, the
    sub-reset merge, the interpolated lockout latch, the maint-window pause of
    every clock, the resolution of computed boundaries that coincide with events,
    the `final` state, and horizon handling."""
    rng = random.Random(20260626)
    for _ in range(8000):
        doc = _random_scenario(rng)
        expected = reference(doc)
        rc, parsed, err = run(doc)
        assert rc == 0, f"nonzero exit on valid scenario; stderr={err!r}\ndoc={doc!r}"
        assert parsed == expected, (
            f"ledger mismatch\ndoc={json.dumps(doc)}\n"
            f"got={json.dumps(parsed)}\nwant={json.dumps(expected)}"
        )
