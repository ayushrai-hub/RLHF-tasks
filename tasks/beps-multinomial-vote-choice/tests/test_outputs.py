# ruff: noqa: E501
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from conftest import run_r

OUT = Path("/app/environment/outputs")
REF = "source('/tmp/beps_ref.R'); ref <- compute_ref()\n"
HIDDEN = os.environ.get("HIDDEN_VARIANT") == "1"

COEF_FILE = OUT / "coefficients.csv"
ME_FILE = OUT / "marginal_effects.csv"
LR_FILE = OUT / "lr_tests.csv"
FIT_FILE = OUT / "model_fit.json"
PLOTS = ["effect_europe_by_knowledge.png", "ame_forest.png", "vote_shares.png",
         "calibration.png", "confusion_heatmap.png"]

TERMS = ["intercept", "age", "gender_male", "econ_national", "econ_household", "blair",
         "hague", "kennedy", "europe", "political_knowledge", "europe_x_political_knowledge"]
PARTIES = ["Conservative", "Labour", "Liberal Democrat"]
PREDS = ["age", "gender_male", "econ_national", "econ_household", "blair", "hague",
         "kennedy", "europe", "political_knowledge"]
LR_TERMS = ["age", "gender_male", "econ_national", "econ_household", "blair", "hague",
            "kennedy", "europe_x_political_knowledge"]
FIT_KEYS = ["n", "n_parameters", "log_likelihood", "deviance", "aic", "mcfadden_r2",
            "accuracy", "multiclass_brier", "interaction_lr_chisq", "interaction_df", "interaction_p"]


def _png_ok(path):
    return path.exists() and path.stat().st_size > 0 and path.read_bytes()[:4] == b"\x89PNG"


def _rounded_to_6(x):
    """A value carries at most six decimal places (equals its own 6-decimal rounding)."""
    return pd.isna(x) or abs(float(x) - round(float(x), 6)) <= 1e-9


def test_A1_coefficients_exists():
    """coefficients.csv is written."""
    assert COEF_FILE.exists(), "coefficients.csv missing"


def test_A2_marginal_effects_exists():
    """marginal_effects.csv is written."""
    assert ME_FILE.exists(), "marginal_effects.csv missing"


def test_A3_lr_tests_exists():
    """lr_tests.csv is written."""
    assert LR_FILE.exists(), "lr_tests.csv missing"


def test_A4_model_fit_exists():
    """model_fit.json is written."""
    assert FIT_FILE.exists(), "model_fit.json missing"


@pytest.mark.parametrize("name", PLOTS)
def test_A5_plots_valid_png(name):
    """Each required plot exists and has a valid PNG header."""
    assert _png_ok(OUT / name), f"{name} missing or not a valid PNG"


@pytest.mark.parametrize("name", PLOTS)
def test_A6_plots_have_real_content(name):
    """Each plot carries actual rendered content, not a blank canvas."""
    path = OUT / name
    assert _png_ok(path), f"{name} missing or not a valid PNG"
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img).reshape(-1, 3)
    colors, counts = np.unique(arr, axis=0, return_counts=True)
    assert len(colors) >= 10, f"{name} has only {len(colors)} distinct colours; looks blank"
    assert counts.max() / arr.shape[0] <= 0.995, f"{name} is {counts.max() / arr.shape[0]:.3f} one colour; looks blank"


def test_B1_coefficients_schema():
    """coefficients.csv has the right columns, 22 rows, both equations and all terms, sorted."""
    df = pd.read_csv(COEF_FILE)
    assert list(df.columns) == ["equation", "term", "estimate", "std_error", "z", "p_value"]
    assert len(df) == 22
    assert set(df["equation"]) == {"labour", "libdem"}
    assert set(df["term"]) == set(TERMS)
    assert df[["equation", "term"]].equals(df.sort_values(["equation", "term"])[["equation", "term"]].reset_index(drop=True))


def test_B2_marginal_effects_schema():
    """marginal_effects.csv has the right columns, 27 rows, every party-by-predictor pair, sorted."""
    df = pd.read_csv(ME_FILE)
    assert list(df.columns) == ["outcome", "predictor", "ame", "ame_se", "ame_z", "ame_p"]
    assert len(df) == 27
    assert set(df["outcome"]) == set(PARTIES)
    assert set(df["predictor"]) == set(PREDS)
    assert df[["outcome", "predictor"]].equals(df.sort_values(["outcome", "predictor"])[["outcome", "predictor"]].reset_index(drop=True))


