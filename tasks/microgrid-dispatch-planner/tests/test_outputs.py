import os
import sys
import json
import hashlib
from pathlib import Path

sys.path.insert(0, "/tests")
sys.path.insert(0, "/app/task_file/scripts")

from model import evaluate as base_evaluate  # noqa: E402
from model_for_tests import strict_evaluate  # noqa: E402

INPUT = Path("/app/task_file/input_data")
OUTPUT = Path("/app/task_file/output_data")

INPUT_HASHES = {
    "units.jsonl": "2e1ab9feee71c78d22a80a5d1cc056735da4300ae7623af66724be2134413b35",
    "config.json": "df194013a5c25259a0c7b2de53f8bdf2faa7b39f7c99941b1594126066092ce4",
}
MODEL_PY_SHA256 = "5c4fa4116f5b4d7b49fffaf43324c0c638b2c27881e4ad6df1da60595d8512fc"

# Published physical constants (must match the cost/emission rules in model.py).
HEAT_CURVE = 0.6
RENEWABLE = {"solar", "wind"}
MAX_OVERSUPPLY = 0.25


def load_units():
    return [json.loads(line) for line in (INPUT / "units.jsonl").read_text().splitlines() if line.strip()]


def load_config():
    return json.loads((INPUT / "config.json").read_text())


def load_plan():
    return json.loads((OUTPUT / "dispatch.json").read_text())


def alloc_map(plan):
    return {a["unit_id"]: a for a in plan["allocations"]}


def release_binary():
    targets = list(Path("/app").rglob("target/release/*"))
    bins = [
        f for f in targets
        if f.is_file() and os.access(f, os.X_OK)
        and "deps" not in f.parts and "build" not in f.parts and not f.suffix
    ]
    assert bins, "No compiled Rust binary found"
    return bins[0]


