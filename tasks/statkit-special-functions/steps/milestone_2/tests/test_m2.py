"""Milestone 2 verifier: regularized incomplete beta + Student-t / F CDFs.

Self-contained: the independent reference and the verifier-owned C probe are
defined inline. The agent's compiled C is driven through the probe and compared
to the reference with numerical tolerance; the agent's own Makefile build and
the frozen C acceptance suite are also exercised.
"""

import glob
import math
import os
import subprocess

# --- Independent reference implementation (verified against SciPy/statsmodels
# --- to high precision). Pure double precision, no third-party deps.


def _gser(a, x):
    if x <= 0.0:
        return 0.0
    ap = a
    summ = 1.0 / a
    delt = summ
    for _ in range(1000):
        ap += 1.0
        delt *= x / ap
        summ += delt
        if abs(delt) < abs(summ) * 1e-16:
            break
    return summ * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a, x):
    fpmin = 1e-300
    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delt = d * c
        h *= delt
        if abs(delt - 1.0) < 1e-16:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gammap(a, x):
    if x < 0.0 or a <= 0.0:
        return float("nan")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _gser(a, x)
    return 1.0 - _gcf(a, x)


def gammaq(a, x):
    if x < 0.0 or a <= 0.0:
        return float("nan")
    if x == 0.0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gser(a, x)
    return _gcf(a, x)


def _betacf(a, b, x):
    fpmin = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delt = d * c
        h *= delt
        if abs(delt - 1.0) < 1e-16:
            break
    return h


def betai(a, b, x):
    if x < 0.0 or x > 1.0 or a <= 0.0 or b <= 0.0:
        return float("nan")
    if x == 0.0 or x == 1.0:
        bt = 0.0
    else:
        bt = math.exp(
            math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
            + a * math.log(x) + b * math.log(1.0 - x)
        )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def chisq_cdf(x, k):
    if k <= 0.0:
        return float("nan")
    if x <= 0.0:
        return 0.0
    return gammap(k / 2.0, x / 2.0)


def chisq_sf(x, k):
    if k <= 0.0:
        return float("nan")
    if x <= 0.0:
        return 1.0
    return gammaq(k / 2.0, x / 2.0)


def tdist_cdf(t, nu):
    if nu <= 0.0:
        return float("nan")
    z = nu / (nu + t * t)
    ib = betai(nu / 2.0, 0.5, z)
    return 1.0 - 0.5 * ib if t >= 0.0 else 0.5 * ib


def tdist_sf(t, nu):
    return 1.0 - tdist_cdf(t, nu)


def fdist_cdf(f, d1, d2):
    if d1 <= 0.0 or d2 <= 0.0:
        return float("nan")
    if f <= 0.0:
        return 0.0
    w = d1 * f / (d1 * f + d2)
    return betai(d1 / 2.0, d2 / 2.0, w)


def chisq_ppf(p, k):
    if p <= 0.0 or p >= 1.0 or k <= 0.0:
        return float("nan")
    lo, hi = 0.0, 1.0
    while chisq_cdf(hi, k) < p:
        hi *= 2.0
        if hi > 1e15:
            break
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if chisq_cdf(mid, k) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def tdist_ppf(p, nu):
    if p <= 0.0 or p >= 1.0 or nu <= 0.0:
        return float("nan")
    lo, hi = -1.0, 1.0
    while tdist_cdf(lo, nu) > p:
        lo *= 2.0
        if lo < -1e15:
            break
    while tdist_cdf(hi, nu) < p:
        hi *= 2.0
        if hi > 1e15:
            break
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if tdist_cdf(mid, nu) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def normal_cdf(x, mu, sigma):
    if sigma <= 0.0:
        return float("nan")
    return 0.5 * math.erfc(-(x - mu) / (sigma * math.sqrt(2.0)))


def ks_sf(t):
    if t <= 0.0:
        return 1.0
    s = 0.0
    sign = 1.0
    a2 = -2.0 * t * t
    for k in range(1, 1000):
        term = sign * math.exp(a2 * k * k)
        s += term
        sign = -sign
        if abs(term) < 1e-18:
            break
    v = 2.0 * s
    if v < 0.0:
        v = 0.0
    if v > 1.0:
        v = 1.0
    return v


def chisq_gof_ref(observed, expected, ddof=0):
    stat = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
    df = len(observed) - 1 - ddof
    return stat, float(df), chisq_sf(stat, df)


def welch_ref(a, b):
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((v - ma) ** 2 for v in a) / (na - 1)
    vb = sum((v - mb) ** 2 for v in b) / (nb - 1)
    sa, sb = va / na, vb / nb
    t = (ma - mb) / math.sqrt(sa + sb)
    df = (sa + sb) ** 2 / (sa * sa / (na - 1) + sb * sb / (nb - 1))
    p = 2.0 * (1.0 - tdist_cdf(abs(t), df))
    return t, df, p


