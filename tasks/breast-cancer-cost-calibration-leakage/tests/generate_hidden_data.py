import sys
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260754)
source = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path("/app/data/breast-cancer-cost-calibration-leakage.csv")
)
dest = (
    Path(sys.argv[2])
    if len(sys.argv) > 2
    else Path("/tmp/breast-cancer-cost-calibration-leakage_hidden.csv")
)
df = pd.read_csv(source)
groups = np.array(sorted(df["audit_group"].astype(str).unique()))
keep = set(
    rng.choice(groups, size=max(1, int(np.ceil(len(groups) * 0.75))), replace=False)
)
out = df[df["audit_group"].astype(str).isin(keep)].copy()
num_cols = [
    c
    for c in out.columns
    if c not in {"target", "event_month"} and pd.api.types.is_numeric_dtype(out[c])
]
for col in num_cols[:8]:
    vals = pd.to_numeric(out[col], errors="coerce")
    sd = float(vals.replace([np.inf, -np.inf], np.nan).std(skipna=True) or 0.0)
    mask = vals.notna() & ~vals.isin([-999, -777])
    out.loc[mask, col] = vals[mask] + rng.normal(0, sd * 0.035, int(mask.sum()))
cat_cols = [
    c
    for c in out.columns
    if c not in {"record_id", "target"} and not pd.api.types.is_numeric_dtype(out[c])
]
for col in cat_cols[:5]:
    mask = rng.random(len(out)) < 0.03
    shuffled = out.loc[mask, col].sample(frac=1, random_state=20260617).to_numpy()
    out.loc[mask, col] = shuffled
out = out.sort_values(["event_month", "record_id"])
dest.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(dest, index=False)
