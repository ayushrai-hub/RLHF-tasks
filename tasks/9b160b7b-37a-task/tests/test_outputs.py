import hashlib
import json
import math
import os
import subprocess
import tempfile


TASK = os.environ.get("TASK_FILE", "/app/task_file")
CASES = os.path.join(TASK, "input_data", "cases.json")
BIN = os.path.join(TASK, "target", "release", "radiocal")
CASES_SHA256 = "4dcba06b9c3bb9e08e3d3ebf4439ad07b65ae1ca55f4ed634eeab0da78902a5f"

ATOL = 2e-8
RTOL = 2e-8

CHI2_95 = {
    1: 3.841458820694124,
    2: 5.991464547107979,
    3: 7.814727903251179,
    4: 9.487729036781154,
    5: 11.070497693516351,
    6: 12.591587243743977,
    7: 14.067140449340169,
    8: 15.50731305586545,
    9: 16.918977604620448,
    10: 18.307038053275146,
}


def finite_number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def parse_curve(rows):
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError("bad curve")
    curve = []
    prev = -math.inf
    for row in rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("bad curve row")
        cal_bp, c14_bp, sigma = row
        if not all(finite_number(x) for x in [cal_bp, c14_bp, sigma]):
            raise ValueError("bad curve row")
        if sigma <= 0 or cal_bp <= prev:
            raise ValueError("bad curve row")
        curve.append((float(cal_bp), float(c14_bp), float(sigma)))
        prev = cal_bp
    return curve


def interpolate_parsed_ref(curve, cal_bp):
    if not finite_number(cal_bp):
        raise ValueError("bad cal_bp")
    cal_bp = float(cal_bp)
    if cal_bp < curve[0][0] or cal_bp > curve[-1][0]:
        raise ValueError("outside curve")
    for lo, hi in zip(curve, curve[1:]):
        if cal_bp <= hi[0]:
            t = (cal_bp - lo[0]) / (hi[0] - lo[0])
            return {
                "c14_bp": lo[1] + t * (hi[1] - lo[1]),
                "sigma": lo[2] + t * (hi[2] - lo[2]),
            }
    return {"c14_bp": curve[-1][1], "sigma": curve[-1][2]}


def interpolate_ref(curve_rows, cal_bp):
    return interpolate_parsed_ref(parse_curve(curve_rows), cal_bp)


def build_wave_curve(start, end, step=1, drift=1.0, phase=0.0):
    rows = []
    cal = float(start)
    while cal <= end + 1e-12:
        wave = 28.0 * math.sin((cal + phase) / 37.0) + 14.0 * math.cos((cal + phase) / 43.0)
        c14 = drift * cal + 620.0 + wave
        sigma = 11.0 + 0.0015 * (cal - start) + 3.0 * math.cos((cal + phase) / 73.0) ** 2
        rows.append([cal, c14, sigma])
        cal += step
    return rows


def sample_series_from_curve(curve, indices, lab_sigma=18.0, reservoir_age=0.0, reservoir_sigma=4.0):
    out = []
    for idx, age_bias in indices:
        out.append(
            {
                "lab_age_bp": curve[idx][1] + age_bias,
                "lab_sigma": lab_sigma,
                "reservoir_age": reservoir_age,
                "reservoir_sigma": reservoir_sigma,
            }
        )
    return out


def wiggle_samples_from_curve(curve, offsets, lab_sigma=18.0, reservoir_age=0.0, reservoir_sigma=4.0):
    samples = []
    for offset, idx in offsets:
        samples.append(
            {
                "offset": float(offset),
                "lab_age_bp": curve[idx][1],
                "lab_sigma": lab_sigma,
                "reservoir_age": reservoir_age,
                "reservoir_sigma": reservoir_sigma,
            }
        )
    return samples


def calibration_ref(op):
    lab_age = op["lab_age_bp"]
    lab_sigma = op["lab_sigma"]
    reservoir_age = op["reservoir_age"]
    reservoir_sigma = op["reservoir_sigma"]
    start = op["start_cal_bp"]
    end = op["end_cal_bp"]
    step = op["step"]
    if not all(finite_number(x) for x in [lab_age, lab_sigma, reservoir_age, reservoir_sigma, start, end, step]):
        raise ValueError("bad calibration number")
    if lab_sigma <= 0 or reservoir_sigma < 0 or start > end or step <= 0 or int(step) != step:
        raise ValueError("bad calibration domain")

    corrected = lab_age - reservoir_age
    log_weights = []
    x = float(start)
    while x <= end + 1e-12:
        c = interpolate_ref(op["curve"], x)
        var = lab_sigma * lab_sigma + c["sigma"] * c["sigma"] + reservoir_sigma * reservoir_sigma
        if var <= 0 or not math.isfinite(var):
            raise ValueError("bad variance")
        diff = corrected - c["c14_bp"]
        logw = -0.5 * diff * diff / var - 0.5 * math.log(2.0 * math.pi * var)
        log_weights.append((x, logw))
        x += step
    if not log_weights:
        raise ValueError("empty grid")

    max_log = max(w for _, w in log_weights)
    weights = [(x, math.exp(w - max_log)) for x, w in log_weights]
    total = sum(w for _, w in weights)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad total")

    points = [[x, w / total] for x, w in weights]
    mean = sum(x * p for x, p in points)
    best = max(p for _, p in points)
    mode = min(x for x, p in points if p == best)
    return {"points": points, "mean_cal_bp": mean, "mode_cal_bp": mode}


def hpd_reports(cal, levels, step):
    reports = []
    for level in levels:
        if not finite_number(level) or level <= 0 or level > 1:
            raise ValueError("bad level")
        order = sorted(range(len(cal["points"])), key=lambda i: (-cal["points"][i][1], cal["points"][i][0]))
        selected = [False] * len(cal["points"])
        mass = 0.0
        for idx in order:
            if mass >= level:
                break
            selected[idx] = True
            mass += cal["points"][idx][1]
        ranges = []
        current = None
        for is_selected, (cal_bp, _prob) in zip(selected, cal["points"]):
            if not is_selected:
                continue
            if current is not None and abs(cal_bp - current[1] - step) <= 1e-9:
                current[1] = cal_bp
            else:
                if current is not None:
                    ranges.append(current)
                current = [cal_bp, cal_bp]
        if current is not None:
            ranges.append(current)
        reports.append({"level": level, "ranges": ranges, "mass": mass})
    return reports


def hpd_ref(op):
    levels = op["levels"]
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    cal = calibration_ref(op)
    return {
        "points": cal["points"],
        "mean_cal_bp": cal["mean_cal_bp"],
        "mode_cal_bp": cal["mode_cal_bp"],
        "intervals": hpd_reports(cal, levels, op["step"]),
    }


