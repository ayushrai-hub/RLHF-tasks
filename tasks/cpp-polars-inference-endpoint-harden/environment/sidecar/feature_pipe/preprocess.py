"""Polars feature generation sidecar for ridge batch scoring."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import polars as pl

REGIONS = ("west", "east", "north", "south")
CHANNELS = ("web", "phone", "retail")


def build_features(rows: list[dict]) -> dict[str, dict[str, float]]:
    null_mode = os.environ.get("FEATURE_NULL_MODE", "forward")
    frame = pl.DataFrame(rows)
    if null_mode == "forward":
        frame = frame.with_columns(
            pl.col("age").forward_fill(),
            pl.col("tenure_months").forward_fill(),
        )
    else:
        frame = frame.with_columns(
            pl.col("age").fill_null(0.0),
            pl.col("tenure_months").fill_null(0.0),
        )
    out: dict[str, dict[str, float]] = {}
    for row in frame.iter_rows(named=True):
        region = row["region"]
        channel = row["channel"]
        if region not in REGIONS or channel not in CHANNELS:
            continue
        features: dict[str, float] = {
            "age_ff": float(row["age"]) / 100.0,
            "tenure_ff": float(row["tenure_months"]) / 60.0,
        }
        for name in REGIONS:
            features[f"region_{name}"] = 1.0 if region == name else 0.0
        for name in CHANNELS:
            features[f"channel_{name}"] = 1.0 if channel == name else 0.0
        out[str(row["row_id"])] = {
            k: round(float(v), 6) for k, v in features.items()
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    features = build_features(rows)
    Path(args.output).write_text(json.dumps(features, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
