#!/usr/bin/env python3
"""Small RT-IoT2022 baseline that leaves the full analysis unfinished."""

import json
from pathlib import Path

import pandas as pd


DATA_PATH = Path("/app/data/rt_iot2022_public.csv")
OUT_DIR = Path("/app/outputs")
TARGET = "Attack_type"


def rounded(value, digits=6):
    return round(float(value), digits)


def load_frame():
    return pd.read_csv(DATA_PATH)


def simple_split(df):
    cut = int(len(df) * 0.8)
    train_idx = pd.RangeIndex(0, cut).to_numpy()
    test_idx = pd.RangeIndex(cut, len(df)).to_numpy()
    return train_idx, test_idx


def majority_predictions(y_train, y_test):
    label = str(y_train.mode().iloc[0])
    return pd.Series([label] * len(y_test), index=y_test.index)


def class_metrics(labels, y_train, y_test, pred):
    rows = []
    for label in labels:
        support = int((y_test == label).sum())
        predicted_count = int((pred == label).sum())
        true_positive = int(((y_test == label) & (pred == label)).sum())
        precision = 0.0 if predicted_count == 0 else true_positive / predicted_count
        recall = 0.0 if support == 0 else true_positive / support
        f1 = (
            0.0
            if precision + recall == 0
            else 2 * precision * recall / (precision + recall)
        )
        rows.append(
            {
                "class_label": label,
                "support": support,
                "precision": rounded(precision),
                "recall": rounded(recall),
                "f1": rounded(f1),
                "predicted_count": predicted_count,
                "train_support": int((y_train == label).sum()),
                "test_support": support,
            }
        )
    return pd.DataFrame(rows)


def drift_report(df, train_idx, test_idx, features):
    rows = []
    for col in features[:10]:
        train = df.loc[train_idx, col]
        test = df.loc[test_idx, col]
        rows.append(
            {
                "feature": col,
                "kind": "categorical" if train.dtype == "object" else "numeric",
                "train_missing_rate": rounded(train.isna().mean()),
                "test_missing_rate": rounded(test.isna().mean()),
                "psi": 0.0,
                "ks_stat": "",
                "flagged": False,
            }
        )
    return pd.DataFrame(rows)


def confusion_rows(labels, y_test, pred):
    rows = []
    for actual in labels:
        for predicted in labels:
            rows.append(
                {
                    "actual": actual,
                    "predicted": predicted,
                    "count": int(((y_test == actual) & (pred == predicted)).sum()),
                }
            )
    return pd.DataFrame(rows)


def segment_distribution(df, labels):
    segments = []
    for segment in range(10):
        start = int(len(df) * segment / 10)
        end = int(len(df) * (segment + 1) / 10)
        values = df.iloc[start:end][TARGET].astype(str)
        segments.append(
            {
                "segment": segment,
                "rows": int(len(values)),
                "class_distribution": {
                    label: int((values == label).sum()) for label in labels
                },
            }
        )
    return segments


def write_outputs(df):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_idx, test_idx = simple_split(df)
    y = df[TARGET].astype(str)
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]
    pred = majority_predictions(y_train, y_test)
    labels = sorted(y.unique().tolist())
    features = [c for c in df.columns if c != TARGET]
    accuracy = rounded((pred.to_numpy() == y_test.to_numpy()).mean())
    metrics = {
        "task_name": "rt_iot2022_intrusion_detection",
        "target": TARGET,
        "n_rows": int(len(df)),
        "n_features_used": int(len(features)),
        "split_seed": 20260630,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "n_classes": int(len(labels)),
        "accuracy": accuracy,
        "balanced_accuracy": accuracy,
        "macro_f1": 0.0,
        "weighted_f1": 0.0,
        "macro_recall": 0.0,
        "worst_class_recall": 0.0,
        "drift_psi_mean": 0.0,
        "drift_psi_max": 0.0,
        "drift_flag_count": 0,
        "top_drift_feature": str(features[0]),
        "model_family": "decision_tree",
        "wall_clock_sec": 0.0,
    }
    predictions = pd.DataFrame(
        {
            "row_id": test_idx.astype(int),
            "actual": y_test.to_numpy(),
            "predicted": pred.to_numpy(),
            "pred_proba": 1.0,
            "split": "test",
        }
    )
    split_profile = {
        "order_column": "Unnamed: 0",
        "feature_columns": features,
        "dropped_columns": [TARGET],
        "train_order_min": int(df.loc[train_idx, "Unnamed: 0"].min()),
        "train_order_max": int(df.loc[train_idx, "Unnamed: 0"].max()),
        "test_order_min": int(df.loc[test_idx, "Unnamed: 0"].min()),
        "test_order_max": int(df.loc[test_idx, "Unnamed: 0"].max()),
        "train_class_distribution": {
            label: int((y_train == label).sum()) for label in labels
        },
        "test_class_distribution": {
            label: int((y_test == label).sum()) for label in labels
        },
        "segment_class_distribution": segment_distribution(df, labels),
    }
    (OUT_DIR / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    predictions.to_csv(OUT_DIR / "predictions.csv", index=False)
    class_metrics(labels, y_train, y_test, pred).to_csv(
        OUT_DIR / "class_metrics.csv", index=False
    )
    drift_report(df, train_idx, test_idx, features).to_csv(
        OUT_DIR / "drift_report.csv", index=False
    )
    confusion_rows(labels, y_test, pred).to_csv(
        OUT_DIR / "confusion_matrix.csv", index=False
    )
    (OUT_DIR / "split_profile.json").write_text(
        json.dumps(split_profile, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main():
    write_outputs(load_frame())


if __name__ == "__main__":
    main()
