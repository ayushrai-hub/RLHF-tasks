"""Deterministic re-estimation tests for tvs-loan-cost-imbalance."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import OrdinalEncoder

SEED = 42
DATA = Path("/app/data/tvs_loan.csv")
SPLIT_PATH = Path("/app/data/split.csv")
OUT = Path("/app/outputs")
ANALYSIS = Path("/app/analysis.R")
TARGET = "V32"
C_FN = 20
C_FP = 1
CAT_COLS = ["V10", "V13", "V14", "V15", "V31"]
MNAR_COLS = ["V21", "V23", "V24", "V26", "V27"]


@pytest.fixture(scope="module")
def raw():
    df = pd.read_csv(DATA, low_memory=False).reset_index(drop=True)
    df["row_id"] = df.index
    return df


@pytest.fixture(scope="module")
def split(raw):
    y = raw[TARGET].astype(int).to_numpy()
    sp = pd.read_csv(SPLIT_PATH)
    tr = sp.loc[sp["split"] == "train", "row_id"].to_numpy()
    te = sp.loc[sp["split"] == "test", "row_id"].to_numpy()
    return {"train_idx": tr, "test_idx": te, "y": y}


@pytest.fixture(scope="module")
def labels(raw):
    return raw.set_index("row_id")[TARGET].astype(int)


@pytest.fixture(scope="module")
def metrics():
    return json.loads((OUT / "metrics.json").read_text())


@pytest.fixture(scope="module")
def preds():
    return pd.read_csv(OUT / "predictions.csv")


@pytest.fixture(scope="module")
def cost_report():
    return json.loads((OUT / "cost_report.json").read_text())


@pytest.fixture(scope="module")
def reference(raw, split):
    df, tr, te, y = raw, split["train_idx"], split["test_idx"], split["y"]
    feat = [c for c in df.columns if c not in (TARGET, "row_id", "V1", "V16")]
    obj = [c for c in CAT_COLS if c in feat]
    num = [c for c in feat if c not in obj]
    work = df.copy()
    work["V15"] = work["V15"].replace({"OWENED BY OFFICE": "OWNED BY OFFICE"})
    for c in MNAR_COLS:
        work[f"{c}_missing"] = df[c].isna().astype(int)
        num = num + [f"{c}_missing"]
    enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    enc.fit(work.iloc[tr][obj].astype(str))
    med = work.iloc[tr][num].apply(pd.to_numeric, errors="coerce").median()

    def tx(rows):
        out = work.iloc[rows][num].apply(pd.to_numeric, errors="coerce").fillna(med)
        out[obj] = enc.transform(work.iloc[rows][obj].astype(str))
        return out

    model = RandomForestClassifier(
        n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=2
    ).fit(tx(tr), y[tr])
    proba = model.predict_proba(tx(te))[:, 1]
    return {
        "roc_auc": roc_auc_score(y[te], proba),
        "pr_auc": average_precision_score(y[te], proba),
    }


@pytest.fixture(scope="module")
def source():
    text = ANALYSIS.read_text()
    text = re.sub(r"#.*", "", text)
    return text.lower()


@pytest.fixture(scope="module")
def aligned(preds, labels):
    y = labels.loc[preds["row_id"]].to_numpy()
    return {
        "y": y,
        "proba": preds["pred_proba"].to_numpy(),
        "label": preds["pred_label"].to_numpy(),
    }


def _cost(label, y):
    fn = int(((label == 0) & (y == 1)).sum())
    fp = int(((label == 1) & (y == 0)).sum())
    return C_FN * fn + C_FP * fp, fn, fp


class TestMinimalGuards:
    def test_all_artifacts_exist(self):
        """All three output files are present."""
        missing = [
            f
            for f in ("metrics.json", "predictions.csv", "cost_report.json")
            if not (OUT / f).exists()
        ]
        assert not missing, f"missing artifacts: {missing}"

    def test_metrics_top_level_schema(self, metrics):
        """metrics.json carries every required top-level key."""
        expected = {
            "roc_auc",
            "pr_auc",
            "recall_default",
            "precision_default",
            "brier",
            "accuracy",
            "n_test",
            "default_rate_test",
            "chosen_threshold",
            "top_feature",
        }
        assert expected.issubset(metrics), f"missing keys: {expected - set(metrics)}"


class TestCardinality:
    def test_n_test_matches_split(self, metrics, split):
        """Reported n_test equals the held-out size of the pinned split."""
        assert metrics["n_test"] == len(split["test_idx"])

    def test_predictions_rowcount(self, preds, split):
        """predictions.csv has one row per held-out test instance."""
        assert len(preds) == len(split["test_idx"])

    def test_predictions_columns(self, preds):
        """predictions.csv columns match the pinned order."""
        assert list(preds.columns) == ["row_id", "pred_proba", "pred_label"]

    def test_row_id_set_matches_test_split(self, preds, split):
        """The submitted row_id set equals the pinned split's test rows."""
        assert set(preds["row_id"]) == set(int(i) for i in split["test_idx"])

    def test_row_id_sorted(self, preds):
        """predictions.csv is sorted by row_id ascending."""
        assert preds["row_id"].is_monotonic_increasing

    def test_pred_label_binary(self, preds):
        """pred_label values are drawn from zero and one."""
        assert set(preds["pred_label"].unique()).issubset({0, 1})

    def test_pred_proba_in_unit_interval(self, preds):
        """pred_proba values lie within the unit interval."""
        assert preds["pred_proba"].between(0.0, 1.0).all()