def write_dynamic_instance(seed):
    """Rewrite the fixture into a renamed, capacity-tight scenario."""
    base_units = load_units()
    base_cfg = load_config()
    buses = base_cfg["buses"]
    feeders = base_cfg["feeders"]

    units = []
    id_map = {}
    for i, u in enumerate(base_units):
        nu = dict(u)
        nu["id"] = f"dyn{seed}_{i:04d}"
        id_map[u["id"]] = nu["id"]
        nu["bus"] = buses[(buses.index(u["bus"]) + seed + i // 47) % len(buses)]
        nu["feeder"] = feeders[(feeders.index(u["feeder"]) + seed * 3 + i // 31) % len(feeders)]
        nu["avail"] = max(0.30, min(1.0, u["avail"] * (0.92 + ((i * 17 + seed * 11) % 19) / 100.0)))
        nu["capacity_kw"] = round(u["capacity_kw"] * (0.94 + ((i * 13 + seed * 5) % 15) / 100.0), 4)
        if u["fuel"] in {"gas", "diesel"}:
            nu["emission_rate"] = round(u["emission_rate"] * (0.96 + ((i + seed) % 9) / 100.0), 6)
        units.append(nu)

    avail_by_fuel = {}
    for u in units:
        avail_by_fuel[u["fuel"]] = avail_by_fuel.get(u["fuel"], 0.0) + u["capacity_kw"] * u["avail"]
    clean_target = (
        avail_by_fuel.get("solar", 0.0)
        + avail_by_fuel.get("wind", 0.0)
        + 0.95 * avail_by_fuel.get("battery", 0.0)
    )
    demand = round(clean_target / (1.012 + 0.003 * seed), 2)

    bus_cap = {b: 0.0 for b in buses}
    for u in units:
        bus_cap[u["bus"]] += u["capacity_kw"] * u["avail"]
    per_bus = {b: round(min(bus_cap[b] * 0.30, demand / len(buses) * (0.45 + 0.02 * ((i + seed) % 3))), 2)
               for i, b in enumerate(buses)}

    conflicts = []
    for a, b in base_cfg["conflict_pairs"][:42]:
        if a in id_map and b in id_map:
            conflicts.append([id_map[a], id_map[b]])
    for i in range(0, min(96, len(units) - 7), 8):
        conflicts.append([units[(i + seed) % len(units)]["id"], units[(i + 7 + 3 * seed) % len(units)]["id"]])

    mandatory = [id_map[u] for u in base_cfg["mandatory_online_units"] if u in id_map]
    cfg = dict(base_cfg)
    cfg["total_demand_kw"] = demand
    cfg["reserve_requirement_kw"] = round(base_cfg["reserve_requirement_kw"] * (0.92 + 0.04 * seed), 2)
    cfg["renewable_min_fraction"] = 0.58 + 0.01 * seed
    cfg["emission_budget"] = round(base_cfg["emission_budget"] * (0.96 + 0.02 * seed), 2)
    cfg["per_bus_min_kw"] = per_bus
    cfg["conflict_pairs"] = conflicts
    cfg["mandatory_online_units"] = mandatory
    cfg["max_committed_thermal"] = max(4, base_cfg["max_committed_thermal"] - (seed % 2))

    (INPUT / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    (INPUT / "units.jsonl").write_text("\n".join(json.dumps(u, sort_keys=True) for u in units) + "\n")


def write_tight_commitment_instance():
    """Rewrite the fixture into a high-renewable, low-thermal commitment case."""
    write_dynamic_instance(8)
    cfg = load_config()
    cfg["max_committed_thermal"] = max(3, cfg["max_committed_thermal"] - 2)
    cfg["renewable_min_fraction"] = min(0.66, cfg["renewable_min_fraction"] + 0.025)
    cfg["reserve_requirement_kw"] = round(cfg["reserve_requirement_kw"] * 1.05, 2)
    cfg["emission_budget"] = round(cfg["emission_budget"] * 0.98, 2)
    cfg["per_bus_min_kw"] = {b: round(v * 1.08, 2) for b, v in cfg["per_bus_min_kw"].items()}
    (INPUT / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")


class TestInputIntegrity:
    def test_units_hash(self):
        """Verify units.jsonl SHA-256 matches the pinned value."""
        h = hashlib.sha256((INPUT / "units.jsonl").read_bytes()).hexdigest()
        assert h == INPUT_HASHES["units.jsonl"]

    def test_config_hash(self):
        """Verify config.json SHA-256 matches the pinned value."""
        h = hashlib.sha256((INPUT / "config.json").read_bytes()).hexdigest()
        assert h == INPUT_HASHES["config.json"]


class TestModelIntegrity:
    def test_model_script_not_tampered(self):
        """Verify model.py has not been modified."""
        h = hashlib.sha256(Path("/app/task_file/scripts/model.py").read_bytes()).hexdigest()
        assert h == MODEL_PY_SHA256, "model.py has been modified — do not edit scoring files"


class TestOutputExists:
    def test_output_file_exists(self):
        """Verify dispatch.json exists in output_data/."""
        assert (OUTPUT / "dispatch.json").exists()


class TestOutputSchema:
    def test_plan_is_object(self):
        """Verify the plan is a JSON object with the two required keys."""
        plan = load_plan()
        assert isinstance(plan, dict)
        assert "allocations" in plan and "frequency_setpoint" in plan

    def test_allocations_cover_all_units_uniquely(self):
        """Verify every unit appears exactly once with in-range fractions."""
        plan = load_plan()
        allocs = plan["allocations"]
        assert isinstance(allocs, list)
        ids = [a["unit_id"] for a in allocs]
        unit_ids = {u["id"] for u in load_units()}
        assert len(ids) == len(set(ids)), "duplicate unit_id entries"
        assert set(ids) == unit_ids, "allocations must cover every unit exactly once"
        for a in allocs:
            assert 0.0 <= a["dispatch_fraction"] <= 1.0, f"dispatch_fraction out of range: {a}"
            assert 0.0 <= a["reserve_share"] <= 1.0, f"reserve_share out of range: {a}"

    def test_frequency_setpoint_in_range(self):
        """Verify frequency_setpoint is a number within [49.0, 51.0]."""
        plan = load_plan()
        fs = plan["frequency_setpoint"]
        assert isinstance(fs, (int, float)) and not isinstance(fs, bool)
        assert 49.0 <= float(fs) <= 51.0


class TestHardConstraints:
    def test_mandatory_units_online(self):
        """Verify every mandatory unit runs at or above its min_stable."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        for uid in cfg["mandatory_online_units"]:
            assert am[uid]["dispatch_fraction"] >= u_map[uid]["min_stable"] - 1e-9, (
                f"mandatory unit {uid} below min_stable"
            )

    def test_supply_meets_demand_without_gross_oversupply(self):
        """Verify served output covers demand and stays within the oversupply cap."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        supply = sum(u_map[uid]["capacity_kw"] * u_map[uid]["avail"] * a["dispatch_fraction"]
                     for uid, a in am.items())
        assert supply >= cfg["total_demand_kw"] - 1e-6, f"supply {supply:.0f} < demand"
        assert supply <= cfg["total_demand_kw"] * (1.0 + MAX_OVERSUPPLY) + 1e-6, "gross oversupply"

    def test_emissions_within_budget(self):
        """Verify total emissions stay within the emission budget."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        emis = 0.0
        for uid, a in am.items():
            u = u_map[uid]
            out = u["capacity_kw"] * u["avail"] * a["dispatch_fraction"]
            emis += u["emission_rate"] * out * (1.0 + HEAT_CURVE * a["dispatch_fraction"])
        assert emis <= cfg["emission_budget"] + 1e-6, f"emissions {emis:.1f} > budget"

    def test_renewable_minimum(self):
        """Verify the renewable share of served output meets the minimum."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        supply = 0.0
        renew = 0.0
        for uid, a in am.items():
            u = u_map[uid]
            out = u["capacity_kw"] * u["avail"] * a["dispatch_fraction"]
            supply += out
            if u["fuel"] in RENEWABLE:
                renew += out
        assert renew / max(supply, 1e-9) >= cfg["renewable_min_fraction"] - 1e-9, "renewable share too low"

    def test_per_bus_minimums(self):
        """Verify every bus clears its local minimum supply."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        bus_out = {b: 0.0 for b in cfg["buses"]}
        for uid, a in am.items():
            u = u_map[uid]
            bus_out[u["bus"]] += u["capacity_kw"] * u["avail"] * a["dispatch_fraction"]
        for b, need in cfg["per_bus_min_kw"].items():
            assert bus_out.get(b, 0.0) >= need - 1e-6, f"bus {b} below local minimum"

    def test_reserve_requirement(self):
        """Verify total committed reserve meets the requirement."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        reserve = 0.0
        for uid, a in am.items():
            u = u_map[uid]
            headroom = u["capacity_kw"] * u["avail"] * (1.0 - a["dispatch_fraction"])
            reserve += headroom * u["responsiveness"] * a["reserve_share"]
        assert reserve >= cfg["reserve_requirement_kw"] - 1e-6, f"reserve {reserve:.0f} below requirement"

    def test_no_conflict_pair_dispatched_hard(self):
        """Verify no feeder conflict pair has both units dispatched above 0.5."""
        cfg = load_config()
        am = alloc_map(load_plan())
        for a, b in cfg["conflict_pairs"]:
            assert not (am[a]["dispatch_fraction"] > 0.5 and am[b]["dispatch_fraction"] > 0.5), (
                f"conflict pair both dispatched hard: {a}, {b}"
            )

    def test_thermal_commitment_cap(self):
        """Verify no more than max_committed_thermal gas/diesel units are dispatched."""
        cfg = load_config()
        u_map = {u["id"]: u for u in load_units()}
        am = alloc_map(load_plan())
        committed = sum(
            1 for uid, a in am.items()
            if u_map[uid]["fuel"] in {"gas", "diesel"} and a["dispatch_fraction"] > 1e-6
        )
        assert committed <= cfg["max_committed_thermal"], (
            f"committed thermal units {committed} exceed cap {cfg['max_committed_thermal']}"
        )


class TestScoreThreshold:
    def test_total_score(self):
        """Verify total_score meets the required threshold."""
        result = base_evaluate(str(INPUT), str(OUTPUT))
        assert "error" not in result, result.get("error")
        assert result["total_score"] >= 0.99, f"score too low: {result['total_score']}"

    def test_primary_subscores(self):
        """Verify the primary quality metrics each clear their floors."""
        result = base_evaluate(str(INPUT), str(OUTPUT))
        assert "error" not in result, result.get("error")
        assert result["service_score"] >= 0.95, f"service too low: {result['service_score']}"
        assert result["efficiency_score"] >= 0.86, f"efficiency too low: {result['efficiency_score']}"
        assert result["stability_score"] >= 0.95, f"stability too low: {result['stability_score']}"
        assert result["renewable_fraction"] >= 0.60, (
            f"renewable fraction too low: {result['renewable_fraction']}"
        )
        assert result["freq_gap"] <= 0.02, f"frequency setpoint too far from settled frequency: {result['freq_gap']}"
        assert result["degraded_output"] <= 800.0, f"degraded output too high: {result['degraded_output']}"


class TestStrictScore:
    def test_strict_score(self):
        """Verify the strict score clears its threshold."""
        result = strict_evaluate(str(INPUT), str(OUTPUT))
        assert "error" not in result, result.get("error")
        assert result["total_score_strict"] >= 0.92, (
            f"strict score {result['total_score_strict']} < 0.92 (dispatch quality gates not met)"
        )


class TestRustImplementation:
    def test_cargo_toml_exists(self):
        """Verify a Cargo.toml exists, confirming a Rust solution."""
        assert len(list(Path("/app").rglob("Cargo.toml"))) >= 1, "No Cargo.toml found"

    def test_compiled_binary_exists(self):
        """Verify a compiled release binary exists in target/release/."""
        targets = list(Path("/app").rglob("target/release/*"))
        bins = [f for f in targets if f.is_file() and os.access(f, os.X_OK)
                and "deps" not in f.parts and "build" not in f.parts and not f.suffix]
        assert len(bins) >= 1, "No compiled Rust binary found in target/release/"

    def test_binary_produces_output(self):
        """Verify the compiled binary runs, writes dispatch.json, and produces a passing score."""
        import subprocess
        binary = release_binary()
        fresh = OUTPUT / "dispatch.json"
        if fresh.exists():
            fresh.unlink()
        result = subprocess.run([str(binary)], env={**os.environ, "HOME": "/root"},
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, f"Binary exited {result.returncode}: {result.stderr[:300]}"
        assert fresh.exists(), "Binary did not write dispatch.json"
        r = base_evaluate(str(INPUT), str(OUTPUT))
        assert r["total_score"] >= 0.99, f"Binary fresh output score too low: {r['total_score']}"

    def test_dynamic_input_not_hardcoded(self):
        """Verify the binary re-optimizes several renamed alternate dispatch instances."""
        import subprocess
        units_path = INPUT / "units.jsonl"
        cfg_path = INPUT / "config.json"
        units_backup = units_path.read_text()
        cfg_backup = cfg_path.read_text()
        output_backup = (OUTPUT / "dispatch.json").read_text() if (OUTPUT / "dispatch.json").exists() else None
        binary = release_binary()
        try:
            for seed in (1, 2, 3, 4, 5):
                write_dynamic_instance(seed)
                fresh = OUTPUT / "dispatch.json"
                if fresh.exists():
                    fresh.unlink()
                run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
                assert run.returncode == 0, f"Binary exited {run.returncode}: {run.stderr[:300]}"
                raw = base_evaluate(str(INPUT), str(OUTPUT))
                assert "error" not in raw, raw.get("error")
                assert raw["total_score"] >= 0.985, f"dynamic raw score too low for seed {seed}: {raw}"
                strict = strict_evaluate(str(INPUT), str(OUTPUT))
                assert strict["total_score_strict"] >= 0.91, (
                    f"dynamic strict score too low for seed {seed}: {strict}"
                )
        finally:
            units_path.write_text(units_backup)
            cfg_path.write_text(cfg_backup)
            if output_backup is None:
                try:
                    (OUTPUT / "dispatch.json").unlink()
                except FileNotFoundError:
                    pass
            else:
                (OUTPUT / "dispatch.json").write_text(output_backup)

    def test_tight_commitment_input_not_hardcoded(self):
        """Verify the binary handles a tighter commitment and renewable mix."""
        import subprocess
        units_path = INPUT / "units.jsonl"
        cfg_path = INPUT / "config.json"
        units_backup = units_path.read_text()
        cfg_backup = cfg_path.read_text()
        output_backup = (OUTPUT / "dispatch.json").read_text() if (OUTPUT / "dispatch.json").exists() else None
        binary = release_binary()
        try:
            write_tight_commitment_instance()
            fresh = OUTPUT / "dispatch.json"
            if fresh.exists():
                fresh.unlink()
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
            assert run.returncode == 0, f"Binary exited {run.returncode}: {run.stderr[:300]}"
            raw = base_evaluate(str(INPUT), str(OUTPUT))
            assert "error" not in raw, raw.get("error")
            assert raw["total_score"] >= 0.99, f"tight commitment raw score too low: {raw}"
            assert raw["renewable_fraction"] >= 0.70, f"renewable share too low: {raw}"
            assert raw["committed_thermal"] <= load_config()["max_committed_thermal"], (
                f"too many committed thermal units: {raw}"
            )
            strict = strict_evaluate(str(INPUT), str(OUTPUT))
            assert strict["total_score_strict"] >= 0.92, (
                f"tight commitment strict score too low: {strict}"
            )
        finally:
            units_path.write_text(units_backup)
            cfg_path.write_text(cfg_backup)
            if output_backup is None:
                try:
                    (OUTPUT / "dispatch.json").unlink()
                except FileNotFoundError:
                    pass
            else:
                (OUTPUT / "dispatch.json").write_text(output_backup)