def welch_ci_ref(a, b, alpha):
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((v - ma) ** 2 for v in a) / (na - 1)
    vb = sum((v - mb) ** 2 for v in b) / (nb - 1)
    sa, sb = va / na, vb / nb
    se = math.sqrt(sa + sb)
    df = (sa + sb) ** 2 / (sa * sa / (na - 1) + sb * sb / (nb - 1))
    tc = tdist_ppf(1.0 - alpha / 2.0, df)
    md = ma - mb
    return md - tc * se, md + tc * se


def ks_normal_ref(sample, mu, sigma):
    xs = sorted(sample)
    n = len(xs)
    dplus = 0.0
    dminus = 0.0
    for i, x in enumerate(xs):
        f = normal_cdf(x, mu, sigma)
        dplus = max(dplus, (i + 1) / n - f)
        dminus = max(dminus, f - i / n)
    d = max(dplus, dminus)
    return d, ks_sf(math.sqrt(n) * d)


def holm(pvals, alpha):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adj = [0.0] * n
    reject = [False] * n
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (n - rank) * pvals[i])
        running = max(running, val)
        adj[i] = running
        reject[i] = adj[i] <= alpha
    return adj, reject


def close(a, b, rtol=1e-9, atol=1e-12):
    if a != a or b != b:  # NaN
        return False
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= atol + rtol * abs(b)


def _isnan(v):
    return v != v


APP = "/app"

_PROBE_C = r"""
#include "statkit/distrib.h"
#include "statkit/specfun.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc < 2) {
        return 2;
    }
    const char *fn = argv[1];
    double r;

    if (strcmp(fn, "gammap") == 0 && argc == 4) {
        r = sk_gammap(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "gammaq") == 0 && argc == 4) {
        r = sk_gammaq(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "betai") == 0 && argc == 5) {
        r = sk_betai(atof(argv[2]), atof(argv[3]), atof(argv[4]));
    } else if (strcmp(fn, "chisq_cdf") == 0 && argc == 4) {
        r = sk_chisq_cdf(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "chisq_sf") == 0 && argc == 4) {
        r = sk_chisq_sf(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "tdist_cdf") == 0 && argc == 4) {
        r = sk_tdist_cdf(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "tdist_sf") == 0 && argc == 4) {
        r = sk_tdist_sf(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "fdist_cdf") == 0 && argc == 5) {
        r = sk_fdist_cdf(atof(argv[2]), atof(argv[3]), atof(argv[4]));
    } else if (strcmp(fn, "chisq_ppf") == 0 && argc == 4) {
        r = sk_chisq_ppf(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "tdist_ppf") == 0 && argc == 4) {
        r = sk_tdist_ppf(atof(argv[2]), atof(argv[3]));
    } else if (strcmp(fn, "normal_cdf") == 0 && argc == 5) {
        r = sk_normal_cdf(atof(argv[2]), atof(argv[3]), atof(argv[4]));
    } else if (strcmp(fn, "ks_sf") == 0 && argc == 3) {
        r = sk_ks_sf(atof(argv[2]));
    } else {
        return 3;
    }

    printf("%.17g\n", r);
    return 0;


}
"""


def build_probe(tag):
    """Compile the verifier probe against the agent's src/*.c; return its path."""
    src = "/tmp/sk_probe_%s.c" % tag
    with open(src, "w") as fh:
        fh.write(_PROBE_C)
    srcs = sorted(glob.glob("/app/src/*.c"))
    if not srcs:
        raise AssertionError("no source files found under /app/src")
    out = "/tmp/sk_probe_%s" % tag
    cmd = ["cc", "-O2", "-std=c11", "-I", "/app/include", src, *srcs, "-lm", "-o", out]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise AssertionError("probe build failed:\n" + res.stdout + "\n" + res.stderr)
    return out


def probe(binpath, fn, *args):
    cmd = [binpath, fn, *[repr(float(a)) for a in args]]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise AssertionError(
            "probe %s%r exited %d: %s" % (fn, args, res.returncode, res.stderr)
        )
    return float(res.stdout.strip())


A_VALUES = [0.5, 1.0, 2.0, 3.5, 6.0, 10.0, 20.0, 50.0]
B_VALUES = [0.5, 1.0, 2.5, 4.0, 8.0, 15.0, 30.0]
X_VALUES = [0.01, 0.1, 0.27, 0.5, 0.73, 0.9, 0.99]
NU_VALUES = [1.0, 2.0, 3.5, 7.0, 10.86, 25.0, 60.0, 120.0]
T_VALUES = [-4.0, -2.1, -0.7, 0.0, 0.4, 1.3, 2.8, 5.0]
F_VALUES = [0.2, 0.8, 1.5, 3.0, 6.0]
D_PAIRS = [(1.0, 1.0), (2.0, 8.0), (5.0, 10.0), (10.0, 20.0), (3.0, 30.0)]


