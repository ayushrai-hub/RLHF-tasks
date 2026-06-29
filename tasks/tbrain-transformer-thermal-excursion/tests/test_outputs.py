"""Behavioral verifier for the transformer-thermal excursion engine.

Each test feeds a JSON scenario to the compiled Go binary in /app as a black box
and asserts the emitted ledger against the contract in /app/docs/spec.md. The
agent edits only the engine source; this verifier supplies its own fixtures and
an independent reference engine for a randomized, boundary-biased differential
cross-check.

The reference models the full state machine: the arm/debounce confirmation, the
clear/recovery dwell and its sub-clear merge, the cumulative over-second budget
with its interpolated one-way insulation-failure latch, the per-asset service window that
PAUSES the dwell and over-second clocks without clearing state, the resolution of
computed confirm/clear boundaries between readings (a boundary that coincides
with an explicit event resolves before that event), and the `final` state at the
horizon. The Go binary and this reference are cross-checked on several thousand
boundary-biased scenarios.

A module-scoped fixture rebuilds the binary once with
`go build -o thermalwatch ./cmd/thermalwatch` so the agent's current source is what is
exercised, even if the agent never rebuilt by hand.
"""

import json
import os
import random
import subprocess

import pytest

APP_DIR = os.environ.get("APP_DIR", "/app")
BIN = os.path.join(APP_DIR, "thermalwatch")


