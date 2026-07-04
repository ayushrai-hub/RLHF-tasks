#!/bin/bash
# Oracle: an empirical-Bayes beta-binomial read on each alloy's per-shot shear-band-nucleation rate. A
# pooled weighted log-rate fit on softening_index sets a prior; each alloy's own banded/uniform shots
# update it; the adopted figure is the lower quantile of that posterior, so an alloy whose log is short or
# all-uniform is sized down hard regardless of how susceptible its ratio reads. Shots are then sized to
# clear the floor and allocated cheap-in-house-bar-first under the capacity. Pure numpy + stdlib,
# closed-form, deterministic.
set -euo pipefail

mkdir -p /app/output
cat > /app/solve_impl.py <<'PY'
import os, csv, json, math
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

DATA = os.environ.get("DATA_DIR", "/app/data")
OUT = os.environ.get("OUT_DIR", "/app/output")
os.makedirs(OUT, exist_ok=True)

TARGET = 0.971   # size a little above the floor
KAPPA = 6.0      # prior pseudo-count blended with each alloy's own shots
Q = 0.05         # lower quantile of the posterior the adopted rate is read at

with open(os.path.join(DATA, "test_program.json")) as f:
    prog = json.load(f)
m_ref = float(prog["reference_softening"])
tmin = float(prog["rate_min"]); tmax = float(prog["rate_max"])
cap = int(prog["bar_capacity"])

ids, softidx, c_house, c_lab = [], [], {}, {}
with open(os.path.join(DATA, "alloys.csv")) as f:
    for r in csv.DictReader(f):
        ids.append(r["alloy_id"])
        softidx.append(float(r["softening_index"]))
        c_house[r["alloy_id"]] = float(r["cost_house"])
        c_lab[r["alloy_id"]] = float(r["cost_lab"])
K = len(ids)
softidx = np.array(softidx)

runs = {i: [] for i in ids}
with open(os.path.join(DATA, "shot_log.csv")) as f:
    for r in csv.DictReader(f):
        runs[r["alloy_id"]].append(int(float(r["banded"])))
k = np.array([sum(runs[i]) for i in ids], dtype=float)
H = np.array([len(runs[i]) for i in ids], dtype=float)


def n_for(theta, target):
    theta = min(max(theta, 1e-6), 0.999999)
    return int(math.ceil(math.log(1.0 - target) / math.log(1.0 - theta)))


def _betacf(x, a, b):
    MAXIT, EPS, FPMIN = 300, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def betai(x, a, b):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lb + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(x, a, b) / a
    return 1.0 - bt * _betacf(1.0 - x, b, a) / b


def beta_q(a, b, q):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if betai(m, a, b) < q:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


# pooled weighted log-rate fit on softening_index -> prior mean per alloy
delta = softidx - m_ref
p_hat = (k + 0.5) / (H + 1.0)
y = np.log(p_hat)
X = np.column_stack([np.ones(K), delta])
w = H * p_hat * (1.0 - p_hat)
w = np.where(w <= 0, 1e-6, w)
W = np.diag(w)
beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
prior = np.clip(np.exp(X @ beta), tmin, tmax)

# beta-binomial posterior (prior pseudo-counts + own banded/uniform shots), read at the lower quantile
a = prior * KAPPA + k
b = (1.0 - prior) * KAPPA + (H - k)
theta = np.array([min(max(beta_q(a[i], b[i], Q), tmin), tmax) for i in range(K)])

n = np.array([n_for(t, TARGET) for t in theta], dtype=int)

# fill cheap in-house-bar shots first (capped) where they save the most over the outside-lab price
save = np.array([c_lab[ids[i]] - c_house[ids[i]] for i in range(K)])
order = np.argsort(-save)
house = np.zeros(K, dtype=int)
remaining = cap
for i in order:
    take = min(int(n[i]), remaining)
    house[i] = take
    remaining -= take
lab = n - house
cost = float(sum(c_house[ids[i]] * house[i] + c_lab[ids[i]] * lab[i] for i in range(K)))
bandprob = 1.0 - (1.0 - theta) ** n

with open(os.path.join(OUT, "shot_plan.csv"), "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["alloy_id", "house_shots", "lab_shots", "adopted_rate"])
    for i in range(K):
        wr.writerow([ids[i], int(house[i]), int(lab[i]), float(theta[i])])

with open(os.path.join(OUT, "kpis.json"), "w") as f:
    json.dump({
        "total_committed_shots": int(n.sum()),
        "total_house_shots": int(house.sum()),
        "total_lab_shots": int(lab.sum()),
        "committed_cost": round(cost, 2),
        "worst_alloy_band_prob": round(float(bandprob.min()), 4),
    }, f, indent=2)
PY

python3 /app/solve_impl.py
