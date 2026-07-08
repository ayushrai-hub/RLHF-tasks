"""Analytical pin-pin helpers used by the verifier (not part of the solver contract)."""

from __future__ import annotations


def pin_pin_reactions_point(length_m: float, force_n: float, pos_m: float) -> tuple[float, float]:
    right = force_n * pos_m / length_m
    left = force_n - right
    return left, right


def pin_pin_reactions_udl(length_m: float, w_n_per_m: float, x0_m: float, x1_m: float) -> tuple[float, float]:
    total = w_n_per_m * (x1_m - x0_m)
    centroid = x0_m + (x1_m - x0_m) / 2.0
    right = total * centroid / length_m
    left = total - right
    return left, right


def vertical_resultant(loads: dict) -> float:
    total = 0.0
    for force_n, _ in loads.get("point_forces", []):
        total += force_n
    for w_n_per_m, x0_m, x1_m in loads.get("udls", []):
        total += w_n_per_m * (x1_m - x0_m)
    return total


def moment_about_left(loads: dict) -> float:
    total = 0.0
    for force_n, pos_m in loads.get("point_forces", []):
        total += force_n * pos_m
    for w_n_per_m, x0_m, x1_m in loads.get("udls", []):
        width = x1_m - x0_m
        total += w_n_per_m * width * (x0_m + width / 2.0)
    for moment_nm, _ in loads.get("point_moments", []):
        total += moment_nm
    return total
