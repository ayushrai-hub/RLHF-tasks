from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import pytest

BASE_CANDIDATES = [
    Path("/app/task_file"),
    Path(__file__).parent.parent / "environment" / "task_file",
]
BASE = next(p for p in BASE_CANDIDATES if p.exists())
INP = BASE / "input_data"
OUT = BASE / "output_data"

RAW_THRESHOLD = 0.90
STRICT_THRESHOLD = 0.83
MIN_ASSIGNED = 198
VALID_MODES = {"DIRECT", "HOLD", "REBLEND"}
CEMENT_GUARD = (5.00, 6.00)
FINE_GUARD = (44.5, 54.5)
MODEL_PY_SHA256 = "643364d01d9a28426fae4c1a1154c69848de398fa997cc04f88ef2fb67b1c1a2"

SUBSCORE_FLOORS = {
    "coverage_score": 0.92,
    "value_score": 0.87,
    "cement_conformance_score": 0.94,
    "deadline_score": 0.52,
    "throughput_balance_score": 0.90,
    "lane_utilization_score": 0.88,
    "bin_balance_score": 0.92,
}

MODEL_FOR_TESTS = Path(__file__).parent / "model_for_tests.py"
SPEC = importlib.util.spec_from_file_location("model_for_tests", MODEL_FOR_TESTS)
model_for_tests = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(model_for_tests)
score_strict = model_for_tests.score_strict


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def canonical_plan(rows):
    return sorted(rows, key=lambda row: row["pour_id"])


def canonical_summary(path):
    return json.loads(path.read_text())


def plan_ids(rows):
    return {row["pour_id"] for row in rows}


