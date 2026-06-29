"""Verifier for dafny-insertion-sort-multiset-sorted: the agent's Dafny proof must
verify without weakening the frozen spec, without escape hatches, and with the method
still behaviorally correct on a range of adversarial inputs."""

import hashlib
import os
import re
import subprocess
import tempfile

APP = "/app"
SRC = os.path.join(APP, "solution.dfy")
TESTS = os.path.dirname(os.path.abspath(__file__))


def _strip(text):
    """Remove // and /* */ comments from Dafny source."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def _spec_region(text):
    """Return the frozen spec block delimited by SPEC-BEGIN / SPEC-END markers.

    Marker-based, NOT line-prefix based: the starter wraps the signature plus every
    requires/ensures/decreases clause between the markers, so a multi-line clause is
    captured whole and cannot be weakened without changing the hash. The agent adds
    the proof (invariants, decreases, lemmas) in the method body, below SPEC-END.
    """
    m = re.search(r"//\s*SPEC-BEGIN\b(.*?)//\s*SPEC-END\b", text, flags=re.S)
    assert m, "SPEC-BEGIN / SPEC-END markers missing"
    return m.group(1)


def _strip_main_method(src):
    """Remove any 'method Main()' block from Dafny source using brace-counting.

    Called before including solution.dfy in a temp harness, so that our harness
    defines the sole Main entry point and Dafny does not see two competing mains.
    Returns the source unchanged if no Main method is found.
    """
    m = re.search(r"\nmethod\s+Main\b[^{]*\{", src)
    if m is None:
        return src
    start = m.start()
    depth = 0
    i = m.end() - 1  # position of the opening '{'
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[:start] + "\n" + src[i + 1 :]
        i += 1
    return src  # opening brace unmatched — return unchanged


def _run_behavioral_case(inp, expected):
    """Sort `inp` via the agent's InsertionSort and return (passed, stdout, stderr).

    Strips any existing Main method from solution.dfy, writes a temp harness that
    defines its own Main, and runs `dafny run --no-verify`. Using a fresh harness
    lets us test arbitrary inputs without requiring the agent to ship a Main method.
    """
    src = _strip_main_method(open(SRC).read())
    arr_lit = ", ".join(str(x) for x in inp)
    exp_lit = ", ".join(str(x) for x in expected)
    n = len(inp)

    with tempfile.NamedTemporaryFile(
        suffix=".dfy", mode="w", delete=False, prefix="sol_"
    ) as sf:
        sf.write(src)
        sol_path = sf.name

    dfy = f"""include "{sol_path}"