class TestMetricConsistency:
    def test_reported_roc_auc_matches_predictions(self, metrics, aligned):
        """Reported roc_auc matches the value recomputed from the submitted probabilities."""
        got = roc_auc_score(aligned["y"], aligned["proba"])
        assert abs(got - metrics["roc_auc"]) < 0.01, f"{got} vs {metrics['roc_auc']}"

    def test_reported_pr_auc_matches_predictions(self, metrics, aligned):
        """Reported pr_auc matches the value recomputed from the submitted probabilities."""
        got = average_precision_score(aligned["y"], aligned["proba"])
        assert abs(got - metrics["pr_auc"]) < 0.03, f"{got} vs {metrics['pr_auc']}"

    def test_reported_brier_matches_predictions(self, metrics, aligned):
        """Reported brier matches the value recomputed from the submitted probabilities."""
        got = brier_score_loss(aligned["y"], aligned["proba"])
        assert abs(got - metrics["brier"]) < 0.005, f"{got} vs {metrics['brier']}"

    def test_reported_recall_matches_labels(self, metrics, aligned):
        """Reported recall_default matches the value recomputed from the submitted labels."""
        got = recall_score(aligned["y"], aligned["label"], zero_division=0)
        assert abs(got - metrics["recall_default"]) < 0.01

    def test_reported_precision_matches_labels(self, metrics, aligned):
        """Reported precision_default matches the value recomputed from the submitted labels."""
        got = precision_score(aligned["y"], aligned["label"], zero_division=0)
        assert abs(got - metrics["precision_default"]) < 0.01

    def test_reported_accuracy_matches_labels(self, metrics, aligned):
        """Reported accuracy matches the value recomputed from the submitted labels."""
        got = float((aligned["label"] == aligned["y"]).mean())
        assert abs(got - metrics["accuracy"]) < 0.005

    def test_reported_default_rate_matches_raw(self, metrics, aligned):
        """Reported default_rate_test matches the raw label rate over the held-out rows."""
        assert abs(float(aligned["y"].mean()) - metrics["default_rate_test"]) < 0.001

    def test_top_feature_is_real_column(self, metrics, raw):
        """top_feature names an actual input column of the dataset."""
        assert metrics["top_feature"] in [
            c for c in raw.columns if c not in (TARGET, "row_id")
        ]


class TestMetricQuality:
    def test_roc_auc_not_far_below_reference(self, metrics, reference):
        """Reported roc_auc is not far below an independently fitted reference."""
        assert metrics["roc_auc"] >= reference["roc_auc"] - 0.05

    def test_pr_auc_not_far_below_reference(self, metrics, reference):
        """Reported pr_auc is not far below an independently fitted reference."""
        assert metrics["pr_auc"] >= reference["pr_auc"] - 0.05

    def test_minority_recall_above_floor(self, aligned):
        """Minority-class recall clears a floor a model that ignores defaulters cannot reach."""
        recall = float(aligned["label"][aligned["y"] == 1].mean())
        assert recall >= 0.20, (
            f"minority recall={recall:.3f}: defaulters are being ignored"
        )


