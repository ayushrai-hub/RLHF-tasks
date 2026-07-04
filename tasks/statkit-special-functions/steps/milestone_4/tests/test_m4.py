"""Milestone 4 verifier: normal CDF + Kolmogorov survival function.

Self-contained: the independent reference and the verifier-owned C probe are
defined inline. Also re-checks the earlier CDFs through the same compiled
library, so a regression there fails here too.
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


NORM_PTS = [-3.0, -1.5, -0.7, 0.0, 0.4, 1.0, 1.96, 2.5]
NORM_PARAMS = [(0.0, 1.0), (5.0, 2.0), (-2.0, 0.5), (100.0, 15.0)]
KS_T = [0.2, 0.35, 0.5, 0.8, 1.0, 1.36, 1.63, 2.0, 2.8, 3.5]


class TestMilestone4:
    """Milestone 4 - normal CDF and the Kolmogorov survival function."""

    probe_bin = None

    @classmethod
    def setup_class(cls):
        r = subprocess.run(["make", "lib"], cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, f"`make lib` failed:\n{r.stdout}\n{r.stderr}"
        cls.probe_bin = build_probe("m4")

    def test_normal_cdf_matches_reference(self):
        """sk_normal_cdf matches the independent reference."""
        for mu, sigma in NORM_PARAMS:
            for z in NORM_PTS:
                x = mu + z * sigma
                got = probe(self.probe_bin, "normal_cdf", x, mu, sigma)
                assert close(got, normal_cdf(x, mu, sigma)), f"normal_cdf({x},{mu},{sigma})={got}"

    def test_normal_cdf_symmetry(self):
        """Phi(z) + Phi(-z) == 1 about the mean."""
        for mu, sigma in NORM_PARAMS:
            for z in [0.3, 1.0, 2.2]:
                lo = probe(self.probe_bin, "normal_cdf", mu - z * sigma, mu, sigma)
                hi = probe(self.probe_bin, "normal_cdf", mu + z * sigma, mu, sigma)
                assert close(lo + hi, 1.0)

    def test_normal_cdf_known(self):
        """Standard-normal reference points."""
        assert close(probe(self.probe_bin, "normal_cdf", 0.0, 0.0, 1.0), 0.5)
        assert close(probe(self.probe_bin, "normal_cdf", 1.0, 0.0, 1.0), 0.8413447460685428, rtol=1e-10, atol=1e-12)
        assert close(probe(self.probe_bin, "normal_cdf", 1.96, 0.0, 1.0), 0.9750021048517796, rtol=1e-10, atol=1e-12)

    def test_normal_cdf_domain_returns_nan(self):
        """Non-positive sigma returns NaN."""
        assert _isnan(probe(self.probe_bin, "normal_cdf", 1.0, 0.0, 0.0))
        assert _isnan(probe(self.probe_bin, "normal_cdf", 1.0, 0.0, -2.0))

    def test_ks_sf_matches_reference(self):
        """sk_ks_sf matches the independent reference across a range of t."""
        for t in KS_T:
            got = probe(self.probe_bin, "ks_sf", t)
            assert close(got, ks_sf(t), rtol=1e-7, atol=1e-9), f"ks_sf({t})={got}"

    def test_ks_sf_boundary_and_monotone(self):
        """ks_sf is 1 at or below 0 and strictly decreasing for t>0."""
        assert close(probe(self.probe_bin, "ks_sf", -1.0), 1.0)
        assert close(probe(self.probe_bin, "ks_sf", 0.0), 1.0)
        assert probe(self.probe_bin, "ks_sf", 0.5) > probe(self.probe_bin, "ks_sf", 1.0)
        assert probe(self.probe_bin, "ks_sf", 1.0) > probe(self.probe_bin, "ks_sf", 2.0)
        assert probe(self.probe_bin, "ks_sf", 0.05) > 0.999

    def test_ks_sf_known(self):
        """Known Kolmogorov survival values."""
        assert close(probe(self.probe_bin, "ks_sf", 1.0), 0.26999967167735456, rtol=1e-7, atol=1e-9)
        assert close(probe(self.probe_bin, "ks_sf", 2.0), 0.0006709252557796953, rtol=1e-7, atol=1e-9)

    def test_milestone_cdfs_still_correct(self):
        """Earlier CDFs/quantiles must remain correct (no regression)."""
        for k in [2.0, 10.0]:
            for x in [1.0, 12.0]:
                assert close(probe(self.probe_bin, "chisq_cdf", x, k), chisq_cdf(x, k))
        assert close(probe(self.probe_bin, "tdist_ppf", 0.975, 9.0), tdist_ppf(0.975, 9.0), rtol=1e-5, atol=1e-6)

    def test_frozen_acceptance_ksdist(self):
        """The frozen tests/test_ksdist.c passes against the agent library."""
        b = subprocess.run(["make", "build/test/test_ksdist"], cwd=APP,
                            capture_output=True, text=True)
        assert b.returncode == 0, f"build failed:\n{b.stdout}\n{b.stderr}"
        r = subprocess.run([os.path.join(APP, "build", "test", "test_ksdist")],
                           cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout
