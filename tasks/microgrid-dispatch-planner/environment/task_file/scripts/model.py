import json
import math
from pathlib import Path


# ---- scoring constants ----
HEAT_CURVE = 0.6          # convexity of emissions in dispatch fraction
FREQ_GAIN = 8.0           # Hz of drift per unit of supply/demand imbalance
DAMP = 1.1                # how strongly committed reserve damps frequency drift
DROOP = 0.5               # Hz of frequency droop at zero synchronous inertia
FREQ_TOL = 0.12           # Hz tolerance band of the stability response
JITTER = 0.05             # Hz of instability added per near-conflict feeder pair
SYNC_FUELS = {"gas", "diesel"}   # synchronous (spinning) sources that carry inertia
NEAR_LO, NEAR_HI = 0.40, 0.50
OVERSUPPLY_SPAN = 0.20    # oversupply fraction that maps service_score to 0
MAX_OVERSUPPLY = 0.25     # hard cap on oversupply
EMIS_TARGET = 2500.0      # emissions level that maps to a full efficiency score
DEG_OUTPUT_CAP = 1100.0   # degraded-unit output above this triggers a penalty
THERMAL_COMMIT_EPS = 1e-6  # a thermal unit counts as committed once dispatched above this

W_SERVICE = 0.30
W_EFFICIENCY = 0.35
W_STABILITY = 0.35

RENEWABLE = {"solar", "wind"}
FREQ_MIN, FREQ_MAX = 49.0, 51.0


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _settled_frequency(nominal, imbalance, reserve_ratio, near_conflicts, inertia_frac):
    # Low synchronous inertia (a renewable/inverter-heavy mix) droops frequency;
    # a supply/demand imbalance drives it, damped by committed reserve; near-conflict
    # feeder pairs add instability.
    droop = DROOP * (1.0 - inertia_frac)
    drift = FREQ_GAIN * imbalance / (1.0 + DAMP * reserve_ratio)
    return nominal - droop + drift + JITTER * near_conflicts


