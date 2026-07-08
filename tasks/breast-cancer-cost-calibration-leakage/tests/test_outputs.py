"""Verifier for breast-cancer-cost-calibration-leakage."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.calibration import CalibratedClassifierCV
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

DATA_DIR = Path(os.environ.get("APP_DATA_DIR", "/app/data"))
OUT_DIR = Path(os.environ.get("APP_OUTPUT_DIR", "/app/outputs"))
LABELS_PATH = Path(os.environ.get("APP_LABELS_PATH", "/tests/eval_labels.csv"))
APP_ANALYSIS = Path(os.environ.get("APP_ANALYSIS_PATH", "/app/analysis.py"))
DATA_PATH = DATA_DIR / "breast-cancer-cost-calibration-leakage.csv"
ID_COL = "record_id"
TARGET_COL = "target"
PERIOD_COL = "event_month"
AUDIT_COL = "audit_group"
BLOCKED_FEATURE_COLUMNS = ["ops_score_a", "ops_code_b", "ops_bucket_c"]
FN_COST = 12.0
FP_COST = 1.0
TEST_PERIOD_START = 10
VALID_PERIOD_START = 8
RANDOM_STATE = 20260657
THRESHOLDS = np.round(np.arange(0.05, 0.951, 0.01), 2)
METRIC_KEYS = [
    "n_train",
    "n_validation",
    "n_test",
    "positive_rate_train",
    "positive_rate_test",
    "roc_auc",
    "pr_auc",
    "brier",
    "ece",
    "balanced_accuracy",
    "f1",
    "precision",
    "recall",
    "specificity",
    "threshold",
    "expected_cost",
    "false_negative_cost",
    "false_positive_cost",
    "primary_metric_value",
    "fairness_demographic_parity_gap",
    "fairness_equal_opportunity_gap",
]
BOOTSTRAP_COLUMNS = [
    "replicate",
    "selected_threshold",
    "expected_cost",
    "recall",
    "specificity",
    "precision",
    "n_resampled",
]
VALIDATION_COLUMNS = [
    "record_id",
    "target",
    "audit_group",
    "probability",
    "prediction",
]


def finite_round(value):
    if value is None:
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    return round(value, 6)


def close(a, b, tol=1e-6):
    if pd.isna(a) and pd.isna(b):
        return True
    return abs(float(a) - float(b)) <= tol


def load_frame():
    df = pd.read_csv(DATA_PATH)
    df[PERIOD_COL] = pd.to_numeric(df[PERIOD_COL], errors="coerce").astype(int)
    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")
    return df


def split_frame(df):
    labeled = df[df[TARGET_COL].notna()].copy()
    test = df[df[TARGET_COL].isna()].copy()
    labeled[TARGET_COL] = labeled[TARGET_COL].astype(int)
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
    return fit.copy(), valid.copy(), test.copy(), train_all.copy()


def load_eval_labels():
    labels = pd.read_csv(LABELS_PATH)
    labels[TARGET_COL] = pd.to_numeric(labels[TARGET_COL], errors="coerce").astype(int)
    return labels


def prospective_columns(df):
    blocked = {ID_COL, TARGET_COL, PERIOD_COL, AUDIT_COL}
    blocked.update(BLOCKED_FEATURE_COLUMNS)
    return [c for c in df.columns if c not in blocked]


def cleaned_features(frame, columns):
    return frame[columns].copy().replace([-999.0, -777.0], np.nan)


def build_reference_model(x):
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
    base = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=RANDOM_STATE,
    )
    return CalibratedClassifierCV(
        estimator=Pipeline([("preprocess", prep), ("model", base)]),
        method="sigmoid",
        cv=3,
    )


def fit_reference(fit):
    cols = prospective_columns(fit)
    x = cleaned_features(fit, cols)
    model = build_reference_model(x)
    model.fit(x, fit[TARGET_COL].to_numpy())
    return model, cols


def probabilities(model, frame, cols):
    return model.predict_proba(cleaned_features(frame, cols))[:, 1]


def confusion_parts(y, probability, threshold):
    pred = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return pred, int(tn), int(fp), int(fn), int(tp)


def score_at_threshold(y, probability, threshold):
    pred, tn, fp, fn, tp = confusion_parts(y, probability, threshold)
    expected_cost = (FN_COST * fn + FP_COST * fp) / max(1, len(y))
    return {
        "threshold": finite_round(threshold),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "expected_cost": finite_round(expected_cost),
        "recall": finite_round(recall_score(y, pred, zero_division=0)),
        "specificity": finite_round(tn / max(1, tn + fp)),
        "precision": finite_round(precision_score(y, pred, zero_division=0)),
    }


def choose_threshold(y, probability):
    candidates = []
    for threshold in THRESHOLDS:
        row = score_at_threshold(y, probability, threshold)
        candidates.append(
            (
                float(row["expected_cost"]),
                -float(row["recall"]),
                float(row["threshold"]),
            )
        )
    candidates.sort()
    return candidates[0][2]


def calibration_rows(y, probability):
    rows = []
    for i in range(10):
        left = i / 10
        right = (i + 1) / 10
        mask = (
            (probability >= left) & (probability <= right)
            if i == 9
            else (probability >= left) & (probability < right)
        )
        count = int(mask.sum())
        if count:
            mean_probability = float(probability[mask].mean())
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
    return pd.DataFrame(rows)


def ece_score(y, probability):
    rows = calibration_rows(y, probability)
    total = rows["count"].sum()
    if total == 0:
        return 0.0
    return float(
        (rows["count"].to_numpy() * rows["absolute_error"].fillna(0).to_numpy()).sum()
        / total
    )


def cost_rows(y, probability):
    return pd.DataFrame(
        [score_at_threshold(y, probability, threshold) for threshold in THRESHOLDS]
    )


def bootstrap_rows(y, probability):
    rows = []
    rng = np.random.default_rng(RANDOM_STATE)
    n = len(y)
    for replicate in range(1, 201):
        sample = rng.integers(0, n, size=n)
        sample_y = y[sample]
        sample_p = probability[sample]
        threshold = choose_threshold(sample_y, sample_p)
        row = score_at_threshold(sample_y, sample_p, threshold)
        rows.append(
            {
                "replicate": replicate,
                "selected_threshold": finite_round(threshold),
                "expected_cost": row["expected_cost"],
                "recall": row["recall"],
                "specificity": row["specificity"],
                "precision": row["precision"],
                "n_resampled": n,
            }
        )
    return pd.DataFrame(rows)


def fairness_rows(validation_scores):
    y = validation_scores[TARGET_COL].to_numpy(dtype=int)
    probability = validation_scores["probability"].to_numpy(dtype=float)
    pred = validation_scores["prediction"].to_numpy(dtype=int)
    group_values = validation_scores[AUDIT_COL].astype(str).fillna("missing")
    overall_pred = float(pred.mean()) if len(pred) else 0.0
    positive_mask = y == 1
    overall_recall = float(pred[positive_mask].mean()) if positive_mask.sum() else 0.0
    rows = []
    for group in sorted(group_values.unique()):
        mask = group_values.to_numpy() == group
        gy = y[mask]
        gp = probability[mask]
        gpred = pred[mask]
        positives = gy == 1
        negatives = gy == 0
        predicted_positive_rate = float(gpred.mean()) if len(gpred) else 0.0
        recall = float(gpred[positives].mean()) if positives.sum() else 0.0
        false_positive_rate = float(gpred[negatives].mean()) if negatives.sum() else 0.0
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
    return pd.DataFrame(rows)


def metrics_from_validation(validation_scores, raw_frame, threshold):
    y = validation_scores[TARGET_COL].to_numpy(dtype=int)
    probability = validation_scores["probability"].to_numpy(dtype=float)
    pred = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    expected_cost = (FN_COST * fn + FP_COST * fp) / max(1, len(y))
    labeled = raw_frame[raw_frame[TARGET_COL].notna()].copy()
    labeled[TARGET_COL] = labeled[TARGET_COL].astype(int)
    train_all = labeled[labeled[PERIOD_COL] < TEST_PERIOD_START].copy()
    eval_rows = raw_frame[raw_frame[TARGET_COL].isna()].copy()
    fair = fairness_rows(validation_scores.assign(prediction=pred))
    return {
        "n_train": int(len(train_all)),
        "n_validation": int(len(validation_scores)),
        "n_test": int(len(eval_rows)),
        "positive_rate_train": finite_round(train_all[TARGET_COL].mean()),
        "positive_rate_test": finite_round(float(y.mean()) if len(y) else 0.0),
        "roc_auc": finite_round(roc_auc_score(y, probability)),
        "pr_auc": finite_round(average_precision_score(y, probability)),
        "brier": finite_round(brier_score_loss(y, probability)),
        "ece": finite_round(ece_score(y, probability)),
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
            float(fair["demographic_parity_gap"].fillna(0).max())
        ),
        "fairness_equal_opportunity_gap": finite_round(
            float(fair["equal_opportunity_gap"].fillna(0).max())
        ),
    }


@pytest.fixture(scope="session")
def raw_frame():
    return load_frame()


@pytest.fixture(scope="session")
def reference(raw_frame):
    fit, valid, test, train_all = split_frame(raw_frame)
    labels = load_eval_labels()
    model, cols = fit_reference(fit)
    p = probabilities(model, test, cols)
    valid_p = probabilities(model, valid, cols)
    threshold = choose_threshold(valid[TARGET_COL].to_numpy(), valid_p)
    eval_join = test[[ID_COL]].merge(
        labels[[ID_COL, TARGET_COL]], on=ID_COL, how="left"
    )
    eval_y = eval_join[TARGET_COL].to_numpy()
    eval_pred = (p >= threshold).astype(int)
    eval_tn, eval_fp, eval_fn, _ = confusion_matrix(
        eval_y, eval_pred, labels=[0, 1]
    ).ravel()
    return {
        "fit": fit,
        "valid": valid,
        "test": test,
        "train_all": train_all,
        "eval_probability": p,
        "eval_target": eval_y,
        "eval_quality": {
            "roc_auc": roc_auc_score(eval_y, p),
            "pr_auc": average_precision_score(eval_y, p),
            "brier": brier_score_loss(eval_y, p),
            "balanced_accuracy": balanced_accuracy_score(eval_y, eval_pred),
            "expected_cost": (FN_COST * eval_fn + FP_COST * eval_fp)
            / max(1, len(eval_y)),
        },
    }


@pytest.fixture(scope="session")
def metrics():
    return json.loads((OUT_DIR / "metrics.json").read_text())


@pytest.fixture(scope="session")
def predictions():
    return pd.read_csv(OUT_DIR / "predictions.csv")


@pytest.fixture(scope="session")
def validation_scores():
    return pd.read_csv(OUT_DIR / "validation_scores.csv")


@pytest.fixture(scope="session")
def calibration_bins():
    return pd.read_csv(OUT_DIR / "calibration_bins.csv")


@pytest.fixture(scope="session")
def cost_curve():
    return pd.read_csv(OUT_DIR / "cost_curve.csv")


@pytest.fixture(scope="session")
def threshold_bootstrap():
    return pd.read_csv(OUT_DIR / "threshold_bootstrap.csv")


@pytest.fixture(scope="session")
def fairness_report():
    return pd.read_csv(OUT_DIR / "fairness_report.csv")


@pytest.fixture(scope="session")
def feature_importance():
    return pd.read_csv(OUT_DIR / "feature_importance.csv")


def eval_labeled_predictions(predictions):
    labels = load_eval_labels()
    merged = predictions.merge(labels[[ID_COL, TARGET_COL]], on=ID_COL, how="left")
    assert not merged[TARGET_COL].isna().any()
    return merged


def test_all_artifacts_exist():
    """All required output files are present."""
    required = [
        "metrics.json",
        "predictions.csv",
        "validation_scores.csv",
        "calibration_bins.csv",
        "cost_curve.csv",
        "threshold_bootstrap.csv",
        "fairness_report.csv",
        "feature_importance.csv",
    ]
    missing = [name for name in required if not (OUT_DIR / name).exists()]
    assert not missing, f"missing files: {missing}"


def test_metrics_top_level_schema(metrics):
    """metrics.json exposes the required keys in order."""
    assert list(metrics.keys()) == METRIC_KEYS


def test_validation_scores_schema(validation_scores):
    """Validation score columns match the contract."""
    assert list(validation_scores.columns) == VALIDATION_COLUMNS


def test_validation_scores_cover_window(validation_scores, reference):
    """Validation scores cover the expected validation window."""
    valid = reference["valid"].copy()
    assert len(validation_scores) == len(valid)
    scores = validation_scores.assign(**{ID_COL: validation_scores[ID_COL].astype(str)})
    valid = valid.assign(**{ID_COL: valid[ID_COL].astype(str)})
    assert validation_scores[ID_COL].astype(str).tolist() == sorted(
        validation_scores[ID_COL].astype(str).tolist()
    )
    merged = scores.merge(
        valid[[ID_COL, TARGET_COL, AUDIT_COL]].assign(
            **{ID_COL: valid[ID_COL].astype(str)}
        ),
        on=ID_COL,
        suffixes=("", "_raw"),
        how="left",
    )
    assert not merged[f"{TARGET_COL}_raw"].isna().any()
    assert np.array_equal(
        merged[TARGET_COL].astype(int).to_numpy(),
        merged[f"{TARGET_COL}_raw"].astype(int).to_numpy(),
    )
    assert (
        merged[AUDIT_COL].astype(str).to_numpy()
        == merged[f"{AUDIT_COL}_raw"].astype(str).to_numpy()
    ).all()


def test_validation_probabilities_and_labels(validation_scores, metrics):
    """Validation probabilities are bounded and labels follow the threshold."""
    assert validation_scores["probability"].between(0, 1).all()
    assert set(validation_scores["prediction"].unique()).issubset({0, 1})
    expected = (
        validation_scores["probability"].to_numpy() >= float(metrics["threshold"])
    ).astype(int)
    assert np.array_equal(expected, validation_scores["prediction"].to_numpy())


def test_predictions_columns(predictions):
    """Prediction columns match the contract."""
    assert list(predictions.columns) == ["record_id", "probability", "prediction"]


def test_predictions_cover_eval_period(predictions, reference):
    """Predictions cover each evaluation record exactly once."""
    assert len(predictions) == len(reference["test"])
    assert predictions["record_id"].is_unique
    assert predictions["record_id"].astype(str).tolist() == sorted(
        predictions["record_id"].astype(str).tolist()
    )
    assert set(predictions["record_id"].astype(str)) == set(
        reference["test"][ID_COL].astype(str)
    )


def test_prediction_probability_and_label_shape(predictions, metrics):
    """Prediction probabilities and labels are well formed."""
    assert predictions["probability"].between(0, 1).all()
    assert predictions["probability"].nunique() > 20
    assert set(predictions["prediction"].unique()).issubset({0, 1})
    assert predictions["prediction"].nunique() == 2
    expected = (
        predictions["probability"].to_numpy() >= float(metrics["threshold"])
    ).astype(int)
    assert np.array_equal(expected, predictions["prediction"].to_numpy())


def test_hidden_eval_discrimination_quality(predictions, reference):
    """Hidden evaluation discrimination stays near the benchmark model."""
    merged = eval_labeled_predictions(predictions)
    auc = roc_auc_score(merged[TARGET_COL], merged["probability"])
    pr_auc = average_precision_score(merged[TARGET_COL], merged["probability"])
    assert auc >= max(0.988, reference["eval_quality"]["roc_auc"] - 0.002)
    assert pr_auc >= 0.998


def test_hidden_eval_brier_quality(predictions, reference):
    """Hidden evaluation probabilities stay calibrated enough."""
    merged = eval_labeled_predictions(predictions)
    brier = brier_score_loss(merged[TARGET_COL], merged["probability"])
    assert brier <= 0.028


def test_hidden_eval_cost_quality(predictions, reference):
    """Hidden evaluation decisions keep asymmetric cost near the benchmark."""
    merged = eval_labeled_predictions(predictions)
    tn, fp, fn, _ = confusion_matrix(
        merged[TARGET_COL], merged["prediction"], labels=[0, 1]
    ).ravel()
    expected_cost = (FN_COST * fn + FP_COST * fp) / max(1, len(merged))
    balanced = balanced_accuracy_score(merged[TARGET_COL], merged["prediction"])
    assert expected_cost <= reference["eval_quality"]["expected_cost"] + 0.025
    assert balanced >= 0.80


def test_prediction_no_target_identity(predictions):
    """Probabilities are not copied hidden labels."""
    merged = eval_labeled_predictions(predictions)
    label = merged[TARGET_COL].to_numpy()
    probability = merged["probability"].to_numpy()
    assert not np.allclose(probability, label)
    assert not np.allclose(probability, 1 - label)


def test_metrics_match_validation_scores(metrics, validation_scores, raw_frame):
    """metrics.json matches independent recomputation from validation scores."""
    y = validation_scores[TARGET_COL].to_numpy(dtype=int)
    probability = validation_scores["probability"].to_numpy(dtype=float)
    threshold = choose_threshold(y, probability)
    expected = metrics_from_validation(validation_scores, raw_frame, threshold)
    for key in METRIC_KEYS:
        tol = 0 if key.startswith("n_") else 1e-6
        assert close(metrics[key], expected[key], tol), f"{key} disagrees"


def test_metrics_cost_weights_and_primary(metrics):
    """Cost weights and primary metric match the contract."""
    assert close(metrics["false_negative_cost"], FN_COST)
    assert close(metrics["false_positive_cost"], FP_COST)
    assert close(metrics["primary_metric_value"], -float(metrics["expected_cost"]))


def test_calibration_columns(calibration_bins):
    """Calibration columns match the contract."""
    assert list(calibration_bins.columns) == [
        "bin_id",
        "bin_left",
        "bin_right",
        "count",
        "mean_probability",
        "observed_rate",
        "absolute_error",
    ]


def test_calibration_matches_validation_scores(calibration_bins, validation_scores):
    """Calibration bins match validation score recomputation."""
    y = validation_scores[TARGET_COL].to_numpy(dtype=int)
    probability = validation_scores["probability"].to_numpy(dtype=float)
    ref = calibration_rows(y, probability)
    assert calibration_bins["bin_id"].astype(int).tolist() == list(range(10))
    assert int(calibration_bins["count"].sum()) == len(validation_scores)
    for agent_row, ref_row in zip(
        calibration_bins.to_dict("records"), ref.to_dict("records")
    ):
        for col in calibration_bins.columns:
            assert close(agent_row[col], ref_row[col], 1e-5), (
                f"calibration {col} disagrees"
            )


def test_cost_curve_columns(cost_curve):
    """Cost curve columns match the contract."""
    assert list(cost_curve.columns) == [
        "threshold",
        "tp",
        "fp",
        "tn",
        "fn",
        "expected_cost",
        "recall",
        "specificity",
        "precision",
    ]


def test_cost_curve_matches_validation_scores(cost_curve, validation_scores):
    """The full cost curve matches validation score recomputation."""
    y = validation_scores[TARGET_COL].to_numpy(dtype=int)
    probability = validation_scores["probability"].to_numpy(dtype=float)
    ref = cost_rows(y, probability)
    assert len(cost_curve) == 91
    assert np.allclose(cost_curve["threshold"].to_numpy(), THRESHOLDS)
    int_cols = {"tp", "fp", "tn", "fn"}
    for i, (agent_row, ref_row) in enumerate(
        zip(cost_curve.to_dict("records"), ref.to_dict("records"))
    ):
        for col in cost_curve.columns:
            if col in int_cols:
                assert int(agent_row[col]) == int(ref_row[col]), (
                    f"cost row {i} {col} disagrees"
                )
            else:
                assert close(agent_row[col], ref_row[col]), (
                    f"cost row {i} {col} disagrees"
                )


def test_threshold_bootstrap_columns(threshold_bootstrap):
    """Threshold bootstrap columns match the contract."""
    assert list(threshold_bootstrap.columns) == BOOTSTRAP_COLUMNS


def test_threshold_bootstrap_matches_validation_scores(
    threshold_bootstrap, validation_scores
):
    """Bootstrap rows match seeded validation score recomputation."""
    y = validation_scores[TARGET_COL].to_numpy(dtype=int)
    probability = validation_scores["probability"].to_numpy(dtype=float)
    ref = bootstrap_rows(y, probability)
    assert len(threshold_bootstrap) == 200
    assert threshold_bootstrap["replicate"].astype(int).tolist() == list(range(1, 201))
    int_cols = {"replicate", "n_resampled"}
    for i, (agent_row, ref_row) in enumerate(
        zip(threshold_bootstrap.to_dict("records"), ref.to_dict("records"))
    ):
        for col in BOOTSTRAP_COLUMNS:
            if col in int_cols:
                assert int(agent_row[col]) == int(ref_row[col]), (
                    f"bootstrap row {i} {col} disagrees"
                )
            else:
                assert close(agent_row[col], ref_row[col]), (
                    f"bootstrap row {i} {col} disagrees"
                )


def test_fairness_columns(fairness_report):
    """Fairness columns match the contract."""
    assert list(fairness_report.columns) == [
        "audit_group",
        "n",
        "observed_positive_rate",
        "predicted_positive_rate",
        "recall",
        "false_positive_rate",
        "mean_probability",
        "demographic_parity_gap",
        "equal_opportunity_gap",
    ]


def test_fairness_matches_validation_scores(
    fairness_report, validation_scores, metrics
):
    """Fairness rows and summary metrics match validation recomputation."""
    ref = fairness_rows(validation_scores)
    assert fairness_report[AUDIT_COL].astype(str).tolist() == ref[AUDIT_COL].tolist()
    for agent_row, ref_row in zip(
        fairness_report.to_dict("records"), ref.to_dict("records")
    ):
        for col in fairness_report.columns:
            if col == AUDIT_COL:
                assert str(agent_row[col]) == str(ref_row[col])
            else:
                assert close(agent_row[col], ref_row[col]), f"fairness {col} disagrees"
    assert close(
        metrics["fairness_demographic_parity_gap"],
        fairness_report["demographic_parity_gap"].max(),
    )
    assert close(
        metrics["fairness_equal_opportunity_gap"],
        fairness_report["equal_opportunity_gap"].max(),
    )


def test_feature_importance_schema_and_order(feature_importance):
    """Feature importance is sorted and well formed."""
    assert list(feature_importance.columns) == ["feature", "importance"]
    assert 1 <= len(feature_importance) <= 30
    assert feature_importance["feature"].is_unique
    assert (feature_importance["importance"] >= 0).all()
    values = feature_importance["importance"].to_numpy()
    assert np.all(values[:-1] >= values[1:] - 1e-12)


def test_feature_importance_excludes_blocked_fields(feature_importance):
    """Feature names exclude leakage and post-review fields."""
    names = set(feature_importance["feature"].astype(str))
    blocked_fragments = {ID_COL, TARGET_COL, PERIOD_COL, AUDIT_COL}
    blocked_fragments.update(BLOCKED_FEATURE_COLUMNS)
    for fragment in blocked_fragments:
        assert not any(fragment in name for name in names), fragment


def test_raw_data_quality_controls(raw_frame, reference):
    """Raw data keeps the intended split and missing-value traps."""
    assert len(reference["test"]) > 0
    assert reference["test"][PERIOD_COL].min() >= TEST_PERIOD_START
    assert len(reference["fit"]) > 0
    assert len(reference["valid"]) > 0
    assert len(set(reference["eval_target"])) == 2
    assert reference["test"][AUDIT_COL].nunique() >= 2
    numeric = raw_frame.select_dtypes(include=[np.number])
    assert ((numeric == -999) | (numeric == -777)).any().any()


def test_outputs_do_not_drop_hard_cases(predictions):
    """Predictions include high-cost positive cases."""
    labels = load_eval_labels()
    merged = predictions.merge(
        labels[[ID_COL, TARGET_COL]], left_on="record_id", right_on=ID_COL
    )
    assert int(merged[TARGET_COL].sum()) == int(labels[TARGET_COL].sum())


def test_analysis_does_not_reference_hidden_or_verifier_artifacts():
    """analysis.py does not read verifier, solution, or reward artifacts."""
    source = APP_ANALYSIS.read_text().lower()
    forbidden = [
        "/tests",
        "eval_labels",
        "/solution",
        "reward.txt",
        "ctrf.json",
        "test_outputs.py",
    ]
    hits = [token for token in forbidden if token in source]
    assert not hits, f"analysis.py references forbidden artifacts: {hits}"