def go_binary():
    candidates = [
        Path("/usr/local/go/bin/go"),
        Path("/mnt/e/Dusker_Folder/go/bin/go"),
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "go"


def build_go_solver(go_sources, tmp_path):
    errors = []
    for path in go_sources:
        binary = tmp_path / "solver"
        result = subprocess.run(
            [go_binary(), "build", "-o", str(binary), str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return binary
        errors.append(result.stderr[-300:])
    pytest.fail(
        "no standalone Go source compiled; provide a self-contained package main file: "
        + " | ".join(errors[-2:])
    )


@pytest.fixture(scope="module")
def loads():
    return {r["pour_id"]: r for r in read_jsonl(INP / "pour_orders.jsonl")}


@pytest.fixture(scope="module")
def lines():
    return {r["batch_lane_id"]: r for r in read_jsonl(INP / "batch_lanes.jsonl")}


@pytest.fixture(scope="module")
def plan_rows():
    return read_jsonl(OUT / "concrete_dispatch_plan.jsonl")


@pytest.fixture(scope="module")
def summary():
    return json.loads((OUT / "concrete_dispatch_summary.json").read_text())


@pytest.fixture(scope="module")
def score_result():
    return score_strict(INP, OUT)


class TestInputIntegrity:
    def test_input_hashes_match(self):
        expected = json.loads((INP / "input_hashes.json").read_text())
        for name, want in expected.items():
            path = INP.parent / name if name.startswith("scripts/") else INP / name
            assert path.exists(), f"Hashed file missing: {name}"
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            assert got == want, f"{name} was modified"

    def test_model_script_not_tampered(self):
        model_path = INP.parent / "scripts" / "model.py"
        got = hashlib.sha256(model_path.read_bytes()).hexdigest()
        assert got == MODEL_PY_SHA256, "model.py was modified"


class TestOutputExists:
    def test_plan_exists(self):
        assert (OUT / "concrete_dispatch_plan.jsonl").exists()

    def test_summary_exists(self):
        assert (OUT / "concrete_dispatch_summary.json").exists()


class TestSchema:
    def test_required_plan_fields(self, plan_rows):
        required = {"pour_id", "assigned", "batch_lane_id", "production_window", "plant_zone",
                    "priority_rank", "handling_mode", "batch_water_l"}
        for row in plan_rows:
            assert required.issubset(row), f"missing required field in {row}"
            assert row["assigned"] is True

    def test_pour_ids_unique_and_known(self, loads, plan_rows):
        ids = [r["pour_id"] for r in plan_rows]
        assert len(ids) == len(set(ids)), "pour_id rows must be unique"
        assert set(ids).issubset(loads), "plan contains unknown pours"

    def test_values_in_basic_ranges(self, plan_rows, lines):
        ranks = []
        for row in plan_rows:
            assert row["batch_lane_id"] in lines
            assert row["plant_zone"] == lines[row["batch_lane_id"]]["plant_zone"]
            assert int(row["production_window"]) in {1, 2, 3, 4, 5, 6}
            assert row["handling_mode"] in VALID_MODES
            ranks.append(int(row["priority_rank"]))
        assert sorted(ranks) == list(range(1, len(ranks) + 1))


class TestHardConstraints:
    def test_public_model_reports_no_penalty(self, score_result):
        assert not score_result.get("penalty"), score_result
        assert not score_result.get("error"), score_result

    def test_all_mandatory_assigned(self, loads, plan_rows):
        assigned = {r["pour_id"] for r in plan_rows}
        missing = [lid for lid, ld in loads.items() if ld["mandatory"] and lid not in assigned]
        assert not missing, f"mandatory pours missing: {missing[:8]}"

    def test_prep_precedence_respected(self, loads, plan_rows):
        win = {r["pour_id"]: int(r["production_window"]) for r in plan_rows}
        for lid, w in win.items():
            prep = loads[lid].get("requires_admixture_prep", "")
            if prep:
                assert prep in win, f"{lid} requires prep pour {prep} which is unscheduled"
                assert win[prep] <= w, f"prep pour {prep} must not run after {lid}"


class TestScoreThresholds:
    def test_raw_score_threshold(self, score_result):
        assert score_result["total_score"] >= RAW_THRESHOLD, score_result

    def test_strict_score_threshold(self, score_result):
        assert score_result["total_score_strict"] >= STRICT_THRESHOLD, score_result

    def test_subscore_floors(self, score_result):
        for key, floor in SUBSCORE_FLOORS.items():
            assert score_result[key] >= floor, (key, score_result[key], floor)


class TestAntiShortcut:
    def test_minimum_assigned(self, plan_rows):
        assert len(plan_rows) >= MIN_ASSIGNED

    def test_uses_multiple_windows_zones_bins_and_modes(self, loads, lines, plan_rows):
        windows = {int(r["production_window"]) for r in plan_rows}
        zones = {lines[r["batch_lane_id"]]["plant_zone"] for r in plan_rows}
        bins = {loads[r["pour_id"]]["aggregate_bin"] for r in plan_rows}
        modes = {r["handling_mode"] for r in plan_rows}
        assert len(windows) >= 5
        assert len(zones) >= 5
        assert len(bins) >= 5
        assert len(modes) >= 2

    def test_no_single_window_or_zone_dominates(self, lines, plan_rows):
        window_counts = Counter(int(r["production_window"]) for r in plan_rows)
        zone_counts = Counter(lines[r["batch_lane_id"]]["plant_zone"] for r in plan_rows)
        total = len(plan_rows)
        assert max(window_counts.values()) / total <= 0.24
        assert max(zone_counts.values()) / total <= 0.30

    def test_late_windows_are_materially_used(self, plan_rows):
        window_counts = Counter(int(r["production_window"]) for r in plan_rows)
        total = len(plan_rows)
        assert window_counts[5] / total >= 0.10
        assert window_counts[6] / total >= 0.10

    def test_cement_inside_guard(self, score_result):
        cement = score_result["weighted_cement_pct"]
        assert CEMENT_GUARD[0] <= cement <= CEMENT_GUARD[1], cement

    def test_fine_inside_guard(self, score_result):
        fine = score_result["weighted_fine_pct"]
        assert FINE_GUARD[0] <= fine <= FINE_GUARD[1], fine

    def test_waters_are_not_placeholder_constants(self, plan_rows):
        values = [float(r["batch_water_l"]) for r in plan_rows]
        assert len({round(v, 2) for v in values}) >= 10
        assert statistics.pstdev(values) >= 5.0

    def test_summary_matches_plan(self, loads, lines, plan_rows, summary):
        assert isinstance(summary.get("assigned_count"), int)
        assert summary["assigned_count"] == len(plan_rows)
        actual_windows = Counter(str(int(r["production_window"])) for r in plan_rows)
        actual_zones = Counter(lines[r["batch_lane_id"]]["plant_zone"] for r in plan_rows)
        actual_lanes = Counter(r["batch_lane_id"] for r in plan_rows)
        actual_cubic_m = sum(float(loads[r["pour_id"]]["cubic_m"]) for r in plan_rows)
        actual_cement = (sum(float(loads[r["pour_id"]]["cement_pct"]) * float(loads[r["pour_id"]]["cubic_m"])
                         for r in plan_rows) / actual_cubic_m) if actual_cubic_m else 0.0
        actual_fine = (sum(float(loads[r["pour_id"]]["fine_pct"]) * float(loads[r["pour_id"]]["cubic_m"])
                       for r in plan_rows) / actual_cubic_m) if actual_cubic_m else 0.0
        assert {str(k): int(v) for k, v in summary["window_counts"].items()} == dict(actual_windows)
        assert {str(k): int(v) for k, v in summary["zone_counts"].items()} == dict(actual_zones)
        assert {str(k): int(v) for k, v in summary["lane_counts"].items()} == dict(actual_lanes)
        assert abs(float(summary["delivered_cubic_m"]) - actual_cubic_m) <= 0.5
        assert abs(float(summary["weighted_cement_pct"]) - actual_cement) <= 1e-3
        assert abs(float(summary["weighted_fine_pct"]) - actual_fine) <= 1e-3


class TestGoLanguageRequirement:
    @pytest.fixture(scope="class")
    def go_sources(self):
        roots = []
        local_task_root = Path(__file__).parent.parent
        if local_task_root != Path("/"):
            roots.append(local_task_root)
        roots.extend([Path("/app"), Path("/tmp")])
        files = []
        for root in roots:
            if root.exists():
                files.extend(root.rglob("*.go"))
        return [
            path
            for path in files
            if "concrete_dispatch_plan.jsonl" in path.read_text(errors="ignore")
            and "pour_orders.jsonl" in path.read_text(errors="ignore")
        ]

    def test_go_source_exists(self, go_sources):
        assert go_sources, "no Go source files found under /app or /tmp"

    def test_go_source_compiles(self, go_sources, tmp_path):
        build_go_solver(go_sources, tmp_path)

    def test_go_binary_reproduces_main_plan(self, go_sources, tmp_path):
        solver = build_go_solver(go_sources, tmp_path)
        fresh_out = tmp_path / "fresh_output"
        fresh_out.mkdir()
        result = subprocess.run([str(solver), str(INP), str(fresh_out)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        fresh_score = score_strict(INP, fresh_out)
        assert not fresh_score.get("penalty"), fresh_score
        assert not fresh_score.get("error"), fresh_score
        assert fresh_score["total_score"] >= RAW_THRESHOLD, fresh_score
        assert fresh_score["total_score_strict"] >= STRICT_THRESHOLD, fresh_score
        for key, floor in SUBSCORE_FLOORS.items():
            assert fresh_score[key] >= floor, (key, fresh_score[key], floor)
        assert canonical_plan(read_jsonl(fresh_out / "concrete_dispatch_plan.jsonl")) == canonical_plan(read_jsonl(OUT / "concrete_dispatch_plan.jsonl"))
        assert canonical_summary(fresh_out / "concrete_dispatch_summary.json") == canonical_summary(OUT / "concrete_dispatch_summary.json")

    def test_solver_responds_to_perturbed_inputs(self, go_sources, tmp_path):
        solver = build_go_solver(go_sources, tmp_path)
        submitted_plan = canonical_plan(read_jsonl(OUT / "concrete_dispatch_plan.jsonl"))
        submitted_ids = plan_ids(submitted_plan)
        perturbed_base = tmp_path / "task_file"
        perturbed_in = perturbed_base / "input_data"
        perturbed_out = perturbed_base / "output_data"
        shutil.copytree(INP, perturbed_in)
        shutil.copytree(BASE / "scripts", perturbed_base / "scripts")
        perturbed_out.mkdir()
        rows = read_jsonl(perturbed_in / "pour_orders.jsonl")
        omitted = [row for row in rows if row["pour_id"] not in submitted_ids]
        target = max(omitted, key=lambda row: (int(row["value"]), row["pour_id"]))
        for row in rows:
            if row["pour_id"] == target["pour_id"]:
                row["mandatory"] = True
                row["value"] = int(row["value"]) + 1200
                row["deadline_window"] = max(int(row["earliest_window"]) + 2, int(row["deadline_window"]))
                break
        (perturbed_in / "pour_orders.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        hashes = json.loads((perturbed_in / "input_hashes.json").read_text())
        hashes["pour_orders.jsonl"] = hashlib.sha256((perturbed_in / "pour_orders.jsonl").read_bytes()).hexdigest()
        (perturbed_in / "input_hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
        result = subprocess.run([str(solver), str(perturbed_in), str(perturbed_out)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        new_plan = canonical_plan(read_jsonl(perturbed_out / "concrete_dispatch_plan.jsonl"))
        assert target["pour_id"] in plan_ids(new_plan), "solver ignored newly mandatory high-value pour"
        assert new_plan != submitted_plan, "solver reused the original plan instead of re-planning"
        assert len(new_plan) >= MIN_ASSIGNED
        perturbed_score = score_strict(perturbed_in, perturbed_out)
        assert not perturbed_score.get("penalty"), perturbed_score
        assert not perturbed_score.get("error"), perturbed_score
        assert perturbed_score["total_score"] >= RAW_THRESHOLD, perturbed_score
        assert perturbed_score["total_score_strict"] >= STRICT_THRESHOLD, perturbed_score