class TestCostReestimation:
    def test_cost_matrix_values(self, cost_report):
        """The cost matrix uses the fixed 20-to-1 false-negative-to-false-positive costs."""
        assert int(cost_report["cost_matrix"]["C_FN"]) == C_FN
        assert int(cost_report["cost_matrix"]["C_FP"]) == C_FP

    def test_chosen_threshold_in_range(self, cost_report):
        """The chosen threshold lies strictly inside the unit interval."""
        assert 0.0 < float(cost_report["chosen_threshold"]) < 1.0

    def test_chosen_threshold_consistent(self, cost_report, metrics):
        """chosen_threshold agrees between metrics.json and cost_report.json."""
        assert (
            abs(
                float(cost_report["chosen_threshold"])
                - float(metrics["chosen_threshold"])
            )
            < 1e-9
        )

    def test_baseline_cost_exact(self, cost_report, aligned):
        """baseline_cost_predict_all_negative equals C_FN times the held-out defaulters."""
        assert int(cost_report["baseline_cost_predict_all_negative"]) == C_FN * int(
            aligned["y"].sum()
        )

    def test_total_cost_at_chosen_matches_labels(self, cost_report, aligned):
        """total_cost_at_chosen matches the cost recomputed from the submitted labels."""
        got, _, _ = _cost(aligned["label"], aligned["y"])
        assert int(cost_report["total_cost_at_chosen"]) == got

    def test_pred_label_consistent_with_threshold(self, aligned, cost_report):
        """pred_label is the thresholding of pred_proba at the chosen threshold."""
        t = float(cost_report["chosen_threshold"])
        agree = float(np.mean(aligned["label"] == (aligned["proba"] >= t).astype(int)))
        assert agree >= 0.99, (
            f"pred_label matches the chosen-threshold rule on only {agree:.3f}"
        )

    def test_total_cost_at_half_matches(self, cost_report, aligned):
        """total_cost_at_0p5 matches the cost recomputed at a 0.5 threshold."""
        labels = (aligned["proba"] >= 0.5).astype(int)
        got, _, _ = _cost(labels, aligned["y"])
        assert abs(int(cost_report["total_cost_at_0p5"]) - got) <= 25

    def test_sweep_argmin_is_chosen(self, cost_report):
        """The chosen threshold is the minimum-cost entry of the reported sweep."""
        sweep = cost_report["threshold_sweep"]
        assert len(sweep) >= 5
        assert int(cost_report["total_cost_at_chosen"]) == min(
            int(r["total_cost"]) for r in sweep
        )

    def test_cost_saving_matches(self, cost_report):
        """cost_saving_vs_half equals the reported half-minus-chosen difference."""
        diff = int(cost_report["total_cost_at_0p5"]) - int(
            cost_report["total_cost_at_chosen"]
        )
        assert int(cost_report["cost_saving_vs_half"]) == diff

    def test_cost_saving_non_negative(self, cost_report):
        """cost_saving_vs_half is not negative."""
        assert int(cost_report["cost_saving_vs_half"]) >= 0

    def test_policy_beats_half(self, cost_report):
        """The chosen-threshold cost is no worse than the uniform 0.5-threshold cost."""
        assert int(cost_report["total_cost_at_chosen"]) <= int(
            cost_report["total_cost_at_0p5"]
        )

    def test_policy_beats_predict_all_negative(self, cost_report):
        """The chosen-threshold cost beats approving every customer."""
        assert int(cost_report["total_cost_at_chosen"]) < int(
            cost_report["baseline_cost_predict_all_negative"]
        )


class TestSource:
    def test_imbalance_handling_present(self, source):
        """The pipeline applies a class-imbalance handling technique."""
        assert any(
            s in source
            for s in [
                "case.weights",
                "case_weights",
                "class.weights",
                "class_weight",
                "weighted",
                "weights =",
                "pos_rate",
                "ovun.sample",
                "rose",
                "smote",
                "upsample",
                "downsample",
                "oversample",
                "undersample",
            ]
        )

    def test_missing_handling_present(self, source):
        """The pipeline handles missing values explicitly."""
        assert any(
            s in source
            for s in [
                "median",
                "is.na",
                "na.rm",
                "impute",
                "_missing",
                "missing_indicator",
            ]
        )

    def test_encoding_present(self, source):
        """The pipeline encodes categorical columns."""
        assert any(
            s in source
            for s in ["encode", "factor(", "as.integer", "match(", "ordinal", "levels"]
        )

    def test_threshold_search_present(self, source):
        """The pipeline searches thresholds to minimise cost rather than fixing 0.5."""
        assert any(
            s in source for s in ["threshold", "which.min", "seq(", "grid", "cost"]
        )

    def test_split_honored_present(self, source):
        """The pipeline honors the pinned train and test split."""
        assert any(s in source for s in ["split", "test_id", "row_id"])

    def test_ranking_metric_present(self, source):
        """The pipeline computes a precision-recall ranking metric."""
        assert any(
            s in source for s in ["pr_auc", "average_precision", "precision", "recall"]
        )

    def test_seeding_present(self, source):
        """The pipeline seeds its stochastic components."""
        assert any(s in source for s in ["set.seed", "seed", "rng"])

    def test_identifier_referenced(self, source):
        """The pipeline references the V1 identifier column it must exclude."""
        assert "v1" in source


class TestPathological:
    def test_roc_auc_below_leakage_ceiling(self, metrics):
        """Reported roc_auc stays below the leakage ceiling."""
        assert metrics["roc_auc"] <= 0.95

    def test_predictions_not_single_class(self, preds):
        """Predicted labels include both classes."""
        assert preds["pred_label"].nunique() == 2

    def test_pred_proba_not_degenerate(self, preds):
        """Predicted probabilities are not constant."""
        assert preds["pred_proba"].std() > 1e-3

    def test_default_rate_plausible(self, metrics, raw):
        """The held-out positive rate stays close to the dataset rate."""
        global_rate = raw[TARGET].astype(int).mean()
        assert abs(metrics["default_rate_test"] - global_rate) < 0.02
