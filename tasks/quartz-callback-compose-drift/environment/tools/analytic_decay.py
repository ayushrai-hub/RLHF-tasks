"""Closed-form decay integral helper used by contract cross-checks."""
import math


def decay_integral(y0: float, dt: float, steps: int) -> float:
    t_end = dt * steps
    return y0 * (1.0 - math.exp(-t_end))
