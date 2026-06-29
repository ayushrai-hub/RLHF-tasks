"""Re-estimation checks for rt-iot2022-drift-multi-class."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
)


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
OUT_DIR = Path(os.environ.get("OUT_DIR", APP_DIR / "outputs"))
REFERENCE_PATH = Path(__file__).with_name("reference_outputs.py")


def read_json(name):
    return json.loads((OUT_DIR / name).read_text(encoding="utf-8"))


def assert_series_match(got, exp, label):
    left = pd.Series(got).reset_index(drop=True)
    right = pd.Series(exp).reset_index(drop=True)
    assert left.equals(right), f"{label} disagrees"


@pytest.fixture(scope="module")
def artifacts():
    return {
        "metrics": read_json("metrics.json"),
        "predictions": pd.read_csv(OUT_DIR / "predictions.csv"),
        "class_metrics": pd.read_csv(OUT_DIR / "class_metrics.csv"),
        "drift_report": pd.read_csv(OUT_DIR / "drift_report.csv"),
        "confusion_matrix": pd.read_csv(OUT_DIR / "confusion_matrix.csv"),
        "split_profile": read_json("split_profile.json"),
    }


@pytest.fixture(scope="module")
def expected():
    import importlib.util

    spec = importlib.util.spec_from_file_location("reference_outputs", REFERENCE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_outputs(module.load_frame())


def test_all_artifacts_exist():
    """Verifies every required output artifact was written."""
    for name in [
        "metrics.json",
        "predictions.csv",
        "class_metrics.csv",
        "drift_report.csv",
        "confusion_matrix.csv",
        "split_profile.json",
    ]:
        assert (OUT_DIR / name).exists(), f"{name} missing"


def test_metrics_top_level_schema(artifacts):
    """Verifies metrics.json exposes the required top-level keys."""
    keys = {
        "task_name",
        "target",
        "n_rows",
        "n_features_used",
        "split_seed",
        "n_train",
        "n_test",
        "n_classes",
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "weighted_f1",
        "macro_recall",
        "worst_class_recall",
        "drift_psi_mean",
        "drift_psi_max",
        "drift_flag_count",
        "top_drift_feature",
        "model_family",
        "wall_clock_sec",
    }
    assert set(artifacts["metrics"]) == keys


@pytest.mark.parametrize(
    "key",
    [
        "n_rows",
        "n_features_used",
        "split_seed",
        "n_train",
        "n_test",
        "n_classes",
        "drift_flag_count",
    ],
)
def test_integer_metrics_match(artifacts, expected, key):
    """Verifies integer metrics match the independently recomputed reference."""
    assert int(artifacts["metrics"][key]) == int(expected["metrics"][key]), (
        f"{key} disagrees"
    )


@pytest.mark.parametrize(
    "key",
    [
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "weighted_f1",
        "macro_recall",
        "worst_class_recall",
        "drift_psi_mean",
        "drift_psi_max",
    ],
)
def test_float_metrics_match(artifacts, expected, key):
    """Verifies floating metrics match the independently recomputed reference."""
    assert artifacts["metrics"][key] == pytest.approx(
        expected["metrics"][key], abs=1e-6
    ), f"{key} disagrees"


@pytest.mark.parametrize(
    "key", ["task_name", "target", "top_drift_feature", "model_family"]
)
def test_string_metrics_match(artifacts, expected, key):
    """Verifies string-valued metrics match the reference output."""
    assert artifacts["metrics"][key] == expected["metrics"][key]


@pytest.mark.parametrize("column", ["row_id", "actual", "predicted", "split"])
def test_predictions_identity_columns_match(artifacts, expected, column):
    """Verifies prediction identity columns match the reference output."""
    assert_series_match(
        artifacts["predictions"][column],
        expected["predictions"][column],
        f"predictions.{column}",
    )


def test_prediction_probabilities_match(artifacts, expected):
    """Verifies prediction probabilities match the reference output."""
    assert np.allclose(
        artifacts["predictions"]["pred_proba"],
        expected["predictions"]["pred_proba"],
        atol=1e-8,
    )


def test_prediction_metrics_recompute(artifacts):
    """Verifies metrics recomputed from predictions match the reported metrics."""
    y = artifacts["predictions"]["actual"]
    pred = artifacts["predictions"]["predicted"]
    assert accuracy_score(y, pred) == pytest.approx(
        artifacts["metrics"]["accuracy"], abs=1e-6
    )
    assert balanced_accuracy_score(y, pred) == pytest.approx(
        artifacts["metrics"]["balanced_accuracy"], abs=1e-6
    )
    assert f1_score(y, pred, average="macro", zero_division=0) == pytest.approx(
        artifacts["metrics"]["macro_f1"], abs=1e-6
    )
    assert recall_score(y, pred, average="macro", zero_division=0) == pytest.approx(
        artifacts["metrics"]["macro_recall"], abs=1e-6
    )


@pytest.mark.parametrize(
    "artifact,columns",
    [
        (
            "class_metrics",
            [
                "class_label",
                "support",
                "precision",
                "recall",
                "f1",
                "predicted_count",
                "train_support",
                "test_support",
            ],
        ),
        (
            "drift_report",
            [
                "feature",
                "kind",
                "train_missing_rate",
                "test_missing_rate",
                "psi",
                "ks_stat",
                "flagged",
            ],
        ),
        ("confusion_matrix", ["actual", "predicted", "count"]),
    ],
)
def test_csv_columns_match(artifacts, artifact, columns):
    """Verifies all CSV artifacts expose the expected columns."""
    assert artifacts[artifact].columns.tolist() == columns


@pytest.mark.parametrize(
    "artifact", ["class_metrics", "drift_report", "confusion_matrix"]
)
def test_csv_row_counts_match(artifacts, expected, artifact):
    """Verifies all CSV artifacts contain the expected number of rows."""
    assert len(artifacts[artifact]) == len(expected[artifact]), (
        f"{artifact} length disagrees"
    )


@pytest.mark.parametrize(
    "column",
    ["class_label", "support", "predicted_count", "train_support", "test_support"],
)
def test_class_metric_identity_match(artifacts, expected, column):
    """Verifies class metric identity columns match the reference output."""
    assert_series_match(
        artifacts["class_metrics"][column],
        expected["class_metrics"][column],
        f"class_metrics.{column}",
    )


@pytest.mark.parametrize("column", ["precision", "recall", "f1"])
def test_class_metric_values_match(artifacts, expected, column):
    """Verifies class metric values match the reference output."""
    assert np.allclose(
        artifacts["class_metrics"][column], expected["class_metrics"][column], atol=1e-6
    )


@pytest.mark.parametrize("column", ["feature", "kind", "flagged"])
def test_drift_identity_columns_match(artifacts, expected, column):
    """Verifies drift report identity columns match the reference output."""
    assert_series_match(
        artifacts["drift_report"][column].astype(str),
        expected["drift_report"][column].astype(str),
        f"drift_report.{column}",
    )


@pytest.mark.parametrize("column", ["train_missing_rate", "test_missing_rate", "psi"])
def test_drift_values_match(artifacts, expected, column):
    """Verifies drift report values match the reference output."""
    assert np.allclose(
        artifacts["drift_report"][column], expected["drift_report"][column], atol=1e-6
    )


def test_numeric_ks_values_match(artifacts, expected):
    """Verifies numeric drift statistics match the reference output."""
    got = pd.to_numeric(artifacts["drift_report"]["ks_stat"], errors="coerce").fillna(
        -1
    )
    exp = pd.to_numeric(expected["drift_report"]["ks_stat"], errors="coerce").fillna(-1)
    assert np.allclose(got, exp, atol=1e-6)


@pytest.mark.parametrize("column", ["actual", "predicted", "count"])
def test_confusion_matrix_match(artifacts, expected, column):
    """Verifies the confusion matrix artifact matches the reference output."""
    assert_series_match(
        artifacts["confusion_matrix"][column],
        expected["confusion_matrix"][column],
        f"confusion_matrix.{column}",
    )


def test_confusion_matrix_recomputes(artifacts):
    """Verifies the confusion matrix recomputes from the prediction rows."""
    labels = sorted(artifacts["class_metrics"]["class_label"].tolist())
    matrix = confusion_matrix(
        artifacts["predictions"]["actual"],
        artifacts["predictions"]["predicted"],
        labels=labels,
    )
    counts = (
        artifacts["confusion_matrix"]
        .pivot(index="actual", columns="predicted", values="count")
        .loc[labels, labels]
        .to_numpy()
    )
    assert np.array_equal(matrix, counts)


@pytest.mark.parametrize(
    "key",
    [
        "order_column",
        "feature_columns",
        "dropped_columns",
        "train_class_distribution",
        "test_class_distribution",
    ],
)
def test_split_profile_objects_match(artifacts, expected, key):
    """Verifies split profile objects match the reference output."""
    assert artifacts["split_profile"][key] == expected["split_profile"][key]


@pytest.mark.parametrize(
    "key", ["train_order_min", "train_order_max", "test_order_min", "test_order_max"]
)
def test_split_profile_order_bounds_match(artifacts, expected, key):
    """Verifies split profile order bounds match the reference output."""
    assert artifacts["split_profile"][key] == expected["split_profile"][key]


def test_all_classes_reported(artifacts):
    """Verifies every expected class appears in the reports."""
    assert len(artifacts["class_metrics"]) == 12
    assert len(set(artifacts["class_metrics"]["class_label"])) == 12


def test_no_order_column_feature(artifacts):
    """Verifies the ordering column is not used as a model feature."""
    assert "Unnamed: 0" not in artifacts["split_profile"]["feature_columns"]


def test_no_single_class_predictions(artifacts):
    """Verifies predictions are not collapsed to a single class."""
    assert artifacts["predictions"]["predicted"].nunique() > 1


def test_probabilities_in_range(artifacts):
    """Verifies predicted probabilities stay within the unit interval."""
    p = artifacts["predictions"]["pred_proba"]
    assert bool(((p >= 0) & (p <= 1)).all())


def test_probabilities_not_constant(artifacts):
    """Verifies predicted probabilities are not constant."""
    assert artifacts["predictions"]["pred_proba"].nunique() > 10


def test_drift_report_has_flags(artifacts):
    """Verifies drift report rows include flagged drift features."""
    assert (
        int(artifacts["drift_report"]["flagged"].sum())
        == artifacts["metrics"]["drift_flag_count"]
    )