def test_B3_lr_tests_schema():
    """lr_tests.csv has the right columns, eight terms each on two degrees of freedom, sorted."""
    df = pd.read_csv(LR_FILE)
    assert list(df.columns) == ["term", "df", "lr_chisq", "p_value"]
    assert set(df["term"]) == set(LR_TERMS)
    assert len(df) == 8
    assert (df["df"] == 2).all()
    assert df["term"].equals(df.sort_values("term")["term"].reset_index(drop=True))


def test_B4_model_fit_keys():
    """model_fit.json carries every required key."""
    d = json.loads(FIT_FILE.read_text())
    for k in FIT_KEYS:
        assert k in d, f"missing key {k}"


def test_B5_six_decimal_rounding():
    """Every numeric output is rounded to at most six decimals, and JSON values are bare numbers."""
    for f in (COEF_FILE, ME_FILE, LR_FILE):
        df = pd.read_csv(f)
        for col in df.select_dtypes(include="number").columns:
            bad = df.loc[~df[col].map(_rounded_to_6), col]
            assert bad.empty, f"{f.name}:{col} has values not rounded to six decimals: {bad.tolist()[:3]}"
    d = json.loads(FIT_FILE.read_text())
    for k, v in d.items():
        assert isinstance(v, (int, float)) and not isinstance(v, bool), f"{k} is not a bare JSON number: {v!r}"
        assert _rounded_to_6(v), f"{k} not rounded to six decimals: {v!r}"


def test_C1_coefficient_inference_well_formed():
    """Coefficient standard errors are positive and p-values lie in the unit interval."""
    df = pd.read_csv(COEF_FILE)
    assert (df["std_error"] > 0).all()
    assert df["p_value"].between(0, 1).all()


def test_C2_marginal_effects_well_formed():
    """Marginal-effect standard errors are positive and p-values lie in the unit interval."""
    df = pd.read_csv(ME_FILE)
    assert (df["ame_se"] > 0).all()
    assert df["ame_p"].between(0, 1).all()


def test_C3_lr_tests_well_formed():
    """Likelihood-ratio statistics are non-negative and their p-values lie in the unit interval."""
    df = pd.read_csv(LR_FILE)
    assert (df["lr_chisq"] >= 0).all()
    assert df["p_value"].between(0, 1).all()


def test_C4_fit_metrics_well_formed():
    """Reported fit metrics fall in their natural ranges."""
    d = json.loads(FIT_FILE.read_text())
    assert d["n"] == 1525 or d["n"] > 0
    assert d["n_parameters"] == 22
    assert 0 <= d["accuracy"] <= 1
    assert 0 <= d["mcfadden_r2"] <= 1
    assert 0 <= d["multiclass_brier"] <= 2
    assert d["deviance"] > 0


def test_D1_coefficients_recompute():
    """Every fitted coefficient and its standard error match an independent recomputation."""
    snippet = REF + r"""
ag <- read.csv('/app/environment/outputs/coefficients.csv', stringsAsFactors=FALSE)
for (i in seq_len(nrow(ref$coef))) {
  rr <- ref$coef[i, ]
  aa <- ag[ag$equation==rr$equation & ag$term==rr$term, ]
  if (nrow(aa)!=1) fail(paste('missing', rr$equation, rr$term))
  if (!approx_ok(aa$estimate, rr$estimate, 5e-3)) fail(sprintf('%s/%s est %.5f vs %.5f', rr$equation, rr$term, aa$estimate, rr$estimate))
  if (!approx_ok(aa$std_error, rr$std_error, 5e-3)) fail(sprintf('%s/%s se %.5f vs %.5f', rr$equation, rr$term, aa$std_error, rr$std_error))
}
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


def test_D2_marginal_effects_recompute():
    """Every average marginal effect and its delta-method standard error match recomputation."""
    snippet = REF + r"""
