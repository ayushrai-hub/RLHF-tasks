"""Milestone 2 tests: the forward net-pay model, the single-figure one-pool
gross-up, and the coupled multi-order target-gross solver.

The one-pool net is a piecewise function of the gross: progressive marginal tax,
then disposable = gross - tax, then a CCPA pool that is the smaller of 25 percent
of disposable and the amount disposable exceeds 21750, capped at 200000, then
net = disposable - pool. grossup solves that inverse by bisection.

target-gross is the binding solve. The employer fixes a take-home net for an
employee carrying several priority-ordered garnishment orders. The CCPA pool is
allocated senior first, each order capped two ways at once: its stored absolute
cap and a per-kind fractional ceiling that is a whole percent of disposable, so
the cap itself moves with the gross. Orders that share a priority are funded as
a group: when the pool cannot cover the group's combined caps it is split across
them pro-rata by largest-remainder rounding, ties to the smaller id, and the
allocate command exposes that per-order breakdown at an explicit gross. The take-home net is disposable minus the
part of the pool the capped orders actually consume, which can be less than the
whole pool. Solving for the gross is therefore a gross-up bisection that wraps a
priority allocation, recomputing the pool and every per-order cap at each
candidate gross.

The reference engine below mirrors the Go model and the literal pins are derived
from it. Two naive shortcuts are pinned alongside the coupled root: one that
reuses the one-pool grossup (withholds the whole pool, ignoring the caps) and one
that freezes each fractional cap at the target disposable instead of recomputing
it. The discriminator asserts the coupled root differs from both.
"""
import math
import os
import shutil
import subprocess

import pytest

APP_DIR = "/app"
BINARY = "/app/pay"
DATA_DIR = "/app/data"
MIN_WAGE_30X = 21750
POOL_CAP = 200000
BRACKETS = [(0, 0), (50000, 10), (200000, 22), (500000, 32)]
KIND_FRAC_PCT = {"child-support": 12, "tax-levy": 25, "creditor": 10}
EXEMPT_STEP = 4250
ARREARS_BPS = 125
STATS_PCT = 75


@pytest.fixture(scope="module", autouse=True)
def build_binary():
    result = subprocess.run(
        ["go", "build", "-o", BINARY, "."],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"go build failed:\n{result.stderr}")


@pytest.fixture()
def fresh_db():
    backup = DATA_DIR + "_bak_m2"
    existed = os.path.isdir(DATA_DIR)
    if existed:
        if os.path.isdir(backup):
            shutil.rmtree(backup)
        shutil.move(DATA_DIR, backup)
    os.makedirs(DATA_DIR, exist_ok=True)
    yield
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    if existed and os.path.isdir(backup):
        shutil.move(backup, DATA_DIR)


# ---- independent reference engine, exact integer arithmetic ----------------

def ref_round(num, den):
    q, r = divmod(num, den)
    twice = r * 2
    if twice > den or (twice == den and q % 2 == 1):
        q += 1
    return q


def ref_tax(gross):
    if gross <= 0:
        return 0
    acc = 0  # cent-percent units
    for i, (thr, rate) in enumerate(BRACKETS):
        nxt = BRACKETS[i + 1][0] if i + 1 < len(BRACKETS) else None
        if gross <= thr:
            break
        top = gross if (nxt is None or gross < nxt) else nxt
        acc += (top - thr) * rate
    return ref_round(acc, 100)


def ref_disposable(gross):
    disp = gross - ref_tax(gross)
    return disp if disp > 0 else 0


def ref_pool(disposable):
    if disposable <= 0:
        return 0
    p25 = ref_round(disposable * 25, 100)
    floor30 = max(disposable - MIN_WAGE_30X, 0)
    pool = min(p25, floor30)
    if pool > POOL_CAP:
        pool = POOL_CAP
    return pool


def frac_pct_for(kind):
    return KIND_FRAC_PCT.get(kind, 100)


def eff_cap(order, disposable):
    # order: (priority, oid, kind, abs_cap)
    frac = ref_round(disposable * frac_pct_for(order[2]), 100)
    return min(order[3], frac)


def ordered_orders(orders):
    # ascending priority then ascending id
    return sorted(orders, key=lambda o: (o[0], o[1]))


