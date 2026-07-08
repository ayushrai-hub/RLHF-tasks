"""Held-out grading library for the geokern fast-math task.

This module is compiled-against and run only at grade time. It rebuilds the
pristine kernel sources under chosen floating-point profiles, runs kernels on
adversarial inputs that are never shipped, and decides each kernel's documented
invariant. None of the partition, witnesses, or suppression set is stored as a
literal: every fact is recomputed here by building and running.
"""

import json
import math
import os
import struct
import subprocess
import tempfile

REF = "/opt/ref"
ARCH = ["-O2", "-mfma"]
STRICT_FP = ["-ffp-contract=off"]
RELEASE_FP = [
    "-ffp-contract=fast",
    "-fassociative-math",
    "-freciprocal-math",
    "-fno-signed-zeros",
    "-fno-trapping-math",
    "-ffinite-math-only",
]
TUS = ["geom", "helpers", "accum", "gain", "guard", "flux"]
SUPPRESS_TOKENS = {
    "ffp-contract",
    "fassociative-math",
    "freciprocal-math",
    "fno-signed-zeros",
    "ffinite-math-only",
}

# kernel -> (translation unit, argument count, invariant id)
KERNELS = {
    "cross2": ("geom", 4, "self_cross_zero"),
    "clamp01": ("geom", 1, "in_unit"),
    "recover": ("accum", 2, "absorbed_zero"),
    "sign_of": ("accum", 1, "sign_set"),
    "cascade": ("gain", 3, "staged_quotient"),
    "roundtrip_residual": ("gain", 1, "small_residual"),
    "polarity": ("flux", 2, "equal_negative"),
    "magdiff": ("flux", 2, "nonneg_real"),
    "domain_guard": ("guard", 2, "never_nan"),
    "horner": ("guard", 1, "ge_constant"),
}

# Adversarial inputs, held out from the shipped samples. Each hazard kernel has
# at least one input that crosses its invariant under the release build; each
# benign kernel has stress inputs that must stay within contract.
HELDOUT = {
    "cross2": [
        [0.1, 0.3, 0.1, 0.3],
        [0.7, 0.2, 0.7, 0.2],
        [1.3, 2.9, 1.3, 2.9],
        [0.31, 0.97, 0.31, 0.97],
    ],
    "clamp01": [[0.5], [2.0], [-1.0], [0.999], [0.0]],
    "recover": [[1e16, 1.0], [1e15, 3.0], [8e15, 7.0], [1e16, 0.5]],
    "sign_of": [[-3.0], [0.0], [2.0], [1e-300]],
    "cascade": [[7.0, 5.0, 3.0], [11.0, 7.0, 13.0], [1.0, 3.0, 7.0], [23.0, 9.0, 5.0]],
    "roundtrip_residual": [[49.0], [0.1], [3.0], [7.0], [1e10], [123.456]],
    "polarity": [[1.0, 1.0], [5.0, 5.0], [2.5, 2.5], [1e9, 1e9]],
    "magdiff": [[0.1, 0.1], [3.3, 3.3], [0.7, 0.7], [2.2, 2.0], [5.0, 5.0]],
    "domain_guard": [[0.0, 0.0], [6.0, 2.0], [9.0, 3.0]],
    "horner": [[0.0], [0.3], [0.5], [1.0], [2.0], [10.0]],
}

EPS = 2.220446049250313e-16
_BUILD_CACHE = {}


def _norm_tu(name):
    return name[:-2] if name.endswith(".c") else name


def _fp_release_minus(tokens):
    drop = set(tokens)
    res = []
    for f in RELEASE_FP:
        if f == "-ffp-contract=fast" and "ffp-contract" in drop:
            res.append("-ffp-contract=off")
            continue
        if f.lstrip("-") in drop:
            continue
        res.append(f)
    return res


def _tu_flags(tu, profile):
    if profile == "strict":
        return ARCH + STRICT_FP
    if profile == "release":
        return ARCH + RELEASE_FP
    toks = []
    for key, val in profile.items():
        if _norm_tu(key) == tu:
            toks = val
            break
    return ARCH + _fp_release_minus(toks)


