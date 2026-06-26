from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: generate_hidden_data.py INPUT_CSV OUTPUT_CSV")
        return 2

    src = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    rng = np.random.default_rng(20260610)

    data = pd.read_csv(src)
    subjects = (
        data[["Subject", "Sex", "Age"]]
        .drop_duplicates()
        .sort_values(["Sex", "Age", "Subject"])
    )

    keep: list[int] = []
    for _, group in subjects.groupby("Sex", sort=True):
        values = group["Subject"].to_numpy()
        take_n = max(10, int(round(len(values) * 0.72)))
        chosen = rng.choice(values, size=take_n, replace=False)
        keep.extend(int(x) for x in chosen)
    keep = sorted(keep)

    hidden = data[data["Subject"].isin(keep)].copy()
    for subject in keep:
        mask = hidden["Subject"] == subject
        age_shift = rng.normal(0, 1.6)
        ht_shift = rng.normal(0, 0.8)
        wt_mult = np.exp(rng.normal(0, 0.035))
        bsa_mult = np.exp(rng.normal(0, 0.025))
        lbm_mult = np.exp(rng.normal(0, 0.025))
        conc_mult = np.exp(rng.normal(0, 0.055))
        time_mult = np.exp(rng.normal(0, 0.006))

        hidden.loc[mask, "Age"] = np.clip(hidden.loc[mask, "Age"] + age_shift, 18, 90)
        hidden.loc[mask, "Ht"] = hidden.loc[mask, "Ht"] + ht_shift
        hidden.loc[mask, "Wt"] = hidden.loc[mask, "Wt"] * wt_mult
        hidden.loc[mask, "BSA"] = hidden.loc[mask, "BSA"] * bsa_mult
        hidden.loc[mask, "LBM"] = hidden.loc[mask, "LBM"] * lbm_mult
        hidden.loc[mask, "Time"] = hidden.loc[mask, "Time"] * time_mult

        observed = mask & hidden["conc"].notna() & (hidden["conc"] > 0)
        noise = np.exp(rng.normal(0, 0.045, size=int(observed.sum())))
        hidden.loc[observed, "conc"] = hidden.loc[observed, "conc"] * conc_mult * noise

        positive_rate = mask & (hidden["Rate"] > 0)
        hidden.loc[positive_rate, "Rate"] = hidden.loc[positive_rate, "Rate"] * np.exp(
            rng.normal(0, 0.025, size=int(positive_rate.sum()))
        )
        positive_amt = mask & (hidden["Amt"] > 0)
        hidden.loc[positive_amt, "Amt"] = hidden.loc[positive_amt, "Amt"] * np.exp(
            rng.normal(0, 0.025, size=int(positive_amt.sum()))
        )

    numeric_cols = ["Time", "conc", "Rate", "Amt", "Age", "Ht", "Wt", "BSA", "LBM"]
    for col in numeric_cols:
        hidden[col] = hidden[col].round(6)

    dest.parent.mkdir(parents=True, exist_ok=True)
    hidden.to_csv(dest, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