ag <- read.csv('/app/environment/outputs/marginal_effects.csv', stringsAsFactors=FALSE)
for (i in seq_len(nrow(ref$me))) {
  rr <- ref$me[i, ]
  aa <- ag[ag$outcome==rr$outcome & ag$predictor==rr$predictor, ]
  if (nrow(aa)!=1) fail(paste('missing', rr$outcome, rr$predictor))
  if (!approx_ok(aa$ame, rr$ame, 5e-3)) fail(sprintf('%s/%s ame %.5f vs %.5f', rr$outcome, rr$predictor, aa$ame, rr$ame))
  if (!approx_ok(aa$ame_se, rr$ame_se, 5e-3)) fail(sprintf('%s/%s ame_se %.5f vs %.5f', rr$outcome, rr$predictor, aa$ame_se, rr$ame_se))
}
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


def test_D3_lr_tests_recompute():
    """Each likelihood-ratio statistic matches recomputation of the dropped-term refit."""
    snippet = REF + r"""
ag <- read.csv('/app/environment/outputs/lr_tests.csv', stringsAsFactors=FALSE)
for (i in seq_len(nrow(ref$lr))) {
  rr <- ref$lr[i, ]
  aa <- ag[ag$term==rr$term, ]
  if (nrow(aa)!=1) fail(paste('missing', rr$term))
  if (!approx_ok(aa$lr_chisq, rr$lr_chisq, 1e-2)) fail(sprintf('%s chisq %.4f vs %.4f', rr$term, aa$lr_chisq, rr$lr_chisq))
}
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


def test_D4_model_fit_recompute():
    """The fit summary matches recomputation of likelihood, pseudo R-squared, accuracy, Brier and the interaction test."""
    snippet = REF + r"""
library(jsonlite)
ag <- fromJSON('/app/environment/outputs/model_fit.json')
f <- ref$fit
if (!approx_ok(ag$log_likelihood, f$log_likelihood, 5e-2)) fail(sprintf('loglik %.4f vs %.4f', ag$log_likelihood, f$log_likelihood))
if (!approx_ok(ag$mcfadden_r2, f$mcfadden_r2, 5e-3)) fail(sprintf('mcfadden %.5f vs %.5f', ag$mcfadden_r2, f$mcfadden_r2))
if (!approx_ok(ag$accuracy, f$accuracy, 5e-3)) fail(sprintf('accuracy %.5f vs %.5f', ag$accuracy, f$accuracy))
if (!approx_ok(ag$multiclass_brier, f$multiclass_brier, 5e-3)) fail(sprintf('brier %.5f vs %.5f', ag$multiclass_brier, f$multiclass_brier))
if (!approx_ok(ag$interaction_lr_chisq, f$interaction_lr_chisq, 1e-2)) fail(sprintf('int_chisq %.4f vs %.4f', ag$interaction_lr_chisq, f$interaction_lr_chisq))
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


def test_E1_leader_own_party_effects():
    """Each leader rating raises the probability of that leader's own party."""
    df = pd.read_csv(ME_FILE).set_index(["outcome", "predictor"])
    assert df.loc[("Labour", "blair"), "ame"] > 0
    assert df.loc[("Conservative", "hague"), "ame"] > 0
    assert df.loc[("Liberal Democrat", "kennedy"), "ame"] > 0


def test_E2_euroscepticism_favours_conservatives():
    """A more Eurosceptic attitude raises the Conservative probability and lowers the Labour probability."""
    df = pd.read_csv(ME_FILE).set_index(["outcome", "predictor"])
    assert df.loc[("Conservative", "europe"), "ame"] > 0
    assert df.loc[("Labour", "europe"), "ame"] < 0


def test_E3_interaction_significant():
    """The Europe-by-political-knowledge interaction is statistically significant."""
    d = json.loads(FIT_FILE.read_text())
    assert d["interaction_p"] < 0.05
    assert d["interaction_lr_chisq"] > 10


def test_E4_model_beats_baseline():
    """The fitted model classifies better than chance and explains a non-trivial share of deviance."""
    d = json.loads(FIT_FILE.read_text())
    assert d["accuracy"] > 0.55
    assert d["mcfadden_r2"] > 0.2


def test_F1_marginal_effects_sum_to_zero():
    """For each predictor the marginal effects across the three parties sum to approximately zero."""
    df = pd.read_csv(ME_FILE)
    sums = df.groupby("predictor")["ame"].sum().abs()
    assert (sums < 1e-3).all(), f"max |sum| {sums.max()}"


def test_F2_interaction_matches_lr_table():
    """The interaction statistic in model_fit.json equals the interaction row of lr_tests.csv."""
    d = json.loads(FIT_FILE.read_text())
    lr = pd.read_csv(LR_FILE).set_index("term")
    assert abs(d["interaction_lr_chisq"] - lr.loc["europe_x_political_knowledge", "lr_chisq"]) < 1e-2


def test_G1_coefficient_z_consistent():
    """Each coefficient z-statistic equals the estimate divided by its standard error."""
    df = pd.read_csv(COEF_FILE)
    tol = 2e-3 * (1 + df["z"].abs())
    assert ((df["estimate"] / df["std_error"] - df["z"]).abs() <= tol).all()


def test_G2_marginal_effect_z_consistent():
    """Each marginal-effect z-statistic equals the effect divided by its standard error."""
    df = pd.read_csv(ME_FILE)
    tol = 2e-3 * (1 + df["ame_z"].abs())
    assert ((df["ame"] / df["ame_se"] - df["ame_z"]).abs() <= tol).all()


def test_G3_n_matches_data():
    """The reported sample size equals the number of rows the model was fit on."""
    snippet = REF + r"""
library(jsonlite)
ag <- fromJSON('/app/environment/outputs/model_fit.json')
if (ag$n != ref$n) fail(sprintf('n %d vs %d', ag$n, ref$n))
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


@pytest.mark.skipif(HIDDEN, reason="public-data precision bound")
def test_H1_accuracy_public_band():
    """On the public data the classification accuracy sits in the expected band."""
    d = json.loads(FIT_FILE.read_text())
    assert 0.64 < d["accuracy"] < 0.72


@pytest.mark.skipif(HIDDEN, reason="public-data precision bound")
def test_H2_mcfadden_public_band():
    """On the public data McFadden's pseudo R-squared sits in the expected band."""
    d = json.loads(FIT_FILE.read_text())
    assert 0.27 < d["mcfadden_r2"] < 0.34


@pytest.mark.skipif(HIDDEN, reason="public-data precision bound")
def test_H3_interaction_chisq_public_band():
    """On the public data the interaction likelihood-ratio statistic sits in the expected band."""
    d = json.loads(FIT_FILE.read_text())
    assert 40 < d["interaction_lr_chisq"] < 62


@pytest.mark.skipif(HIDDEN, reason="public-data precision bound")
def test_H4_key_ames_public_band():
    """On the public data the Blair-on-Labour and Europe-on-Conservative effects sit in their bands."""
    df = pd.read_csv(ME_FILE).set_index(["outcome", "predictor"])
    assert 0.09 < df.loc[("Labour", "blair"), "ame"] < 0.13
    assert 0.015 < df.loc[("Conservative", "europe"), "ame"] < 0.035


EKI_FILE = OUT / "europe_knowledge_interaction.json"
EKI_KEYS = ["ame_europe_k0_conservative", "ame_europe_k0_labour", "ame_europe_k0_libdem",
            "ame_europe_k3_conservative", "ame_europe_k3_labour", "ame_europe_k3_libdem",
            "interaction_effect_conservative", "interaction_effect_labour", "interaction_effect_libdem"]


def test_A7_eki_exists():
    """europe_knowledge_interaction.json is written."""
    assert EKI_FILE.exists(), "europe_knowledge_interaction.json missing"


def test_B6_eki_keys():
    """europe_knowledge_interaction.json carries the nine required keys as bare numbers."""
    d = json.loads(EKI_FILE.read_text())
    for k in EKI_KEYS:
        assert k in d, f"missing key {k}"
        assert isinstance(d[k], (int, float)) and not isinstance(d[k], bool), f"{k} not numeric"


def test_C5_eki_well_formed():
    """Each interaction effect is the high-minus-low-knowledge difference and the three sum to zero."""
    d = json.loads(EKI_FILE.read_text())
    for party in ("conservative", "labour", "libdem"):
        diff = d[f"ame_europe_k3_{party}"] - d[f"ame_europe_k0_{party}"]
        assert abs(d[f"interaction_effect_{party}"] - diff) < 1e-5, party
    total = sum(d[f"interaction_effect_{p}"] for p in ("conservative", "labour", "libdem"))
    assert abs(total) < 1e-4, total


def test_D5_eki_recompute():
    """The counterfactual Europe marginal effects at each knowledge level and their interaction match recomputation; the tight tolerance excludes the raw interaction coefficient."""
    snippet = REF + r"""
library(jsonlite)
ag <- fromJSON('/app/environment/outputs/europe_knowledge_interaction.json')
e <- ref$eki
for (k in names(e)) {
  if (!approx_ok(ag[[k]], e[[k]], 1e-3)) fail(sprintf('%s %.6f vs %.6f', k, ag[[k]], e[[k]]))
}
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


@pytest.mark.skipif(HIDDEN, reason="public-data precision bound")
def test_H5_eki_public_band():
    """On the public data euroscepticism among the knowledgeable moves strongly toward the Conservatives."""
    d = json.loads(EKI_FILE.read_text())
    assert d["ame_europe_k3_conservative"] > d["ame_europe_k0_conservative"]
    assert 0.03 < d["interaction_effect_conservative"] < 0.08
    assert d["interaction_effect_labour"] < 0
    assert d["interaction_effect_libdem"] < 0


EFD_FILE = OUT / "europe_first_difference.json"
EFD_KEYS = ["share_europhile_conservative", "share_europhile_labour", "share_europhile_libdem",
            "share_eurosceptic_conservative", "share_eurosceptic_labour", "share_eurosceptic_libdem",
            "first_diff_conservative", "first_diff_labour", "first_diff_libdem"]


def test_A8_efd_exists():
    """europe_first_difference.json is written."""
    assert EFD_FILE.exists(), "europe_first_difference.json missing"


def test_B7_efd_keys():
    """europe_first_difference.json carries the nine required keys as bare numbers."""
    d = json.loads(EFD_FILE.read_text())
    for k in EFD_KEYS:
        assert k in d, f"missing key {k}"
        assert isinstance(d[k], (int, float)) and not isinstance(d[k], bool), f"{k} not numeric"


def test_C6_efd_well_formed():
    """Each scenario's party shares are probabilities summing to one, and first differences are eurosceptic-minus-europhile and sum to zero."""
    d = json.loads(EFD_FILE.read_text())
    for scen in ("europhile", "eurosceptic"):
        shares = [d[f"share_{scen}_{p}"] for p in ("conservative", "labour", "libdem")]
        assert all(0 <= s <= 1 for s in shares), (scen, shares)
        assert abs(sum(shares) - 1) < 1e-4, (scen, sum(shares))
    for p in ("conservative", "labour", "libdem"):
        diff = d[f"share_eurosceptic_{p}"] - d[f"share_europhile_{p}"]
        assert abs(d[f"first_diff_{p}"] - diff) < 1e-5, p
    total = sum(d[f"first_diff_{p}"] for p in ("conservative", "labour", "libdem"))
    assert abs(total) < 1e-4, total


def test_D6_efd_recompute():
    """The population-average vote shares under a fully Europhile and fully Eurosceptic electorate and their first differences match recomputation; the tight tolerance excludes evaluating at covariate means or substituting the instantaneous Europe derivative."""
    snippet = REF + r"""
library(jsonlite)
ag <- fromJSON('/app/environment/outputs/europe_first_difference.json')
e <- ref$efd
for (k in names(e)) {
  if (!approx_ok(ag[[k]], e[[k]], 1e-3)) fail(sprintf('%s %.6f vs %.6f', k, ag[[k]], e[[k]]))
}
quit(status=0)
"""
    r = run_r(snippet)
    assert r.returncode == 0, r.stderr or r.stdout


@pytest.mark.skipif(HIDDEN, reason="public-data precision bound")
def test_H6_efd_public_band():
    """On the public data a fully Eurosceptic electorate shifts decisively toward the Conservatives and away from Labour."""
    d = json.loads(EFD_FILE.read_text())
    assert d["first_diff_conservative"] > 0.1
    assert d["first_diff_labour"] < 0