def build(profile):
    """Compile the pristine library under a profile and return the driver path.

    profile is "strict", "release", or a dict mapping translation-unit name to
    a list of suppression tokens to drop from the release bundle for that unit.
    """
    key = json.dumps(profile, sort_keys=True) if isinstance(profile, dict) else profile
    if key in _BUILD_CACHE and os.path.exists(_BUILD_CACHE[key]):
        return _BUILD_CACHE[key]
    d = tempfile.mkdtemp(prefix="geokern_")
    objs = []
    for tu in TUS:
        obj = os.path.join(d, tu + ".o")
        flags = _tu_flags(tu, profile)
        cmd = (
            ["gcc"]
            + flags
            + ["-I", REF + "/include", "-c", REF + "/src/" + tu + ".c", "-o", obj]
        )
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0, "compile %s failed: %s" % (tu, r.stderr)
        objs.append(obj)
    ktobj = os.path.join(d, "kerneltest.o")
    r = subprocess.run(
        ["gcc"]
        + ARCH
        + ["-I", REF + "/include", "-c", REF + "/tools/kerneltest.c", "-o", ktobj],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, "compile driver failed: %s" % r.stderr
    objs.append(ktobj)
    binp = os.path.join(d, "kerneltest")
    r = subprocess.run(
        ["gcc"] + ARCH + ["-o", binp] + objs + ["-lm"], capture_output=True, text=True
    )
    assert r.returncode == 0, "link failed: %s" % r.stderr
    _BUILD_CACHE[key] = binp
    return binp


def _hexarg(x):
    return x if isinstance(x, str) else float(x).hex()


def run(binp, kernel, args):
    argv = [binp, kernel] + [_hexarg(a) for a in args]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, "run %s failed: %s" % (kernel, r.stderr)
    s = r.stdout.strip()
    try:
        return float.fromhex(s)
    except ValueError:
        low = s.lower()
        if "nan" in low:
            return float("nan")
        if "inf" in low:
            return float("-inf") if s.startswith("-") else float("inf")
        raise


def same_bits(a, b):
    return struct.pack(">d", a) == struct.pack(">d", b)


def inv_holds(kernel, args, out):
    """True iff the kernel's documented invariant holds for this output."""
    k = kernel
    if k == "cross2":
        ax, ay, bx, by = args[:4]
        return out == 0.0 if (ax == bx and ay == by) else True
    if k == "clamp01":
        return (not math.isnan(out)) and 0.0 <= out <= 1.0
    if k == "recover":
        a, b = args[:2]
        return out == 0.0 if (a + b) == a else True
    if k == "sign_of":
        return out in (-1.0, 0.0, 1.0)
    if k == "cascade":
        a, b, c = args[:3]
        try:
            exp = (a / b) / c
        except ZeroDivisionError:
            return True
        return out == exp
    if k == "roundtrip_residual":
        return (not math.isnan(out)) and out <= 8 * EPS
    if k == "polarity":
        a, b = args[:2]
        return out == -1.0 if a == b else True
    if k == "magdiff":
        return (not math.isnan(out)) and out >= 0.0
    if k == "domain_guard":
        return not math.isnan(out)
    if k == "horner":
        x = args[0]
        return out >= 1.0 if x >= 0.0 else True
    raise ValueError(k)


def truth_is_hazard(kernel, sb, rb):
    """A kernel is a hazard iff some held-out input has the release build cross
    the invariant while the strict build holds it."""
    for args in HELDOUT[kernel]:
        so = run(sb, kernel, args)
        ro = run(rb, kernel, args)
        if inv_holds(kernel, args, so) and not inv_holds(kernel, args, ro):
            return True, args
    return False, None


def any_divergence(kernel, sb, rb):
    for args in HELDOUT[kernel]:
        if not same_bits(run(sb, kernel, args), run(rb, kernel, args)):
            return True, args
    return False, None


def load_result(path):
    assert os.path.exists(path), "missing output file: %s" % path
    with open(path) as f:
        return json.load(f)