@pytest.fixture(scope="module", autouse=True)
def build_binary():
    proc = subprocess.run(
        ["go", "build", "-o", "thermalwatch", "./cmd/thermalwatch"],
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


def prod(name, limit, arm, clear, budget):
    return {"name": name, "limit": limit, "arm": arm, "clear": clear, "budget": budget}


def rd(t, p, temp):
    return {"t": t, "asset": p, "temp": temp}


def svc(t, p):
    return {"t": t, "asset": p, "type": "service"}


def endsvc(t, p):
    return {"t": t, "asset": p, "type": "endservice"}


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
    """Per-asset excursion state machine over its (reading|service) timeline."""

    def __init__(self, c, horizon):
        self.limit, self.arm, self.clear, self.budget = c
        self.horizon = horizon
        self.mode = IDLE
        self.frozen = False
        self.have_temp = False
        self.cur_temp = 0
        self.cur_start = 0
        self.clear_from = 0
        # remaining non-frozen dwell seconds until the pending boundary fires;
        # -1 means no pending boundary.
        self.remain = -1
        self.cum = 0
        self.failed = False
        self.failed_at = 0
        self.last_end = 0
        self.excs = []

    def over(self):
        return self.have_temp and self.cur_temp > self.limit

    def finalize(self, end):
        if self.cur_start < end:
            self.excs.append({"start": self.cur_start, "end": end})
        self.last_end = end

    def accrue_to(self, frm, to):
        if self.failed or to <= frm:
            return False
        dur = to - frm
        if self.cum + dur >= self.budget:
            self.failed_at = frm + (self.budget - self.cum)
            self.cum = self.budget
            self.failed = True
            self.finalize(self.failed_at)
            return True
        self.cum += dur
        return False

    def fire_boundary(self, b):
        if self.mode == ARMING:
            if self.over():
                self.mode = ACTIVE
                self.remain = -1
                if self.budget == 0:
                    self.failed_at = b
                    self.cum = 0
                    self.failed = True
                    self.finalize(b)
            else:
                self.mode = IDLE
                self.remain = -1
        elif self.mode == CLEARING:
            if not self.over():
                self.finalize(self.clear_from)
                self.mode = IDLE
                self.remain = -1
            else:
                self.remain = -1

    def step(self, frm, to):
        while frm < to and not self.failed:
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
                self.clear_from = t
                self.remain = self.clear
                if self.clear == 0:
                    self.fire_boundary(t)
        elif self.mode == CLEARING:
            if over:
                self.mode = ACTIVE
                self.remain = -1

    def on_reading(self, t, temp):
        self.cur_temp = temp
        self.have_temp = True
        if not self.frozen:
            self.evaluate(t)

    def run(self, evs):
        evs = sorted(evs, key=lambda e: e[0])  # stable; ties keep array order
        clock = evs[0][0]
        for (t, kind, temp) in evs:
            self.step(clock, t)
            clock = t
            if self.failed:
                break
            # A boundary coinciding with this event resolves BEFORE the event,
            # using the over state that holds up to this instant.
            if self.remain == 0 and not self.frozen:
                self.remain = -1
                self.fire_boundary(t)
                if self.failed:
                    break
            if kind == "reading":
                self.on_reading(t, temp)
            elif kind == "service":
                self.frozen = True
            elif kind == "endservice":
                self.frozen = False
                self.evaluate(t)
            if self.failed:
                break

        if not self.failed:
            self.step(clock, self.horizon)
            if not self.failed and self.remain == 0 and not self.frozen:
                self.remain = -1
                self.fire_boundary(self.horizon)

        if not self.failed:
            if self.mode == ACTIVE:
                self.finalize(self.horizon)
            elif self.mode == CLEARING:
                self.finalize(self.clear_from)

        if self.failed:
            return (self.excs, self.cum, self.failed_at,
                    {"state": "failed", "since": self.failed_at})
        if self.mode == ACTIVE:
            final = {"state": "over", "since": self.cur_start}
        elif self.mode == CLEARING:
            final = {"state": "ok", "since": self.clear_from}
        else:
            final = {"state": "ok", "since": self.last_end}
        return self.excs, self.cum, None, final


def reference(doc):
    if not isinstance(doc, dict):
        raise _Bad("top")
    prods_in, reads_in = doc.get("assets"), doc.get("readings")
    if not isinstance(prods_in, list) or not isinstance(reads_in, list):
        raise _Bad("arrays")
    assets, per = {}, {}
    for p in prods_in:
        if not isinstance(p, dict):
            raise _Bad("p")
        name = p.get("name")
        if not isinstance(name, str) or name == "" or name in assets:
            raise _Bad("name")
        limit = _ci(p.get("limit"), "limit")
        arm = _ci(p.get("arm"), "arm")
        clear = _ci(p.get("clear"), "clear")
        budget = _ci(p.get("budget"), "budget")
        if arm < 0 or clear < 0 or budget < 0:
            raise _Bad("neg")
        assets[name] = (limit, arm, clear, budget)
        per[name] = []
    max_t = None
    for r in reads_in:
        if not isinstance(r, dict):
            raise _Bad("r")
        t = _ci(r.get("t"), "t")
        if t < 0:
            raise _Bad("t<0")
        pn = r.get("asset")
        if pn not in assets:
            raise _Bad("unknown")
        ty = r.get("type")
        if ty is None or ty == "reading":
            temp = _ci(r.get("temp"), "temp")
            per[pn].append((t, "reading", temp))
        elif ty in ("service", "endservice"):
            if r.get("temp") is not None:
                raise _Bad("service temp")
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
    for name in sorted(assets):
        out.append(_one(name, assets[name], per[name], horizon, has_h))
    return {"assets": out}


def _one(name, c, evs, horizon, has_h):
    evs_sorted = sorted(evs, key=lambda e: e[0])
    service_open = False
    last_read_t = None
    for (t, kind, _temp) in evs_sorted:
        if kind == "service":
            if service_open:
                raise _Bad("nested service")
            service_open = True
        elif kind == "endservice":
            if not service_open:
                raise _Bad("endservice without service")
            service_open = False
        else:
            if last_read_t == t:
                raise _Bad("dup t")
            last_read_t = t
    if service_open:
        raise _Bad("service left open")
    if not evs or not has_h:
        return {"name": name, "excursions": [], "over_seconds": 0,
                "failed_at": None, "final": {"state": "ok", "since": 0}}
    excs, cum, failed_at, final = _Sim(c, horizon).run(evs)
    return {"name": name, "excursions": excs, "over_seconds": cum,
            "failed_at": failed_at, "final": final}


# ---------------------------------------------------------------------------
# Output-shape invariants.
# ---------------------------------------------------------------------------
def assert_shape(out):
    assert set(out.keys()) == {"assets"}, out
    for p in out["assets"]:
        assert set(p.keys()) == {
            "name", "excursions", "over_seconds", "failed_at", "final"}, p
        prev_end = None
        total = 0
        for e in p["excursions"]:
            assert set(e.keys()) == {"start", "end"}, e
            assert isinstance(e["start"], int) and isinstance(e["end"], int)
            assert e["start"] < e["end"], f"zero/neg excursion: {e}"
            if prev_end is not None:
                assert prev_end <= e["start"], "excursions overlap/out of order"
            prev_end = e["end"]
            total += e["end"] - e["start"]
        assert isinstance(p["over_seconds"], int)
        assert p["failed_at"] is None or isinstance(p["failed_at"], int)
        f = p["final"]
        assert set(f.keys()) == {"state", "since"}, f
        assert f["state"] in ("ok", "over", "failed")
        assert isinstance(f["since"], int)
        if p["failed_at"] is not None:
            assert f["state"] == "failed" and f["since"] == p["failed_at"]


# ---------------------------------------------------------------------------
# Targeted fixtures, each pinning one rule from the spec. Expected outputs were
# generated by running the reference engine.
# ---------------------------------------------------------------------------
def one(doc):
    out = ledger(doc)
    assert_shape(out)
    return out["assets"][0]


CASES = {
    # original dwell/budget corners
    "subarm_transient_suppressed": {
        "assets": [prod("a", 0, 3, 2, 100)],
        "readings": [rd(0, "a", 5), rd(2, "a", -1), rd(10, "a", 0)],
    },
    "exact_arm_confirms_start_at_crossing": {
        "assets": [prod("a", 0, 3, 2, 100)],
        "readings": [rd(0, "a", 5), rd(3, "a", -1), rd(10, "a", 0)],
    },
    "subclear_dip_merges": {
        "assets": [prod("a", 0, 1, 3, 100)],
        "readings": [rd(0, "a", 5), rd(5, "a", -1), rd(7, "a", 5),
                     rd(9, "a", -1), rd(20, "a", 0)],
    },
    "rebreach_at_full_clear_new_excursion": {
        "assets": [prod("a", 0, 1, 3, 100)],
        "readings": [rd(0, "a", 5), rd(5, "a", -1), rd(8, "a", 5),
                     rd(10, "a", -1), rd(20, "a", 0)],
    },
    "end_is_return_not_return_plus_clear": {
        "assets": [prod("a", 0, 2, 5, 100)],
        "readings": [rd(0, "a", 9), rd(10, "a", -1), rd(40, "a", 0)],
    },
    "budget_fails_interpolated": {
        "assets": [prod("a", 0, 0, 5, 4)],
        "readings": [rd(0, "a", 7), rd(100, "a", 7)],
    },
    "budget_zero_fails_at_confirm": {
        "assets": [prod("a", 0, 3, 2, 0)],
        "readings": [rd(0, "a", 7), rd(100, "a", 7)],
    },
    "until_truncates_open": {
        "assets": [prod("a", 0, 2, 5, 100)],
        "readings": [rd(0, "a", 9)], "until": 12,
    },
    "return_exactly_at_confirm": {
        "assets": [prod("a", 0, 3, 2, 100)],
        "readings": [rd(0, "a", 7), rd(3, "a", -1), rd(10, "a", 0)],
    },
    # service-window (freeze) corners
    "service_pauses_arm_dwell": {
        "assets": [prod("a", 0, 5, 3, 100)],
        "readings": [rd(0, "a", 7), svc(2, "a"), endsvc(8, "a"),
                     rd(20, "a", -1), rd(40, "a", 0)],
    },
    "service_pauses_clear_dwell": {
        "assets": [prod("a", 0, 2, 10, 100)],
        "readings": [rd(0, "a", 7), rd(5, "a", -1), svc(7, "a"),
                     endsvc(17, "a"), rd(40, "a", 0)],
    },
    "service_pauses_over_seconds": {
        "assets": [prod("a", 0, 0, 5, 100)],
        "readings": [rd(0, "a", 7), svc(4, "a"), endsvc(10, "a"), rd(20, "a", -1)],
    },
    "confirm_boundary_at_service_start": {
        "assets": [prod("a", 0, 5, 3, 100)],
        "readings": [rd(0, "a", 7), svc(5, "a"), endsvc(9, "a"), rd(30, "a", -1)],
    },
    "clear_boundary_at_service_start": {
        "assets": [prod("a", 0, 3, 5, 100)],
        "readings": [rd(0, "a", 7), rd(3, "a", -1), svc(8, "a"),
                     endsvc(20, "a"), rd(30, "a", 0)],
    },
    "insulation-failure_with_freeze_pause": {
        "assets": [prod("a", 0, 0, 2, 10)],
        "readings": [rd(0, "a", 7), svc(4, "a"), endsvc(9, "a"), rd(30, "a", -1)],
    },
    # final-state corners
    "final_over_at_horizon": {
        "assets": [prod("a", 0, 2, 5, 100)],
        "readings": [rd(0, "a", 9)], "until": 12,
    },
    "final_ok_clearing_at_horizon": {
        "assets": [prod("a", 0, 1, 8, 100)],
        "readings": [rd(0, "a", 9), rd(5, "a", -1)], "until": 9,
    },
    "degenerate_all_zero": {
        "assets": [prod("a", 0, 0, 0, 0)],
        "readings": [rd(0, "a", 7), rd(5, "a", 7)],
    },
}

EXPECTED = {
    "subarm_transient_suppressed": {
        "name": "a", "excursions": [], "over_seconds": 0,
        "failed_at": None, "final": {"state": "ok", "since": 0}},
    "exact_arm_confirms_start_at_crossing": {
        "name": "a", "excursions": [{"start": 0, "end": 3}], "over_seconds": 0,
        "failed_at": None, "final": {"state": "ok", "since": 3}},
    "subclear_dip_merges": {
        "name": "a", "excursions": [{"start": 0, "end": 9}], "over_seconds": 6,
        "failed_at": None, "final": {"state": "ok", "since": 9}},
    "rebreach_at_full_clear_new_excursion": {
        "name": "a", "excursions": [{"start": 0, "end": 5}, {"start": 8, "end": 10}],
        "over_seconds": 5, "failed_at": None, "final": {"state": "ok", "since": 10}},
    "end_is_return_not_return_plus_clear": {
        "name": "a", "excursions": [{"start": 0, "end": 10}], "over_seconds": 8,
        "failed_at": None, "final": {"state": "ok", "since": 10}},
    "budget_fails_interpolated": {
        "name": "a", "excursions": [{"start": 0, "end": 4}], "over_seconds": 4,
        "failed_at": 4, "final": {"state": "failed", "since": 4}},
    "budget_zero_fails_at_confirm": {
        "name": "a", "excursions": [{"start": 0, "end": 3}], "over_seconds": 0,
        "failed_at": 3, "final": {"state": "failed", "since": 3}},
    "until_truncates_open": {
        "name": "a", "excursions": [{"start": 0, "end": 12}], "over_seconds": 10,
        "failed_at": None, "final": {"state": "over", "since": 0}},
    "return_exactly_at_confirm": {
        "name": "a", "excursions": [{"start": 0, "end": 3}], "over_seconds": 0,
        "failed_at": None, "final": {"state": "ok", "since": 3}},
    "service_pauses_arm_dwell": {
        "name": "a", "excursions": [{"start": 0, "end": 20}], "over_seconds": 9,
        "failed_at": None, "final": {"state": "ok", "since": 20}},
    "service_pauses_clear_dwell": {
        "name": "a", "excursions": [{"start": 0, "end": 5}], "over_seconds": 3,
        "failed_at": None, "final": {"state": "ok", "since": 5}},
    "service_pauses_over_seconds": {
        "name": "a", "excursions": [{"start": 0, "end": 20}], "over_seconds": 14,
        "failed_at": None, "final": {"state": "ok", "since": 20}},
    "confirm_boundary_at_service_start": {
        "name": "a", "excursions": [{"start": 0, "end": 30}], "over_seconds": 21,
        "failed_at": None, "final": {"state": "ok", "since": 30}},
    "clear_boundary_at_service_start": {
        "name": "a", "excursions": [{"start": 0, "end": 3}], "over_seconds": 0,
        "failed_at": None, "final": {"state": "ok", "since": 3}},
    "insulation-failure_with_freeze_pause": {
        "name": "a", "excursions": [{"start": 0, "end": 15}], "over_seconds": 10,
        "failed_at": 15, "final": {"state": "failed", "since": 15}},
    "final_over_at_horizon": {
        "name": "a", "excursions": [{"start": 0, "end": 12}], "over_seconds": 10,
        "failed_at": None, "final": {"state": "over", "since": 0}},
    "final_ok_clearing_at_horizon": {
        "name": "a", "excursions": [{"start": 0, "end": 5}], "over_seconds": 4,
        "failed_at": None, "final": {"state": "ok", "since": 5}},
    "degenerate_all_zero": {
        "name": "a", "excursions": [], "over_seconds": 0,
        "failed_at": 0, "final": {"state": "failed", "since": 0}},
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_curated_fixture(name):
    assert one(CASES[name]) == EXPECTED[name], name


def test_reference_matches_curated():
    """Guard: the in-file reference agrees with every curated expectation."""
    for name, doc in CASES.items():
        assert reference(doc)["assets"][0] == EXPECTED[name], name


def test_assets_sorted_and_independent():
    doc = {"assets": [prod("b", 0, 1, 1, 100), prod("a", 5, 1, 1, 100)],
           "readings": [rd(0, "b", 9), rd(5, "b", -1),
                        rd(0, "a", 9), rd(5, "a", 1)]}
    out = ledger(doc)
    assert_shape(out)
    assert [p["name"] for p in out["assets"]] == ["a", "b"]
    assert out == reference(doc)


# ---------------------------------------------------------------------------
# Invalid inputs.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("doc", [
    {"assets": [prod("a", 0, 1, 1, 5)]},  # missing readings
    {"assets": [prod("a", 0, 1, 1, 5)], "readings": [rd(0, "zz", 1)]},  # unknown asset
    {"assets": [prod("a", 0, -1, 1, 5)], "readings": []},  # negative arm
    {"assets": [prod("a", 0, 1, 1, 5), prod("a", 1, 1, 1, 5)], "readings": []},  # dup
    {"assets": [prod("a", 0, 1, 1, 5)],
     "readings": [rd(3, "a", 1), rd(3, "a", 2)]},  # dup timestamp same asset
    {"assets": [prod("a", 0, 1, 1, 5)], "readings": [rd(0, "a", 1)], "until": -1},  # until<last
    {"assets": [prod("a", 0, 1, 1, 5)], "readings": [rd(-2, "a", 1)]},  # negative t
    # service-window structural errors
    {"assets": [prod("a", 0, 1, 1, 5)],
     "readings": [endsvc(2, "a")]},  # endservice without service
    {"assets": [prod("a", 0, 1, 1, 5)],
     "readings": [svc(1, "a"), svc(2, "a"), endsvc(3, "a")]},  # nested service
    {"assets": [prod("a", 0, 1, 1, 5)],
     "readings": [svc(1, "a")]},  # service left open
    {"assets": [prod("a", 0, 1, 1, 5)],
     "readings": [{"t": 1, "asset": "a", "type": "service", "temp": 5},
                  endsvc(2, "a")]},  # service carries temp
    {"assets": [prod("a", 0, 1, 1, 5)],
     "readings": [{"t": 1, "asset": "a", "type": "bogus"}]},  # unknown type
])
def test_invalid_inputs_exit_nonzero_with_no_stdout(doc):
    rc, parsed, err = run(doc)
    assert rc != 0, f"expected nonzero exit; parsed={parsed!r}"
    assert parsed is None
    with pytest.raises(_Bad):
        reference(doc)


