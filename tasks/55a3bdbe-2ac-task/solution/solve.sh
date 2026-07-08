#!/bin/bash
# Oracle: pooled read-rate fit on the read margin, sized from the lower end of the prediction band so
# the joint worst-case recovery floor holds across the re-read at minimum committed cost. Pure numpy +
# stdlib, closed-form, deterministic.
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

TARGET = 0.970   # size a little above the floor
ZPRED = 3.0      # lower end of the prediction band (carry per-cartridge uncertainty)

with open(os.path.join(DATA, "salvage_program.json")) as f:
    spec = json.load(f)
g_ref = float(spec["reference_margin"])
tmin = float(spec["rate_min"]); tmax = float(spec["rate_max"])
cap = int(spec["bench_capacity"])

ids, margin, c_bench, c_lab = [], [], {}, {}
with open(os.path.join(DATA, "cartridges.csv")) as f:
    for r in csv.DictReader(f):
        ids.append(r["cartridge_id"])
        margin.append(float(r["read_margin"]))
        c_bench[r["cartridge_id"]] = float(r["cost_bench"])
        c_lab[r["cartridge_id"]] = float(r["cost_lab"])
K = len(ids)
margin = np.array(margin)

reads = {i: [] for i in ids}
with open(os.path.join(DATA, "read_log.csv")) as f:
    for r in csv.DictReader(f):
        reads[r["cartridge_id"]].append(int(float(r["verified"])))
k = np.array([sum(reads[i]) for i in ids], dtype=float)
H = np.array([len(reads[i]) for i in ids], dtype=float)


def n_for(theta, target):
    theta = min(max(theta, 1e-6), 0.999999)
    return int(math.ceil(math.log(1.0 - target) / math.log(1.0 - theta)))


delta = margin - g_ref
p_hat = (k + 0.5) / (H + 1.0)
y = np.log(p_hat)
X = np.column_stack([np.ones(K), delta])
w = H * p_hat * (1.0 - p_hat)
W = np.diag(w)
beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
resid = y - X @ beta
s2 = float((w * resid**2).sum() / w.sum() * K / (K - 2))
XtWXi = np.linalg.inv(X.T @ W @ X)
theta = np.empty(K)
for z in range(K):
    xz = X[z]
    sd = math.sqrt(max(float(xz @ XtWXi @ xz) + s2, 0.0))
    theta[z] = min(max(math.exp(float(xz @ beta) - ZPRED * sd), tmin), tmax)

n = np.array([n_for(t, TARGET) for t in theta], dtype=int)

# allocate cheap bench passes (capped) to the cartridges where they save the most
save = np.array([c_lab[ids[i]] - c_bench[ids[i]] for i in range(K)])
order = np.argsort(-save)
bench = np.zeros(K, dtype=int)
remaining = cap
for i in order:
    take = min(int(n[i]), remaining)
    bench[i] = take
    remaining -= take
lab = n - bench
cost = float(sum(c_bench[ids[i]] * bench[i] + c_lab[ids[i]] * lab[i] for i in range(K)))
recovery = 1.0 - (1.0 - theta) ** n

with open(os.path.join(OUT, "recovery_plan.csv"), "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["cartridge_id", "bench_passes", "lab_passes"])
    for i in range(K):
        wr.writerow([ids[i], int(bench[i]), int(lab[i])])

with open(os.path.join(OUT, "kpis.json"), "w") as f:
    json.dump({
        "total_committed_passes": int(n.sum()),
        "total_bench_passes": int(bench.sum()),
        "total_lab_passes": int(lab.sum()),
        "committed_cost": round(cost, 2),
        "worst_cartridge_recovery_prob": round(float(recovery.min()), 4),
    }, f, indent=2)
PY

python3 /app/solve_impl.py
