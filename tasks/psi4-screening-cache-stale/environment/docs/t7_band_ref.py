"""Reference T7 band helpers."""
import hashlib

T4_NARROW = 1e-6
T4_WIDE = 1e-2


def compare_t4(stored: float, target: float, cached: bool, wide_on_cached: bool) -> int:
    band = T4_WIDE if cached and wide_on_cached else T4_NARROW
    tol = band * max(abs(target), 1e-9)
    return 0 if abs(stored - target) <= tol else 1


def within_narrow(rms: float) -> bool:
    return rms <= T4_NARROW * 10.0


def body_digest_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()