# ---------------------------------------------------------------------------
# Randomized, boundary-biased differential cross-check.
# ---------------------------------------------------------------------------
def _random_scenario(rng):
    nprod = rng.randint(1, 3)
    names = ["p%d" % i for i in range(nprod)]
    # Degenerate zero-valued params are oversampled to hit the arm=0/clear=0/
    # budget=0 corners.
    assets = [{"name": nm,
                 "limit": rng.randint(-2, 5),
                 "arm": rng.choice([0, 0, 1, 2, 3, 4]),
                 "clear": rng.choice([0, 0, 1, 2, 3, 4]),
                 "budget": rng.choice([0, 0, 1, 2, 3, 4, 6, 8])}
                for nm in names]
    nread = rng.randint(0, 16)
    readings = []
    tpool = {}
    svc_open = {nm: False for nm in names}
    for _ in range(nread):
        nm = rng.choice(names)
        # Bias the next timestamp toward the most recent switch + a dwell so
        # readings and service edges frequently land exactly on a computed
        # confirm/clear/insulation-failure boundary.
        t = tpool.get(nm, rng.randint(0, 2))
        roll = rng.random()
        if roll < 0.20:
            if svc_open[nm]:
                readings.append({"t": t, "asset": nm, "type": "endservice"})
                svc_open[nm] = False
            else:
                readings.append({"t": t, "asset": nm, "type": "service"})
                svc_open[nm] = True
            tpool[nm] = t + rng.choice([1, 1, 2, 3, 4])
        else:
            readings.append(rd(t, nm, rng.randint(-3, 8)))
            tpool[nm] = t + rng.choice([1, 1, 2, 3, 4])
    # Close any open service windows so the scenario stays valid.
    for nm in names:
        if svc_open[nm]:
            t = tpool.get(nm, 0)
            readings.append({"t": t, "asset": nm, "type": "endservice"})
            tpool[nm] = t + 1
    doc = {"assets": assets, "readings": readings}
    if rng.random() < 0.5:
        mx = max((r["t"] for r in readings), default=0)
        doc["until"] = mx + rng.choice([0, 1, 2, 3, 5])
    return doc


def test_differential_against_reference():
    """On several thousand boundary-biased scenarios the binary's ledger must
    match the independent reference, exercising the arm/clear dwells, the
    sub-clear merge, the interpolated insulation-failure latch, the service-window pause of
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