def ref_allocate(disposable, pool, orders):
    """Grouped priority-waterfall allocation. Orders sharing a priority are funded
    together; when the remaining pool cannot cover a group's combined effective
    caps the pool is split across the group in proportion to those caps with
    largest-remainder rounding, ties broken by ascending id, and the binding
    group consumes the whole remaining pool so nothing cascades to a junior group.
    Returns (total_allocated, allocs) with allocs aligned to ordered order."""
    ords = ordered_orders(orders)
    amount = {o[1]: 0 for o in ords}
    remaining = pool
    i, n = 0, len(ords)
    while i < n and remaining > 0:
        pr = ords[i][0]
        j = i
        group = []
        while j < n and ords[j][0] == pr:
            group.append((ords[j], eff_cap(ords[j], disposable)))
            j += 1
        sumcaps = sum(c for _, c in group)
        if sumcaps <= 0:
            i = j
            continue
        if remaining >= sumcaps:
            for o, c in group:
                amount[o[1]] = c
            remaining -= sumcaps
            i = j
            continue
        base = [remaining * c // sumcaps for _, c in group]
        rem = [remaining * c - b * sumcaps for (_, c), b in zip(group, base)]
        leftover = remaining - sum(base)
        idxs = sorted(range(len(group)), key=lambda k: (-rem[k], group[k][0][1]))
        for k in range(leftover):
            base[idxs[k]] += 1
        for (o, _), b in zip(group, base):
            amount[o[1]] = b
        remaining = 0
        i = j
    allocs = [(o[1], o[2], amount[o[1]]) for o in ords]
    total = sum(a[2] for a in allocs)
    return total, allocs


def naive_seq_allocate(disposable, pool, orders):
    """WRONG: a flat senior-first walk that allocates min(remaining, cap) to each
    order one at a time, ignoring that equal-priority orders must share a binding
    pool pro-rata. It produces the same TOTAL as the grouped allocation but a
    different per-order split whenever an equal-priority group binds."""
    remaining = pool
    allocs = []
    for o in ordered_orders(orders):
        a = min(remaining, eff_cap(o, disposable))
        allocs.append((o[1], o[2], a))
        remaining -= a
    return sum(a[2] for a in allocs), allocs


def ref_alloc_at_gross(gross, orders):
    """Per-order withheld amounts the `allocate` command prints for a gross."""
    disp = ref_disposable(gross)
    pool = ref_pool(disp)
    _, allocs = ref_allocate(disp, pool, orders)
    return allocs


def ref_net(gross):
    """one-pool net: disposable minus the whole CCPA pool."""
    disp = ref_disposable(gross)
    return disp - ref_pool(disp)


def ref_multinet(gross, orders):
    """coupled net: disposable minus what the capped orders actually consume."""
    disp = ref_disposable(gross)
    pool = ref_pool(disp)
    total, _ = ref_allocate(disp, pool, orders)
    return disp - total


def _bisect(target, netfn):
    if target <= 0:
        return 0
    lo, hi, guard = target, target * 4, 0
    while netfn(hi) < target and guard < 100:
        hi *= 2
        guard += 1
    it = 0
    while lo < hi and it < 200:
        mid = (lo + hi) // 2
        if netfn(mid) >= target:
            hi = mid
        else:
            lo = mid + 1
        it += 1
    return lo


def ref_grossup(target):
    return _bisect(target, ref_net)


def ref_target_gross(target, orders):
    return _bisect(target, lambda g: ref_multinet(g, orders))


# ---- reference engine for project (multi-period) and stats (cap summary) ----

def ref_pool_floor(disposable, floor):
    """CCPA pool with an exemption-adjusted protected floor instead of the flat
    30x-minimum 21750."""
    if disposable <= 0:
        return 0
    p25 = ref_round(disposable * 25, 100)
    fl = max(disposable - floor, 0)
    return min(min(p25, fl), POOL_CAP)


def ref_eff_cap(kind, abs_cap, disposable):
    return min(abs_cap, ref_round(disposable * frac_pct_for(kind), 100))


def ref_alloc_capped(pool, specs, caps):
    """Grouped largest-remainder waterfall over priority-ordered specs with an
    explicit per-order cap list. specs: (priority, id, kind, abs_cap) ascending."""
    res = [0] * len(specs)
    remaining = pool
    i = 0
    while i < len(specs) and remaining > 0:
        pr = specs[i][0]
        j = i
        while j < len(specs) and specs[j][0] == pr:
            j += 1
        grp = list(range(i, j))
        sumcaps = sum(caps[k] for k in grp)
        if sumcaps <= 0:
            i = j
            continue
        if remaining >= sumcaps:
            for k in grp:
                res[k] = caps[k]
            remaining -= sumcaps
            i = j
            continue
        base = [remaining * caps[k] // sumcaps for k in grp]
        rem = [remaining * caps[k] - base[t] * sumcaps for t, k in enumerate(grp)]
        leftover = remaining - sum(base)
        order = sorted(range(len(grp)), key=lambda t: (-rem[t], specs[grp[t]][1]))
        for t in range(leftover):
            base[order[t]] += 1
        for t, k in enumerate(grp):
            res[k] = base[t]
        remaining = 0
        i = j
    return res


def ref_project(specs, gross, periods, exempt):
    """Multi-period sim: exemption-floor pool, per-period claim of effective cap
    plus carried arrears, grouped largest-remainder allocation, and an unmet
    remainder that compounds by ARREARS_BPS into the next period's arrears."""
    specs = sorted(specs, key=lambda s: (s[0], s[1]))
    floor = MIN_WAGE_30X + exempt * EXEMPT_STEP
    disp = ref_disposable(gross)
    pool = ref_pool_floor(disp, floor)
    n = len(specs)
    arr = [0] * n
    tot = [0] * n
    for _ in range(periods):
        caps = [ref_eff_cap(specs[k][2], specs[k][3], disp) + arr[k] for k in range(n)]
        alloc = ref_alloc_capped(pool, specs, caps)
        for k in range(n):
            tot[k] += alloc[k]
            unmet = caps[k] - alloc[k]
            arr[k] = ref_round(unmet * (10000 + ARREARS_BPS), 10000)
    return [(specs[k][1], specs[k][2], tot[k], arr[k]) for k in range(n)]


def ref_stats(caps):
    xs = sorted(caps)
    n = len(xs)
    if n == 0:
        return (0, 0, 0, 0)
    s = sum(xs)
    sq = sum(x * x for x in xs)
    mean = ref_round(s, n)
    var = ref_round(n * sq - s * s, n * n)
    rank = math.ceil(STATS_PCT * n / 100)
    return (n, xs[rank - 1], var, mean)


def naive_single_pool(target, orders):
    """WRONG: reuse the one-pool gross-up, withholding the entire CCPA pool and
    ignoring that the capped orders cannot absorb it. Over-withholds and lands on
    a larger gross whenever the orders under-fill the pool."""
    return _bisect(target, ref_net)


def naive_fixed_caps(target, orders):
    """WRONG: freeze each order's fractional cap at the cap it would have at the
    target disposable, instead of recomputing it at every candidate gross."""
    disp_ref = target

    def netfn(gross):
        disp = ref_disposable(gross)
        pool = ref_pool(disp)
        remaining, total = pool, 0
        for o in ordered_orders(orders):
            frac = ref_round(disp_ref * frac_pct_for(o[2]), 100)
            cap = min(o[3], frac)
            a = min(remaining, cap)
            remaining -= a
            total += a
        return disp - total

    return _bisect(target, netfn)


# ---- the canonical discriminator order set ---------------------------------
# (priority, id, kind, abs_cap). The senior child-support order's 12 percent
# fractional ceiling binds across the bracket; the junior orders hit their small
# absolute caps; the three caps together cannot absorb the whole pool, so the
# pool under-fills and the one-pool shortcut over-withholds.
DISC_ORDERS = [
    (1, 1, "child-support", 60000),
    (2, 2, "tax-levy", 18000),
    (3, 3, "creditor", 9000),
]


def run(args):
    return subprocess.run([BINARY] + list(args), capture_output=True, text=True)


def init_db():
    assert run(["init"]).returncode == 0


def net(gross):
    r = run(["net", str(gross)])
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())


def grossup(target):
    r = run(["grossup", str(target)])
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())


