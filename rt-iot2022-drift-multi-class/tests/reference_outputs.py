"""Independent reference calculations for rt-iot2022-drift-multi-class tests."""

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder


TASK_NAME = "rt-iot2022-drift-multi-class"
TARGET = "Attack_type"
ORDER_COL = "Unnamed: 0"
SPLIT_SEED = 20260630
ALL_LABELS = [
    "ARP_poisioning",
    "DDOS_Slowloris",
    "DOS_SYN_Hping",
    "MQTT_Publish",
    "Metasploit_Brute_Force_SSH",
    "NMAP_FIN_SCAN",
    "NMAP_OS_DETECTION",
    "NMAP_TCP_scan",
    "NMAP_UDP_SCAN",
    "NMAP_XMAS_TREE_SCAN",
    "Thing_Speak",
    "Wipro_bulb",
]


def paths():
    app_dir = Path(os.environ.get("APP_DIR", "/app"))
    data_dir = Path(os.environ.get("DATA_DIR", app_dir / "data"))
    out_dir = Path(os.environ.get("OUT_DIR", app_dir / "outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, out_dir


def load_frame():
    data_dir, _ = paths()
    df = pd.read_csv(data_dir / "rt_iot2022_public.csv")
    return df.sort_values(ORDER_COL).reset_index(drop=True)


def order_split(df):
    train_parts = []
    test_parts = []
    for _, group in df.groupby(TARGET, sort=False):
        idx = group.sort_values(ORDER_COL).index.to_numpy()
        cut = max(1, int(np.floor(0.7 * len(idx))))
        if cut >= len(idx):
            cut = len(idx) - 1
        train_parts.append(idx[:cut])
        test_parts.append(idx[cut:])
    train_idx = np.sort(np.concatenate(train_parts))
    test_idx = np.sort(np.concatenate(test_parts))
    return train_idx, test_idx


def feature_lists(df):
    drop = [TARGET, ORDER_COL]
    features = [c for c in df.columns if c not in drop]
    categorical = [c for c in features if df[c].dtype == "object"]
    numeric = [c for c in features if c not in categorical]
    return numeric, categorical


def make_pipeline(numeric, categorical):
    pre = ColumnTransformer(
        [
            ("num", SimpleImputer(strategy="median"), numeric),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OrdinalEncoder(
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                                encoded_missing_value=-1,
                            ),
                        ),
                    ]
                ),
                categorical,
            ),
        ],
        verbose_feature_names_out=False,
    )
    model = RandomForestClassifier(
        n_estimators=120,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=1,
        random_state=7002,
    )
    return Pipeline([("pre", pre), ("model", model)])


def psi_numeric(a, b, bins=10):
    quantiles = np.unique(np.nanquantile(a, np.linspace(0, 1, bins + 1)))
    if len(quantiles) < 3:
        quantiles = np.linspace(np.nanmin(a), np.nanmax(a) + 1e-9, bins + 1)
    ac = np.histogram(a, bins=quantiles)[0].astype(float)
    bc = np.histogram(b, bins=quantiles)[0].astype(float)
    ap = np.clip(ac / max(ac.sum(), 1.0), 1e-6, 1.0)
    bp = np.clip(bc / max(bc.sum(), 1.0), 1e-6, 1.0)
    return float(np.sum((ap - bp) * np.log(ap / bp)))


def psi_categorical(a, b):
    av = pd.Series(a).astype(str).value_counts(normalize=True)
    bv = pd.Series(b).astype(str).value_counts(normalize=True)
    keys = sorted(set(av.index) | set(bv.index))
    ap = np.array([max(float(av.get(k, 0.0)), 1e-6) for k in keys])
    bp = np.array([max(float(bv.get(k, 0.0)), 1e-6) for k in keys])
    ap = ap / ap.sum()
    bp = bp / bp.sum()
    return float(np.sum((ap - bp) * np.log(ap / bp)))


def drift_report(df, train_idx, test_idx, numeric, categorical):
    rows = []
    for col in numeric:
        train = pd.to_numeric(df.loc[train_idx, col], errors="coerce")
        test = pd.to_numeric(df.loc[test_idx, col], errors="coerce")
        tr = train.fillna(train.median()).to_numpy(dtype=float)
        te = test.fillna(train.median()).to_numpy(dtype=float)
        psi = psi_numeric(tr, te)
        ks = float(ks_2samp(tr, te).statistic)
        rows.append(
            {
                "feature": col,
                "kind": "numeric",
                "train_missing_rate": round(float(train.isna().mean()), 6),
                "test_missing_rate": round(float(test.isna().mean()), 6),
                "psi": round(psi, 6),
                "ks_stat": round(ks, 6),
                "flagged": bool(psi >= 0.10 or ks >= 0.08),
            }
        )
    for col in categorical:
        psi = psi_categorical(df.loc[train_idx, col], df.loc[test_idx, col])
        rows.append(
            {
                "feature": col,
                "kind": "categorical",
                "train_missing_rate": round(
                    float(df.loc[train_idx, col].isna().mean()), 6
                ),
                "test_missing_rate": round(
                    float(df.loc[test_idx, col].isna().mean()), 6
                ),
                "psi": round(psi, 6),
                "ks_stat": "",
                "flagged": bool(psi >= 0.10),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["psi", "feature"], ascending=[False, True])
        .reset_index(drop=True)
    )


