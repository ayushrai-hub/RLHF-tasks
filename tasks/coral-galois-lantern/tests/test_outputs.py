"""Verifier for the coral galois lantern quintic analyzer.

The agent must build a pure-Rust (std-only) program that, for each monic integer
quintic, reports irreducibility over Q, the exact discriminant, the Galois group of an
irreducible quintic (one of C5, D5, F20, A5, S5), and radical-solvability.

At verification time we synthesize a *fresh* batch of quintics (so nothing can be
hard-coded) whose discriminants are deliberately driven past 2**127 by a
group-preserving scaling x -> x/s (disc scales by s**20), run the agent's program on
it, and compare its answers to an independent ground-truth computed here from scratch:

  * Galois group / irreducibility / solvability via Dedekind's theorem: factor f mod p
    for many good primes, read the Frobenius cycle type (degrees of the irreducible
    factors), and map the observed set of cycle types to the unique transitive subgroup
    of S5 it can belong to.
  * The exact discriminant via the Sylvester resultant det(Syl(f, f')) using Python's
    arbitrary-precision integers.
  * Built-in safety net: G <= A5 (read from cycle-type parity) must agree with the exact
    discriminant being a perfect square, so the two independent methods cross-check on
    every irreducible input or the run errors out.

The batch always contains disguised representatives of all five groups (canonical
generators translated and scaled, which preserves the splitting field), reducible
quintics, and random ones, so every branch is exercised and every discriminant is huge.
"""

import json
import math
import os
import random
import re
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
WORKDIR = Path("/tmp/coral_galois_lantern_verify")
ALLOWED_GROUPS = {"C5", "D5", "F20", "A5", "S5"}
SOLVABLE_GROUPS = {"C5", "D5", "F20"}
TWO_127 = 1 << 127

# --------------------------------------------------------------------------- #
#  Ground-truth classifier (pure standard library)                            #
# --------------------------------------------------------------------------- #

def _primes_up_to(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, math.isqrt(n) + 1):
        if sieve[i]:
            sieve[i * i:: i] = bytearray(len(sieve[i * i:: i]))
    return [i for i in range(2, n + 1) if sieve[i]]

PRIME_BOUND = 8000
PRIMES = _primes_up_to(PRIME_BOUND)


def _pnorm(a, p):
    a = [x % p for x in a]
    while len(a) > 1 and a[-1] == 0:
        a.pop()
    return a


def _pdeg(a):
    return len(a) - 1


def _psub(a, b, p):
    n = max(len(a), len(b))
    r = [0] * n
    for i in range(len(a)):
        r[i] += a[i]
    for i in range(len(b)):
        r[i] -= b[i]
    return _pnorm(r, p)


def _pmul(a, b, p):
    if a == [0] or b == [0]:
        return [0]
    r = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                r[i + j] = (r[i + j] + ai * bj) % p
    return _pnorm(r, p)


def _pdivmod(a, b, p):
    a = _pnorm(a[:], p)
    b = _pnorm(b, p)
    inv = pow(b[-1], p - 2, p)
    q = [0] * max(1, len(a) - len(b) + 1)
    while a != [0] and _pdeg(a) >= _pdeg(b):
        shift = _pdeg(a) - _pdeg(b)
        coef = (a[-1] * inv) % p
        q[shift] = coef
        for i in range(len(b)):
            a[shift + i] = (a[shift + i] - coef * b[i]) % p
        a = _pnorm(a, p)
    return _pnorm(q, p), _pnorm(a, p)


def _pmod(a, b, p):
    return _pdivmod(a, b, p)[1]


def _pgcd(a, b, p):
    a = _pnorm(a, p)
    b = _pnorm(b, p)
    while b != [0]:
        a, b = b, _pmod(a, b, p)
    if a == [0]:
        return [0]
    inv = pow(a[-1], p - 2, p)
    return _pnorm([(x * inv) % p for x in a], p)


def _pow_p(base, modulus, p):
    """Raise base to the p-th power modulo `modulus` in F_p[x]."""
    result = [1]
    b = _pmod(base, modulus, p)
    e = p
    while e > 0:
        if e & 1:
            result = _pmod(_pmul(result, b, p), modulus, p)
        e >>= 1
        if e:
            b = _pmod(_pmul(b, b, p), modulus, p)
    return result