def curve_mixture_ref(op):
    models = op["curves"]
    levels = op["levels"]
    lab_age = op["lab_age_bp"]
    lab_sigma = op["lab_sigma"]
    reservoir_age = op["reservoir_age"]
    reservoir_sigma = op["reservoir_sigma"]
    start = op["start_cal_bp"]
    end = op["end_cal_bp"]
    step = op["step"]
    if not isinstance(models, list) or not 2 <= len(models) <= 5:
        raise ValueError("bad curve model count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    if not all(finite_number(x) for x in [lab_age, lab_sigma, reservoir_age, reservoir_sigma, start, end, step]):
        raise ValueError("bad curve mixture number")
    if lab_sigma <= 0 or reservoir_sigma < 0 or start > end or step <= 0 or int(step) != step:
        raise ValueError("bad curve mixture domain")
    for level in levels:
        if not finite_number(level) or level <= 0 or level > 1:
            raise ValueError("bad level")

    parsed_models = []
    for model in models:
        weight = model["weight"]
        if not finite_number(weight) or weight <= 0:
            raise ValueError("bad curve model weight")
        parsed_models.append((float(weight), parse_curve(model["curve"])))

    grid = []
    x = float(start)
    while x <= end + 1e-12:
        grid.append(x)
        x += step
    if not grid:
        raise ValueError("empty grid")

    corrected = lab_age - reservoir_age
    covered = [False] * len(grid)
    log_weights = []
    for model_idx, (weight, curve) in enumerate(parsed_models):
        log_prior = math.log(weight)
        for grid_idx, cal_bp in enumerate(grid):
            try:
                c = interpolate_parsed_ref(curve, cal_bp)
            except ValueError:
                continue
            covered[grid_idx] = True
            var = lab_sigma * lab_sigma + c["sigma"] * c["sigma"] + reservoir_sigma * reservoir_sigma
            if var <= 0 or not math.isfinite(var):
                raise ValueError("bad curve mixture variance")
            diff = corrected - c["c14_bp"]
            logw = log_prior - 0.5 * diff * diff / var - 0.5 * math.log(2.0 * math.pi * var)
            log_weights.append((model_idx, grid_idx, logw))
    if not all(covered):
        raise ValueError("uncovered curve mixture grid point")
    if not log_weights:
        raise ValueError("empty curve mixture posterior")

    max_log = max(w for _m, _g, w in log_weights)
    weights = [(m, g, math.exp(w - max_log)) for m, g, w in log_weights]
    total = sum(w for _m, _g, w in weights)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad curve mixture total")

    calendar_probs = [0.0] * len(grid)
    curve_probs = [0.0] * len(parsed_models)
    joint = []
    for model_idx, grid_idx, weight in weights:
        prob = weight / total
        calendar_probs[grid_idx] += prob
        curve_probs[model_idx] += prob
        joint.append([model_idx, grid[grid_idx], prob])

    points = [[cal_bp, prob] for cal_bp, prob in zip(grid, calendar_probs)]
    mean = sum(x * p for x, p in points)
    best = max(p for _x, p in points)
    mode = min(x for x, p in points if p == best)
    cal = {"points": points}
    return {
        "joint": joint,
        "points": points,
        "mean_cal_bp": mean,
        "mode_cal_bp": mode,
        "curve_posteriors": [[idx, prob] for idx, prob in enumerate(curve_probs)],
        "intervals": hpd_reports(cal, levels, step),
    }


def combine_ref(op):
    dets = op["determinations"]
    if not isinstance(dets, list) or not 1 <= len(dets) <= 11:
        raise ValueError("bad determination count")
    values = []
    for det in dets:
        age = det["age_bp"]
        sigma = det["sigma"]
        reservoir_age = det["reservoir_age"]
        reservoir_sigma = det["reservoir_sigma"]
        if not all(finite_number(x) for x in [age, sigma, reservoir_age, reservoir_sigma]):
            raise ValueError("bad determination")
        if sigma <= 0 or reservoir_sigma < 0:
            raise ValueError("bad determination")
        corrected = age - reservoir_age
        var = sigma * sigma + reservoir_sigma * reservoir_sigma
        values.append((corrected, 1.0 / var))
    weight_sum = sum(w for _, w in values)
    mean = sum(age * w for age, w in values) / weight_sum
    sigma = math.sqrt(1.0 / weight_sum)
    chi_square = sum(w * (age - mean) ** 2 for age, w in values)
    dof = len(values) - 1
    passes = True if dof == 0 else chi_square <= CHI2_95[dof]
    return {
        "age_bp": mean,
        "sigma": sigma,
        "chi_square": chi_square,
        "dof": dof,
        "passes": passes,
    }


def sequence_ref(op):
    samples = op["samples"]
    levels = op["levels"]
    if not isinstance(samples, list) or not 2 <= len(samples) <= 6:
        raise ValueError("bad sample count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    min_gaps = op.get("min_gaps", [0.0] * (len(samples) - 1))
    max_gaps_raw = op.get("max_gaps")
    max_gaps = max_gaps_raw if max_gaps_raw is not None else [math.inf] * (len(samples) - 1)
    if not isinstance(min_gaps, list) or len(min_gaps) != len(samples) - 1:
        raise ValueError("bad sequence minimum gaps")
    if not isinstance(max_gaps, list) or len(max_gaps) != len(samples) - 1:
        raise ValueError("bad sequence maximum gaps")
    for lo, hi in zip(min_gaps, max_gaps):
        if not finite_number(lo) or lo < 0:
            raise ValueError("bad sequence minimum gap")
        if max_gaps_raw is not None and not finite_number(hi):
            raise ValueError("bad sequence maximum gap")
        if hi < lo:
            raise ValueError("bad sequence maximum gap")
    independent = []
    for sample in samples:
        sample_op = {
            "curve": op["curve"],
            "lab_age_bp": sample["lab_age_bp"],
            "lab_sigma": sample["lab_sigma"],
            "reservoir_age": sample["reservoir_age"],
            "reservoir_sigma": sample["reservoir_sigma"],
            "start_cal_bp": op["start_cal_bp"],
            "end_cal_bp": op["end_cal_bp"],
            "step": op["step"],
        }
        independent.append(calibration_ref(sample_op))
    grid_len = len(independent[0]["points"])
    if any(len(cal["points"]) != grid_len for cal in independent):
        raise ValueError("inconsistent grids")

    probs = [[p for _x, p in cal["points"]] for cal in independent]
    n = len(samples)
    left = [[0.0] * grid_len for _ in range(n)]
    left[0] = probs[0][:]
    for s in range(1, n):
        for j in range(grid_len):
            current_bp = independent[s]["points"][j][0]
            mass = 0.0
            for k in range(grid_len):
                gap = independent[s - 1]["points"][k][0] - current_bp
                if gap + 1e-9 >= min_gaps[s - 1] and gap <= max_gaps[s - 1] + 1e-9:
                    mass += left[s - 1][k]
            left[s][j] = probs[s][j] * mass

    right = [[0.0] * grid_len for _ in range(n)]
    right[-1] = probs[-1][:]
    for s in range(n - 2, -1, -1):
        for j in range(grid_len):
            current_bp = independent[s]["points"][j][0]
            mass = 0.0
            for k in range(grid_len):
                gap = current_bp - independent[s + 1]["points"][k][0]
                if gap + 1e-9 >= min_gaps[s] and gap <= max_gaps[s] + 1e-9:
                    mass += right[s + 1][k]
            right[s][j] = probs[s][j] * mass

    total = sum(left[-1])
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad order probability")

    marginals = []
    for s, cal in enumerate(independent):
        points = []
        for j, (cal_bp, _p) in enumerate(cal["points"]):
            probability = left[s][j] * right[s][j] / probs[s][j] / total if probs[s][j] > 0 else 0.0
            points.append([cal_bp, probability])
        marginal = {
            "points": points,
            "mean_cal_bp": sum(x * p for x, p in points),
            "mode_cal_bp": min(x for x, p in points if p == max(q for _y, q in points)),
        }
        marginals.append(
            {
                "sample": s,
                "points": points,
                "mean_cal_bp": marginal["mean_cal_bp"],
                "mode_cal_bp": marginal["mode_cal_bp"],
                "intervals": hpd_reports(marginal, levels, op["step"]),
            }
        )
    return {"order_probability": total, "marginals": marginals}


def sequence_from_probability_grids(grid, probs, levels, step, min_gaps=None, max_gaps=None, allow_zero=False):
    n = len(probs)
    min_bounds = min_gaps if min_gaps is not None else [0.0] * (n - 1)
    max_bounds = max_gaps if max_gaps is not None else [math.inf] * (n - 1)
    if not isinstance(min_bounds, list) or len(min_bounds) != n - 1:
        raise ValueError("bad sequence minimum gaps")
    if not isinstance(max_bounds, list) or len(max_bounds) != n - 1:
        raise ValueError("bad sequence maximum gaps")
    for lo, hi in zip(min_bounds, max_bounds):
        if not finite_number(lo) or lo < 0:
            raise ValueError("bad sequence minimum gap")
        if max_gaps is not None and not finite_number(hi):
            raise ValueError("bad sequence maximum gap")
        if hi < lo:
            raise ValueError("bad sequence maximum gap")

    grid_len = len(grid)
    left = [[0.0] * grid_len for _ in range(n)]
    left[0] = probs[0][:]
    for s in range(1, n):
        for j, current_bp in enumerate(grid):
            mass = 0.0
            for k, older_bp in enumerate(grid):
                gap = older_bp - current_bp
                if gap + 1e-9 >= min_bounds[s - 1] and gap <= max_bounds[s - 1] + 1e-9:
                    mass += left[s - 1][k]
            left[s][j] = probs[s][j] * mass

    right = [[0.0] * grid_len for _ in range(n)]
    right[-1] = probs[-1][:]
    for s in range(n - 2, -1, -1):
        for j, current_bp in enumerate(grid):
            mass = 0.0
            for k, younger_bp in enumerate(grid):
                gap = current_bp - younger_bp
                if gap + 1e-9 >= min_bounds[s] and gap <= max_bounds[s] + 1e-9:
                    mass += right[s + 1][k]
            right[s][j] = probs[s][j] * mass

    total = sum(left[-1])
    if total < 0 or not math.isfinite(total):
        raise ValueError("bad order probability")
    if total == 0:
        if not allow_zero:
            raise ValueError("bad order probability")
        marginals = []
        for s in range(n):
            points = [[cal_bp, 0.0] for cal_bp in grid]
            cal = {"points": points}
            marginals.append(
                {
                    "sample": s,
                    "points": points,
                    "mean_cal_bp": 0.0,
                    "mode_cal_bp": grid[0],
                    "intervals": hpd_reports(cal, levels, step),
                }
            )
        return {"order_probability": 0.0, "marginals": marginals}

    marginals = []
    for s in range(n):
        points = []
        for j, cal_bp in enumerate(grid):
            probability = left[s][j] * right[s][j] / probs[s][j] / total if probs[s][j] > 0 else 0.0
            points.append([cal_bp, probability])
        marginal = {
            "points": points,
            "mean_cal_bp": sum(x * p for x, p in points),
            "mode_cal_bp": min(x for x, p in points if p == max(q for _y, q in points)),
        }
        marginals.append(
            {
                "sample": s,
                "points": points,
                "mean_cal_bp": marginal["mean_cal_bp"],
                "mode_cal_bp": marginal["mode_cal_bp"],
                "intervals": hpd_reports(marginal, levels, step),
            }
        )
    return {"order_probability": total, "marginals": marginals}


def curve_mixture_sequence_ref(op):
    models = op["curves"]
    samples = op["samples"]
    levels = op["levels"]
    if not isinstance(models, list) or not 2 <= len(models) <= 5:
        raise ValueError("bad curve model count")
    if not isinstance(samples, list) or not 2 <= len(samples) <= 6:
        raise ValueError("bad sample count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")

    start = op["start_cal_bp"]
    end = op["end_cal_bp"]
    step = op["step"]
    if not all(finite_number(x) for x in [start, end, step]):
        raise ValueError("bad curve mixture sequence grid")
    if start > end or step <= 0 or int(step) != step:
        raise ValueError("bad curve mixture sequence grid")

    grid = []
    x = float(start)
    while x <= end + 1e-12:
        grid.append(x)
        x += step
    if not grid:
        raise ValueError("empty curve mixture sequence grid")

    parsed = []
    for idx, model in enumerate(models):
        weight = model["weight"]
        if not finite_number(weight) or weight <= 0:
            raise ValueError("bad curve model weight")
        parsed.append((idx, float(weight), parse_curve(model["curve"])))

    covered = [False] * len(grid)
    for _idx, _weight, curve in parsed:
        for grid_idx, cal_bp in enumerate(grid):
            try:
                interpolate_parsed_ref(curve, cal_bp)
                covered[grid_idx] = True
            except ValueError:
                pass
    if not all(covered):
        raise ValueError("uncovered curve mixture sequence grid point")

    prior_total = sum(weight for _idx, weight, _curve in parsed)
    per_model = []
    for idx, weight, curve in parsed:
        probs = []
        for sample in samples:
            values = [sample["lab_age_bp"], sample["lab_sigma"], sample["reservoir_age"], sample["reservoir_sigma"]]
            if not all(finite_number(x) for x in values):
                raise ValueError("bad sequence sample")
            if sample["lab_sigma"] <= 0 or sample["reservoir_sigma"] < 0:
                raise ValueError("bad sequence sample")
            corrected = sample["lab_age_bp"] - sample["reservoir_age"]
            log_weights = []
            for cal_bp in grid:
                try:
                    c = interpolate_parsed_ref(curve, cal_bp)
                except ValueError:
                    log_weights.append(-math.inf)
                    continue
                var = sample["lab_sigma"] ** 2 + c["sigma"] ** 2 + sample["reservoir_sigma"] ** 2
                if var <= 0 or not math.isfinite(var):
                    raise ValueError("bad sequence variance")
                diff = corrected - c["c14_bp"]
                log_weights.append(-0.5 * diff * diff / var - 0.5 * math.log(2.0 * math.pi * var))
            max_log = max(log_weights)
            if not math.isfinite(max_log):
                raise ValueError("empty curve mixture sequence model support")
            weights = [math.exp(logw - max_log) if math.isfinite(logw) else 0.0 for logw in log_weights]
            total = sum(weights)
            if total <= 0 or not math.isfinite(total):
                raise ValueError("bad curve mixture sequence sample total")
            probs.append([w / total for w in weights])
        seq = sequence_from_probability_grids(
            grid,
            probs,
            levels,
            step,
            op.get("min_gaps"),
            op.get("max_gaps"),
            allow_zero=True,
        )
        if seq["order_probability"] < 0 or not math.isfinite(seq["order_probability"]):
            raise ValueError("bad model order probability")
        per_model.append((idx, weight, seq))
    if prior_total <= 0 or not math.isfinite(prior_total):
        raise ValueError("bad prior total")

    evidence_total = sum(weight * seq["order_probability"] for _idx, weight, seq in per_model)
    if evidence_total <= 0 or not math.isfinite(evidence_total):
        raise ValueError("bad curve mixture sequence evidence")

    sample_count = len(samples)
    mixed_probs = [[0.0 for _ in grid] for _ in range(sample_count)]
    model_rows = []
    for idx, weight, seq in per_model:
        posterior = weight * seq["order_probability"] / evidence_total
        model_rows.append([idx, seq["order_probability"], posterior])
        if len(seq["marginals"]) != sample_count:
            raise ValueError("inconsistent sequence sample count")
        for sample_idx, marginal in enumerate(seq["marginals"]):
            if [x for x, _p in marginal["points"]] != grid:
                raise ValueError("inconsistent curve mixture sequence grid")
            for grid_idx, (_x, prob) in enumerate(marginal["points"]):
                mixed_probs[sample_idx][grid_idx] += posterior * prob

    marginals = []
    for sample_idx, probs in enumerate(mixed_probs):
        points = [[cal_bp, prob] for cal_bp, prob in zip(grid, probs)]
        mean = sum(x * p for x, p in points)
        best = max(p for _x, p in points)
        mode = min(x for x, p in points if p == best)
        cal = {"points": points}
        marginals.append(
            {
                "sample": sample_idx,
                "points": points,
                "mean_cal_bp": mean,
                "mode_cal_bp": mode,
                "intervals": hpd_reports(cal, levels, op["step"]),
            }
        )

    return {
        "order_probability": evidence_total / prior_total,
        "model_order_probabilities": model_rows,
        "marginals": marginals,
    }


def wiggle_ref(op):
    samples = op["samples"]
    levels = op["levels"]
    start = op["anchor_start_bp"]
    end = op["anchor_end_bp"]
    step = op["anchor_step"]
    if not isinstance(samples, list) or not 2 <= len(samples) <= 12:
        raise ValueError("bad wiggle sample count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    if not all(finite_number(x) for x in [start, end, step]):
        raise ValueError("bad anchor grid")
    if start > end or step <= 0 or int(step) != step:
        raise ValueError("bad anchor grid")

    prev_offset = -math.inf
    for idx, sample in enumerate(samples):
        values = [
            sample["offset"],
            sample["lab_age_bp"],
            sample["lab_sigma"],
            sample["reservoir_age"],
            sample["reservoir_sigma"],
        ]
        if not all(finite_number(x) for x in values):
            raise ValueError("bad wiggle sample")
        if sample["offset"] < 0 or sample["offset"] <= prev_offset:
            raise ValueError("bad wiggle offset")
        if idx == 0 and sample["offset"] != 0:
            raise ValueError("bad wiggle offset")
        if sample["lab_sigma"] <= 0 or sample["reservoir_sigma"] < 0:
            raise ValueError("bad wiggle uncertainty")
        prev_offset = sample["offset"]

    log_weights = []
    anchor = float(start)
    while anchor <= end + 1e-12:
        logw = 0.0
        valid = True
        for sample in samples:
            cal_bp = anchor - sample["offset"]
            try:
                c = interpolate_ref(op["curve"], cal_bp)
            except ValueError:
                valid = False
                break
            corrected = sample["lab_age_bp"] - sample["reservoir_age"]
            var = sample["lab_sigma"] ** 2 + c["sigma"] ** 2 + sample["reservoir_sigma"] ** 2
            if var <= 0 or not math.isfinite(var):
                raise ValueError("bad wiggle variance")
            diff = corrected - c["c14_bp"]
            logw += -0.5 * diff * diff / var - 0.5 * math.log(2.0 * math.pi * var)
        if valid:
            log_weights.append((anchor, logw))
        anchor += step
    if not log_weights:
        raise ValueError("no valid anchors")
    max_log = max(w for _x, w in log_weights)
    weights = [(x, math.exp(w - max_log)) for x, w in log_weights]
    total = sum(w for _x, w in weights)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad wiggle total")
    points = [[x, w / total] for x, w in weights]
    mean = sum(x * p for x, p in points)
    best = max(p for _x, p in points)
    mode = min(x for x, p in points if p == best)
    anchor_cal = {"points": points}
    return {
        "points": points,
        "mean_anchor_bp": mean,
        "mode_anchor_bp": mode,
        "intervals": hpd_reports(anchor_cal, levels, step),
        "sample_calendar": [
            {
                "sample": idx,
                "mean_cal_bp": mean - sample["offset"],
                "mode_cal_bp": mode - sample["offset"],
            }
            for idx, sample in enumerate(samples)
        ],
    }


def reservoir_wiggle_ref(op):
    samples = op["samples"]
    levels = op["levels"]
    anchor_start = op["anchor_start_bp"]
    anchor_end = op["anchor_end_bp"]
    anchor_step = op["anchor_step"]
    shift_start = op["shift_start"]
    shift_end = op["shift_end"]
    shift_step = op["shift_step"]
    if not isinstance(samples, list) or not 2 <= len(samples) <= 12:
        raise ValueError("bad reservoir wiggle sample count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    if not all(finite_number(x) for x in [anchor_start, anchor_end, anchor_step, shift_start, shift_end, shift_step]):
        raise ValueError("bad reservoir wiggle grid")
    if anchor_start > anchor_end or anchor_step <= 0 or int(anchor_step) != anchor_step:
        raise ValueError("bad anchor grid")
    if shift_start > shift_end or shift_step <= 0 or int(shift_step) != shift_step:
        raise ValueError("bad shift grid")

    prev_offset = -math.inf
    for idx, sample in enumerate(samples):
        values = [
            sample["offset"],
            sample["lab_age_bp"],
            sample["lab_sigma"],
            sample["reservoir_age"],
            sample["reservoir_sigma"],
        ]
        if not all(finite_number(x) for x in values):
            raise ValueError("bad reservoir wiggle sample")
        if sample["offset"] < 0 or sample["offset"] <= prev_offset:
            raise ValueError("bad reservoir wiggle offset")
        if idx == 0 and sample["offset"] != 0:
            raise ValueError("bad reservoir wiggle offset")
        if sample["lab_sigma"] <= 0 or sample["reservoir_sigma"] < 0:
            raise ValueError("bad reservoir wiggle uncertainty")
        prev_offset = sample["offset"]

    shift_values = []
    shift = float(shift_start)
    while shift <= shift_end + 1e-12:
        shift_values.append(shift)
        shift += shift_step
    if not shift_values:
        raise ValueError("empty shift grid")

    anchor_values = []
    log_weights = []
    anchor = float(anchor_start)
    while anchor <= anchor_end + 1e-12:
        curve_points = []
        valid_anchor = True
        for sample in samples:
            try:
                curve_points.append(interpolate_ref(op["curve"], anchor - sample["offset"]))
            except ValueError:
                valid_anchor = False
                break
        if valid_anchor:
            anchor_idx = len(anchor_values)
            anchor_values.append(anchor)
            for shift_idx, reservoir_shift in enumerate(shift_values):
                logw = 0.0
                for sample, c in zip(samples, curve_points):
                    corrected = sample["lab_age_bp"] - sample["reservoir_age"] - reservoir_shift
                    var = sample["lab_sigma"] ** 2 + c["sigma"] ** 2 + sample["reservoir_sigma"] ** 2
                    if var <= 0 or not math.isfinite(var):
                        raise ValueError("bad reservoir wiggle variance")
                    diff = corrected - c["c14_bp"]
                    logw += -0.5 * diff * diff / var - 0.5 * math.log(2.0 * math.pi * var)
                log_weights.append((anchor_idx, shift_idx, logw))
        anchor += anchor_step
    if not log_weights:
        raise ValueError("no valid reservoir wiggle pairs")

    max_log = max(w for _a, _s, w in log_weights)
    weights = [(a, s, math.exp(w - max_log)) for a, s, w in log_weights]
    total = sum(w for _a, _s, w in weights)
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad reservoir wiggle total")

    anchor_probs = [0.0] * len(anchor_values)
    shift_probs = [0.0] * len(shift_values)
    joint = []
    for anchor_idx, shift_idx, weight in weights:
        prob = weight / total
        anchor_probs[anchor_idx] += prob
        shift_probs[shift_idx] += prob
        joint.append([anchor_values[anchor_idx], shift_values[shift_idx], prob])

    anchor_dist = phase_distribution(anchor_values, anchor_probs, levels, anchor_step)
    shift_dist = phase_distribution(shift_values, shift_probs, levels, shift_step)
    return {
        "joint": joint,
        "anchor": {
            "points": anchor_dist["points"],
            "mean_anchor_bp": anchor_dist["mean"],
            "mode_anchor_bp": anchor_dist["mode"],
            "intervals": anchor_dist["intervals"],
        },
        "reservoir_shift": {
            "points": shift_dist["points"],
            "mean_years": shift_dist["mean"],
            "mode_years": shift_dist["mode"],
            "intervals": shift_dist["intervals"],
        },
        "sample_calendar": [
            {
                "sample": idx,
                "mean_cal_bp": anchor_dist["mean"] - sample["offset"],
                "mode_cal_bp": anchor_dist["mode"] - sample["offset"],
            }
            for idx, sample in enumerate(samples)
        ],
    }


def phase_distribution(values, probs, levels, step):
    points = [[value, prob] for value, prob in zip(values, probs)]
    mean = sum(x * p for x, p in points)
    best = max(p for _x, p in points)
    mode = min(x for x, p in points if p == best)
    cal = {"points": points}
    return {
        "points": points,
        "mean": mean,
        "mode": mode,
        "intervals": hpd_reports(cal, levels, step),
    }


def phase_ref(op):
    samples = op["samples"]
    levels = op["levels"]
    if not isinstance(samples, list) or not 2 <= len(samples) <= 10:
        raise ValueError("bad phase sample count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    independent = []
    for sample in samples:
        sample_op = {
            "curve": op["curve"],
            "lab_age_bp": sample["lab_age_bp"],
            "lab_sigma": sample["lab_sigma"],
            "reservoir_age": sample["reservoir_age"],
            "reservoir_sigma": sample["reservoir_sigma"],
            "start_cal_bp": op["start_cal_bp"],
            "end_cal_bp": op["end_cal_bp"],
            "step": op["step"],
        }
        independent.append(calibration_ref(sample_op))
    grid = [x for x, _p in independent[0]["points"]]
    if any([x for x, _p in cal["points"]] != grid for cal in independent):
        raise ValueError("inconsistent phase grids")

    prefixes = []
    for cal in independent:
        prefix = [0.0]
        for _x, prob in cal["points"]:
            prefix.append(prefix[-1] + prob)
        prefixes.append(prefix)

    raw_pairs = []
    total = 0.0
    n = len(grid)
    for start_idx in range(n):
        for end_idx in range(start_idx + 1):
            weight = 1.0
            for prefix in prefixes:
                weight *= max(0.0, prefix[start_idx + 1] - prefix[end_idx])
            if weight > 0 and math.isfinite(weight):
                total += weight
                raw_pairs.append((start_idx, end_idx, weight))
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad phase posterior")

    boundary_pairs = []
    start_probs = [0.0] * n
    end_probs = [0.0] * n
    span_probs = [0.0] * n
    for start_idx, end_idx, weight in raw_pairs:
        prob = weight / total
        start_probs[start_idx] += prob
        end_probs[end_idx] += prob
        span_probs[start_idx - end_idx] += prob
        boundary_pairs.append([grid[start_idx], grid[end_idx], prob])

    start_dist = phase_distribution(grid, start_probs, levels, op["step"])
    end_dist = phase_distribution(grid, end_probs, levels, op["step"])
    span_values = [i * op["step"] for i in range(n)]
    span_dist = phase_distribution(span_values, span_probs, levels, op["step"])
    return {
        "boundary_pairs": boundary_pairs,
        "start": {
            "points": start_dist["points"],
            "mean_cal_bp": start_dist["mean"],
            "mode_cal_bp": start_dist["mode"],
            "intervals": start_dist["intervals"],
        },
        "end": {
            "points": end_dist["points"],
            "mean_cal_bp": end_dist["mean"],
            "mode_cal_bp": end_dist["mode"],
            "intervals": end_dist["intervals"],
        },
        "span": {
            "points": span_dist["points"],
            "mean_years": span_dist["mean"],
            "mode_years": span_dist["mode"],
            "intervals": span_dist["intervals"],
        },
    }


def prefix_sums(values):
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    return prefix


def range_sum(prefix, lo, hi):
    if lo > hi or lo >= len(prefix) - 1:
        return 0.0
    hi = min(hi, len(prefix) - 2)
    if lo > hi:
        return 0.0
    return prefix[hi + 1] - prefix[lo]


def lower_grid_offset(years, step):
    if years <= 0:
        return 0
    return int(math.ceil((years - 1e-9) / step))


def upper_grid_offset(years, step, max_offset):
    if math.isinf(years):
        return max_offset
    return int(max(0, math.floor((years + 1e-9) / step)))


def phase_sequence_ref(op):
    phases = op["phases"]
    levels = op["levels"]
    if not isinstance(phases, list) or not 2 <= len(phases) <= 4:
        raise ValueError("bad phase sequence count")
    if not isinstance(levels, list):
        raise ValueError("bad levels")
    start = op["start_cal_bp"]
    end = op["end_cal_bp"]
    step = op["step"]
    if not all(finite_number(x) for x in [start, end, step]):
        raise ValueError("bad phase sequence grid")
    if start > end or step <= 0 or int(step) != step:
        raise ValueError("bad phase sequence grid")
    for level in levels:
        if not finite_number(level) or level <= 0 or level > 1:
            raise ValueError("bad level")

    min_gaps = op.get("min_gaps", [0.0] * (len(phases) - 1))
    max_gaps_raw = op.get("max_gaps")
    max_gaps = max_gaps_raw if max_gaps_raw is not None else [math.inf] * (len(phases) - 1)
    if not isinstance(min_gaps, list) or len(min_gaps) != len(phases) - 1:
        raise ValueError("bad phase sequence minimum gaps")
    if not isinstance(max_gaps, list) or len(max_gaps) != len(phases) - 1:
        raise ValueError("bad phase sequence maximum gaps")
    for lo, hi in zip(min_gaps, max_gaps):
        if not finite_number(lo) or lo < 0:
            raise ValueError("bad phase sequence minimum gap")
        if max_gaps_raw is not None and not finite_number(hi):
            raise ValueError("bad phase sequence maximum gap")
        if hi < lo:
            raise ValueError("bad phase sequence maximum gap")

    grid = []
    x = float(start)
    while x <= end + 1e-12:
        grid.append(x)
        x += step
    if not grid:
        raise ValueError("empty phase sequence grid")
    grid_len = len(grid)

    candidates_by_phase = []
    for phase in phases:
        samples = phase["samples"]
        if not isinstance(samples, list) or not 1 <= len(samples) <= 8:
            raise ValueError("bad phase sequence sample count")
        min_span = phase.get("min_span", 0.0)
        max_span = phase.get("max_span", math.inf)
        if not finite_number(min_span) or min_span < 0:
            raise ValueError("bad phase sequence span")
        if "max_span" in phase and not finite_number(max_span):
            raise ValueError("bad phase sequence span")
        if max_span < min_span:
            raise ValueError("bad phase sequence span")

        independent = []
        for sample in samples:
            sample_op = {
                "curve": op["curve"],
                "lab_age_bp": sample["lab_age_bp"],
                "lab_sigma": sample["lab_sigma"],
                "reservoir_age": sample["reservoir_age"],
                "reservoir_sigma": sample["reservoir_sigma"],
                "start_cal_bp": start,
                "end_cal_bp": end,
                "step": step,
            }
            independent.append(calibration_ref(sample_op))
        if any([x for x, _p in cal["points"]] != grid for cal in independent):
            raise ValueError("inconsistent phase sequence grids")

        prefixes = []
        for cal in independent:
            prefixes.append(prefix_sums([prob for _x, prob in cal["points"]]))

        candidates = []
        for start_idx in range(grid_len):
            for end_idx in range(start_idx + 1):
                span = grid[start_idx] - grid[end_idx]
                if span + 1e-9 < min_span or span > max_span + 1e-9:
                    continue
                weight = 1.0
                for prefix in prefixes:
                    weight *= max(0.0, prefix[start_idx + 1] - prefix[end_idx])
                if weight > 0 and math.isfinite(weight):
                    candidates.append((start_idx, end_idx, start_idx - end_idx, weight))
        if not candidates:
            raise ValueError("empty phase sequence candidates")
        candidates_by_phase.append(candidates)

    forward = [[candidate[3] for candidate in candidates_by_phase[0]]]
    for phase_idx in range(1, len(phases)):
        by_end = [0.0] * grid_len
        for candidate, mass in zip(candidates_by_phase[phase_idx - 1], forward[phase_idx - 1]):
            by_end[candidate[1]] += mass
        prefix = prefix_sums(by_end)
        min_offset = lower_grid_offset(min_gaps[phase_idx - 1], step)
        max_offset = upper_grid_offset(max_gaps[phase_idx - 1], step, grid_len - 1)
        current = []
        for candidate in candidates_by_phase[phase_idx]:
            lo = candidate[0] + min_offset
            hi = min(candidate[0] + max_offset, grid_len - 1)
            current.append(candidate[3] * range_sum(prefix, lo, hi))
        forward.append(current)

    total = sum(forward[-1])
    if total <= 0 or not math.isfinite(total):
        raise ValueError("bad phase sequence posterior")

    backward = [[] for _ in phases]
    backward[-1] = [candidate[3] for candidate in candidates_by_phase[-1]]
    for phase_idx in range(len(phases) - 2, -1, -1):
        by_start = [0.0] * grid_len
        for candidate, mass in zip(candidates_by_phase[phase_idx + 1], backward[phase_idx + 1]):
            by_start[candidate[0]] += mass
        prefix = prefix_sums(by_start)
        min_offset = lower_grid_offset(min_gaps[phase_idx], step)
        max_offset = upper_grid_offset(max_gaps[phase_idx], step, grid_len - 1)
        current = []
        for candidate in candidates_by_phase[phase_idx]:
            if candidate[1] >= min_offset:
                hi = candidate[1] - min_offset
                lo = max(0, candidate[1] - max_offset)
                compatible = range_sum(prefix, lo, hi)
            else:
                compatible = 0.0
            current.append(candidate[3] * compatible)
        backward[phase_idx] = current

    span_values = [i * step for i in range(grid_len)]
    phase_outputs = []
    for phase_idx, candidates in enumerate(candidates_by_phase):
        start_probs = [0.0] * grid_len
        end_probs = [0.0] * grid_len
        span_probs = [0.0] * grid_len
        for cand_idx, candidate in enumerate(candidates):
            posterior = forward[phase_idx][cand_idx] * backward[phase_idx][cand_idx] / candidate[3] / total
            if posterior > 0 and math.isfinite(posterior):
                start_probs[candidate[0]] += posterior
                end_probs[candidate[1]] += posterior
                span_probs[candidate[2]] += posterior
        start_dist = phase_distribution(grid, start_probs, levels, step)
        end_dist = phase_distribution(grid, end_probs, levels, step)
        span_dist = phase_distribution(span_values, span_probs, levels, step)
        phase_outputs.append(
            {
                "phase": phase_idx,
                "start": {
                    "points": start_dist["points"],
                    "mean_cal_bp": start_dist["mean"],
                    "mode_cal_bp": start_dist["mode"],
                    "intervals": start_dist["intervals"],
                },
                "end": {
                    "points": end_dist["points"],
                    "mean_cal_bp": end_dist["mean"],
                    "mode_cal_bp": end_dist["mode"],
                    "intervals": end_dist["intervals"],
                },
                "span": {
                    "points": span_dist["points"],
                    "mean_years": span_dist["mean"],
                    "mode_years": span_dist["mode"],
                    "intervals": span_dist["intervals"],
                },
            }
        )

    gap_posteriors = []
    for phase_idx in range(len(phases) - 1):
        left_by_end = [0.0] * grid_len
        for candidate, mass in zip(candidates_by_phase[phase_idx], forward[phase_idx]):
            left_by_end[candidate[1]] += mass
        right_by_start = [0.0] * grid_len
        for candidate, mass in zip(candidates_by_phase[phase_idx + 1], backward[phase_idx + 1]):
            right_by_start[candidate[0]] += mass

        min_offset = lower_grid_offset(min_gaps[phase_idx], step)
        max_offset = upper_grid_offset(max_gaps[phase_idx], step, grid_len - 1)
        gap_probs = [0.0] * grid_len
        for end_idx, left_mass in enumerate(left_by_end):
            if left_mass <= 0:
                continue
            min_start = max(0, end_idx - max_offset)
            if end_idx < min_offset:
                continue
            max_start = end_idx - min_offset
            for start_idx in range(min_start, max_start + 1):
                right_mass = right_by_start[start_idx]
                if right_mass > 0:
                    gap_probs[end_idx - start_idx] += left_mass * right_mass / total

        gap_dist = phase_distribution(span_values, gap_probs, levels, step)
        gap_posteriors.append(
            {
                "gap": phase_idx,
                "points": gap_dist["points"],
                "mean_years": gap_dist["mean"],
                "mode_years": gap_dist["mode"],
                "intervals": gap_dist["intervals"],
            }
        )

    return {"phases": phase_outputs, "gap_posteriors": gap_posteriors}


def reference_op(op):
    kind = op["kind"]
    if kind == "interpolate":
        return interpolate_ref(op["curve"], op["cal_bp"])
    if kind == "calibrate":
        return calibration_ref(op)
    if kind == "hpd":
        return hpd_ref(op)
    if kind == "curve_mixture_calibrate":
        return curve_mixture_ref(op)
    if kind == "combine":
        return combine_ref(op)
    if kind == "sequence":
        return sequence_ref(op)
    if kind == "curve_mixture_sequence":
        return curve_mixture_sequence_ref(op)
    if kind == "wiggle_match":
        return wiggle_ref(op)
    if kind == "reservoir_wiggle_match":
        return reservoir_wiggle_ref(op)
    if kind == "phase_bounds":
        return phase_ref(op)
    if kind == "phase_sequence":
        return phase_sequence_ref(op)
    raise ValueError("unknown kind")


def reference_cases(cases):
    out = []
    for case in cases:
        results = []
        for op in case["ops"]:
            kind = op.get("kind", "")
            try:
                results.append({"kind": kind, "output": reference_op(op), "error": False})
            except Exception:
                results.append({"kind": kind, "output": None, "error": True})
        out.append({"id": case["id"], "results": results})
    return out


def build_binary():
    env = os.environ.copy()
    env["CARGO_NET_OFFLINE"] = "true"
    proc = subprocess.run(
        ["cargo", "build", "--release", "--locked"],
        cwd=TASK,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "warning:" not in proc.stderr.lower(), proc.stderr


def run_cases(path):
    proc = subprocess.run(
        [BIN, path],
        cwd=TASK,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def assert_close(actual, expected, path="root"):
    if expected is None or isinstance(expected, (str, bool)):
        assert actual == expected, path
    elif isinstance(expected, (int, float)):
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool), path
        assert math.isfinite(actual), path
        assert abs(actual - expected) <= ATOL + RTOL * abs(expected), (path, actual, expected)
    elif isinstance(expected, list):
        assert isinstance(actual, list), path
        assert len(actual) == len(expected), path
        for i, (a_item, e_item) in enumerate(zip(actual, expected)):
            assert_close(a_item, e_item, f"{path}[{i}]")
    elif isinstance(expected, dict):
        assert isinstance(actual, dict), path
        assert set(actual) == set(expected), path
        for key in expected:
            assert_close(actual[key], expected[key], f"{path}.{key}")
    else:
        raise AssertionError(f"unsupported expected type at {path}")


def compare_results(actual, expected):
    assert len(actual) == len(expected)
    for case_idx, (a_case, e_case) in enumerate(zip(actual, expected)):
        assert a_case["id"] == e_case["id"]
        assert len(a_case["results"]) == len(e_case["results"])
        for op_idx, (a_res, e_res) in enumerate(zip(a_case["results"], e_case["results"])):
            prefix = f"case {case_idx} op {op_idx} ({e_res['kind']})"
            assert a_res["kind"] == e_res["kind"], prefix
            assert a_res["error"] == e_res["error"], prefix
            if e_res["error"]:
                assert a_res["output"] is None, prefix
            else:
                assert_close(a_res["output"], e_res["output"], prefix)


def write_temp_cases(cases):
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    with handle:
        json.dump(cases, handle)
    return handle.name


def test_sample_cases_match_documented_model():
    build_binary()
    with open(CASES, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == CASES_SHA256
    with open(CASES) as f:
        cases = json.load(f)
    compare_results(run_cases(CASES), reference_cases(cases))


def test_cli_rejects_extra_positional_arguments():
    build_binary()
    cases = [{"id": "empty", "ops": []}]
    path = write_temp_cases(cases)
    try:
        proc = subprocess.run(
            [BIN, path, path],
            cwd=TASK,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        assert proc.returncode != 0
        assert proc.stdout.strip() == ""
    finally:
        os.unlink(path)


def test_heldout_multimodal_hpd_and_replicates():
    build_binary()
    cases = [
        {
            "id": "heldout-multimodal",
            "ops": [
                {
                    "kind": "interpolate",
                    "curve": [[0, 45, 8], [40, 80, 12], [100, 160, 30], [180, 205, 14]],
                    "cal_bp": 70,
                },
                {
                    "kind": "hpd",
                    "curve": [
                        [0, 820, 18],
                        [50, 880, 20],
                        [100, 960, 22],
                        [150, 900, 18],
                        [200, 962, 24],
                        [250, 1040, 22],
                        [300, 990, 18],
                        [350, 1080, 25],
                    ],
                    "lab_age_bp": 970,
                    "lab_sigma": 18,
                    "reservoir_age": 12,
                    "reservoir_sigma": 7,
                    "start_cal_bp": 0,
                    "end_cal_bp": 350,
                    "step": 10,
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "combine",
                    "determinations": [
                        {"age_bp": 970, "sigma": 18, "reservoir_age": 12, "reservoir_sigma": 7},
                        {"age_bp": 948, "sigma": 22, "reservoir_age": -4, "reservoir_sigma": 5},
                        {"age_bp": 1005, "sigma": 27, "reservoir_age": 35, "reservoir_sigma": 11},
                        {"age_bp": 955, "sigma": 20, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                },
                {
                    "kind": "sequence",
                    "curve": [
                        [0, 820, 18],
                        [50, 880, 20],
                        [100, 960, 22],
                        [150, 900, 18],
                        [200, 962, 24],
                        [250, 1040, 22],
                        [300, 990, 18],
                        [350, 1080, 25],
                        [400, 1115, 24],
                    ],
                    "samples": [
                        {"lab_age_bp": 1070, "lab_sigma": 18, "reservoir_age": 12, "reservoir_sigma": 7},
                        {"lab_age_bp": 1005, "lab_sigma": 21, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 962, "lab_sigma": 18, "reservoir_age": -5, "reservoir_sigma": 5},
                        {"lab_age_bp": 902, "lab_sigma": 24, "reservoir_age": 20, "reservoir_sigma": 8},
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 400,
                    "step": 5,
                    "min_gaps": [15, 25, 20],
                    "max_gaps": [165, 140, 115],
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "wiggle_match",
                    "curve": [
                        [0, 710, 16],
                        [35, 762, 18],
                        [80, 805, 20],
                        [130, 845, 17],
                        [190, 940, 25],
                        [250, 905, 21],
                        [310, 1015, 19],
                        [370, 1060, 23],
                        [430, 1110, 22],
                    ],
                    "samples": [
                        {"offset": 0, "lab_age_bp": 1042, "lab_sigma": 16, "reservoir_age": 8, "reservoir_sigma": 4},
                        {"offset": 22, "lab_age_bp": 1015, "lab_sigma": 19, "reservoir_age": 7, "reservoir_sigma": 4},
                        {"offset": 57, "lab_age_bp": 968, "lab_sigma": 18, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 91, "lab_age_bp": 929, "lab_sigma": 21, "reservoir_age": -6, "reservoir_sigma": 5},
                        {"offset": 136, "lab_age_bp": 860, "lab_sigma": 20, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 174, "lab_age_bp": 804, "lab_sigma": 22, "reservoir_age": 5, "reservoir_sigma": 4},
                    ],
                    "anchor_start_bp": 180,
                    "anchor_end_bp": 420,
                    "anchor_step": 4,
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "phase_bounds",
                    "curve": [
                        [0, 710, 16],
                        [35, 762, 18],
                        [80, 805, 20],
                        [130, 845, 17],
                        [190, 940, 25],
                        [250, 905, 21],
                        [310, 1015, 19],
                        [370, 1060, 23],
                        [430, 1110, 22],
                    ],
                    "samples": [
                        {"lab_age_bp": 1075, "lab_sigma": 21, "reservoir_age": 8, "reservoir_sigma": 4},
                        {"lab_age_bp": 1010, "lab_sigma": 19, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 965, "lab_sigma": 18, "reservoir_age": -4, "reservoir_sigma": 5},
                        {"lab_age_bp": 905, "lab_sigma": 25, "reservoir_age": 15, "reservoir_sigma": 7},
                        {"lab_age_bp": 842, "lab_sigma": 22, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                    "start_cal_bp": 20,
                    "end_cal_bp": 410,
                    "step": 10,
                    "levels": [0.5, 0.8, 0.95],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_curve_mixture_calibration():
    build_binary()
    cases = [
        {
            "id": "heldout-curve-mixture",
            "ops": [
                {
                    "kind": "curve_mixture_calibrate",
                    "curves": [
                        {
                            "weight": 0.52,
                            "curve": [
                                [0, 780, 18],
                                [55, 850, 19],
                                [120, 935, 24],
                                [185, 900, 18],
                                [240, 1015, 26],
                            ],
                        },
                        {
                            "weight": 0.31,
                            "curve": [
                                [40, 805, 20],
                                [100, 890, 22],
                                [165, 970, 20],
                                [230, 945, 24],
                                [300, 1090, 25],
                            ],
                        },
                        {
                            "weight": 0.17,
                            "curve": [
                                [0, 760, 21],
                                [75, 870, 18],
                                [150, 925, 28],
                                [225, 1035, 19],
                                [300, 1075, 30],
                            ],
                        },
                    ],
                    "lab_age_bp": 968,
                    "lab_sigma": 19,
                    "reservoir_age": 14,
                    "reservoir_sigma": 6,
                    "start_cal_bp": 0,
                    "end_cal_bp": 300,
                    "step": 10,
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "curve_mixture_calibrate",
                    "curves": [
                        {
                            "weight": 4.0,
                            "curve": [
                                [80, 610, 14],
                                [160, 720, 16],
                                [240, 810, 20],
                                [320, 860, 18],
                                [400, 980, 23],
                            ],
                        },
                        {
                            "weight": 2.5,
                            "curve": [
                                [120, 650, 18],
                                [200, 760, 15],
                                [280, 790, 25],
                                [360, 930, 17],
                                [460, 1010, 21],
                            ],
                        },
                        {
                            "weight": 1.5,
                            "curve": [
                                [80, 640, 20],
                                [180, 700, 19],
                                [260, 840, 22],
                                [340, 910, 20],
                                [460, 995, 26],
                            ],
                        },
                        {
                            "weight": 0.75,
                            "curve": [
                                [80, 600, 17],
                                [140, 690, 18],
                                [240, 735, 24],
                                [340, 875, 19],
                                [460, 1030, 22],
                            ],
                        },
                        {
                            "weight": 0.25,
                            "curve": [
                                [180, 730, 16],
                                [260, 820, 21],
                                [340, 865, 18],
                                [420, 985, 24],
                                [500, 1080, 20],
                            ],
                        },
                    ],
                    "lab_age_bp": 888,
                    "lab_sigma": 17,
                    "reservoir_age": -8,
                    "reservoir_sigma": 5,
                    "start_cal_bp": 80,
                    "end_cal_bp": 460,
                    "step": 20,
                    "levels": [0.4, 0.68, 0.9],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_curve_mixture_sequence_conditioning():
    build_binary()
    base_curve = build_wave_curve(0.0, 1500.0, 2, drift=0.965, phase=21.0)
    cases = [
        {
            "id": "heldout-curve-mixture-sequence",
            "ops": [
                {
                    "kind": "curve_mixture_sequence",
                    "curves": [
                        {
                            "weight": 0.95,
                            "curve": [
                                [row[0], row[1] + 4.0 + 0.8 * math.sin((row[0] + 17.0) / 53.0), row[2] * 1.02]
                                for row in base_curve
                            ],
                        },
                        {
                            "weight": 0.72,
                            "curve": [
                                [row[0], row[1] - 11.0 + 1.1 * math.cos((row[0] + 29.0) / 47.0), row[2] * 0.98]
                                for row in base_curve
                            ],
                        },
                        {
                            "weight": 0.48,
                            "curve": [
                                [row[0], row[1] + 17.0 + 0.7 * math.sin((row[0] + 43.0) / 61.0), row[2] * 1.05]
                                for row in base_curve
                            ],
                        },
                        {
                            "weight": 0.37,
                            "curve": [
                                [row[0], row[1] - 5.0 + 0.9 * math.cos((row[0] + 11.0) / 37.0), row[2] * 0.96]
                                for row in base_curve
                            ],
                        },
                        {
                            "weight": 0.19,
                            "curve": [
                                [row[0], row[1] + 9.0 + 0.5 * math.sin((row[0] + 71.0) / 67.0), row[2] * 1.01]
                                for row in base_curve
                            ],
                        },
                    ],
                    "samples": sample_series_from_curve(
                        base_curve,
                        [
                            (690, 7.0),
                            (615, -4.0),
                            (535, 5.5),
                            (455, -6.0),
                            (365, 4.0),
                            (280, -3.0),
                        ],
                        lab_sigma=19.0,
                        reservoir_age=3.5,
                        reservoir_sigma=4.5,
                    ),
                    "start_cal_bp": 120,
                    "end_cal_bp": 1440,
                    "step": 2,
                    "min_gaps": [45, 35, 40, 30, 35],
                    "max_gaps": [190, 180, 170, 165, 150],
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "curve_mixture_sequence",
                    "curves": [
                        {
                            "weight": 1.0,
                            "curve": [[0, 700, 16], [80, 770, 18], [160, 835, 22], [240, 890, 19], [320, 985, 25]],
                        },
                        {
                            "weight": 0.65,
                            "curve": [[0, 715, 18], [80, 748, 20], [160, 860, 18], [240, 875, 23], [320, 1005, 21]],
                        },
                    ],
                    "samples": [
                        {"lab_age_bp": 966, "lab_sigma": 18, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 895, "lab_sigma": 20, "reservoir_age": 4, "reservoir_sigma": 3},
                        {"lab_age_bp": 820, "lab_sigma": 19, "reservoir_age": -5, "reservoir_sigma": 4},
                    ],
                    "start_cal_bp": 20,
                    "end_cal_bp": 300,
                    "step": 10,
                    "min_gaps": [40, 30],
                    "levels": [0.5, 0.95],
                },
                {
                    "kind": "curve_mixture_sequence",
                    "curves": [
                        {
                            "weight": 0.8,
                            "curve": [
                                [row[0], row[1] + 7.0 + 0.5 * math.sin(row[0] / 41.0), row[2] * 1.03]
                                for row in base_curve
                                if 120 <= row[0] <= 920
                            ],
                        },
                        {
                            "weight": 0.55,
                            "curve": [
                                [row[0], row[1] - 13.0 + 0.4 * math.cos(row[0] / 39.0), row[2] * 0.97]
                                for row in base_curve
                                if 500 <= row[0] <= 1440
                            ],
                        },
                        {
                            "weight": 0.35,
                            "curve": [
                                [row[0], row[1] + 3.0 + 0.7 * math.sin(row[0] / 57.0), row[2] * 1.01]
                                for row in base_curve
                                if 300 <= row[0] <= 1180
                            ],
                        },
                        {
                            "weight": 0.42,
                            "curve": [
                                [row[0], row[1] - 4.0 + 0.3 * math.cos(row[0] / 31.0), row[2] * 1.04]
                                for row in base_curve
                                if 620 <= row[0] <= 680
                            ],
                        },
                    ],
                    "samples": sample_series_from_curve(
                        base_curve,
                        [
                            (410, 4.0),
                            (350, -5.0),
                            (285, 3.5),
                        ],
                        lab_sigma=17.0,
                        reservoir_age=2.0,
                        reservoir_sigma=3.0,
                    ),
                    "start_cal_bp": 120,
                    "end_cal_bp": 1440,
                    "step": 4,
                    "min_gaps": [70, 60],
                    "max_gaps": [300, 260],
                    "levels": [0.5, 0.9],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_gap_constrained_sequences():
    build_binary()
    cases = [
        {
            "id": "heldout-sequence-gaps",
            "ops": [
                {
                    "kind": "sequence",
                    "curve": [
                        [0, 700, 15],
                        [60, 760, 18],
                        [130, 850, 21],
                        [210, 900, 17],
                        [280, 1010, 26],
                        [360, 975, 20],
                        [450, 1120, 24],
                        [540, 1185, 22],
                        [620, 1260, 28],
                    ],
                    "samples": [
                        {"lab_age_bp": 1180, "lab_sigma": 18, "reservoir_age": 10, "reservoir_sigma": 4},
                        {"lab_age_bp": 1115, "lab_sigma": 20, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 1045, "lab_sigma": 19, "reservoir_age": -8, "reservoir_sigma": 6},
                        {"lab_age_bp": 982, "lab_sigma": 22, "reservoir_age": 18, "reservoir_sigma": 7},
                        {"lab_age_bp": 895, "lab_sigma": 21, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 805, "lab_sigma": 23, "reservoir_age": 6, "reservoir_sigma": 5},
                    ],
                    "start_cal_bp": 40,
                    "end_cal_bp": 560,
                    "step": 10,
                    "min_gaps": [20, 10, 30, 15, 25],
                    "max_gaps": [130, 120, 150, 110, 100],
                    "levels": [0.4, 0.68, 0.9],
                },
                {
                    "kind": "sequence",
                    "curve": [[0, 640, 18], [80, 730, 18], [160, 760, 25], [240, 850, 19]],
                    "samples": [
                        {"lab_age_bp": 765, "lab_sigma": 16, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 742, "lab_sigma": 18, "reservoir_age": 5, "reservoir_sigma": 4},
                        {"lab_age_bp": 710, "lab_sigma": 20, "reservoir_age": -6, "reservoir_sigma": 5},
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 240,
                    "step": 10,
                    "max_gaps": [60, 80],
                    "levels": [0.5, 0.95],
                },
                {
                    "kind": "sequence",
                    "curve": [[0, 640, 18], [80, 730, 18], [160, 760, 25], [240, 850, 19]],
                    "samples": [
                        {"lab_age_bp": 815, "lab_sigma": 18, "reservoir_age": 12, "reservoir_sigma": 4},
                        {"lab_age_bp": 752, "lab_sigma": 18, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 685, "lab_sigma": 20, "reservoir_age": -10, "reservoir_sigma": 5},
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 240,
                    "step": 10,
                    "min_gaps": [40, 30],
                    "levels": [0.5, 0.95],
                },
                {
                    "kind": "sequence",
                    "curve": [[0, 100, 8], [50, 150, 8], [100, 200, 8]],
                    "samples": [
                        {"lab_age_bp": 180, "lab_sigma": 12, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 130, "lab_sigma": 12, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 100,
                    "step": 10,
                    "min_gaps": [140],
                    "levels": [0.68],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_reservoir_shift_wiggle_match():
    build_binary()
    cases = [
        {
            "id": "heldout-reservoir-wiggle",
            "ops": [
                {
                    "kind": "reservoir_wiggle_match",
                    "curve": [
                        [0, 650, 16],
                        [45, 700, 18],
                        [95, 790, 22],
                        [155, 835, 19],
                        [230, 930, 27],
                        [310, 885, 21],
                        [390, 1045, 20],
                        [470, 1110, 24],
                        [560, 1175, 23],
                    ],
                    "samples": [
                        {"offset": 0, "lab_age_bp": 1088, "lab_sigma": 17, "reservoir_age": 12, "reservoir_sigma": 5},
                        {"offset": 24, "lab_age_bp": 1057, "lab_sigma": 18, "reservoir_age": 8, "reservoir_sigma": 4},
                        {"offset": 51, "lab_age_bp": 1005, "lab_sigma": 19, "reservoir_age": -6, "reservoir_sigma": 6},
                        {"offset": 83, "lab_age_bp": 944, "lab_sigma": 20, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 121, "lab_age_bp": 895, "lab_sigma": 22, "reservoir_age": 15, "reservoir_sigma": 7},
                        {"offset": 166, "lab_age_bp": 818, "lab_sigma": 21, "reservoir_age": 2, "reservoir_sigma": 4},
                    ],
                    "anchor_start_bp": 190,
                    "anchor_end_bp": 500,
                    "anchor_step": 5,
                    "shift_start": -35,
                    "shift_end": 45,
                    "shift_step": 5,
                    "levels": [0.4, 0.68, 0.9],
                },
                {
                    "kind": "reservoir_wiggle_match",
                    "curve": [
                        [0, 410, 12],
                        [50, 480, 14],
                        [100, 505, 18],
                        [150, 590, 15],
                        [200, 640, 20],
                    ],
                    "samples": [
                        {"offset": 0, "lab_age_bp": 608, "lab_sigma": 15, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 35, "lab_age_bp": 553, "lab_sigma": 16, "reservoir_age": 4, "reservoir_sigma": 3},
                        {"offset": 75, "lab_age_bp": 488, "lab_sigma": 18, "reservoir_age": -8, "reservoir_sigma": 4},
                    ],
                    "anchor_start_bp": 20,
                    "anchor_end_bp": 190,
                    "anchor_step": 10,
                    "shift_start": -20,
                    "shift_end": 30,
                    "shift_step": 10,
                    "levels": [0.5, 0.95],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_ordered_phase_sequence_boundaries():
    build_binary()
    curve = build_wave_curve(0.0, 1200.0, 2, drift=0.97, phase=9.0)
    cases = [
        {
            "id": "heldout-phase-sequence",
            "ops": [
                {
                    "kind": "phase_sequence",
                    "curve": curve,
                    "phases": [
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(540, 5.0), (500, -4.0), (455, 3.0)],
                                lab_sigma=18.0,
                                reservoir_age=4.0,
                                reservoir_sigma=3.0,
                            ),
                            "min_span": 150,
                            "max_span": 340,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(390, -3.0), (335, 5.0), (295, -2.0)],
                                lab_sigma=19.0,
                                reservoir_age=-2.0,
                                reservoir_sigma=4.0,
                            ),
                            "min_span": 120,
                            "max_span": 310,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(230, 4.0), (180, -5.0), (130, 3.0)],
                                lab_sigma=20.0,
                                reservoir_age=3.0,
                                reservoir_sigma=5.0,
                            ),
                            "min_span": 140,
                            "max_span": 330,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(90, -2.0), (65, 4.0), (40, -3.0)],
                                lab_sigma=21.0,
                                reservoir_age=-1.0,
                                reservoir_sigma=4.0,
                            ),
                            "min_span": 70,
                            "max_span": 220,
                        },
                    ],
                    "start_cal_bp": 80,
                    "end_cal_bp": 1160,
                    "step": 2,
                    "min_gaps": [40, 50, 20],
                    "max_gaps": [230, 220, 170],
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "phase_sequence",
                    "curve": curve,
                    "phases": [
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(520, 1.0), (470, -2.0)],
                                lab_sigma=17.0,
                                reservoir_age=0.0,
                                reservoir_sigma=0.0,
                            ),
                            "min_span": 80,
                            "max_span": 260,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(310, 2.5), (260, -1.5)],
                                lab_sigma=18.0,
                                reservoir_age=5.0,
                                reservoir_sigma=4.0,
                            ),
                            "min_span": 70,
                            "max_span": 240,
                        },
                    ],
                    "start_cal_bp": 160,
                    "end_cal_bp": 1120,
                    "step": 4,
                    "min_gaps": [30],
                    "levels": [0.5, 0.9],
                },
                {
                    "kind": "phase_sequence",
                    "curve": curve,
                    "phases": [
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(420, 2.0), (385, -2.5)],
                                lab_sigma=16.0,
                                reservoir_age=1.0,
                                reservoir_sigma=2.5,
                            ),
                            "min_span": 43.5,
                            "max_span": 126.5,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(285, 3.5), (245, -1.0)],
                                lab_sigma=17.0,
                                reservoir_age=-3.0,
                                reservoir_sigma=3.0,
                            ),
                            "min_span": 37.5,
                            "max_span": 118.5,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(165, -2.0), (135, 2.5)],
                                lab_sigma=18.0,
                                reservoir_age=2.0,
                                reservoir_sigma=3.5,
                            ),
                            "min_span": 22.5,
                            "max_span": 84.5,
                        },
                    ],
                    "start_cal_bp": 80,
                    "end_cal_bp": 620,
                    "step": 10,
                    "min_gaps": [17.5, 26.5],
                    "max_gaps": [93.5, 104.5],
                    "levels": [0.5, 0.9],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_error_handling_and_incoherent_replicates():
    build_binary()
    cases = [
        {
            "id": "heldout-errors",
            "ops": [
                {
                    "kind": "calibrate",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "lab_age_bp": 30,
                    "lab_sigma": 10,
                    "reservoir_age": 0,
                    "reservoir_sigma": 0,
                    "start_cal_bp": -10,
                    "end_cal_bp": 50,
                    "step": 10,
                },
                {
                    "kind": "calibrate",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "lab_age_bp": 30,
                    "lab_sigma": 10,
                    "reservoir_age": 0,
                    "reservoir_sigma": 0,
                    "start_cal_bp": 0,
                    "end_cal_bp": 50,
                    "step": 2.5,
                },
                {
                    "kind": "combine",
                    "determinations": [
                        {"age_bp": 1000, "sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"age_bp": 1120, "sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                },
                {
                    "kind": "curve_mixture_calibrate",
                    "curves": [
                        {"weight": 0.0, "curve": [[0, 10, 4], [50, 65, 4]]},
                        {"weight": 1.0, "curve": [[0, 12, 5], [50, 67, 5]]},
                    ],
                    "lab_age_bp": 30,
                    "lab_sigma": 10,
                    "reservoir_age": 0,
                    "reservoir_sigma": 0,
                    "start_cal_bp": 0,
                    "end_cal_bp": 50,
                    "step": 10,
                    "levels": [0.68],
                },
                {
                    "kind": "curve_mixture_calibrate",
                    "curves": [
                        {"weight": 1.0, "curve": [[0, 10, 4], [30, 40, 4]]},
                        {"weight": 1.0, "curve": [[70, 80, 5], [100, 110, 5]]},
                    ],
                    "lab_age_bp": 60,
                    "lab_sigma": 10,
                    "reservoir_age": 0,
                    "reservoir_sigma": 0,
                    "start_cal_bp": 0,
                    "end_cal_bp": 100,
                    "step": 10,
                    "levels": [0.68],
                },
                {
                    "kind": "interpolate",
                    "curve": [[0, 10, 4], [0, 12, 5], [50, 65, 4]],
                    "cal_bp": 10,
                },
                {
                    "kind": "sequence",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "samples": [
                        {"lab_age_bp": 30, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 40, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": -1},
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 50,
                    "step": 10,
                    "levels": [0.68],
                },
                {
                    "kind": "sequence",
                    "curve": [[0, 10, 4], [50, 65, 4], [100, 95, 5]],
                    "samples": [
                        {"lab_age_bp": 75, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 45, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"lab_age_bp": 25, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 100,
                    "step": 10,
                    "min_gaps": [20, 40],
                    "max_gaps": [30, 35],
                    "levels": [0.68],
                },
                {
                    "kind": "wiggle_match",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "samples": [
                        {"offset": 0, "lab_age_bp": 30, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 0, "lab_age_bp": 40, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                    "anchor_start_bp": 0,
                    "anchor_end_bp": 50,
                    "anchor_step": 10,
                    "levels": [0.68],
                },
                {
                    "kind": "reservoir_wiggle_match",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "samples": [
                        {"offset": 0, "lab_age_bp": 30, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 20, "lab_age_bp": 40, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                    "anchor_start_bp": 0,
                    "anchor_end_bp": 10,
                    "anchor_step": 10,
                    "shift_start": -10,
                    "shift_end": 10,
                    "shift_step": 5,
                    "levels": [0.68],
                },
                {
                    "kind": "reservoir_wiggle_match",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "samples": [
                        {"offset": 0, "lab_age_bp": 30, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                        {"offset": 10, "lab_age_bp": 40, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0},
                    ],
                    "anchor_start_bp": 20,
                    "anchor_end_bp": 50,
                    "anchor_step": 10,
                    "shift_start": 10,
                    "shift_end": -10,
                    "shift_step": 5,
                    "levels": [0.68],
                },
                {
                    "kind": "phase_bounds",
                    "curve": [[0, 10, 4], [50, 65, 4]],
                    "samples": [
                        {"lab_age_bp": 30, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0}
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 50,
                    "step": 10,
                    "levels": [0.68],
                },
                {
                    "kind": "phase_sequence",
                    "curve": [[0, 10, 4], [50, 65, 4], [100, 110, 5]],
                    "phases": [
                        {
                            "samples": [
                                {"lab_age_bp": 95, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0}
                            ],
                            "min_span": 30,
                            "max_span": 20,
                        },
                        {
                            "samples": [
                                {"lab_age_bp": 45, "lab_sigma": 10, "reservoir_age": 0, "reservoir_sigma": 0}
                            ],
                            "min_span": 0,
                            "max_span": 30,
                        },
                    ],
                    "start_cal_bp": 0,
                    "end_cal_bp": 100,
                    "step": 10,
                    "levels": [0.68],
                },
            ],
        }
    ]
    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_scale_stress_sequence_and_phase():
    build_binary()
    curve = build_wave_curve(0.0, 2400.0, 1, drift=0.94)

    cases = [
        {
            "id": "heldout-scale-stress",
            "ops": [
                {
                    "kind": "sequence",
                    "curve": curve,
                    "samples": sample_series_from_curve(
                        curve,
                        [
                            (2200, 2.0),
                            (1975, 6.0),
                            (1740, -4.0),
                            (1480, 8.0),
                            (1220, 12.0),
                            (920, -6.0),
                        ],
                        lab_sigma=20.0,
                        reservoir_age=3.0,
                        reservoir_sigma=4.0,
                    ),
                    "start_cal_bp": 0,
                    "end_cal_bp": 2400,
                    "step": 1,
                    "min_gaps": [40, 35, 30, 25, 20],
                    "max_gaps": [420, 390, 360, 320, 280],
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "sequence",
                    "curve": curve,
                    "samples": sample_series_from_curve(
                        curve,
                        [
                            (2285, 1.5),
                            (2050, -3.0),
                            (1815, 4.5),
                            (1540, -2.0),
                            (1280, 6.0),
                            (980, -4.0),
                        ],
                        lab_sigma=19.0,
                        reservoir_age=2.0,
                        reservoir_sigma=3.0,
                    ),
                    "start_cal_bp": 0,
                    "end_cal_bp": 2400,
                    "step": 1,
                    "min_gaps": [50, 45, 40, 35, 30],
                    "max_gaps": [390, 360, 330, 300, 260],
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "phase_bounds",
                    "curve": curve,
                    "samples": sample_series_from_curve(
                        curve,
                        [
                            (2360, -1.5),
                            (2140, 2.5),
                            (1960, 0.0),
                            (1780, -2.0),
                            (1600, 3.0),
                            (1420, -3.0),
                        ],
                        lab_sigma=25.0,
                        reservoir_age=4.0,
                        reservoir_sigma=3.0,
                    ),
                    "start_cal_bp": 0,
                    "end_cal_bp": 2400,
                    "step": 5,
                    "levels": [0.5, 0.8, 0.95],
                },
                {
                    "kind": "curve_mixture_calibrate",
                    "curves": [
                        {"weight": 0.92, "curve": [[row[0], row[1] + 6.0 + 0.8 * math.sin((row[0] + 31.0) / 57.0), row[2] * 1.03] for row in curve]},
                        {"weight": 0.68, "curve": [[row[0], row[1] - 9.0 + 0.6 * math.cos((row[0] + 11.0) / 49.0), row[2] * 0.97] for row in curve]},
                        {"weight": 0.43, "curve": [[row[0], row[1] + 12.0 + 1.0 * math.sin((row[0] + 73.0) / 41.0), row[2] * 1.01] for row in curve]},
                        {"weight": 0.31, "curve": [[row[0], row[1] - 4.0 + 0.9 * math.cos((row[0] + 19.0) / 33.0), row[2] * 0.99] for row in curve]},
                        {"weight": 0.21, "curve": [[row[0], row[1] + 2.0 + 0.5 * math.sin((row[0] + 59.0) / 61.0), row[2] * 1.02] for row in curve]},
                    ],
                    "lab_age_bp": 2300.0,
                    "lab_sigma": 21.0,
                    "reservoir_age": 5.5,
                    "reservoir_sigma": 4.2,
                    "start_cal_bp": 0,
                    "end_cal_bp": 2400,
                    "step": 1,
                    "levels": [0.45, 0.75, 0.95],
                },
            ],
        }
    ]

    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_advanced_contract_scale_and_optional_bounds():
    build_binary()
    curve = build_wave_curve(0.0, 1800.0, 2, drift=0.955, phase=37.0)
    cases = [
        {
            "id": "heldout-advanced-contract-scale",
            "ops": [
                {
                    "kind": "curve_mixture_sequence",
                    "curves": [
                        {
                            "weight": 0.81,
                            "curve": [
                                [row[0], row[1] + 6.0 + 0.7 * math.sin((row[0] + 13.0) / 47.0), row[2] * 1.01]
                                for row in curve
                                if 180 <= row[0] <= 990
                            ],
                        },
                        {
                            "weight": 0.52,
                            "curve": [
                                [row[0], row[1] - 12.0 + 0.8 * math.cos((row[0] + 31.0) / 59.0), row[2] * 0.98]
                                for row in curve
                                if 690 <= row[0] <= 1650
                            ],
                        },
                        {
                            "weight": 0.44,
                            "curve": [
                                [row[0], row[1] + 3.0 + 0.6 * math.sin((row[0] + 71.0) / 53.0), row[2] * 1.04]
                                for row in curve
                                if 330 <= row[0] <= 1410
                            ],
                        },
                        {
                            "weight": 0.29,
                            "curve": [
                                [row[0], row[1] - 5.0 + 0.5 * math.cos((row[0] + 17.0) / 43.0), row[2] * 1.02]
                                for row in curve
                                if 840 <= row[0] <= 900
                            ],
                        },
                    ],
                    "samples": sample_series_from_curve(
                        curve,
                        [
                            (690, 5.5),
                            (626, -3.0),
                            (558, 4.5),
                            (491, -4.0),
                            (421, 3.0),
                            (352, -2.5),
                        ],
                        lab_sigma=18.0,
                        reservoir_age=2.5,
                        reservoir_sigma=4.0,
                    ),
                    "start_cal_bp": 180,
                    "end_cal_bp": 1650,
                    "step": 3,
                    "min_gaps": [35.5, 41.5, 32.5, 29.5, 38.5],
                    "max_gaps": [180.5, 174.5, 169.5, 157.5, 148.5],
                    "levels": [0.5, 0.6827, 0.9],
                },
                {
                    "kind": "phase_sequence",
                    "curve": curve,
                    "phases": [
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(820, 2.0), (790, -1.5), (755, 2.5), (724, -2.0), (690, 1.0), (656, -2.5), (625, 1.5), (596, -1.0)],
                                lab_sigma=21.0,
                                reservoir_age=4.0,
                                reservoir_sigma=3.0,
                            ),
                            "min_span": 120,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(535, -1.5), (506, 2.0), (478, -2.5), (449, 1.5), (421, -1.0), (394, 2.5), (366, -2.0), (339, 1.0)],
                                lab_sigma=22.0,
                                reservoir_age=-2.0,
                                reservoir_sigma=4.0,
                            ),
                            "min_span": 90,
                            "max_span": 310,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(300, 2.5), (278, -1.0), (256, 1.5), (233, -2.0), (211, 1.0), (189, -1.5), (168, 2.0), (146, -2.5)],
                                lab_sigma=23.0,
                                reservoir_age=3.0,
                                reservoir_sigma=5.0,
                            ),
                            "max_span": 260,
                        },
                        {
                            "samples": sample_series_from_curve(
                                curve,
                                [(118, -1.0), (101, 2.0), (86, -1.5), (72, 1.0), (59, -2.0), (47, 1.5), (35, -1.0), (24, 2.5)],
                                lab_sigma=24.0,
                                reservoir_age=-1.0,
                                reservoir_sigma=4.0,
                            ),
                            "min_span": 30,
                            "max_span": 180,
                        },
                    ],
                    "start_cal_bp": 40,
                    "end_cal_bp": 1720,
                    "step": 4,
                    "min_gaps": [44.5, 33.5, 21.5],
                    "levels": [0.5, 0.8, 0.95],
                },
            ],
        }
    ]

    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_heldout_precision_and_tie_breaking_rules():
    build_binary()
    cases = [
        {
            "id": "heldout-mode-ties",
            "ops": [
                {
                    "kind": "calibrate",
                    "curve": [[0, 1000, 8], [8, 1008, 8]],
                    "lab_age_bp": 1004,
                    "lab_sigma": 10,
                    "reservoir_age": 0,
                    "reservoir_sigma": 0,
                    "start_cal_bp": 0,
                    "end_cal_bp": 8,
                    "step": 4,
                },
                {
                    "kind": "hpd",
                    "curve": [[0, 1000, 8], [8, 1008, 8]],
                    "lab_age_bp": 1004,
                    "lab_sigma": 10,
                    "reservoir_age": 0,
                    "reservoir_sigma": 0,
                    "start_cal_bp": 0,
                    "end_cal_bp": 8,
                    "step": 4,
                    "levels": [0.8],
                },
            ],
        }
    ]

    path = write_temp_cases(cases)
    try:
        compare_results(run_cases(path), reference_cases(cases))
    finally:
        os.unlink(path)


def test_cargo_toml_keeps_std_only_contract():
    with open(os.path.join(TASK, "Cargo.toml")) as f:
        lines = f.readlines()
    in_deps = False
    dep_lines = []
    for raw in lines:
        line = raw.strip()
        if line == "[dependencies]":
            in_deps = True
            continue
        if in_deps and line.startswith("[") and line.endswith("]"):
            in_deps = False
        if in_deps and line and not line.startswith("#"):
            dep_lines.append(line)
    assert dep_lines == []