def segment_profile(df):
    order = np.arange(len(df))
    seg = np.minimum((order * 10) // len(df), 9)
    rows = []
    for s in range(10):
        sub = df.loc[seg == s, TARGET]
        rows.append(
            {
                "segment": int(s),
                "rows": int(len(sub)),
                "class_distribution": {
                    str(k): int(v) for k, v in sub.value_counts().sort_index().items()
                },
            }
        )
    return rows


def evaluate_outputs(df):
    t0 = time.time()
    train_idx, test_idx = order_split(df)
    numeric, categorical = feature_lists(df)
    pipe = make_pipeline(numeric, categorical)
    X_train = df.loc[train_idx, numeric + categorical]
    y_train = df.loc[train_idx, TARGET].astype(str)
    X_test = df.loc[test_idx, numeric + categorical]
    y_test = df.loc[test_idx, TARGET].astype(str)
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    proba = pipe.predict_proba(X_test)
    classes = list(pipe.named_steps["model"].classes_)
    pred_prob = np.array(
        [proba[i, classes.index(label)] for i, label in enumerate(pred)]
    )
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, pred, labels=ALL_LABELS, zero_division=0
    )
    predicted_counts = pd.Series(pred).value_counts()
    train_counts = y_train.value_counts()
    test_counts = y_test.value_counts()
    class_metrics = pd.DataFrame(
        {
            "class_label": ALL_LABELS,
            "support": support.astype(int),
            "precision": np.round(precision, 6),
            "recall": np.round(recall, 6),
            "f1": np.round(f1, 6),
            "predicted_count": [int(predicted_counts.get(c, 0)) for c in ALL_LABELS],
            "train_support": [int(train_counts.get(c, 0)) for c in ALL_LABELS],
            "test_support": [int(test_counts.get(c, 0)) for c in ALL_LABELS],
        }
    ).sort_values("class_label")
    matrix = confusion_matrix(y_test, pred, labels=ALL_LABELS)
    cm_rows = []
    for i, actual in enumerate(ALL_LABELS):
        for j, predicted in enumerate(ALL_LABELS):
            cm_rows.append(
                {"actual": actual, "predicted": predicted, "count": int(matrix[i, j])}
            )
    cm = pd.DataFrame(cm_rows).sort_values(["actual", "predicted"])
    drift = drift_report(df, train_idx, test_idx, numeric, categorical)
    metrics = {
        "task_name": TASK_NAME,
        "target": TARGET,
        "n_rows": int(len(df)),
        "n_features_used": int(len(numeric) + len(categorical)),
        "split_seed": int(SPLIT_SEED),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "n_classes": int(len(ALL_LABELS)),
        "accuracy": round(float(accuracy_score(y_test, pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_test, pred)), 6),
        "macro_f1": round(
            float(
                f1_score(
                    y_test, pred, labels=ALL_LABELS, average="macro", zero_division=0
                )
            ),
            6,
        ),
        "weighted_f1": round(
            float(
                f1_score(
                    y_test, pred, labels=ALL_LABELS, average="weighted", zero_division=0
                )
            ),
            6,
        ),
        "macro_recall": round(
            float(
                recall_score(
                    y_test, pred, labels=ALL_LABELS, average="macro", zero_division=0
                )
            ),
            6,
        ),
        "worst_class_recall": round(float(np.min(recall)), 6),
        "drift_psi_mean": round(float(drift["psi"].mean()), 6),
        "drift_psi_max": round(float(drift["psi"].max()), 6),
        "drift_flag_count": int(drift["flagged"].sum()),
        "top_drift_feature": str(drift.iloc[0]["feature"]),
        "model_family": "random_forest",
        "wall_clock_sec": round(float(time.time() - t0), 3),
    }
    predictions = pd.DataFrame(
        {
            "row_id": test_idx.astype(int),
            "actual": y_test.to_numpy(),
            "predicted": pred.astype(str),
            "pred_proba": np.round(pred_prob, 8),
            "split": "test",
        }
    ).sort_values("row_id")
    split_profile = {
        "order_column": ORDER_COL,
        "feature_columns": numeric + categorical,
        "dropped_columns": [TARGET, ORDER_COL],
        "train_order_min": int(df.loc[train_idx, ORDER_COL].min()),
        "train_order_max": int(df.loc[train_idx, ORDER_COL].max()),
        "test_order_min": int(df.loc[test_idx, ORDER_COL].min()),
        "test_order_max": int(df.loc[test_idx, ORDER_COL].max()),
        "train_class_distribution": {
            str(k): int(v) for k, v in y_train.value_counts().sort_index().items()
        },
        "test_class_distribution": {
            str(k): int(v) for k, v in y_test.value_counts().sort_index().items()
        },
        "segment_class_distribution": segment_profile(df),
    }
    return {
        "metrics": metrics,
        "predictions": predictions,
        "class_metrics": class_metrics,
        "drift_report": drift,
        "confusion_matrix": cm,
        "split_profile": split_profile,
    }
