"""Verifier for c-safe-format-spec.

Builds the agent's tree and drives the sfmt CLI over a held-out conformance
corpus that ships beside this verifier, never inside the agent environment. Each
vector's rendered bytes are compared to the reference output byte for byte, and
each rejection must arrive through the normal returned error path, never a crash.
An implementation that leans on the platform printf, or that skips any of the
contract's edge rules, diverges from the corpus and does not pass.
"""

import re
import subprocess
import uuid
from pathlib import Path

import pytest

ENV = Path("/app/environment")
BIN = ENV / "sfmt"
CORPUS = Path(__file__).resolve().parent / "corpus"
EXAMPLES = ENV / "testdata" / "examples"

CRASH_SIGNATURES = (
    "addresssanitizer",
    "heap-buffer-overflow",
    "stack-buffer-overflow",
    "==error==",
    "sanitizer",
    "segmentation fault",
    "sigsegv",
    "sigabrt",
    "core dumped",
    "stack smashing",
    "malloc(): ",
    "free(): ",
    "corrupted",
)


def _strip_c_comments(src: str) -> str:
    """Drop block and line comments so a source-grep cannot match commented text."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", "", src)
    return src


def crashed(r) -> bool:
    """True if the process died on a signal or printed a crash signature."""
    if r.returncode < 0:
        return True
    err = r.stderr.decode("latin-1", "ignore").lower()
    return any(sig in err for sig in CRASH_SIGNATURES)


@pytest.fixture(scope="session")
def binary():
    """Build the sfmt CLI from the agent's tree once per session."""
    subprocess.run(["make", "clean"], cwd=str(ENV), capture_output=True, timeout=120)
    build = subprocess.run(["make"], cwd=str(ENV), capture_output=True, timeout=300)
    assert build.returncode == 0, (
        "make failed:\n"
        + build.stdout.decode("latin-1", "ignore")
        + build.stderr.decode("latin-1", "ignore")
    )
    assert BIN.exists(), "sfmt binary not produced"
    return str(BIN)


def run_vec(binary, vec_path):
    """Render one vector file and return the CompletedProcess."""
    return subprocess.run(
        [binary, "fmt", str(vec_path)], capture_output=True, timeout=30
    )


# ---- corpus discovery --------------------------------------------------------


def _stems(d):
    return sorted(p.stem for p in d.glob("*.vec")) if d.exists() else []


CORPUS_STEMS = _stems(CORPUS)
EXAMPLE_STEMS = _stems(EXAMPLES)


def test_binary_builds(binary):
    """The agent's module compiles into the sfmt binary."""
    assert Path(binary).exists()


def test_corpus_present():
    """The held-out corpus is available and large enough to be meaningful."""
    assert len(CORPUS_STEMS) >= 250, (
        f"expected the full held-out corpus, found {len(CORPUS_STEMS)}"
    )


def _check_vector(binary, stem, base):
    want = (base / (stem + ".out")).read_bytes()
    r = run_vec(binary, base / (stem + ".vec"))
    assert not crashed(r), (
        f"{stem}: rendered via a crash, not the normal path\n"
        f"stderr:\n{r.stderr.decode('latin-1', 'ignore')}"
    )
    assert r.stdout == want, f"{stem}: got {r.stdout!r}, want {want!r}"
    if want.startswith(b"@ERR:"):
        assert r.returncode == 1, f"{stem}: a rejection must exit nonzero"
    else:
        assert r.returncode == 0, f"{stem}: a valid render must exit zero"


@pytest.mark.parametrize("stem", EXAMPLE_STEMS)
def test_shipped_examples(binary, stem):
    """Every shipped example renders to its committed bytes."""
    _check_vector(binary, stem, EXAMPLES)


@pytest.mark.parametrize("stem", CORPUS_STEMS)
def test_corpus_byte_exact(binary, stem):
    """Each held-out vector renders to the exact reference byte sequence."""
    _check_vector(binary, stem, CORPUS)


# ---- test-time vector construction (defeats fixture hardcoding) --------------


def _enc(b: bytes) -> str:
    out = []
    for x in b:
        if x == 0x5C:
            out.append("\\\\")
        elif x == 0x0A:
            out.append("\\n")
        elif x == 0x09:
            out.append("\\t")
        elif x == 0x0D:
            out.append("\\r")
        elif x == 0x00:
            out.append("\\0")
        elif 0x20 <= x < 0x7F:
            out.append(chr(x))
        else:
            out.append("\\x%02x" % x)
    return "".join(out)


def _vec_text(fmt: bytes, args) -> str:
    lines = ["fmt\t" + _enc(fmt)]
    for kind, val in args:
        if kind == "s":
            lines.append("arg\ts\t" + _enc(val))
        else:
            lines.append("arg\t%s\t%d" % (kind, val))
    return "\n".join(lines) + "\n"


def _render(binary, tmp_path, fmt: bytes, args):
    vec = tmp_path / ("t_%s.vec" % uuid.uuid4().hex[:8])
    vec.write_text(_vec_text(fmt, args), encoding="utf-8", newline="\n")
    r = run_vec(binary, vec)
    assert not crashed(r), f"crash on {fmt!r}: {r.stderr!r}"
    return r


def test_literal_is_verbatim(binary, tmp_path):
    """A format with no conversions is emitted byte for byte."""
    r = _render(binary, tmp_path, b"plain text, no percent", [])
    assert r.stdout == b"plain text, no percent" and r.returncode == 0