def evaluate(input_dir, output_dir):
    inp = Path(input_dir)
    out = Path(output_dir)
    try:
        units = load_jsonl(inp / "units.jsonl")
        config = json.loads((inp / "config.json").read_text())
        dispatch = json.loads((out / "dispatch.json").read_text())
    except Exception as e:
        return {"total_score": 0.0, "error": f"load failure: {e}"}

    u_map = {u["id"]: u for u in units}

    if not isinstance(dispatch, dict):
        return {"total_score": 0.0, "error": "dispatch.json must be a JSON object"}
    allocs = dispatch.get("allocations")
    fset = dispatch.get("frequency_setpoint")
    if not isinstance(allocs, list):
        return {"total_score": 0.0, "error": "allocations must be a list"}
    if not isinstance(fset, (int, float)) or isinstance(fset, bool):
        return {"total_score": 0.0, "error": "frequency_setpoint must be a number"}
    fset = float(fset)
    if fset < FREQ_MIN or fset > FREQ_MAX:
        return {"total_score": 0.0, "error": f"frequency_setpoint {fset} out of [{FREQ_MIN}, {FREQ_MAX}]"}

    f = {}
    r = {}
    seen = set()
    for a in allocs:
        uid = a.get("unit_id")
        if uid not in u_map:
            return {"total_score": 0.0, "error": f"unknown unit_id: {uid}"}
        if uid in seen:
            return {"total_score": 0.0, "error": f"duplicate unit_id: {uid}"}
        seen.add(uid)
        df = a.get("dispatch_fraction")
        rs = a.get("reserve_share")
        if not isinstance(df, (int, float)) or isinstance(df, bool) or not 0.0 <= df <= 1.0:
            return {"total_score": 0.0, "error": f"dispatch_fraction out of range for {uid}"}
        if not isinstance(rs, (int, float)) or isinstance(rs, bool) or not 0.0 <= rs <= 1.0:
            return {"total_score": 0.0, "error": f"reserve_share out of range for {uid}"}
        f[uid] = float(df)
        r[uid] = float(rs)
    if seen != set(u_map):
        return {"total_score": 0.0, "error": f"allocations must cover all {len(u_map)} units (missing {len(set(u_map) - seen)})"}

    # ---- derived quantities ----
    demand = config["total_demand_kw"]
    supply = 0.0
    total_emissions = 0.0
    renewable_output = 0.0
    total_reserve = 0.0
    bus_output = {b: 0.0 for b in config["buses"]}
    degraded_output = 0.0
    sync_output = 0.0
    committed_thermal = 0
    for uid, u in u_map.items():
        avail_cap = u["capacity_kw"] * u["avail"]
        out_kw = avail_cap * f[uid]
        supply += out_kw
        bus_output[u["bus"]] += out_kw
        total_emissions += u["emission_rate"] * out_kw * (1.0 + HEAT_CURVE * f[uid])
        if u["fuel"] in RENEWABLE:
            renewable_output += out_kw
        if u["fuel"] in SYNC_FUELS:
            sync_output += out_kw
            if f[uid] > THERMAL_COMMIT_EPS:
                committed_thermal += 1
        if u.get("degraded"):
            degraded_output += out_kw
        headroom = avail_cap * (1.0 - f[uid])
        total_reserve += headroom * u["responsiveness"] * r[uid]

    # ---- hard constraints ----
    for uid in config["mandatory_online_units"]:
        if f.get(uid, 0.0) < u_map[uid]["min_stable"] - 1e-9:
            return {"total_score": 0.0, "error": f"mandatory unit {uid} below min_stable"}

    if supply < demand:
        return {"total_score": 0.0, "error": f"supply {supply:.0f} < demand {demand}"}
    if supply > demand * (1.0 + MAX_OVERSUPPLY):
        return {"total_score": 0.0, "error": f"supply {supply:.0f} exceeds oversupply cap"}
    if total_emissions > config["emission_budget"]:
        return {"total_score": 0.0, "error": f"emissions {total_emissions:.1f} > budget {config['emission_budget']}"}
    renewable_fraction = renewable_output / max(supply, 1e-9)
    if renewable_fraction < config["renewable_min_fraction"]:
        return {"total_score": 0.0, "error": f"renewable fraction {renewable_fraction:.3f} < min"}
    for b, need in config["per_bus_min_kw"].items():
        if bus_output.get(b, 0.0) < need - 1e-9:
            return {"total_score": 0.0, "error": f"bus {b} output {bus_output.get(b, 0.0):.0f} < min {need}"}
    if total_reserve < config["reserve_requirement_kw"]:
        return {"total_score": 0.0, "error": f"reserve {total_reserve:.0f} < requirement {config['reserve_requirement_kw']}"}
    for a, b in config["conflict_pairs"]:
        if f.get(a, 0.0) > 0.5 and f.get(b, 0.0) > 0.5:
            return {"total_score": 0.0, "error": f"conflict pair both dispatched hard: {a}, {b}"}
    # Only a limited number of synchronous (gas/diesel) generators can be brought
    # online and dispatched this period — a unit-commitment limit. Units held purely
    # as standby reserve (dispatch_fraction == 0) do not count against it.
    max_thermal = config.get("max_committed_thermal")
    if max_thermal is not None and committed_thermal > max_thermal:
        return {"total_score": 0.0,
                "error": f"committed thermal units {committed_thermal} exceed cap {max_thermal}"}

    # ---- soft scoring ----
    excess = max(0.0, supply / demand - 1.0)
    service_score = max(0.0, 1.0 - excess / OVERSUPPLY_SPAN)

    efficiency_score = max(0.0, min(1.0, EMIS_TARGET / max(total_emissions, 1e-9)))

    near_conflicts = 0
    for a, b in config["conflict_pairs"]:
        if NEAR_LO <= f.get(a, 0.0) <= NEAR_HI and NEAR_LO <= f.get(b, 0.0) <= NEAR_HI:
            near_conflicts += 1
    imbalance = (supply - demand) / demand
    reserve_ratio = min(1.5, total_reserve / max(config["reserve_requirement_kw"], 1e-9))
    inertia_frac = sync_output / max(supply, 1e-9)
    settled = _settled_frequency(config["nominal_frequency"], imbalance, reserve_ratio, near_conflicts, inertia_frac)
    stability_raw = math.exp(-((fset - settled) / FREQ_TOL) ** 2)
    stability_score = stability_raw * min(1.0, 0.5 + 0.5 * reserve_ratio)

    total = (
        W_SERVICE * service_score
        + W_EFFICIENCY * efficiency_score
        + W_STABILITY * stability_score
    )

    # Leaning on near-conflict feeder pairs erodes the whole plan.
    if near_conflicts > 0:
        total *= 0.92 ** min(near_conflicts, 5)
    # Running degraded units hard wastes the emission budget.
    if degraded_output > DEG_OUTPUT_CAP:
        total *= 0.85
    # A tightly balanced, well-tuned, renewable-heavy plan earns a small bonus.
    if excess < 0.03 and abs(fset - settled) < 0.02 and renewable_fraction > 0.45:
        total *= 1.05

    total = max(0.0, min(1.0, total))
    return {
        "total_score": round(total, 4),
        "service_score": round(service_score, 4),
        "efficiency_score": round(efficiency_score, 4),
        "stability_score": round(stability_score, 4),
        "settled_frequency": round(settled, 4),
        "frequency_setpoint": round(fset, 4),
        "freq_gap": round(abs(fset - settled), 4),
        "supply": round(supply, 1),
        "oversupply_pct": round(excess * 100, 2),
        "total_emissions": round(total_emissions, 1),
        "renewable_fraction": round(renewable_fraction, 4),
        "reserve": round(total_reserve, 1),
        "reserve_ratio": round(reserve_ratio, 3),
        "near_conflicts": near_conflicts,
        "degraded_output": round(degraded_output, 1),
        "committed_thermal": committed_thermal,
    }