method Main() decreases * {{
  var a := new int[{n}][{arr_lit}];
  InsertionSort(a);
  var exp := [{exp_lit}];
  var ok := true;
  for k := 0 to {n} invariant true {{
    if a[k] != exp[k] {{ ok := false; }}
  }}
  if ok {{ print "OK\\n"; }} else {{ print "FAIL\\n"; }}
}}
"""
    with tempfile.NamedTemporaryFile(
        suffix=".dfy", mode="w", delete=False, prefix="harness_"
    ) as hf:
        hf.write(dfy)
        harness_path = hf.name

    r = subprocess.run(
        ["dafny", "run", "--no-verify", "--target", "py", harness_path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    os.unlink(sol_path)
    os.unlink(harness_path)
    return "OK" in r.stdout, r.stdout, r.stderr


def test_verifies():
    """`dafny verify` discharges every proof obligation (exit 0)."""
    r = subprocess.run(
        ["dafny", "verify", "--resource-limit", "20000000", SRC],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_spec_frozen():
    """The marked specification region is byte-identical to the shipped spec."""
    want = dict(
        line.split(None, 1)[::-1]
        for line in open(os.path.join(TESTS, "manifest.sha256")).read().splitlines()
        if line.strip()
    )
    got = hashlib.sha256(_spec_region(open(SRC).read()).encode()).hexdigest()
    assert got == want["spec_region"].strip(), "specification was modified"


def test_no_escape_hatch():
    """The proof uses no assume/axiom/verify-false/extern escape and no vacuous ensures.

    Comment-stripped, whitespace/paren-tolerant regexes catch common spellings.
    """
    src = _strip(open(SRC).read())
    assert not re.search(r"\bassume\b", src), "forbidden: assume"
    assert not re.search(r"\{\s*:\s*axiom\b", src), "forbidden: {:axiom}"
    assert not re.search(r"\{\s*:\s*verify\s+false\b", src), (
        "forbidden: {:verify false}"
    )
    assert not re.search(r"\{\s*:\s*extern\b", src), "forbidden: {:extern}"
    assert not re.search(r"ensures\s+true\s*(;|//|$)", src, re.M), (
        "vacuous ensures true"
    )


def test_behavioral():
    """Sorts eight adversarial input shapes correctly (dafny run --no-verify, temp harness).

    Cases cover: fully reversed length-10, already-sorted (no-op proof), all-duplicates,
    negative values, mixed-sign, alternating duplicates, one element out of place in a
    sea of equals, and a longer input with repeated values.
    """
    cases = [
        ([10, 9, 8, 7, 6, 5, 4, 3, 2, 1], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        ([1, 1, 1, 1, 1], [1, 1, 1, 1, 1]),
        ([-5, 3, -1, 0, -3, 2], [-5, -3, -1, 0, 2, 3]),
        ([100, -100, 0, 50, -50], [-100, -50, 0, 50, 100]),
        ([2, 1, 2, 1, 2, 1], [1, 1, 1, 2, 2, 2]),
        ([5, 5, 5, 1, 5, 5], [1, 5, 5, 5, 5, 5]),
        ([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5], [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9]),
    ]
    for inp, expected in cases:
        ok, stdout, stderr = _run_behavioral_case(inp, expected)
        assert ok, f"behavioral failure for {inp}: stdout={stdout!r} stderr={stderr!r}"


def test_empty_array():
    """InsertionSort on a zero-length array completes without panic."""
    src = _strip_main_method(open(SRC).read())

    with tempfile.NamedTemporaryFile(
        suffix=".dfy", mode="w", delete=False, prefix="sol_"
    ) as sf:
        sf.write(src)
        sol_path = sf.name

    dfy = f"""include "{sol_path}"
method Main() decreases * {{
  var a := new int[0];
  InsertionSort(a);
  assert a.Length == 0;
  print "OK\\n";
}}
"""
    with tempfile.NamedTemporaryFile(
        suffix=".dfy", mode="w", delete=False, prefix="empty_"
    ) as hf:
        hf.write(dfy)
        harness_path = hf.name

    r = subprocess.run(
        ["dafny", "run", "--no-verify", "--target", "py", harness_path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    os.unlink(sol_path)
    os.unlink(harness_path)
    assert "OK" in r.stdout, (
        f"empty-array test failed: stdout={r.stdout!r} stderr={r.stderr!r}"
    )


def test_no_ghost_copy():
    """solution.dfy does not contain both 'ghost var' and 'new int' simultaneously.

    The ghost-copy reward-hack allocates a ghost array (ghost var ... := new int[...]),
    sorts the ghost copy non-destructively, then copies values back element-by-element.
    A genuine proof works on `a` in-place with loop invariants and never needs to
    allocate new storage.
    """
    src = _strip(open(SRC).read())
    has_ghost_var = bool(re.search(r"\bghost\s+var\b", src))
    has_new_int = bool(re.search(r"\bnew\s+int\b", src))
    assert not (has_ghost_var and has_new_int), (
        "solution contains both 'ghost var' and 'new int' — "
        "suspected ghost-copy-then-assign reward hack"
    )


def test_no_decreases_star():
    """InsertionSort body does not use decreases * (skips termination proof)."""
    src = open("/app/solution.dfy").read()
    method_start = src.find("method InsertionSort")
    if method_start == -1:
        method_start = src.find("method ")
    method_src = src[method_start:]
    main_start = method_src.find("method Main")
    if main_start != -1:
        method_src = method_src[:main_start]
    assert "decreases *" not in method_src, "InsertionSort uses 'decreases *'"
