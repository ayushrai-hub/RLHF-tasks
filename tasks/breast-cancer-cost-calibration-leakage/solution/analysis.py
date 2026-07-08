"""Reference analysis for breast-cancer-cost-calibration-leakage."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.calibration import CalibratedClassifierCV

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
DATA_PATH = APP_DIR / "data" / "breast-cancer-cost-calibration-leakage.csv"
OUT_DIR = APP_DIR / "outputs"
ID_COL = "record_id"
TARGET_COL = "target"
PERIOD_COL = "event_month"
AUDIT_COL = "audit_group"
FN_COST = 12.0
FP_COST = 1.0
TEST_PERIOD_START = 10
VALID_PERIOD_START = 8
RANDOM_STATE = 20260657


def finite_round(value):
    if value is None:
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    return round(value, 6)


def read_frame():
    df = pd.read_csv(DATA_PATH)
    df[PERIOD_COL] = pd.to_numeric(df[PERIOD_COL], errors="coerce").astype(int)
    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")
    return df


def split_by_label(df):
    labeled = df[df[TARGET_COL].notna()].copy()
    evaluation = df[df[TARGET_COL].isna()].copy()
    labeled[TARGET_COL] = labeled[TARGET_COL].astype(int)
    return labeled, evaluation


def cleaned_features(frame, columns, use_sentinels):
    x = frame[columns].copy()
    if use_sentinels:
        x = x.replace([-999.0, -777.0], np.nan)
    return x


def build_model(x, balanced):
    numeric = [c for c in x.columns if pd.api.types.is_numeric_dtype(x[c])]
    categorical = [c for c in x.columns if c not in numeric]
    num_pipe = Pipeline(
        [("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    cat_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    prep = ColumnTransformer(
        [("num", num_pipe, numeric), ("cat", cat_pipe, categorical)],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    weight = "balanced" if balanced else None
    base = LogisticRegression(
        max_iter=2000, class_weight=weight, solver="lbfgs", random_state=RANDOM_STATE
    )
    return Pipeline([("preprocess", prep), ("model", base)])


def probabilities(model, frame, cols, use_sentinels):
    x = cleaned_features(frame, cols, use_sentinels)
    return model.predict_proba(x)[:, 1]


def ece_score(y, p):
    rows = calibration_rows(y, p)
    total = sum(r["count"] for r in rows)
    if total == 0:
        return 0.0
    return (
        sum(
            r["count"] * (0.0 if r["absolute_error"] is None else r["absolute_error"])
            for r in rows
        )
        / total
    )


def calibration_rows(y, p):
    rows = []
    for i in range(10):
        left = i / 10
        right = (i + 1) / 10
        if i == 9:
            mask = (p >= left) & (p <= right)
        else:
            mask = (p >= left) & (p < right)
        count = int(mask.sum())
        if count:
            mean_probability = float(p[mask].mean())
            observed_rate = float(y[mask].mean())
            absolute_error = abs(mean_probability - observed_rate)
        else:
            mean_probability = None
            observed_rate = None
            absolute_error = None
        rows.append(
            {
                "bin_id": i,
                "bin_left": finite_round(left),
                "bin_right": finite_round(right),
                "count": count,
                "mean_probability": finite_round(mean_probability),
                "observed_rate": finite_round(observed_rate),
                "absolute_error": finite_round(absolute_error),
            }
        )
    return rows


def cost_rows(y, p):
    rows = []
    for threshold in np.round(np.arange(0.05, 0.951, 0.01), 2):
        pred = (p >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        expected_cost = (FN_COST * fn + FP_COST * fp) / max(1, len(y))
        rows.append(
            {
                "threshold": finite_round(threshold),
                "tp": int(tp),
                "fp": int(fp),
                "tn": int(tn),
                "fn": int(fn),
                "expected_cost": finite_round(expected_cost),
                "recall": finite_round(recall_score(y, pred, zero_division=0)),
                "specificity": finite_round(tn / max(1, tn + fp)),
                "precision": finite_round(precision_score(y, pred, zero_division=0)),
            }
        )
    return rows


def bootstrap_rows(y, p):
    rows = []
    rng = np.random.default_rng(RANDOM_STATE)
    thresholds = np.round(np.arange(0.05, 0.951, 0.01), 2)
    n = len(y)
    for replicate in range(1, 201):
        sample = rng.integers(0, n, size=n)
        sample_y = y[sample]
        sample_p = p[sample]
        scored = []
        for threshold in thresholds:
            pred = (sample_p >= threshold).astype(int)
            tn, fp, fn, tp = confusion_matrix(sample_y, pred, labels=[0, 1]).ravel()
            expected_cost = (FN_COST * fn + FP_COST * fp) / max(1, n)
            recall = recall_score(sample_y, pred, zero_division=0)
            scored.append((expected_cost, -recall, threshold, pred, tn, fp, fn, tp))
        expected_cost, _, threshold, pred, tn, fp, fn, tp = sorted(scored)[0]
        rows.append(
            {
                "replicate": replicate,
                "selected_threshold": finite_round(threshold),
                "expected_cost": finite_round(expected_cost),
                "recall": finite_round(recall_score(sample_y, pred, zero_division=0)),
                "specificity": finite_round(tn / max(1, tn + fp)),
                "precision": finite_round(
                    precision_score(sample_y, pred, zero_division=0)
                ),
                "n_resampled": int(n),
            }
        )
    return rows


def fairness_rows(frame, y, p, pred):
    overall_pred = float(pred.mean()) if len(pred) else 0.0
    positives = y == 1
    overall_recall = float(pred[positives].mean()) if positives.sum() else 0.0
    rows = []
    groups = sorted(frame[AUDIT_COL].astype(str).fillna("missing").unique())
    values = frame[AUDIT_COL].astype(str).fillna("missing").to_numpy()
    for group in groups:
        mask = values == group
        gy = y[mask]
        gp = p[mask]
        gpred = pred[mask]
        neg = gy == 0
        pos = gy == 1
        predicted_positive_rate = float(gpred.mean()) if len(gpred) else 0.0
        recall = float(gpred[pos].mean()) if pos.sum() else 0.0
        false_positive_rate = float(gpred[neg].mean()) if neg.sum() else 0.0
        rows.append(
            {
                "audit_group": group,
                "n": int(mask.sum()),
                "observed_positive_rate": finite_round(
                    float(gy.mean()) if len(gy) else 0.0
                ),
                "predicted_positive_rate": finite_round(predicted_positive_rate),
                "recall": finite_round(recall),
                "false_positive_rate": finite_round(false_positive_rate),
                "mean_probability": finite_round(float(gp.mean()) if len(gp) else 0.0),
                "demographic_parity_gap": finite_round(
                    abs(predicted_positive_rate - overall_pred)
                ),
                "equal_opportunity_gap": finite_round(abs(recall - overall_recall)),
            }
        )
    return rows


def feature_rows(pipe):
    prep = pipe.named_steps["preprocess"]
    est = pipe.named_steps["model"]
    names = list(prep.get_feature_names_out())
    coefs = np.abs(est.coef_[0])
    total = float(coefs.sum()) or 1.0
    collapsed = {}
    for name, coef in zip(names, coefs):
        feature = str(name)
        collapsed[feature] = collapsed.get(feature, 0.0) + float(coef) / total
    out = [{"feature": k, "importance": finite_round(v)} for k, v in collapsed.items()]
    out.sort(key=lambda r: (-float(r["importance"] or 0), r["feature"]))
    return out[:30]


def metric_dict(train_all, valid, evaluation, y, p, pred, threshold, fair):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    expected_cost = (FN_COST * fn + FP_COST * fp) / max(1, len(y))
    return {
        "n_train": int(len(train_all)),
        "n_validation": int(len(valid)),
        "n_test": int(len(evaluation)),
        "positive_rate_train": finite_round(train_all[TARGET_COL].mean()),
        "positive_rate_test": finite_round(float(y.mean()) if len(y) else 0.0),
        "roc_auc": finite_round(roc_auc_score(y, p)),
        "pr_auc": finite_round(average_precision_score(y, p)),
        "brier": finite_round(brier_score_loss(y, p)),
        "ece": finite_round(ece_score(y, p)),
        "balanced_accuracy": finite_round(balanced_accuracy_score(y, pred)),
        "f1": finite_round(f1_score(y, pred, zero_division=0)),
        "precision": finite_round(precision_score(y, pred, zero_division=0)),
        "recall": finite_round(recall_score(y, pred, zero_division=0)),
        "specificity": finite_round(tn / max(1, tn + fp)),
        "threshold": finite_round(threshold),
        "expected_cost": finite_round(expected_cost),
        "false_negative_cost": finite_round(FN_COST),
        "false_positive_cost": finite_round(FP_COST),
        "primary_metric_value": finite_round(-expected_cost),
        "fairness_demographic_parity_gap": finite_round(
            max([r["demographic_parity_gap"] or 0.0 for r in fair] or [0.0])
        ),
        "fairness_equal_opportunity_gap": finite_round(
            max([r["equal_opportunity_gap"] or 0.0 for r in fair] or [0.0])
        ),
    }


def write_outputs(
    metrics, predictions, validation_scores, bins, costs, bootstrap, fair, features
):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    predictions.to_csv(OUT_DIR / "predictions.csv", index=False)
    validation_scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)
    pd.DataFrame(bins).to_csv(OUT_DIR / "calibration_bins.csv", index=False)
    pd.DataFrame(costs).to_csv(OUT_DIR / "cost_curve.csv", index=False)
    pd.DataFrame(bootstrap).to_csv(OUT_DIR / "threshold_bootstrap.csv", index=False)
    pd.DataFrame(fair).to_csv(OUT_DIR / "fairness_report.csv", index=False)
    pd.DataFrame(features).to_csv(OUT_DIR / "feature_importance.csv", index=False)


def split_frame(df):
    labeled, evaluation = split_by_label(df)
    train_all = labeled[labeled[PERIOD_COL] < TEST_PERIOD_START].copy()
    valid = train_all[train_all[PERIOD_COL] >= VALID_PERIOD_START].copy()
    fit = train_all[train_all[PERIOD_COL] < VALID_PERIOD_START].copy()
    if valid[TARGET_COL].nunique() < 2 or fit[TARGET_COL].nunique() < 2:
        fit, valid = train_test_split(
            train_all,
            test_size=0.25,
            random_state=RANDOM_STATE,
            stratify=train_all[TARGET_COL],
        )
    return fit.copy(), valid.copy(), evaluation.copy(), train_all.copy()


def model_columns(df):
    blocked = {ID_COL, TARGET_COL, PERIOD_COL, AUDIT_COL}
    blocked.update(["ops_score_a", "ops_code_b", "ops_bucket_c"])
    return [c for c in df.columns if c not in blocked]


def fit_reference_model(fit):
    cols = model_columns(fit)
    x = cleaned_features(fit, cols, True)
    y = fit[TARGET_COL].to_numpy()
    model = CalibratedClassifierCV(
        estimator=build_model(x, True), method="sigmoid", cv=3
    )
    model.fit(x, y)
    return model, cols


def choose_threshold(y, p):
    rows = []
    for threshold in np.round(np.arange(0.05, 0.951, 0.01), 2):
        pred = (p >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        cost = (FN_COST * fn + FP_COST * fp) / max(1, len(y))
        rows.append((cost, -recall_score(y, pred, zero_division=0), threshold))
    rows.sort()
    return float(rows[0][2])


def reference_feature_rows(model):
    pipe = model.calibrated_classifiers_[0].estimator
    return feature_rows(pipe)


def main():
    df = read_frame()
    fit, valid, evaluation, train_all = split_frame(df)
    model, cols = fit_reference_model(fit)
    valid_p = probabilities(model, valid, cols, True)
    valid_p_out = np.round(valid_p, 6)
    valid_y = valid[TARGET_COL].to_numpy()
    threshold = choose_threshold(valid_y, valid_p_out)
    valid_pred = (valid_p_out >= threshold).astype(int)
    eval_p = probabilities(model, evaluation, cols, True)
    eval_p_out = np.round(eval_p, 6)
    eval_pred = (eval_p_out >= threshold).astype(int)
    fair = fairness_rows(valid, valid_y, valid_p_out, valid_pred)
    metrics = metric_dict(
        train_all,
        valid,
        evaluation,
        valid_y,
        valid_p_out,
        valid_pred,
        threshold,
        fair,
    )
    predictions = pd.DataFrame(
        {
            "record_id": evaluation[ID_COL].astype(str).to_numpy(),
            "probability": eval_p_out,
            "prediction": eval_pred.astype(int),
        }
    ).sort_values("record_id")
    validation_scores = pd.DataFrame(
        {
            "record_id": valid[ID_COL].astype(str).to_numpy(),
            "target": valid_y.astype(int),
            "audit_group": valid[AUDIT_COL].astype(str).fillna("missing").to_numpy(),
            "probability": valid_p_out,
            "prediction": valid_pred.astype(int),
        }
    ).sort_values("record_id")
    sorted_valid_y = validation_scores["target"].to_numpy(dtype=int)
    sorted_valid_p = validation_scores["probability"].to_numpy(dtype=float)
    write_outputs(
        metrics,
        predictions,
        validation_scores,
        calibration_rows(valid_y, valid_p_out),
        cost_rows(valid_y, valid_p_out),
        bootstrap_rows(sorted_valid_y, sorted_valid_p),
        fair,
        reference_feature_rows(model),
    )


if __name__ == "__main__":
    main()