def seed_disc_employee(name="bob"):
    assert run(["add-employee", name, "--gross", "200000",
                "--mandatory", "0"]).returncode == 0
    for (_, _, kind, cap) in DISC_ORDERS:
        pr = {"child-support": 1, "tax-levy": 2, "creditor": 3}[kind]
        assert run(["add-order", name, "--kind", kind, "--priority", str(pr),
                    "--cap", str(cap)]).returncode == 0


def target_gross(name, target):
    r = run(["target-gross", name, str(target)])
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())


def parse_alloc(text):
    out = []
    for ln in text.strip().splitlines():
        if not ln.strip():
            continue
        p = ln.split()
        out.append((int(p[0]), p[1], int(p[2])))
    return out


def allocate(name, gross):
    r = run(["allocate", name, str(gross)])
    assert r.returncode == 0, r.stderr
    return parse_alloc(r.stdout)


# An equal-priority junior pair (ids 2 and 3 both at priority 2) that the
# remaining pool must split pro-rata after the senior order is funded. At a low
# gross the pool binds inside this group, so the two creditors share it by the
# largest-remainder rule rather than the senior creditor taking its whole cap.
EQ_ORDERS = [
    (1, 1, "tax-levy", 20000),
    (2, 2, "creditor", 10000),
    (2, 3, "creditor", 5000),
]

