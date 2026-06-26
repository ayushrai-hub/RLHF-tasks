"""Independent reference for buoy wavelet spectra pipeline."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml

import tomli

RHO = 1025.0
G = 9.81
FIXTURES = Path("/app/fixtures")
PROFILES = Path("/app/profiles")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_profile(yaml_path: Path, toml_path: Path) -> dict[str, Any]:
    y = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    t = tomli.loads(toml_path.read_text(encoding="utf-8"))
    profile = {
        "sample_rate_hz": float(y["sample_rate_hz"]),
        "reference_epoch_ms": int(y["drift"]["reference_epoch_ms"]),
        "drift_rate_pa_per_hour": float(y["drift"]["rate_pa_per_hour"]),
        "min_scale": int(y["wavelet"]["min_scale"]),
        "upper_scale": int(y["wavelet"]["upper_scale"]),
        "num_scales": int(y["wavelet"]["num_scales"]),
        "coi_factor": float(y["wavelet"]["coi_factor"]),
        "low_hz": float(y["bands"]["low_hz"]),
        "high_hz": float(y["bands"]["high_hz"]),
    }
    if "drift" in t and "rate_pa_per_hour" in t["drift"]:
        profile["drift_rate_pa_per_hour"] = float(t["drift"]["rate_pa_per_hour"])
    if "wavelet" in t and "coi_factor" in t["wavelet"]:
        profile["coi_factor"] = float(t["wavelet"]["coi_factor"])
    return profile


def read_series(path: Path) -> list[tuple[int, float, int]]:
    rows: list[tuple[int, float, int]] = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append((int(row["timestamp_ms"]), float(row["pressure_hpa"]), int(row["quality_flag"])))
    return rows


def apply_drift(rows: list[tuple[int, float, int]], profile: dict[str, Any]) -> list[float]:
    out: list[float] = []
    ref = profile["reference_epoch_ms"]
    rate = profile["drift_rate_pa_per_hour"]
    for ts, p, _ in rows:
        hours = (ts - ref) / 3_600_000.0
        out.append(p - rate * hours)
    return out


def interpolate_gaps(rows: list[tuple[int, float, int]], pressures: list[float]) -> list[float]:
    out = pressures[:]
    n = len(rows)
    for i, (_, __, flag) in enumerate(rows):
        if flag != 0:
            continue
        left = i - 1
        while left >= 0 and rows[left][2] == 0:
            left -= 1
        right = i + 1
        while right < n and rows[right][2] == 0:
            right += 1
        if left >= 0 and right < n:
            frac = (i - left) / (right - left)
            out[i] = out[left] + frac * (out[right] - out[left])
        elif left >= 0:
            out[i] = out[left]
        elif right < n:
            out[i] = out[right]
    return out


def log_scales(min_s: int, max_s: int, count: int) -> list[float]:
    log_min = math.log(min_s)
    log_max = math.log(max_s)
    return [math.exp(log_min + (i / (count - 1)) * (log_max - log_min)) for i in range(count)]


def morlet_power(eta: list[float], center: int, scale: float, sample_rate: float) -> float:
    half = int(math.ceil(scale * 2))
    total = 0.0
    cnt = 0
    for k in range(-half, half + 1):
        idx = center + k
        if idx < 0 or idx >= len(eta):
            continue
        t = k / sample_rate
        w = math.exp(-t * t / (2 * scale * scale)) * math.cos(5 * t / scale)
        total += eta[idx] * w
        cnt += 1
    return (total / cnt) ** 2 if cnt else 0.0


def analyze(pressures: list[float], profile: dict[str, Any]) -> dict[str, float]:
    mean = sum(pressures) / len(pressures)
    eta = [(p - mean) / (RHO * G) for p in pressures]
    n = len(eta)
    scales = log_scales(profile["min_scale"], profile["upper_scale"], profile["num_scales"])
    sample_rate = profile["sample_rate_hz"]
    coi_factor = profile["coi_factor"]

    time_valid = [False] * n
    for t in range(n):
        for scale in scales:
            coi_w = int(math.ceil(coi_factor * scale))
            if t >= coi_w and t < n - coi_w:
                time_valid[t] = True
                break

    max_power = -1.0
    peak_f = profile["low_hz"]
    for scale in scales:
        coi_w = int(math.ceil(coi_factor * scale))
        for t in range(coi_w, n - coi_w):
            if not time_valid[t]:
                continue
            power = morlet_power(eta, t, scale, sample_rate)
            freq = 1.0 / (scale / sample_rate)
            if profile["low_hz"] <= freq <= profile["high_hz"] and power > max_power:
                max_power = power
                peak_f = freq

    masked = sum(1 for v in time_valid if not v)
    used_vals = [eta[t] for t in range(n) if time_valid[t]]
    m0 = sum(v * v for v in used_vals) / len(used_vals) if used_vals else 0.0

    return {
        "significant_wave_height_m": 4.0 * math.sqrt(m0),
        "peak_period_s": 1.0 / peak_f if peak_f > 0 else 0.0,
        "coi_masked_ratio": masked / n if n else 0.0,
    }


def mean_drift_correction(rows: list[tuple[int, float, int]], profile: dict[str, Any]) -> float:
    ref = profile["reference_epoch_ms"]
    rate = profile["drift_rate_pa_per_hour"]
    total = 0.0
    for ts, _, _ in rows:
        hours = (ts - ref) / 3_600_000.0
        total += abs(rate * hours)
    return total / len(rows) if rows else 0.0


def resolve_path(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    if rel.startswith("profiles/"):
        return Path("/app") / rel
    return root / rel


def reference_run(manifest_path: Path, fixtures_root: Path = FIXTURES) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    profile = merge_profile(
        resolve_path(fixtures_root, manifest["profile"]),
        resolve_path(fixtures_root, manifest["toml_overlay"]),
    )
    rows = read_series(resolve_path(fixtures_root, manifest["series_path"]))
    corrected = apply_drift(rows, profile)
    filled = interpolate_gaps(rows, corrected)
    spectral = analyze(filled, profile)
    return {
        "run_id": manifest["run_id"],
        "significant_wave_height_m": round(spectral["significant_wave_height_m"], 6),
        "peak_period_s": round(spectral["peak_period_s"], 6),
        "coi_masked_ratio": round(spectral["coi_masked_ratio"], 6),
        "samples_used": len(rows),
        "drift_correction_pa": round(mean_drift_correction(rows, profile), 6),
    }