class TestMilestone2:
    """Milestone 2 - incomplete beta and the t / F distribution CDFs."""

    probe_bin = None

    @classmethod
    def setup_class(cls):
        r = subprocess.run(["make", "lib"], cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, f"`make lib` failed:\n{r.stdout}\n{r.stderr}"
        cls.probe_bin = build_probe("m2")

    def test_betai_matches_reference(self):
        """sk_betai matches the independent reference across a wide grid."""
        for a in A_VALUES:
            for b in B_VALUES:
                for x in X_VALUES:
                    got = probe(self.probe_bin, "betai", a, b, x)
                    assert close(got, betai(a, b, x)), f"betai({a},{b},{x})={got}"

    def test_betai_symmetry(self):
        """I_x(a,b) + I_{1-x}(b,a) == 1."""
        for a in A_VALUES:
            for b in B_VALUES:
                x = 0.41
                lo = probe(self.probe_bin, "betai", a, b, x)
                hi = probe(self.probe_bin, "betai", b, a, 1.0 - x)
                assert close(lo + hi, 1.0), f"sym fail a={a} b={b}: {lo+hi}"

    def test_betai_known_identities(self):
        """I_x(1,1)=x, I_x(a,1)=x^a, I_x(1,b)=1-(1-x)^b."""
        for x in [0.13, 0.37, 0.6, 0.88]:
            assert close(probe(self.probe_bin, "betai", 1.0, 1.0, x), x)
            assert close(probe(self.probe_bin, "betai", 3.0, 1.0, x), x ** 3.0)
            assert close(probe(self.probe_bin, "betai", 1.0, 4.0, x), 1.0 - (1.0 - x) ** 4.0)

    def test_betai_domain_returns_nan(self):
        """sk_betai returns NaN for x out of [0,1] or non-positive a or b."""
        assert _isnan(probe(self.probe_bin, "betai", 2.0, 3.0, -0.1))
        assert _isnan(probe(self.probe_bin, "betai", 2.0, 3.0, 1.1))
        assert _isnan(probe(self.probe_bin, "betai", 0.0, 3.0, 0.5))
        assert _isnan(probe(self.probe_bin, "betai", 2.0, -1.0, 0.5))

    def test_tdist_cdf_matches_reference(self):
        """sk_tdist_cdf matches the reference, including non-integer nu."""
        for nu in NU_VALUES:
            for t in T_VALUES:
                got = probe(self.probe_bin, "tdist_cdf", t, nu)
                assert close(got, tdist_cdf(t, nu)), f"tdist_cdf({t},{nu})={got}"

    def test_tdist_symmetry_and_complement(self):
        """CDF(-t)=1-CDF(t) and CDF+SF=1 from the compiled library."""
        for nu in NU_VALUES:
            for t in [0.4, 1.3, 2.8]:
                c = probe(self.probe_bin, "tdist_cdf", t, nu)
                cm = probe(self.probe_bin, "tdist_cdf", -t, nu)
                s = probe(self.probe_bin, "tdist_sf", t, nu)
                assert close(cm, 1.0 - c)
                assert close(c + s, 1.0)

    def test_tdist_at_zero(self):
        """t CDF at 0 is exactly 1/2 for any nu."""
        for nu in NU_VALUES:
            assert close(probe(self.probe_bin, "tdist_cdf", 0.0, nu), 0.5)

    def test_tdist_invalid_df_returns_nan(self):
        """Student-t CDF returns NaN for non-positive nu."""
        assert _isnan(probe(self.probe_bin, "tdist_cdf", 1.0, 0.0))
        assert _isnan(probe(self.probe_bin, "tdist_cdf", 1.0, -3.0))

    def test_fdist_cdf_matches_reference(self):
        """sk_fdist_cdf matches the reference F-distribution CDF."""
        for d1, d2 in D_PAIRS:
            for f in F_VALUES:
                got = probe(self.probe_bin, "fdist_cdf", f, d1, d2)
                assert close(got, fdist_cdf(f, d1, d2)), f"fdist_cdf({f},{d1},{d2})={got}"

    def test_fdist_invalid_df_returns_nan(self):
        """F CDF returns NaN for non-positive d1 or d2."""
        assert _isnan(probe(self.probe_bin, "fdist_cdf", 2.0, -1.0, 5.0))
        assert _isnan(probe(self.probe_bin, "fdist_cdf", 2.0, 5.0, 0.0))

    def test_milestone1_chisq_still_correct(self):
        """Milestone 1 chi-square CDF must remain correct (no regression)."""
        for k in [1.0, 4.0, 10.0, 30.0]:
            for x in [0.7, 4.0, 12.0, 35.0]:
                got = probe(self.probe_bin, "chisq_cdf", x, k)
                assert close(got, chisq_cdf(x, k)), f"chisq regressed at ({x},{k})"

    def test_frozen_acceptance_beta_and_dists(self):
        """The frozen tests/test_incbeta.c and tests/test_tdist_fdist.c pass."""
        for name in ("test_incbeta", "test_tdist_fdist"):
            b = subprocess.run(["make", f"build/test/{name}"], cwd=APP,
                               capture_output=True, text=True)
            assert b.returncode == 0, f"build {name} failed:\n{b.stdout}\n{b.stderr}"
            r = subprocess.run([os.path.join(APP, "build", "test", name)],
                               cwd=APP, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout
