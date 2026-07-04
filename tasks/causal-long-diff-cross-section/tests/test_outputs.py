import csv
import json
import math
import os
import random
import shutil
import subprocess
import tempfile

import numpy as np

APP = "/app"
ESTIMATE = os.path.join(APP, "estimate.json")
PUBLIC_DATA = os.path.join(APP, "data")
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _load_json(path):
    """Read a JSON file."""
    with open(path) as fh:
        return json.load(fh)


def _load_truth(name):
    """Load verifier-only truth metadata."""
    return _load_json(os.path.join(FIX, name))


def _run_agent(data_dir):
    """Run analysis.R against one data directory."""
    if os.path.exists(ESTIMATE):
        os.remove(ESTIMATE)
    env = dict(os.environ, CAUSAL_DATA_DIR=data_dir)
    run = subprocess.run(
        ["Rscript", os.path.join(APP, "analysis.R")],
        cwd=APP,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert run.returncode == 0, run.stderr
    assert os.path.exists(ESTIMATE), "estimate.json not found"
    return _load_json(ESTIMATE)


def _copy_data_dir(source):
    """Copy a data directory into a temporary location."""
    dest = tempfile.mkdtemp(prefix="causal-data-")
    shutil.copy(os.path.join(source, "main.csv"), os.path.join(dest, "main.csv"))
    params = os.path.join(source, "params.json")
    if os.path.exists(params):
        shutil.copy(params, os.path.join(dest, "params.json"))
    return dest


def _shuffle_data_dir(source):
    """Copy a data directory with rows in deterministic shuffled order."""
    dest = _copy_data_dir(source)
    with open(os.path.join(dest, "main.csv")) as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fields = reader.fieldnames
    random.Random(20260703).shuffle(rows)
    with open(os.path.join(dest, "main.csv"), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return dest


def _repeat_data_dir(source, times):
    """Copy a data directory with rows repeated a fixed number of times."""
    dest = _copy_data_dir(source)
    with open(os.path.join(dest, "main.csv")) as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fields = reader.fieldnames
    repeated = rows * times
    with open(os.path.join(dest, "main.csv"), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(repeated)
    return dest


def _write_case(rows, params):
    """Write a synthetic case into a temporary data directory."""
    dest = tempfile.mkdtemp(prefix="causal-stress-")
    with open(os.path.join(dest, "main.csv"), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(dest, "params.json"), "w") as fh:
        json.dump(params, fh)
    return dest


def _naive_estimate(data_dir):
    """Compute the follow-up-only shortcut."""
    rows = []
    with open(os.path.join(data_dir, "main.csv")) as fh:
        for row in csv.DictReader(fh):
            rows.append((float(row["d_treatment"]), float(row["y_followup"])))
    treatment = np.array([row[0] for row in rows])
    outcome = np.array([row[1] for row in rows])
    design = np.column_stack([np.ones(len(rows)), treatment])
    coef = np.linalg.lstsq(design, outcome, rcond=None)[0]
    return float(coef[1])


def _make_stress_case():
    """Create a compact two-period outcome sample."""
    rows = []
    baselines = [4.0, 5.5, 6.0, 7.5, 9.0, 10.0]
    for unit, base in enumerate(baselines):
        treatment = int(unit >= 3)
        follow = base + 2.2 * treatment
        rows.append({"unit_id": unit, "d_treatment": treatment, "y_baseline": base, "y_followup": follow})
    return _write_case(rows, {}), {"true_val": 2.2, "tol": 1e-8, "naive_min_relerr": 0.2}



def _relative_error(value, truth):
    """Compute relative error against a nonzero truth."""
    return abs(float(value) - float(truth)) / abs(float(truth))


def _assert_within(out, truth):
    """Assert an output estimate is within truth tolerance."""
    assert "estimate" in out and math.isfinite(float(out["estimate"]))
    assert _relative_error(out["estimate"], truth["true_val"]) <= float(truth["tol"])


def test_output_schema():
    """The output JSON contains one finite numeric estimate."""
    out = _run_agent(PUBLIC_DATA)
    assert "estimate" in out and math.isfinite(float(out["estimate"]))


def test_estimate_matches_public_truth():
    """The estimate matches verifier truth on the public sample."""
    truth = _load_truth("public_truth.json")
    _assert_within(_run_agent(PUBLIC_DATA), truth)


def test_naive_estimator_fails():
    """The obvious shortcut estimator remains outside tolerance."""
    truth = _load_truth("public_truth.json")
    naive = _naive_estimate(PUBLIC_DATA)
    assert _relative_error(naive, truth["true_val"]) >= float(truth["naive_min_relerr"])


def test_hidden_seed_generalizes():
    """The estimator generalizes to the hidden sample."""
    truth = _load_truth("hidden_truth.json")
    _assert_within(_run_agent(os.path.join(FIX, "hidden")), truth)


def test_shuffled_rows_match_public_truth():
    """A deterministic row permutation does not change the estimate."""
    truth = _load_truth("public_truth.json")
    _assert_within(_run_agent(_shuffle_data_dir(PUBLIC_DATA)), truth)


def test_synthetic_stress_case_generalizes():
    """A small adversarial synthetic case has the expected estimate."""
    data_dir, truth = _make_stress_case()
    _assert_within(_run_agent(data_dir), truth)


def test_repeated_stress_case_is_stable():
    """A repeated larger stress case keeps the same estimate."""
    data_dir, truth = _make_stress_case()
    repeated = _repeat_data_dir(data_dir, 25)
    _assert_within(_run_agent(repeated), truth)


def test_wrong_magnitude_is_rejected_by_tolerance():
    """A sign-correct but wrong-magnitude value is outside tolerance."""
    truth = _load_truth("public_truth.json")
    candidate = float(truth["true_val"]) * 0.55
    assert _relative_error(candidate, truth["true_val"]) > float(truth["tol"])


def test_no_forbidden_access_or_public_constants():
    """analysis.R does not read verifier files or embed known truth values."""
    src = open(os.path.join(APP, "analysis.R")).read()
    public_truth = _load_truth("public_truth.json")
    hidden_truth = _load_truth("hidden_truth.json")
    assert "/tests" not in src
    assert "public_truth" not in src
    assert "hidden_truth" not in src
    assert f'{float(public_truth["true_val"]):.6f}' not in src
    assert f'{float(hidden_truth["true_val"]):.6f}' not in src