# Two equal-cap orders at the same priority whose kind carries no fractional
# ceiling, so an odd remaining pool splits to a single tie-broken leftover cent.
TIE_ORDERS = [
    (1, 1, "other", 5000),
    (1, 2, "other", 5000),
]


def seed_orders(name, specs, gross=999999):
    assert run(["add-employee", name, "--gross", str(gross),
                "--mandatory", "0"]).returncode == 0
    for (pr, _oid, kind, cap) in specs:
        assert run(["add-order", name, "--kind", kind, "--priority", str(pr),
                    "--cap", str(cap)]).returncode == 0


def parse_project(text):
    out = []
    for ln in text.strip().splitlines():
        if not ln.strip():
            continue
        p = ln.split()
        out.append((int(p[0]), p[1], int(p[2]), int(p[3])))
    return out


def project_run(name, gross, periods, exempt=None):
    args = ["project", name, "--gross", str(gross), "--periods", str(periods)]
    if exempt is not None:
        args += ["--exempt", str(exempt)]
    r = run(args)
    assert r.returncode == 0, r.stderr
    return parse_project(r.stdout)


def stats_run(name):
    r = run(["stats", name])
    assert r.returncode == 0, r.stderr
    return tuple(int(x) for x in r.stdout.split())


# A senior child-support order that clears every period above two equal-priority
# creditors whose combined claim binds the pool, so the shortfall carries forward
# and compounds. At a low gross the exemption-raised floor shrinks the pool below
# the 25 percent limit.
PROJ_ORDERS = [
    (1, 1, "child-support", 8000),
    (2, 2, "creditor", 6000),
    (2, 3, "creditor", 3000),
]

# Cap sets exercising the three summary conventions. VAR caps separate population
# from sample variance and nearest-rank from interpolation; EVEN and ODD pin the
# half-to-even mean on an exact .5 average from an even and an odd floor.
VAR_ORDERS = [(1, 1, "other", 100), (2, 2, "other", 200), (3, 3, "other", 600)]
EVEN_ORDERS = [(1, 1, "other", 1000), (2, 2, "other", 1000),
               (3, 3, "other", 1001), (4, 4, "other", 1001)]
ODD_ORDERS = [(1, 1, "other", 1001), (2, 2, "other", 1002)]


