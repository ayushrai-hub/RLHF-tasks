import glob
import json
import os
import re
import subprocess
import tempfile

import pytest

APP = "/app"
TESTS = "/tests"
REF_SRC = os.path.join(TESTS, "ref", "xiangqi_ref.cpp")
FIX = os.path.join(TESTS, "fixtures")

GRADER = tempfile.mkdtemp(prefix="xiangqi_grader_")

BANNED = [
    "stockfish",
    "fairy",
    "pikafish",
    "elephanteye",
    "eleeye",
    "xqwizard",
    "libxiangqi",
    "cchess",
    "leela",
    "python-chess",
    "syzygy",
    "gaviota",
    "nnue",
    "tablebase",
]


def _compile(sources, out, defines=None):
    cmd = ["g++", "-O2", "-std=c++17"]
    if defines:
        cmd += ["-D" + d for d in defines]
    cmd += sources + ["-o", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return out if r.returncode == 0 and os.path.exists(out) else None


def _build_agent():
    srcs = sorted(glob.glob(os.path.join(APP, "src", "*.cpp")))
    if not srcs:
        return None
    return _compile(srcs, os.path.join(GRADER, "agent_perft"))


def _build_ref(name, defines=None):
    return _compile([REF_SRC], os.path.join(GRADER, name), defines)


AGENT = _build_agent()
REF = _build_ref("ref_full")
REF_NAIVE = _build_ref("ref_naive", ["NO_FLYING", "NO_CANNON"])
REF_NOFLY = _build_ref("ref_nofly", ["NO_FLYING"])
REF_NOCAN = _build_ref("ref_nocan", ["NO_CANNON"])


def _load(name):
    with open(os.path.join(FIX, name)) as fh:
        return json.load(fh)


HIDDEN = _load("hidden.json")
ANCHORS = _load("anchors.json")
VISIBLE = _load("visible.json")
PUBLISHED = [a for a in ANCHORS if a["id"].startswith("init_")]
MICRO = [a for a in ANCHORS if a["id"].endswith("_micro")]


def run(binary, fen, side, depth):
    if binary is None:
        return None
    try:
        r = subprocess.run(
            [binary],
            input=f"{fen} {side} {depth}\n",
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None
    out = r.stdout.strip()
    if not re.fullmatch(r"-?\d+", out):
        return None
    return int(out)


def _agent_sources_text():
    text = ""
    for p in sorted(glob.glob(os.path.join(APP, "src", "*.cpp"))) + sorted(
        glob.glob(os.path.join(APP, "src", "*.hpp"))
    ):
        with open(p, "r", errors="ignore") as fh:
            text += fh.read() + "\n"
    return text


def _strip_comments(text):
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


def test_builds():
    """Agent sources and every reference variant compile."""
    assert AGENT is not None, "agent sources under /app/src did not compile"
    assert REF is not None and REF_NAIVE is not None
    assert REF_NOFLY is not None and REF_NOCAN is not None


def test_hidden_set_is_large_enough():
    """The hidden battery holds at least thirty independently graded positions."""
    assert len(HIDDEN) >= 30


@pytest.mark.parametrize("a", PUBLISHED, ids=[a["id"] for a in PUBLISHED])
def test_reference_matches_published_constant(a):
    """The reference reproduces each cross engine verified initial position perft."""
    assert run(REF, a["fen"], a["side"], a["depth"]) == a["expected"]


@pytest.mark.parametrize("a", PUBLISHED, ids=[a["id"] for a in PUBLISHED])
def test_agent_matches_published_constant(a):
    """The agent engine reproduces each published initial position perft constant."""
    assert run(AGENT, a["fen"], a["side"], a["depth"]) == a["expected"]


def test_flying_micro_isolates_the_rule():
    """Dropping the facing generals rule alone changes the count on the flying micro anchor."""
    m = next(a for a in MICRO if a["id"] == "flying_micro")
    assert run(REF, m["fen"], m["side"], m["depth"]) == m["expected"]
    assert run(REF_NOFLY, m["fen"], m["side"], m["depth"]) == m["noflying"]
    assert run(REF_NOFLY, m["fen"], m["side"], m["depth"]) != m["expected"]
    assert run(REF_NOCAN, m["fen"], m["side"], m["depth"]) == m["expected"]


def test_cannon_micro_isolates_the_rule():
    """Treating the cannon capture like a chariot alone changes the count on the cannon micro anchor."""
    m = next(a for a in MICRO if a["id"] == "cannon_micro")
    assert run(REF, m["fen"], m["side"], m["depth"]) == m["expected"]
    assert run(REF_NOCAN, m["fen"], m["side"], m["depth"]) == m["nocannon"]
    assert run(REF_NOCAN, m["fen"], m["side"], m["depth"]) != m["expected"]
    assert run(REF_NOFLY, m["fen"], m["side"], m["depth"]) == m["expected"]


@pytest.mark.parametrize("fx", HIDDEN, ids=[f["id"] for f in HIDDEN])
def test_hidden_agent_matches_reference(fx):
    """On each hidden position the agent perft equals the independently recomputed reference."""
    ref = run(REF, fx["fen"], fx["side"], fx["depth"])
    assert ref == fx["expected"]
    assert run(AGENT, fx["fen"], fx["side"], fx["depth"]) == ref


def test_naive_fails_every_hidden():
    """A pseudo legal engine dropping both the facing rule and the cannon screen mismatches on every hidden position."""
    mismatches = sum(
        1
        for fx in HIDDEN
        if run(REF_NAIVE, fx["fen"], fx["side"], fx["depth"])
        != run(REF, fx["fen"], fx["side"], fx["depth"])
    )
    assert mismatches == len(HIDDEN)


def test_flying_rule_is_necessary():
    """At least one hidden position changes count when the facing generals rule is removed."""
    assert any(
        run(REF_NOFLY, fx["fen"], fx["side"], fx["depth"])
        != run(REF, fx["fen"], fx["side"], fx["depth"])
        for fx in HIDDEN
    )


def test_cannon_rule_is_necessary():
    """At least one hidden position changes count when the cannon screen capture is removed."""
    assert any(
        run(REF_NOCAN, fx["fen"], fx["side"], fx["depth"])
        != run(REF, fx["fen"], fx["side"], fx["depth"])
        for fx in HIDDEN
    )


def test_partial_rule_engines_all_fail():
    """No engine that fixes only one of the two interacting rules matches the reference everywhere."""
    for partial in (REF_NAIVE, REF_NOFLY, REF_NOCAN):
        diffs = sum(
            1
            for fx in HIDDEN
            if run(partial, fx["fen"], fx["side"], fx["depth"])
            != run(REF, fx["fen"], fx["side"], fx["depth"])
        )
        assert diffs >= 1


def test_both_rules_jointly_pivot_many_positions():
    """A majority of hidden positions require the facing rule and many require the cannon screen."""
    fly = sum(1 for fx in HIDDEN if fx["piv_fly"])
    can = sum(1 for fx in HIDDEN if fx["piv_can"])
    assert fly >= len(HIDDEN) // 2 and can >= 5


@pytest.mark.parametrize("fx", VISIBLE, ids=[f["id"] for f in VISIBLE])
def test_visible_agent_matches_reference(fx):
    """On each visible sanity position the agent matches the reference and the published count."""
    assert run(REF, fx["fen"], fx["side"], fx["depth"]) == fx["expected"]
    assert run(AGENT, fx["fen"], fx["side"], fx["depth"]) == fx["expected"]


def test_agent_output_is_nonnegative_integer():
    """The agent emits a single parseable non negative integer for a normal query."""
    val = run(AGENT, HIDDEN[0]["fen"], HIDDEN[0]["side"], HIDDEN[0]["depth"])
    assert val is not None and val >= 0


def test_agent_depth_zero_is_one():
    """Perft of depth zero is one for any position the agent reads."""
    assert run(AGENT, HIDDEN[0]["fen"], HIDDEN[0]["side"], 0) == 1


def test_no_external_engine_library():
    """The agent sources do not import or vendor a known xiangqi or chess engine or tablebase."""
    text = _strip_comments(_agent_sources_text()).lower()
    for banned in BANNED:
        assert banned not in text, f"forbidden reference found: {banned}"


def test_no_bundled_answer_data():
    """The project ships no tablebase, opening book, or precomputed answer artifact."""
    bad = []
    for root, _dirs, files in os.walk(APP):
        for fn in files:
            if fn.lower().endswith(
                (".bin", ".egt", ".book", ".tbw", ".tbz", ".nnue", ".dat")
            ):
                bad.append(os.path.join(root, fn))
    assert not bad, f"unexpected data artifacts: {bad}"


def test_reference_is_deterministic():
    """Recomputing a hidden position twice yields the identical reference integer."""
    fx = HIDDEN[len(HIDDEN) // 2]
    assert run(REF, fx["fen"], fx["side"], fx["depth"]) == run(
        REF, fx["fen"], fx["side"], fx["depth"]
    )


def test_agent_matches_reference_is_deterministic():
    """The agent returns the same integer on a repeated identical query."""
    fx = HIDDEN[0]
    assert run(AGENT, fx["fen"], fx["side"], fx["depth"]) == run(
        AGENT, fx["fen"], fx["side"], fx["depth"]
    )