def _deriv_lowfirst(a, p):
    if len(a) <= 1:
        return [0]
    return _pnorm([(i * a[i]) % p for i in range(1, len(a))], p)


def _poly_mod_p(c, p):
    return _pnorm([x % p for x in reversed(c)], p)


def _cycle_type_mod_p(c, p):
    """Sorted degrees of the irreducible factors of c mod p, or None for a bad prime."""
    if c[0] % p == 0:
        return None
    f = _poly_mod_p(c, p)
    if _pdeg(f) != len(c) - 1:
        return None
    fp = _deriv_lowfirst(f, p)
    if fp == [0] or _pdeg(_pgcd(f, fp, p)) != 0:
        return None  # not squarefree mod p -> ramified, skip
    degs = []
    fcur = f[:]
    x = [0, 1]
    h = x[:]
    d = 1
    while _pdeg(fcur) >= 1 and d <= _pdeg(fcur):
        h = _pow_p(h, fcur, p)
        g = _pgcd(_psub(h, x, p), fcur, p)
        if _pdeg(g) > 0:
            k = _pdeg(g) // d
            degs.extend([d] * k)
            fcur, _ = _pdivmod(fcur, g, p)
            fcur = _pnorm(fcur, p)
            if _pdeg(fcur) >= 1:
                h = _pmod(h, fcur, p)
        d += 1
    if _pdeg(fcur) >= 1:
        degs.append(_pdeg(fcur))
    return tuple(sorted(degs))


# exact discriminant via Sylvester resultant Res(f, f') -------------------- #

def _det_int(mat):
    from fractions import Fraction
    n = len(mat)
    m = [[Fraction(x) for x in row] for row in mat]
    det = Fraction(1)
    for col in range(n):
        piv = next((r for r in range(col, n) if m[r][col] != 0), None)
        if piv is None:
            return 0
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
            det = -det
        det *= m[col][col]
        inv = m[col][col]
        for r in range(col + 1, n):
            if m[r][col] != 0:
                f = m[r][col] / inv
                for cc in range(col, n):
                    m[r][cc] -= f * m[col][cc]
    return int(det)