class TestMilestone2:
    # ---- forward one-pool net model ----------------------------------------

    def test_net_zero_gross(self, fresh_db):
        init_db()
        assert net(0) == 0

    def test_net_below_first_bracket_no_tax(self, fresh_db):
        init_db()
        assert ref_tax(40000) == 0
        assert ref_pool(40000) == 10000
        assert net(40000) == ref_net(40000)

    def test_net_pool_zero_below_30x_floor(self, fresh_db):
        init_db()
        assert ref_pool(21750) == 0
        assert net(21750) == ref_net(21750)

    def test_net_progressive_tax_matches_reference(self, fresh_db):
        init_db()
        for g in [60000, 150000, 200000, 250000, 500000, 750000, 333333]:
            assert net(g) == ref_net(g), g

    def test_net_round_half_even_tax_tie(self, fresh_db):
        init_db()
        assert ref_tax(50005) == 0
        assert net(50005) == ref_net(50005)

    def test_net_pool_absolute_cap_binds(self, fresh_db):
        init_db()
        big = 5000000
        assert ref_pool(ref_disposable(big)) == POOL_CAP
        assert net(big) == ref_net(big)

    def test_net_bad_input(self, fresh_db):
        init_db()
        for bad in ["-1", "10.5", "abc", ""]:
            r = run(["net", bad])
            assert r.returncode != 0, bad
            assert r.stdout.strip() == "bad_input", bad

    # ---- one-pool grossup root-finder --------------------------------------

    def test_grossup_zero_target(self, fresh_db):
        init_db()
        assert grossup(0) == 0

    def test_grossup_is_smallest_integer_root(self, fresh_db):
        init_db()
        for tgt in [100000, 150000, 200000, 250000, 300000, 400000]:
            g = grossup(tgt)
            assert ref_net(g) >= tgt, (tgt, g)
            assert ref_net(g - 1) < tgt, (tgt, g)

    def test_grossup_matches_reference_many(self, fresh_db):
        init_db()
        for tgt in [80000, 100000, 175000, 222222, 250000, 333333, 480000]:
            assert grossup(tgt) == ref_grossup(tgt), tgt

    def test_grossup_bad_input(self, fresh_db):
        init_db()
        for bad in ["-5", "3.14", "xyz", ""]:
            r = run(["grossup", bad])
            assert r.returncode != 0, bad
            assert r.stdout.strip() == "bad_input", bad

    # ---- coupled multi-order target-gross ----------------------------------

    def test_target_gross_zero_target(self, fresh_db):
        init_db()
        seed_disc_employee()
        assert target_gross("bob", 0) == 0

    def test_target_gross_unknown_employee(self, fresh_db):
        init_db()
        r = run(["target-gross", "ghost", "100000"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_target_gross_bad_input(self, fresh_db):
        init_db()
        seed_disc_employee()
        for bad in ["-5", "3.14", "xyz", ""]:
            r = run(["target-gross", "bob", bad])
            assert r.returncode != 0, bad
            assert r.stdout.strip() == "bad_input", bad

    def test_target_gross_is_smallest_integer_root(self, fresh_db):
        init_db()
        seed_disc_employee()
        for tgt in [150000, 175000, 200000, 250000, 300000, 222222]:
            g = target_gross("bob", tgt)
            assert ref_multinet(g, DISC_ORDERS) >= tgt, (tgt, g)
            assert ref_multinet(g - 1, DISC_ORDERS) < tgt, (tgt, g)

    def test_target_gross_matches_reference_many(self, fresh_db):
        init_db()
        seed_disc_employee()
        for tgt in [150000, 175000, 200000, 230000, 250000, 280000, 300000, 222222]:
            assert target_gross("bob", tgt) == ref_target_gross(tgt, DISC_ORDERS), tgt

    def test_target_gross_no_orders_is_disposable_root(self, fresh_db):
        init_db()
        assert run(["add-employee", "noorders", "--gross", "100000",
                    "--mandatory", "0"]).returncode == 0
        # With no orders nothing is garnished, so multinet == disposable. The
        # smallest gross whose disposable clears the target.
        for tgt in [100000, 175000, 222222]:
            g = target_gross("noorders", tgt)
            assert ref_disposable(g) >= tgt, (tgt, g)
            assert ref_disposable(g - 1) < tgt, (tgt, g)

    def test_pool_underfills_when_caps_bind(self, fresh_db):
        init_db()
        seed_disc_employee()
        g = target_gross("bob", 200000)
        disp = ref_disposable(g)
        pool = ref_pool(disp)
        total, allocs = ref_allocate(disp, pool, DISC_ORDERS)
        # The capped orders cannot absorb the whole pool: part is never withheld.
        assert total < pool, (total, pool)
        # Concrete allocation pins at the converged gross.
        assert g == 293531
        assert disp == 257954
        assert pool == 64488
        assert total == 57954
        assert [a[2] for a in allocs] == [30954, 18000, 9000]

    # ---- discriminator: coupled root vs both naive shortcuts ---------------

    def test_target_gross_differs_from_both_naive(self, fresh_db):
        """KEY: at a target net of 200000 the coupled nested bisection, the
        one-pool shortcut, and the frozen-cap shortcut all land on a DIFFERENT
        gross. The one-pool form withholds the whole CCPA pool and lands high
        because the capped orders cannot absorb it; the frozen-cap form mis-sizes
        the senior 12 percent child-support cap and lands low. The binary must
        return the coupled root."""
        init_db()
        seed_disc_employee()
        tgt = 200000
        converged = target_gross("bob", tgt)
        single = naive_single_pool(tgt, DISC_ORDERS)
        fixed = naive_fixed_caps(tgt, DISC_ORDERS)
        assert converged == ref_target_gross(tgt, DISC_ORDERS)
        # All three solvers disagree.
        assert len({converged, single, fixed}) == 3
        assert converged != single, "one-pool shortcut must not match"
        assert converged != fixed, "frozen-cap shortcut must not match"
        # Concrete pins from the reference engine.
        assert converged == 293531
        assert single == 304700
        assert fixed == 284615
        # The coupled gross nets exactly the target at the threshold cent.
        assert ref_multinet(converged, DISC_ORDERS) == tgt
        assert ref_multinet(converged - 1, DISC_ORDERS) == tgt - 1
        # The one-pool shortcut over-withholds, so its gross overshoots.
        assert ref_multinet(single, DISC_ORDERS) > tgt
        assert single > converged
        # The frozen-cap shortcut under-withholds the senior order, so its gross
        # undershoots the true coupled net.
        assert ref_multinet(fixed, DISC_ORDERS) < tgt
        assert fixed < converged

    def test_naive_single_overshoots_across_targets(self, fresh_db):
        init_db()
        seed_disc_employee()
        for tgt in [175000, 222222, 250000, 300000]:
            converged = target_gross("bob", tgt)
            single = naive_single_pool(tgt, DISC_ORDERS)
            fixed = naive_fixed_caps(tgt, DISC_ORDERS)
            assert single > converged, tgt
            assert fixed != converged, tgt
            assert ref_multinet(converged, DISC_ORDERS) >= tgt

    def test_fractional_cap_moves_with_gross(self, fresh_db):
        init_db()
        seed_disc_employee()
        # The senior child-support 12 percent ceiling is what couples the cap to
        # the gross. At the converged 200000 target the effective cap is the
        # fractional 12 percent, not the 60000 absolute, proving the fractional
        # ceiling binds and is recomputed at the solved disposable.
        g = target_gross("bob", 200000)
        disp = ref_disposable(g)
        child = DISC_ORDERS[0]
        frac = ref_round(disp * 12, 100)
        assert frac < child[3], (frac, child[3])
        assert eff_cap(child, disp) == frac

    # ---- per-order allocation with the equal-priority proportional split ----

    def test_allocate_fully_funded_caps(self, fresh_db):
        init_db()
        seed_orders("carol", EQ_ORDERS)
        # A high gross floats the pool above the combined caps, so each order is
        # funded to its own effective cap.
        got = allocate("carol", 250000)
        assert got == ref_alloc_at_gross(250000, EQ_ORDERS)
        assert [a[2] for a in got] == [20000, 10000, 5000]

    def test_allocate_proportional_largest_remainder(self, fresh_db):
        """KEY: at a low gross the priority-2 pool binds and the two equal-priority
        creditors split it pro-rata by largest remainder, not first-come. A flat
        senior-first min(remaining, cap) walk gives the junior creditor its whole
        1500 and the last creditor nothing; the grouped rule splits 949/551 with
        the leftover cent going to the larger remainder."""
        init_db()
        seed_orders("dave", EQ_ORDERS)
        got = allocate("dave", 90000)
        ref = ref_alloc_at_gross(90000, EQ_ORDERS)
        assert got == ref
        # Concrete pins at disposable 86000, pool 21500.
        assert [a[2] for a in got] == [20000, 949, 551]
        # The flat sequential shortcut disagrees on the per-order split.
        disp = ref_disposable(90000)
        pool = ref_pool(disp)
        _, naive = naive_seq_allocate(disp, pool, EQ_ORDERS)
        assert [a[2] for a in naive] == [20000, 1500, 0]
        assert got != naive
        # but both consume the same total, so target-gross is unaffected.
        assert sum(a[2] for a in got) == sum(a[2] for a in naive) == pool

    def test_allocate_tie_break_smaller_id(self, fresh_db):
        init_db()
        seed_orders("erin", TIE_ORDERS)
        # disposable 30003, pool 7501; two equal 5000 caps split 3751/3750 with the
        # single leftover cent broken toward the smaller order id.
        got = allocate("erin", 30003)
        assert got == ref_alloc_at_gross(30003, TIE_ORDERS)
        assert [a[2] for a in got] == [3751, 3750]

    def test_allocate_matches_reference_many(self, fresh_db):
        init_db()
        seed_orders("frank", EQ_ORDERS)
        for g in [70000, 88000, 90000, 95000, 120000, 160000, 250000, 91234]:
            assert allocate("frank", g) == ref_alloc_at_gross(g, EQ_ORDERS), g

    def test_allocate_grouped_differs_from_sequential_across_grosses(self, fresh_db):
        init_db()
        seed_orders("grace", EQ_ORDERS)
        seen_diff = False
        for g in [86000, 88000, 90000, 92000, 95000]:
            got = allocate("grace", g)
            disp = ref_disposable(g)
            pool = ref_pool(disp)
            _, naive = naive_seq_allocate(disp, pool, EQ_ORDERS)
            assert got == ref_alloc_at_gross(g, EQ_ORDERS)
            assert sum(a[2] for a in got) == sum(a[2] for a in naive)
            if got != naive:
                seen_diff = True
        assert seen_diff, "the grouped split must differ from sequential somewhere"

    def test_allocate_no_orders_empty(self, fresh_db):
        init_db()
        assert run(["add-employee", "solo", "--gross", "100000",
                    "--mandatory", "0"]).returncode == 0
        r = run(["allocate", "solo", "100000"])
        assert r.returncode == 0
        assert [ln for ln in r.stdout.strip().splitlines() if ln.strip()] == []

    def test_allocate_unknown_employee(self, fresh_db):
        init_db()
        r = run(["allocate", "ghost", "100000"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_allocate_bad_input(self, fresh_db):
        init_db()
        seed_orders("hank", EQ_ORDERS)
        for bad in ["-1", "10.5", "abc", ""]:
            r = run(["allocate", "hank", bad])
            assert r.returncode != 0, bad
            assert r.stdout.strip() == "bad_input", bad

    def test_earlier_milestone_one_still_works(self, fresh_db):
        init_db()
        assert run(["add-employee", "alice", "--gross", "200000",
                    "--mandatory", "40000"]).returncode == 0
        r = run(["employees"])
        assert r.stdout.strip().split() == ["1", "alice", "200000", "40000"]

    # ---- multi-period projection with arrears carry and exemption floor -----

    def test_project_floor_arrears_and_split(self, fresh_db):
        """KEY: over three periods the exemption-raised floor shrinks the pool to
        9750 (the flat 21750 floor would leave 10000), the senior child-support
        order clears each period, the two equal-priority creditors bind and split
        pro-rata by largest remainder, and the unmet remainder carries forward
        compounding by 125 bps. The result is pinned literally and against the
        reference engine."""
        init_db()
        seed_orders("phil", PROJ_ORDERS)
        got = project_run("phil", 40000, 3, exempt=2)
        assert got == ref_project(PROJ_ORDERS, 40000, 3, 2)
        assert got == [
            (1, "child-support", 14400, 0),
            (2, "creditor", 8486, 3602),
            (3, "creditor", 6364, 2702),
        ]
        disp = ref_disposable(40000)
        assert ref_pool_floor(disp, MIN_WAGE_30X + 2 * EXEMPT_STEP) == 9750
        assert ref_pool_floor(disp, MIN_WAGE_30X) == 10000

    def test_project_exempt_default_zero_differs(self, fresh_db):
        """Omitting --exempt uses the flat 21750 floor, so the pool and the
        per-order totals differ from the exempt=2 run on the same orders."""
        init_db()
        seed_orders("zoe", PROJ_ORDERS)
        got0 = project_run("zoe", 40000, 3)
        assert got0 == ref_project(PROJ_ORDERS, 40000, 3, 0)
        got2 = project_run("zoe", 40000, 3, exempt=2)
        assert got0 != got2

    def test_project_single_pass_shortcut_differs(self, fresh_db):
        """A naive forward pass that funds each order once and multiplies by the
        period count, ignoring the arrears carry and using the flat floor,
        disagrees with the coupled simulation, which also leaves real arrears."""
        init_db()
        seed_orders("ivan", PROJ_ORDERS)
        got = project_run("ivan", 40000, 3, exempt=2)
        specs = sorted(PROJ_ORDERS, key=lambda s: (s[0], s[1]))
        disp = ref_disposable(40000)
        pool = ref_pool_floor(disp, MIN_WAGE_30X)  # naive: flat floor
        caps = [ref_eff_cap(k, c, disp) for (_, _, k, c) in specs]
        one = ref_alloc_capped(pool, specs, caps)
        naive = [(specs[i][1], specs[i][2], one[i] * 3, 0) for i in range(len(specs))]
        assert got != naive
        assert any(g[3] != 0 for g in got)

    def test_project_matches_reference_many(self, fresh_db):
        init_db()
        seed_orders("jane", PROJ_ORDERS)
        for (g, p, k) in [(40000, 1, 0), (40000, 2, 1), (45000, 4, 2),
                          (60000, 3, 0), (38000, 5, 3)]:
            assert project_run("jane", g, p, exempt=k) == \
                ref_project(PROJ_ORDERS, g, p, k), (g, p, k)

    def test_project_no_orders_empty(self, fresh_db):
        init_db()
        assert run(["add-employee", "none", "--gross", "100000",
                    "--mandatory", "0"]).returncode == 0
        r = run(["project", "none", "--gross", "40000", "--periods", "3"])
        assert r.returncode == 0
        assert [ln for ln in r.stdout.strip().splitlines() if ln.strip()] == []

    def test_project_unknown_employee(self, fresh_db):
        init_db()
        r = run(["project", "ghost", "--gross", "40000", "--periods", "3"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_project_bad_input(self, fresh_db):
        init_db()
        seed_orders("kara", PROJ_ORDERS)
        for extra in [["--gross", "0", "--periods", "3"],
                      ["--gross", "40000", "--periods", "0"],
                      ["--gross", "40000", "--periods", "3", "--exempt", "-1"],
                      ["--gross", "10.5", "--periods", "3"],
                      ["--gross", "40000", "--periods", "2.5"],
                      ["--gross", "40000", "--periods", "3", "--exempt", "1.5"]]:
            r = run(["project", "kara"] + extra)
            assert r.returncode != 0, extra
            assert r.stdout.strip() == "bad_input", extra

    # ---- cap summary statistics with the three convention traps ------------

    def test_stats_nearest_rank_and_population_variance(self, fresh_db):
        """KEY: stats reports nearest-rank p75 (a stored cap, not interpolated),
        population variance dividing by n, and a half-even mean. Caps 100/200/600
        give 600, 46667, 300; the sample variance 70000 and the linear p75 400
        are both the wrong conventions."""
        init_db()
        seed_orders("nora", VAR_ORDERS)
        assert stats_run("nora") == ref_stats([100, 200, 600])
        assert stats_run("nora") == (3, 600, 46667, 300)
        s, n, sq = 900, 3, 100 ** 2 + 200 ** 2 + 600 ** 2
        assert ref_round(n * sq - s * s, n * (n - 1)) == 70000

    def test_stats_mean_half_even_even_floor(self, fresh_db):
        """Caps averaging exactly 1000.5 round to the even 1000, where half-up
        would give 1001."""
        init_db()
        seed_orders("opal", EVEN_ORDERS)
        assert stats_run("opal") == ref_stats([1000, 1000, 1001, 1001])
        assert stats_run("opal") == (4, 1001, 0, 1000)

    def test_stats_mean_half_even_odd_floor(self, fresh_db):
        """Caps averaging exactly 1001.5 round up to the even 1002."""
        init_db()
        seed_orders("pete", ODD_ORDERS)
        assert stats_run("pete") == ref_stats([1001, 1002])
        assert stats_run("pete") == (2, 1002, 0, 1002)

    def test_stats_no_orders_zeros(self, fresh_db):
        init_db()
        assert run(["add-employee", "quin", "--gross", "100000",
                    "--mandatory", "0"]).returncode == 0
        assert stats_run("quin") == (0, 0, 0, 0)

    def test_stats_unknown_employee(self, fresh_db):
        init_db()
        r = run(["stats", "ghost"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"