def test_double_percent(binary, tmp_path):
    """%% renders exactly one percent sign."""
    r = _render(binary, tmp_path, b"a%%b", [])
    assert r.stdout == b"a%b"


def test_distinct_values_differ(binary, tmp_path):
    """Distinct arguments to one format produce distinct output."""
    a = _render(binary, tmp_path, b"%d", [("i", 1)]).stdout
    b = _render(binary, tmp_path, b"%d", [("i", 2)]).stdout
    assert a != b and a == b"1" and b == b"2"


def test_generated_nonce_roundtrips(binary, tmp_path):
    """A freshly generated string argument round-trips, so a solution cannot
    pass by hardcoding the shipped example bytes."""
    token = uuid.uuid4().hex
    r = _render(binary, tmp_path, b"<%s>", [("s", token.encode())])
    assert r.stdout == b"<" + token.encode() + b">"


def test_percent_n_rejected(binary, tmp_path):
    """A generated %n never renders and reports the contract error."""
    r = _render(binary, tmp_path, b"x%n", [("i", 1)])
    assert r.stdout == b"@ERR:PERCENT_N" and r.returncode == 1


def test_stdlib_shortcut_diverges(binary, tmp_path):
    """Two rules the platform printf gets wrong: octal alt-form prefix and
    decimal grouping. A shortcut over libc fails both."""
    r = _render(binary, tmp_path, b"%#o", [("u", 8)])
    assert r.stdout == b"0o10"
    r = _render(binary, tmp_path, b"%'d", [("i", 1234567)])
    assert r.stdout == b"1_234_567"


def test_utf8_precision_counts_codepoints(binary, tmp_path):
    """String precision counts code points, not bytes."""
    r = _render(binary, tmp_path, b"%.3s", [("s", "héllo".encode())])
    assert r.stdout == "hél".encode("utf-8")


def test_grouped_zero_pad(binary, tmp_path):
    """Zero padding a grouped decimal groups the leading zeros too."""
    assert (
        _render(binary, tmp_path, b"%'015d", [("i", 1234)]).stdout == b"000_000_001_234"
    )
    assert _render(binary, tmp_path, b"%'08d", [("i", 1234)]).stdout == b"0001_234"


def test_dynamic_width_precision(binary, tmp_path):
    """Width and precision taken from arguments, negative width left-justifies."""
    assert (
        _render(binary, tmp_path, b"%*d", [("i", 8), ("i", 42)]).stdout == b"      42"
    )
    assert (
        _render(binary, tmp_path, b"%*d", [("i", -8), ("i", 42)]).stdout == b"42      "
    )
    assert _render(binary, tmp_path, b"%.*d", [("i", 4), ("i", 42)]).stdout == b"0042"


def test_alt_form_prefix_suppressed_on_zero(binary, tmp_path):
    """The # alternate-form prefix is emitted only for a non-zero value; a zero
    renders as a bare 0 for x, X, o, and b alike (not just hex)."""
    for conv in (b"x", b"X", b"o", b"b"):
        r = _render(binary, tmp_path, b"%#" + conv, [("u", 0)])
        assert r.stdout == b"0", (conv, r.stdout)


def test_grouped_zero_pad_boundary(binary, tmp_path):
    """When the grouped magnitude already meets or exceeds the field width no
    zeros are added and it is emitted unchanged; a short magnitude is zero-filled
    and then grouped across the padded field."""
    # grouped form of 1234567 is 9 bytes, wider than width 8: emitted unchanged
    assert _render(binary, tmp_path, b"%'08d", [("i", 1234567)]).stdout == b"1_234_567"
    assert _render(binary, tmp_path, b"%'08u", [("u", 1234567)]).stdout == b"1_234_567"
    # small magnitude zero-filled, then grouped over the whole field
    assert _render(binary, tmp_path, b"%'06d", [("i", 12)]).stdout == b"00_012"


def test_grouping_applies_to_unsigned(binary, tmp_path):
    """The ' flag groups %u exactly as it groups %d/%i, and a run of fewer than
    four digits is never given a separator."""
    assert _render(binary, tmp_path, b"%'u", [("u", 1234567)]).stdout == b"1_234_567"
    assert _render(binary, tmp_path, b"%'d", [("i", 12)]).stdout == b"12"


# ---- source integrity --------------------------------------------------------


def test_core_is_implemented():
    """The formatter is genuinely implemented, not left as the stub."""
    src = _strip_c_comments((ENV / "src" / "format.c").read_text())
    body = src[src.find("sf_format") :]
    assert "SF_ERR_NOT_IMPLEMENTED" not in body, (
        "sf_format still returns the not-implemented sentinel"
    )


def test_harness_still_calls_core():
    """The CLI still routes through sf_format; the fix is in the library, not a
    bypass in the driver."""
    main = _strip_c_comments((ENV / "cmd" / "sfmt" / "main.c").read_text())
    assert "sf_format(" in main, "the CLI no longer calls sf_format"
    vec = _strip_c_comments((ENV / "src" / "vec.c").read_text())
    assert "sf_vec_parse" in vec, "the vector parser was removed"


def test_security_notes_written():
    """security_notes.md names the format-string class and the safety theme."""
    notes = ENV / "security_notes.md"
    assert notes.exists(), "security_notes.md not written at /app/environment"
    body = notes.read_text().lower()
    assert "format string" in body or "format-string" in body, "missing the class"
    assert "cwe-134" in body, "missing the CWE reference"
    assert "%n" in body, "missing the %n write-primitive theme"
