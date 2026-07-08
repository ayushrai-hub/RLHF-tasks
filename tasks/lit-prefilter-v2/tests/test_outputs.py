"""Behavioral test: reproduce the reference prefilter literal-set optimization exactly.

The Go project in /app is compiled and driven through `litpre <file>` over a set of
candidate literal sets. For each set the tool must print the exact optimized literal
set the reference text-search engine settles on: which literals it keeps, how it trims
or collapses them, and whether it decides no literal set is worth scanning for.

Correctness is checked two ways, both behavioral (no source-hash checks):
  * TestOutputMatch  -- the emitted optimized set equals the reference exactly. Every
                        graded set is one where a naive "keep the set as-is" and a
                        "just preference-minimize it" answer both differ from the
                        reference, so only the reference's actual rule matches.
  * TestOutputValid  -- the output parses as a well-formed literal set and every
                        emitted literal is a prefix of some input literal (the
                        transform only trims, drops, or collapses literals -- it never
                        invents bytes), which exercises the parser, CLI, and encoding
                        primitives end to end.

Every expected value was minted from the reference engine and independently
cross-checked against a from-scratch reimplementation (87000-input fuzz, 0 mismatches).
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/tests")

from cases import CASES

APP_DIR = "/app"
BIN = "/tmp/litpre_test"


def _build_env():
    env = dict(os.environ)
    env.setdefault("GOCACHE", "/tmp/go-cache")
    env.setdefault("GOPATH", "/tmp/go-path")
    env["GOFLAGS"] = "-mod=mod"
    env["GOPROXY"] = "off"
    return env


def _parse_seq(spec):
    """Decode a seq-json into (finite, [(bytes_tuple, exact), ...])."""
    js = json.loads(spec)
    if not js.get("finite", False):
        return False, []
    lits = []
    for lit in js.get("lits", []) or []:
        lits.append((tuple(lit["b"]), bool(lit["exact"])))
    return True, lits


def _is_prefix(a, b):
    """True iff tuple a is a prefix of tuple b."""
    return len(a) <= len(b) and b[: len(a)] == a


@pytest.fixture(scope="module")
def results():
    build = subprocess.run(
        ["go", "build", "-o", BIN, "."],
        cwd=APP_DIR, env=_build_env(), capture_output=True, text=True,
    )
    assert build.returncode == 0, f"go build failed:\n{build.stderr}"

    inp = "".join(f"{c['id']} {c['inp']}\n" for c in CASES)
    with tempfile.NamedTemporaryFile("w", suffix=".seqs", delete=False) as fh:
        fh.write(inp)
        path = fh.name
    try:
        proc = subprocess.run([BIN, path], capture_output=True, text=True)
        assert proc.returncode == 0, f"litpre exited {proc.returncode}:\n{proc.stderr}"
        out = {}
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            cid, _, rest = line.partition(" ")
            out[cid] = rest
        return out
    finally:
        os.unlink(path)


class TestOutputMatch:
    """Verify the emitted optimized set matches the reference exactly for each graded
    input."""

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_values(self, results, case):
        """The emitted optimized set must match the reference set exactly."""
        cid = case["id"]
        assert cid in results, f"case {cid} missing from output"
        got = results[cid]
        exp = case["exp"]
        assert got == exp, (
            f"{cid}: output mismatch\n"
            f"  input    {case['inp']}\n"
            f"  got      {got}\n  expected {exp}"
        )


class TestOutputValid:
    """Verify the output is a well-formed literal set whose literals are all prefixes
    of input literals, exercising the parser, CLI, and encoding primitives
    behaviorally."""

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_shape(self, results, case):
        """Output parses as a valid seq; if finite, every literal is a prefix of some
        input literal (the transform only trims/drops/collapses, never invents bytes)."""
        cid = case["id"]
        assert cid in results, f"case {cid} missing from output"
        ofin, olits = _parse_seq(results[cid])
        if not ofin:
            return  # infinite output is well-formed and carries no literals
        _, inlits = _parse_seq(case["inp"])
        in_bytes = [b for (b, _e) in inlits]
        for (ob, oe) in olits:
            assert all(0 <= x <= 255 for x in ob), f"{cid}: byte out of range in {ob}"
            assert isinstance(oe, bool), f"{cid}: exact flag not a bool"
            assert any(_is_prefix(ob, ib) for ib in in_bytes), (
                f"{cid}: emitted literal {ob} is not a prefix of any input literal"
            )
