"""Milestone 5 verifier: the statctl CLI.

Self-contained: the independent reference is defined inline. Builds the agent's
CLI with `make`, runs it on dynamically generated .spec suites covering all
three test kinds, and compares the JSON report (statistics, Holm-adjusted
p-values, reject decisions, chi-square critical values, Welch confidence
intervals, and Kolmogorov-Smirnov results) to the reference with numerical
tolerance. Also checks report format, ordering, malformed-block handling, the
alpha directive, and exit codes from docs/FORMAT.md. statctl routes through the
milestone 1-4 functions, so a regression there fails these tests too.
"""

import json
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


APP = "/app"
STATCTL = os.path.join(APP, "build", "statctl")


def _write(path, text):
    with open(path, "w") as f:
        f.write(text)


def _run(spec_path, out_path=None):
    args = [STATCTL, spec_path]
    if out_path is not None:
        args += ["-o", out_path]
    return subprocess.run(args, cwd=APP, capture_output=True, text=True, timeout=120)


class TestMilestone5:
    """Milestone 5 - statctl runner: three test kinds, Holm, intervals."""

    @classmethod
    def setup_class(cls):
        r = subprocess.run(["make", "all"], cwd=APP, capture_output=True, text=True)
        assert r.returncode == 0, f"`make all` failed:\n{r.stdout}\n{r.stderr}"
        assert os.path.isfile(STATCTL), "build/statctl was not produced"

    def test_basic_suite_values(self):
        """statctl computes chisq and welch correctly, in order, default alpha."""
        spec = (
            "test die chisq_gof\n"
            "observed 18 22 20 25 15 20\n"
            "expected 20 20 20 20 20 20\n"
            "end\n"
            "test yield welch_t\n"
            "sample_a 12.1 11.8 12.5 12.0 11.6 12.3 12.2 11.9\n"
            "sample_b 11.2 11.5 10.9 11.8 11.0 11.4 11.1\n"
            "end\n"
        )
        _write("/tmp/m5_basic.spec", spec)
        r = _run("/tmp/m5_basic.spec", "/tmp/m5_basic.json")
        assert r.returncode == 0, r.stderr
        data = json.loads(open("/tmp/m5_basic.json").read())
        assert data["version"] == 1
        assert close(data["alpha"], 0.05, rtol=1e-9, atol=1e-12)
        tests = data["tests"]
        assert [t["id"] for t in tests] == ["die", "yield"]

        s0, df0, p0 = chisq_gof_ref([18, 22, 20, 25, 15, 20], [20] * 6, 0)
        assert close(tests[0]["statistic"], s0, rtol=1e-6, atol=1e-9)
        assert close(tests[0]["df"], df0, rtol=1e-6, atol=1e-9)
        assert close(tests[0]["pvalue"], p0, rtol=1e-6, atol=1e-9)
        assert close(tests[0]["critical_value"], chisq_ppf(0.95, df0), rtol=1e-5, atol=1e-6)

        a = [12.1, 11.8, 12.5, 12.0, 11.6, 12.3, 12.2, 11.9]
        b = [11.2, 11.5, 10.9, 11.8, 11.0, 11.4, 11.1]
        s1, df1, p1 = welch_ref(a, b)
        lo, hi = welch_ci_ref(a, b, 0.05)
        assert close(tests[1]["statistic"], s1, rtol=1e-6, atol=1e-9)
        assert close(tests[1]["ci_low"], lo, rtol=1e-5, atol=1e-6)
        assert close(tests[1]["ci_high"], hi, rtol=1e-5, atol=1e-6)

        adj, rej = holm([p0, p1], 0.05)
        assert close(tests[0]["adj_pvalue"], adj[0], rtol=1e-6, atol=1e-9)
        assert tests[1]["reject"] is rej[1]

    def test_ks_normal_values(self):
        """A ks_normal test reports the K-S statistic and p-value, no df/extras."""
        sample = [4.1, 5.2, 4.8, 6.0, 5.5, 4.9, 5.1, 5.8, 4.4, 5.0, 6.2, 4.7]
        spec = "test norm ks_normal\nsample " + " ".join(str(v) for v in sample) + "\nmu 5.0\nsigma 0.7\nend\n"
        _write("/tmp/m5_ks.spec", spec)
        r = _run("/tmp/m5_ks.spec", "/tmp/m5_ks.json")
        assert r.returncode == 0, r.stderr
        t = json.loads(open("/tmp/m5_ks.json").read())["tests"][0]
        assert t["kind"] == "ks_normal"
        assert "df" not in t and "critical_value" not in t and "ci_low" not in t
        d, p = ks_normal_ref(sample, 5.0, 0.7)
        assert close(t["statistic"], d, rtol=1e-6, atol=1e-9), f"D={t['statistic']} ref={d}"
        assert close(t["pvalue"], p, rtol=1e-6, atol=1e-9), f"p={t['pvalue']} ref={p}"

    def test_three_kinds_with_holm(self):
        """All three kinds run together; Holm is applied across them."""
        ks_sample = [1.2, 4.8, 2.1, 9.9, 0.3, 7.7, 5.5, 3.3, 8.8, 6.1]
        spec = (
            "alpha 0.05\n"
            "test g chisq_gof\nobserved 40 10 10 20\nexpected 20 20 20 20\nend\n"
            "test w welch_t\nsample_a 5 6 5 7 6\nsample_b 5.1 6.1 5 6.9 6\nend\n"
            "test k ks_normal\nsample " + " ".join(str(v) for v in ks_sample) + "\nmu 5.0\nsigma 1.0\nend\n"
        )
        _write("/tmp/m5_three.spec", spec)
        r = _run("/tmp/m5_three.spec", "/tmp/m5_three.json")
        assert r.returncode == 0, r.stderr
        tests = json.loads(open("/tmp/m5_three.json").read())["tests"]
        assert [t["kind"] for t in tests] == ["chisq_gof", "welch_t", "ks_normal"]
        raw = [
            chisq_gof_ref([40, 10, 10, 20], [20] * 4, 0)[2],
            welch_ref([5, 6, 5, 7, 6], [5.1, 6.1, 5, 6.9, 6])[2],
            ks_normal_ref(ks_sample, 5.0, 1.0)[1],
        ]
        adj, rej = holm(raw, 0.05)
        for i in range(3):
            assert close(tests[i]["pvalue"], raw[i], rtol=1e-6, atol=1e-9)
            assert close(tests[i]["adj_pvalue"], adj[i], rtol=1e-6, atol=1e-9)
            assert tests[i]["reject"] is rej[i]

    def test_holm_correction(self):
        """Holm-adjusted p-values and reject decisions match the reference."""
        spec = (
            "alpha 0.05\n"
            "test t1 chisq_gof\nobserved 40 10 10 20\nexpected 20 20 20 20\nend\n"
            "test t2 welch_t\nsample_a 10 11 10 12 11\nsample_b 5 6 5 7 6\nend\n"
            "test t3 chisq_gof\nobserved 22 18 20\nexpected 20 20 20\nend\n"
            "test t4 welch_t\nsample_a 5 6 5 7 6\nsample_b 5.1 6.1 5 6.9 6\nend\n"
        )
        _write("/tmp/m5_holm.spec", spec)
        r = _run("/tmp/m5_holm.spec", "/tmp/m5_holm.json")
        assert r.returncode == 0, r.stderr
        tests = json.loads(open("/tmp/m5_holm.json").read())["tests"]
        raw = [
            chisq_gof_ref([40, 10, 10, 20], [20] * 4, 0)[2],
            welch_ref([10, 11, 10, 12, 11], [5, 6, 5, 7, 6])[2],
            chisq_gof_ref([22, 18, 20], [20] * 3, 0)[2],
            welch_ref([5, 6, 5, 7, 6], [5.1, 6.1, 5, 6.9, 6])[2],
        ]
        adj, rej = holm(raw, 0.05)
        for i in range(4):
            assert close(tests[i]["adj_pvalue"], adj[i], rtol=1e-6, atol=1e-9)
            assert tests[i]["reject"] is rej[i]

    def test_alpha_directive_changes_decisions(self):
        """The alpha directive sets the reported alpha and reject threshold."""
        spec = (
            "alpha 0.001\n"
            "test g chisq_gof\nobserved 30 10 10 10\nexpected 15 15 15 15\nend\n"
        )
        _write("/tmp/m5_alpha.spec", spec)
        r = _run("/tmp/m5_alpha.spec", "/tmp/m5_alpha.json")
        assert r.returncode == 0, r.stderr
        data = json.loads(open("/tmp/m5_alpha.json").read())
        assert close(data["alpha"], 0.001, rtol=1e-9, atol=1e-12)
        t = data["tests"][0]
        s, df, p = chisq_gof_ref([30, 10, 10, 10], [15] * 4, 0)
        assert close(t["critical_value"], chisq_ppf(0.999, df), rtol=1e-5, atol=1e-6)
        adj, rej = holm([p], 0.001)
        assert t["reject"] is rej[0]

    def test_report_is_minified_one_line(self):
        """Report is a single minified JSON line with one trailing newline."""
        _write("/tmp/m5_fmt.spec",
               "test a chisq_gof\nobserved 10 12 8\nexpected 10 10 10\nend\n")
        r = _run("/tmp/m5_fmt.spec", "/tmp/m5_fmt.json")
        assert r.returncode == 0, r.stderr
        raw = open("/tmp/m5_fmt.json").read()
        assert raw.endswith("\n") and raw.count("\n") == 1
        body = raw[:-1]
        assert ", " not in body and ": " not in body
        json.loads(body)

    def test_comments_and_blank_lines_ignored(self):
        """Comments and blank lines do not affect parsing."""
        spec = (
            "# c\n\n"
            "test t1 chisq_gof\n   # x\nobserved 30 28 34 26 32\n\nexpected 30 30 30 30 30\nend\n"
        )
        _write("/tmp/m5_comments.spec", spec)
        r = _run("/tmp/m5_comments.spec", "/tmp/m5_comments.json")
        assert r.returncode == 0, r.stderr
        tests = json.loads(open("/tmp/m5_comments.json").read())["tests"]
        assert len(tests) == 1 and tests[0]["id"] == "t1"

    def test_ddof_changes_degrees_of_freedom(self):
        """ddof reduces chi-square degrees of freedom."""
        _write("/tmp/m5_ddof.spec",
               "test fit chisq_gof\nddof 2\nobserved 9 14 20 22 18 12 5\nexpected 7 13 21 24 17 10 8\nend\n")
        r = _run("/tmp/m5_ddof.spec", "/tmp/m5_ddof.json")
        assert r.returncode == 0, r.stderr
        t = json.loads(open("/tmp/m5_ddof.json").read())["tests"][0]
        s, df, p = chisq_gof_ref([9, 14, 20, 22, 18, 12, 5], [7, 13, 21, 24, 17, 10, 8], 2)
        assert close(t["df"], 4.0, rtol=1e-9, atol=1e-9)
        assert close(t["statistic"], s, rtol=1e-6, atol=1e-9)

    def test_welch_df_is_non_integer(self):
        """Welch-Satterthwaite df is fractional, not na+nb-2."""
        _write("/tmp/m5_welch.spec",
               "test w welch_t\nsample_a 5.1 4.9 6.2 5.7 5.5 6.0 5.3\nsample_b 4.2 4.8 3.9 4.5 4.1 4.7\nend\n")
        r = _run("/tmp/m5_welch.spec", "/tmp/m5_welch.json")
        assert r.returncode == 0, r.stderr
        t = json.loads(open("/tmp/m5_welch.json").read())["tests"][0]
        s, df, p = welch_ref([5.1, 4.9, 6.2, 5.7, 5.5, 6.0, 5.3], [4.2, 4.8, 3.9, 4.5, 4.1, 4.7])
        assert close(t["df"], df, rtol=1e-6, atol=1e-9)
        assert abs(t["df"] - round(t["df"])) > 1e-3
        assert abs(t["df"] - (7 + 6 - 2)) > 1e-3

    def test_malformed_blocks_skipped(self):
        """Malformed blocks of every kind are skipped; valid ones still run."""
        spec = (
            "test bad1 chisq_gof\nobserved 5 5 5\nexpected 5 0 5\nend\n"
            "test bad2 welch_t\nsample_a 5.0\nsample_b 1 2 3\nend\n"
            "test bad3 ks_normal\nsample 1 2 3\nmu 2.0\nend\n"
            "test bad4 ks_normal\nsample 1 2 3\nmu 2.0\nsigma 0\nend\n"
            "test ok ks_normal\nsample 1 2 3 4\nmu 2.5\nsigma 1.0\nend\n"
        )
        _write("/tmp/m5_bad.spec", spec)
        r = _run("/tmp/m5_bad.spec", "/tmp/m5_bad.json")
        assert r.returncode == 0, r.stderr
        tests = json.loads(open("/tmp/m5_bad.json").read())["tests"]
        assert [t["id"] for t in tests] == ["ok"]

    def test_no_valid_tests_exit_nonzero(self):
        """A suite with only malformed blocks exits non-zero."""
        _write("/tmp/m5_none.spec",
               "test bad chisq_gof\nobserved 1 2 3\nexpected 1 2\nend\n")
        r = _run("/tmp/m5_none.spec", "/tmp/m5_none.json")
        assert r.returncode != 0

    def test_missing_spec_exit_nonzero(self):
        """A missing spec file exits non-zero."""
        r = _run("/tmp/does_not_exist_m5.spec", "/tmp/m5_missing.json")
        assert r.returncode != 0

    def test_default_output_path(self):
        """With no -o, statctl writes /app/output/report.json."""
        out = os.path.join(APP, "output", "report.json")
        if os.path.exists(out):
            os.remove(out)
        _write("/tmp/m5_default.spec",
               "test d chisq_gof\nobserved 11 9 10\nexpected 10 10 10\nend\n")
        r = _run("/tmp/m5_default.spec", None)
        assert r.returncode == 0, r.stderr
        assert os.path.isfile(out)
        json.loads(open(out).read())