def _discriminant(c):
    n = len(c) - 1
    fp = [c[i] * (n - i) for i in range(n)]  # derivative, highest-first
    size = (n - 1) + n
    syl = [[0] * size for _ in range(size)]
    for i in range(n - 1):
        for j in range(len(c)):
            syl[i][i + j] = c[j]
    for i in range(n):
        for j in range(len(fp)):
            syl[(n - 1) + i][i + j] = fp[j]
    res = _det_int(syl)
    return ((-1) ** (n * (n - 1) // 2)) * res


def _is_square(n):
    if n < 0:
        return False
    r = math.isqrt(n)
    return r * r == n


# exact pair-sum resolvent R2(Z) = prod_{i<j}(Z - (x_i + x_j)) --------------- #
# (degree 10, monic, integer coefficients) computed from the quintic via Newton's
# identities and the power sums of the pairwise sums -- no roots, no floating point.

def _power_sums(c, K):
    """Power sums p_0..p_K of the roots of monic quintic c (highest-first)."""
    e = [((-1) ** k) * c[k] for k in range(1, 6)]  # e_1..e_5 (elementary symmetric)

    def eget(i):
        return e[i - 1] if 1 <= i <= 5 else 0

    p = [5]  # p_0 = number of roots
    for k in range(1, K + 1):
        s = sum(((-1) ** (i - 1)) * eget(i) * p[k - i] for i in range(1, k))
        s += ((-1) ** (k - 1)) * k * eget(k)
        p.append(s)
    return p


def _resolvent_pairsum(c):
    from fractions import Fraction
    p = _power_sums(c, 10)
    # power sums of the pairwise sums: q_k = (1/2)[sum_m C(k,m) p_m p_{k-m} - 2^k p_k]
    q = []
    for k in range(11):
        tot = sum(math.comb(k, m) * p[m] * p[k - m] for m in range(k + 1)) - (2 ** k) * p[k]
        q.append(tot // 2)
    # elementary symmetric functions of the pairwise sums via Newton's identities
    ee = [Fraction(1)]
    for k in range(1, 11):
        s = sum(Fraction((-1) ** (i - 1)) * ee[k - i] * q[i] for i in range(1, k + 1))
        ee.append(s / k)
    coeffs = []
    for k in range(11):
        val = ((-1) ** k) * ee[k]
        assert val.denominator == 1, f"non-integer resolvent coefficient for {c[:2]}"
        coeffs.append(int(val))
    return coeffs  # highest-first, length 11, leading 1


def classify(c):
    """Return (irreducible, group_or_None, solvable, discriminant) for a monic quintic."""
    disc = _discriminant(c)
    observed = set()
    for p in PRIMES:
        ct = _cycle_type_mod_p(c, p)
        if ct is not None:
            observed.add(ct)

    def has(t):
        return t in observed

    if not has((5,)):
        # reducible quintic: every irreducible factor has degree <= 4, hence solvable
        return (False, None, True, disc)

    in_a5 = not (has((1, 1, 1, 2)) or has((1, 4)) or has((2, 3)))
    assert disc != 0, f"non-squarefree quintic slipped into the batch: {c}"
    assert in_a5 == _is_square(disc), (
        f"ground-truth methods disagree on {c}: cycle-parity in_A5={in_a5} "
        f"but disc_is_square={_is_square(disc)}"
    )

    if in_a5:
        group = "A5" if has((1, 1, 3)) else ("D5" if has((1, 2, 2)) else "C5")
    else:
        group = "S5" if (has((1, 1, 1, 2)) or has((1, 1, 3)) or has((2, 3))) else "F20"
    return (True, group, group in SOLVABLE_GROUPS, disc)


# --------------------------------------------------------------------------- #
#  Fresh batch synthesis (every discriminant driven past 2**127)              #
# --------------------------------------------------------------------------- #

CANONICAL = {
    "S5": [1, 0, 0, 0, -1, -1],
    "F20": [1, 0, 0, 0, 0, -2],
    "C5": [1, 1, -4, -3, 3, 1],
    "A5": [1, 0, 0, 0, 20, 16],
    "D5": [1, 0, 0, 0, -5, 12],
}


def _translate(c, k):
    """f(x + k): preserves the Galois group and the discriminant."""
    coeffs = list(reversed(c))  # low-first
    out = [0] * 6
    for i in range(6):
        ai = coeffs[i]
        if ai:
            for j in range(i + 1):
                out[j] += ai * math.comb(i, j) * (k ** (i - j))
    return list(reversed(out))


def _scale(c, s):
    """s**5 * f(x / s): monic, preserves the Galois group, multiplies disc by s**20."""
    return [c[i] * (s ** i) for i in range(6)]  # c[i] is the coeff of x**(5-i)


def _poly_mul(a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    return r


def _gen_batch(rng):
    rows = []  # (coeffs, known_label) ; known_label in groups, "reducible", or None
    for g, base in CANONICAL.items():
        for _ in range(3):
            poly = _scale(_translate(base, rng.randint(-4, 4)), rng.randint(70, 200))
            rows.append((poly, g))
    # reducible quintics: (linear)(quartic) or (quadratic)(cubic), squarefree, scaled large
    made = 0
    while made < 5:
        if rng.random() < 0.5:
            small = _poly_mul([1, -rng.randint(-3, 3)], [1] + [rng.randint(-4, 4) for _ in range(4)])
        else:
            small = _poly_mul([1, rng.randint(-4, 4), rng.randint(1, 4)], [1] + [rng.randint(-3, 3) for _ in range(3)])
        if len(small) == 6 and _discriminant(small) != 0:
            rows.append((_scale(small, rng.randint(70, 200)), "reducible"))
            made += 1
    # random large-coefficient quintics (mostly S5) -- prevents hard-coding
    made = 0
    while made < 9:
        poly = [1] + [rng.randint(-10 ** 6, 10 ** 6) for _ in range(5)]
        if _discriminant(poly) != 0:
            rows.append((poly, None))
            made += 1
    rng.shuffle(rows)
    return rows


# --------------------------------------------------------------------------- #
#  Build + run the agent's program once, share results across tests           #
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def run():
    WORKDIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(int.from_bytes(os.urandom(8), "big"))
    rows = _gen_batch(rng)
    inputs = [c for c, _ in rows]
    labels = [lab for _, lab in rows]

    in_path = WORKDIR / "input.txt"
    out_path = WORKDIR / "output.json"
    if out_path.exists():
        out_path.unlink()
    in_path.write_text("".join(" ".join(map(str, c)) + "\n" for c in inputs))

    env = dict(os.environ, CARGO_NET_OFFLINE="true", CARGO_TERM_COLOR="never")
    build = subprocess.run(
        ["cargo", "build", "--release", "--quiet"],
        cwd=str(APP), env=env, capture_output=True, text=True, timeout=600,
    )
    run_proc = None
    if build.returncode == 0:
        run_proc = subprocess.run(
            ["cargo", "run", "--release", "--quiet", "--", str(in_path), str(out_path)],
            cwd=str(APP), env=env, capture_output=True, text=True, timeout=300,
        )

    results = None
    if out_path.exists():
        try:
            results = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            results = None

    expected = [classify(c) + (_resolvent_pairsum(c),) for c in inputs]
    return {
        "inputs": inputs,
        "labels": labels,
        "expected": expected,
        "results": results,
        "build": build,
        "run": run_proc,
    }


def _aligned(run):
    """Return list of (poly, expected_tuple, result_obj) by input order."""
    assert run["results"] is not None, "no parseable output JSON was produced"
    res = run["results"]
    assert len(res) == len(run["inputs"]), (
        f"expected {len(run['inputs'])} results, got {len(res)}"
    )
    return list(zip(run["inputs"], run["expected"], res))


# --------------------------------------------------------------------------- #
#  Tests                                                                       #
# --------------------------------------------------------------------------- #

def test_project_builds(run):
    """The agent's Rust project must compile with cargo (std-only, offline)."""
    assert run["build"].returncode == 0, (
        "cargo build failed:\n" + run["build"].stdout + "\n" + run["build"].stderr
    )


def test_program_runs_and_emits_valid_schema(run):
    """The program runs and writes a JSON array matching the required schema."""
    assert run["run"] is not None and run["run"].returncode == 0, (
        "program did not run cleanly:\n"
        + (run["run"].stderr if run["run"] else "binary never executed")
    )
    rows = _aligned(run)
    for poly, _expected, obj in rows:
        assert isinstance(obj, dict), f"entry is not an object: {obj!r}"
        for key in ("polynomial", "irreducible", "discriminant", "galois_group",
                    "solvable_by_radicals", "pair_sum_resolvent"):
            assert key in obj, f"missing key {key!r} in {obj!r}"
        # the polynomial is an echo of the input; accept JSON numbers (expected) or
        # numeric strings, but the integer values and order must match exactly
        assert [int(x) for x in obj["polynomial"]] == list(poly), (
            f"polynomial echoed wrong / out of order: got {obj['polynomial']}, want {poly}"
        )
        assert isinstance(obj["irreducible"], bool)
        assert isinstance(obj["solvable_by_radicals"], bool)
        assert isinstance(obj["discriminant"], str), "discriminant must be a decimal string"
        int(obj["discriminant"])  # must parse as an integer
        res = obj["pair_sum_resolvent"]
        assert isinstance(res, list) and len(res) == 11, "resolvent must list 11 coefficients"
        assert all(isinstance(x, str) for x in res), "resolvent coefficients must be decimal strings"
        assert int(res[0]) == 1, "the pair-sum resolvent is monic, so its leading coefficient is 1"
        [int(x) for x in res]  # all must parse as integers
        grp = obj["galois_group"]
        assert grp is None or grp in ALLOWED_GROUPS, f"illegal group label {grp!r}"
        if obj["irreducible"]:
            assert grp in ALLOWED_GROUPS, "irreducible quintic must name one of the five groups"
        else:
            assert grp is None, "reducible quintic must have a null group"


def test_discriminant_is_correct(run):
    """The exact integer discriminant must match for every polynomial (big integers)."""
    wrong = []
    for poly, expected, obj in _aligned(run):
        if int(obj["discriminant"]) != expected[3]:
            wrong.append((poly[:2], obj["discriminant"][:12] + "...", str(expected[3])[:12] + "..."))
    assert not wrong, "discriminant errors (poly_head, got, want): " + str(wrong[:6])


def test_discriminants_force_bignum(run):
    """Sanity: many discriminants exceed 2**127, so a 64/128-bit solution cannot be exact."""
    big = [e[3] for e in run["expected"] if abs(e[3]) > TWO_127]
    assert len(big) >= 10, (
        f"expected most discriminants to exceed 2**127, only {len(big)} did"
    )


def test_pair_sum_resolvent_is_correct(run):
    """The degree-10 pairwise-sum resolvent must match exactly for every polynomial.

    Each of the eleven integer coefficients must agree; the intermediate power sums of
    the pairwise sums overflow 128-bit integers on the large inputs, so this can only be
    computed with arbitrary-precision arithmetic, not floating point or fixed-width ints.
    """
    wrong = []
    for poly, expected, obj in _aligned(run):
        got = [int(x) for x in obj["pair_sum_resolvent"]]
        if got != expected[4]:
            wrong.append((poly[:2], got[:3], expected[4][:3]))
    assert not wrong, "pair-sum resolvent errors (poly_head, got_head, want_head): " + str(wrong[:6])


def test_irreducibility_is_correct(run):
    """Each polynomial's irreducibility over Q is identified correctly."""
    wrong = []
    for poly, expected, obj in _aligned(run):
        if bool(obj["irreducible"]) != expected[0]:
            wrong.append((poly[:2], obj["irreducible"], expected[0]))
    assert not wrong, "irreducibility errors (poly_head, got, want): " + str(wrong[:8])


def test_galois_group_is_correct(run):
    """Every irreducible quintic is assigned its true Galois group over Q."""
    wrong = []
    for poly, expected, obj in _aligned(run):
        if expected[0] and obj["galois_group"] != expected[1]:
            wrong.append((poly[:2], obj["galois_group"], expected[1]))
    assert not wrong, "Galois group errors (poly_head, got, want): " + str(wrong[:8])


def test_solvability_is_correct(run):
    """solvable_by_radicals is correct for both irreducible and reducible inputs."""
    wrong = []
    for poly, expected, obj in _aligned(run):
        if bool(obj["solvable_by_radicals"]) != expected[2]:
            wrong.append((poly[:2], obj["solvable_by_radicals"], expected[2]))
    assert not wrong, "solvability errors (poly_head, got, want): " + str(wrong[:8])


def test_reducible_quintics_marked_solvable(run):
    """Reducible quintics are flagged reducible and solvable (all factors have degree <= 4)."""
    seen = 0
    for poly, expected, obj in _aligned(run):
        if not expected[0]:
            seen += 1
            assert obj["irreducible"] is False
            assert obj["galois_group"] is None
            assert obj["solvable_by_radicals"] is True, (
                f"reducible quintic wrongly marked unsolvable: {poly[:2]}"
            )
    assert seen >= 1, "batch generation produced no reducible quintics"


def test_all_branches_exercised(run):
    """Sanity: the batch covers all five groups plus reducible (so each branch is graded)."""
    groups_present = {e[1] for e in run["expected"] if e[0]}
    assert ALLOWED_GROUPS.issubset(groups_present), (
        f"batch failed to cover every group, only saw {sorted(groups_present)}"
    )
    assert any(not e[0] for e in run["expected"]), "batch covered no reducible case"


def test_uses_only_standard_library(run):
    """No third-party crates: Cargo.toml must declare no runtime dependencies."""
    manifests = [m for m in APP.rglob("Cargo.toml") if "target" not in m.parts]
    assert manifests, "no Cargo.toml found under /app"
    dep_re = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=", re.MULTILINE)
    for man in manifests:
        text = man.read_text()
        m = re.search(r"(?ms)^\[dependencies\]\s*(.*?)(?=^\[|\Z)", text)
        if m:
            deps = dep_re.findall(m.group(1))
            assert not deps, f"external crates are not allowed, found {deps} in {man}"


def test_does_not_shell_out(run):
    """The analyzer must be implemented in Rust, not by invoking external solvers.

    Targets process-spawning and references to external CAS tooling; plain
    std::process::exit (no subprocess) is allowed.
    """
    forbidden = re.compile(
        r"Command|\bsystem\s*\(|/usr/bin/|/bin/sh|\bpython\b|sympy|\bsage\b|\bpari\b",
        re.IGNORECASE,
    )
    sources = [p for p in APP.rglob("*.rs") if "target" not in p.parts]
    assert sources, "no Rust sources found under /app"
    offenders = []
    for src in sources:
        for n, line in enumerate(src.read_text(errors="ignore").splitlines(), 1):
            if line.lstrip().startswith("//"):
                continue
            if forbidden.search(line):
                offenders.append(f"{src}:{n}: {line.strip()}")
    assert not offenders, "looks like the solution shells out / uses non-Rust tooling:\n" + "\n".join(offenders[:8])
