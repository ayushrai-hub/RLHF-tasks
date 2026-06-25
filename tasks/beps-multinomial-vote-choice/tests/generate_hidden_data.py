import numpy as np
import pandas as pd

INPUT_PATH = "/app/environment/data/BEPS.csv"
OUTPUT_PATH = "/app/environment/data/BEPS.csv"
SEED = 20260605


def main():
    rng = np.random.default_rng(SEED)
    df = pd.read_csv(INPUT_PATH)
    n_orig = len(df)

    keep = []
    for _, idx in df.groupby("vote").groups.items():
        idx = np.array(idx)
        k = max(3, int(round(len(idx) * 0.85)))
        keep.extend(rng.choice(idx, size=k, replace=False).tolist())
    df = df.loc[sorted(keep)].reset_index(drop=True)

    sd = df["age"].std()
    df["age"] = np.rint(df["age"] + rng.normal(0, sd * 0.05, size=len(df))).astype(int)

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"[hidden] {n_orig} -> {len(df)} rows")


if __name__ == "__main__":
    main()
