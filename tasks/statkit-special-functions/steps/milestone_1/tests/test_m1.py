"""Milestone 1 verifier: regularized incomplete gamma + chi-square CDF.

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


A_VALUES = [0.5, 1.0, 1.7, 2.5, 4.0, 7.3, 12.0, 30.0, 80.0, 150.0]
X_VALUES = [0.05, 0.3, 0.9, 1.5, 3.2, 7.7, 15.0, 40.0, 90.0, 200.0]
CHI_DF = [1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 40.0, 100.0]
CHI_X = [0.1, 0.7, 1.8, 4.0, 9.0, 16.0, 30.0, 55.0, 120.0]


class TestMilestone1:
    """Milestone 1 - incomplete gamma kernels and the chi-square CDF."""

    probe_bin = None

    @classmethod
    def setup_class(cls):
        r = subprocess.run(["make", "lib"], cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, f"`make lib` failed:\n{r.stdout}\n{r.stderr}"
        cls.probe_bin = build_probe("m1")

    def test_make_lib_produces_archive(self):
        """`make lib` builds the static library archive."""
        assert os.path.isfile(os.path.join(APP, "build", "libstatkit.a"))

    def test_gammap_matches_reference(self):
        """sk_gammap matches the independent reference across a wide grid."""
        for a in A_VALUES:
            for x in X_VALUES:
                got = probe(self.probe_bin, "gammap", a, x)
                assert close(got, gammap(a, x)), f"gammap({a},{x})={got}"

    def test_gammaq_matches_reference(self):
        """sk_gammaq matches the independent reference across a wide grid."""
        for a in A_VALUES:
            for x in X_VALUES:
                got = probe(self.probe_bin, "gammaq", a, x)
                assert close(got, gammaq(a, x)), f"gammaq({a},{x})={got}"

    def test_gamma_complement(self):
        """P(a,x) + Q(a,x) == 1 from the compiled library."""
        for a in A_VALUES:
            for x in X_VALUES:
                p = probe(self.probe_bin, "gammap", a, x)
                q = probe(self.probe_bin, "gammaq", a, x)
                assert close(p + q, 1.0), f"P+Q={p+q} at ({a},{x})"

    def test_gammap_known_identities(self):
        """P(1,x)=1-e^-x and P(1/2,x)=erf(sqrt(x))."""
        for x in [0.2, 1.0, 2.5, 6.0, 11.0]:
            assert close(probe(self.probe_bin, "gammap", 1.0, x), 1.0 - math.exp(-x))
            assert close(probe(self.probe_bin, "gammap", 0.5, x), math.erf(math.sqrt(x)))

    def test_gammap_domain_returns_nan(self):
        """sk_gammap returns NaN for a<=0 or x<0."""
        assert _isnan(probe(self.probe_bin, "gammap", -1.0, 2.0))
        assert _isnan(probe(self.probe_bin, "gammap", 0.0, 2.0))
        assert _isnan(probe(self.probe_bin, "gammap", 2.0, -1.0))

    def test_gammaq_domain_returns_nan(self):
        """sk_gammaq returns NaN for a<=0 or x<0 (documented contract)."""
        assert _isnan(probe(self.probe_bin, "gammaq", -1.0, 2.0))
        assert _isnan(probe(self.probe_bin, "gammaq", 0.0, 2.0))
        assert _isnan(probe(self.probe_bin, "gammaq", 2.0, -1.0))

    def test_chisq_cdf_matches_reference(self):
        """sk_chisq_cdf matches the reference chi-square CDF."""
        for k in CHI_DF:
            for x in CHI_X:
                got = probe(self.probe_bin, "chisq_cdf", x, k)
                assert close(got, chisq_cdf(x, k)), f"chisq_cdf({x},{k})={got}"

    def test_chisq_sf_matches_reference(self):
        """sk_chisq_sf matches the reference chi-square survival function."""
        for k in CHI_DF:
            for x in CHI_X:
                got = probe(self.probe_bin, "chisq_sf", x, k)
                assert close(got, chisq_sf(x, k)), f"chisq_sf({x},{k})={got}"

    def test_chisq_cdf_sf_complement(self):
        """chi-square CDF + SF == 1."""
        for k in CHI_DF:
            for x in CHI_X:
                c = probe(self.probe_bin, "chisq_cdf", x, k)
                s = probe(self.probe_bin, "chisq_sf", x, k)
                assert close(c + s, 1.0), f"cdf+sf={c+s} at ({x},{k})"

    def test_chisq_invalid_df_returns_nan(self):
        """chi-square CDF/SF return NaN for non-positive degrees of freedom."""
        assert _isnan(probe(self.probe_bin, "chisq_cdf", 5.0, 0.0))
        assert _isnan(probe(self.probe_bin, "chisq_cdf", 5.0, -2.0))
        assert _isnan(probe(self.probe_bin, "chisq_sf", 5.0, -1.0))

    def test_frozen_acceptance_incgamma(self):
        """The frozen tests/test_incgamma.c passes against the agent library."""
        b = subprocess.run(["make", "build/test/test_incgamma"], cwd=APP,
                            capture_output=True, text=True)
        assert b.returncode == 0, f"build failed:\n{b.stdout}\n{b.stderr}"
        r = subprocess.run([os.path.join(APP, "build", "test", "test_incgamma")],
                           cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout

    def test_frozen_acceptance_chisq(self):
        """The frozen tests/test_chisq.c passes against the agent library."""
        b = subprocess.run(["make", "build/test/test_chisq"], cwd=APP,
                            capture_output=True, text=True)
        assert b.returncode == 0, f"build failed:\n{b.stdout}\n{b.stderr}"
        r = subprocess.run([os.path.join(APP, "build", "test", "test_chisq")],
                           cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout
