"""Verifier for variform-ruby-transform-allowlist-audit.

Loads the agent's variform tree, drives the command-line tool against the
well-formed and hostile transformation specs, and source-greps the planted-bug
files for the structural fixes that a single invocation cannot observe.

Every refusal must be the library's own clean error path: a non-zero exit with a
subsystem-named stderr line and no Ruby backtrace or interpreter abort.
"""

import json
import re
import subprocess
import uuid
from pathlib import Path

import pytest

ENV = Path("/app/environment")
LIB = ENV / "lib" / "variform"
VALIDATION = LIB / "validation"
VALID = ENV / "testdata" / "valid"
EXPLOITS = ENV / "testdata" / "exploits"
BIN = ENV / "bin" / "variform"

METHOD_ALLOWLIST = VALIDATION / "method_allowlist.rb"
METHOD_GATE = VALIDATION / "method_gate.rb"
SCALAR_SCAN = VALIDATION / "scalar_scan.rb"
HASH_SCAN = VALIDATION / "hash_scan.rb"
LIST_SCAN = VALIDATION / "list_scan.rb"

METHOD_KEYWORDS = ["transform", "variant"]
METHOD_RESOURCE = ["method", "unsupported"]
ARGUMENT_KEYWORDS = ["transform", "variant"]
ARGUMENT_RESOURCE = ["option", "forbidden", "argument"]

RUBY_CRASH_SIGNATURES = (
    "\tfrom ",
    "rescue in ",
    "(jsonerror)",
    "(nomethoderror)",
    "(typeerror)",
    "(nameerror)",
    "(argumenterror)",
    "(runtimeerror)",
    "(nomatchingpatternerror)",
    "stack level too deep",
    "unhandled exception",
)


def _strip_ruby_comments(src: str) -> str:
    """Remove =begin/=end blocks and # line comments, preserving #{} interpolation."""
    src = re.sub(r"^=begin\b.*?^=end\b", "", src, flags=re.DOTALL | re.MULTILINE)
    out = []
    for line in src.split("\n"):
        res = []
        i = 0
        in_str = None
        while i < len(line):
            ch = line[i]
            if in_str:
                res.append(ch)
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch in ('"', "'"):
                in_str = ch
                res.append(ch)
                i += 1
                continue
            if ch == "#" and not (i + 1 < len(line) and line[i + 1] == "{"):
                break
            res.append(ch)
            i += 1
        out.append("".join(res))
    return "\n".join(out)


def _read(path: Path) -> str:
    return _strip_ruby_comments(path.read_text())


def _allowlist_excludes_passthrough(src: str) -> bool:
    """True if none of the pass-through methods remain as allow-list entries."""
    return not any(
        re.search(rf"^\s*{name}\s*$", src, re.MULTILINE)
        for name in ("apply", "loader", "saver")
    )


def _method_gate_uses_exact_match(src: str) -> bool:
    """True if the gate matches a method exactly rather than by substring."""
    exact = bool(re.search(r"ALLOWED\s*\.\s*(include\?|member\?)", src)) or bool(
        re.search(r"==\s*(name|candidate)\b|\b(name|candidate)\s*==", src)
    )
    substring = bool(
        re.search(r"(candidate|name)\s*\.\s*(include\?|start_with\?|match\??|=~)", src)
    )
    return exact and not substring


def _method_gate_no_name_reduction(src: str) -> bool:
    """True if the gate matches the whole name, not a first-token reduction."""
    return not re.search(r"\.split\b|\.first\b|\[\s*0\s*\]|\.take\s*\(|\.slice\b", src)


def _scalar_scan_is_case_insensitive(src: str) -> bool:
    """True if the option scan folds case (downcase / upcase / casecmp / regex /i)."""
    fold = re.search(r"\.\s*downcase\b|\.\s*upcase\b|casecmp", src)
    iflag = re.search(r"/(?:\\.|[^/\n\\])+/[a-z]*i", src)
    return bool(fold or iflag)


def _hash_scan_scans_keys(src: str) -> bool:
    """True if the object walk passes the key (not just the value) to a scanner."""
    match = re.search(r"\|\s*([A-Za-z_]\w*)\s*,\s*[A-Za-z_]\w*\s*\|", src)
    if not match:
        return False
    key_var = match.group(1)
    return bool(
        re.search(
            rf"(ArgumentScan|ScalarScan)\s*\.\s*\w+\s*\(\s*{re.escape(key_var)}\b", src
        )
    )


def _list_scan_recurses(src: str) -> bool:
    """True if the array walk dispatches each element through the recursive scan."""
    match = re.search(r"\.each\b[^\n|]*\|\s*([A-Za-z_]\w*)\s*\|", src)
    if not match:
        return False
    element = match.group(1)
    return bool(
        re.search(
            rf"(ArgumentScan|ListScan|HashScan)\s*\.\s*\w+\s*\(\s*{re.escape(element)}\b",
            src,
        )
    )


def _run(cmd, timeout=90, stdin=None):
    return subprocess.run(
        cmd,
        cwd=str(ENV),
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


def check_file(path) -> subprocess.CompletedProcess:
    return _run(["ruby", str(BIN), "check", str(path)])


def check_spec(spec, tmp_path) -> subprocess.CompletedProcess:
    p = tmp_path / f"spec_{uuid.uuid4().hex[:8]}.json"
    p.write_text(json.dumps(spec))
    return check_file(p)


def assert_clean_rejection(r, name, keywords, resource_words=None):
    """Assert a non-zero exit with a subsystem keyword and no Ruby crash signature."""
    err = r.stderr.lower()
    for sig in RUBY_CRASH_SIGNATURES:
        assert sig not in err, (
            f"{name} refused via a crash, not a clean error path:\n{r.stderr}"
        )
    assert r.returncode != 0, (
        f"{name} was accepted (exit 0); it must be refused:\n{r.stdout}\n{r.stderr}"
    )
    assert any(k in err for k in keywords), (
        f"{name} stderr must name a subsystem in {keywords}:\n{r.stderr}"
    )
    if resource_words:
        assert any(w in err for w in resource_words), (
            f"{name} stderr must name the failure in {resource_words}:\n{r.stderr}"
        )


@pytest.fixture(scope="session", autouse=True)
def library_loads():
    """The agent's tree must load without a syntax or load error."""
    r = _run(["ruby", "-e", "$LOAD_PATH.unshift('lib'); require 'variform'"])
    assert r.returncode == 0, f"variform failed to load:\n{r.stderr}"
    return True


def test_cli_usage_on_no_subcommand():
    """The bare tool prints usage and exits non-zero."""
    r = _run(["ruby", str(BIN)])
    assert r.returncode == 2, (
        f"bare cli should exit 2 with usage; got {r.returncode}\n{r.stderr}"
    )
    assert "usage" in r.stderr.lower(), r.stderr


@pytest.mark.parametrize("fixture", sorted(p.name for p in VALID.glob("valid_*.json")))
def test_valid_corpus_plans(fixture):
    """Every well-formed spec, including the boundary cases, plans cleanly."""
    r = check_file(VALID / fixture)
    assert r.returncode == 0, f"{fixture} was rejected by the patched tool:\n{r.stderr}"


def test_boundary_valid_specs_still_plan():
    """The integer, hash-key, nested, offset, and letter-token boundary specs still plan."""
    for fixture in (
        "valid_006_quality_zero.json",
        "valid_007_hash_argument.json",
        "valid_008_nested_argument.json",
        "valid_009_offset_geometry.json",
        "valid_010_letter_tokens.json",
    ):
        r = check_file(VALID / fixture)
        assert r.returncode == 0, (
            f"{fixture} boundary-valid rejected; fix too aggressive:\n{r.stderr}"
        )


def test_exploit_passthrough_saver_rejected():
    """A spec using a pass-through writer method is refused (bug 1)."""
    r = check_file(EXPLOITS / "exploit_passthrough_saver.json")
    assert_clean_rejection(r, "passthrough_saver", METHOD_KEYWORDS, METHOD_RESOURCE)


def test_exploit_passthrough_apply_rejected():
    """A spec using the apply pass-through pipeline method is refused (bug 1)."""
    r = check_file(EXPLOITS / "exploit_passthrough_apply.json")
    assert_clean_rejection(r, "passthrough_apply", METHOD_KEYWORDS, METHOD_RESOURCE)


def test_generated_passthrough_rejected(tmp_path):
    """A freshly minted pass-through-method spec is refused (bug 1)."""
    marker = uuid.uuid4().hex
    spec = [{"name": "loader", "argument": f"msl:/tmp/{marker}.msl"}]
    assert_clean_rejection(
        check_spec(spec, tmp_path),
        "generated_passthrough",
        METHOD_KEYWORDS,
        METHOD_RESOURCE,
    )


def test_allowlist_drops_passthrough_methods():
    """method_allowlist.rb no longer lists apply, loader, or saver (bug 1)."""
    assert _allowlist_excludes_passthrough(_read(METHOD_ALLOWLIST)), (
        "method_allowlist.rb must drop the pass-through methods apply, loader, saver."
    )


def test_exploit_method_smuggle_rejected():
    """A method name carrying smuggled option tokens is refused (bug 2)."""
    r = check_file(EXPLOITS / "exploit_method_smuggle.json")
    assert_clean_rejection(r, "method_smuggle", METHOD_KEYWORDS, METHOD_RESOURCE)


def test_generated_method_smuggle_rejected(tmp_path):
    """A freshly minted smuggled-method spec is refused (bug 2)."""
    marker = uuid.uuid4().hex
    spec = [{"name": f"resize -write /tmp/{marker}.txt", "argument": "10x10"}]
    assert_clean_rejection(
        check_spec(spec, tmp_path),
        "generated_smuggle",
        METHOD_KEYWORDS,
        METHOD_RESOURCE,
    )


def test_method_gate_matches_exactly():
    """method_gate.rb matches a method exactly, not by substring (bug 2)."""
    assert _method_gate_uses_exact_match(_read(METHOD_GATE)), (
        "method_gate.rb must match a method name exactly against the allow-list, "
        "not by a substring check on the candidate name."
    )


def test_method_gate_rejects_name_reduction():
    """method_gate.rb matches the whole name, not a first-token reduction (bug 6)."""
    assert _method_gate_no_name_reduction(_read(METHOD_GATE)), (
        "method_gate.rb must match the method name as given; reducing it to its "
        "first whitespace-separated token lets a name carrying extra option tokens pass."
    )


def test_generated_method_canonical_whitespace_rejected(tmp_path):
    """A method name padded with whitespace and extra option tokens is refused (bug 6)."""
    marker = uuid.uuid4().hex
    spec = [{"name": f"  resize \t -write /tmp/{marker}.txt ", "argument": "10x10"}]
    assert_clean_rejection(
        check_spec(spec, tmp_path),
        "generated_canonical",
        METHOD_KEYWORDS,
        METHOD_RESOURCE,
    )


def test_exploit_case_flag_rejected():
    """A forbidden option supplied in upper case is refused (bug 3)."""
    r = check_file(EXPLOITS / "exploit_case_flag.json")
    assert_clean_rejection(r, "case_flag", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_case_flag_rejected(tmp_path):
    """A freshly minted mixed-case forbidden-option spec is refused (bug 3)."""
    marker = uuid.uuid4().hex
    spec = [{"name": "resize", "argument": f"-Write /tmp/{marker}.txt"}]
    assert_clean_rejection(
        check_spec(spec, tmp_path),
        "generated_case",
        ARGUMENT_KEYWORDS,
        ARGUMENT_RESOURCE,
    )


def test_scalar_scan_is_case_insensitive():
    """scalar_scan.rb lowercases the argument before the deny-list check (bug 3)."""
    assert _scalar_scan_is_case_insensitive(_read(SCALAR_SCAN)), (
        "scalar_scan.rb must compare the argument case-insensitively so a forbidden "
        "option in any letter case is caught."
    )


def test_exploit_plus_flag_rejected():
    """A forbidden option supplied in its plus form is refused (bug 7)."""
    r = check_file(EXPLOITS / "exploit_plus_flag.json")
    assert_clean_rejection(r, "plus_flag", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_plus_flag_rejected(tmp_path):
    """Freshly minted plus-form forbidden-option specs are refused (bug 7)."""
    marker = uuid.uuid4().hex
    for arg in (f"+write /tmp/{marker}.txt", f"+set registry:{marker} 1"):
        assert_clean_rejection(
            check_spec([{"name": "resize", "argument": arg}], tmp_path),
            "generated_plus",
            ARGUMENT_KEYWORDS,
            ARGUMENT_RESOURCE,
        )


def test_exploit_coder_indirection_rejected():
    """An argument carrying a coder pseudo-protocol is refused (bug 8)."""
    r = check_file(EXPLOITS / "exploit_coder_indirection.json")
    assert_clean_rejection(r, "coder_indirection", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_coder_indirection_rejected(tmp_path):
    """Freshly minted coder, at-file, and pipe indirections are refused (bug 8)."""
    marker = uuid.uuid4().hex
    for arg in (
        f"msl:/tmp/{marker}.msl",
        f"@/tmp/{marker}.lst",
        f"label:@/tmp/{marker}",
    ):
        assert_clean_rejection(
            check_spec([{"name": "resize", "argument": arg}], tmp_path),
            "generated_coder",
            ARGUMENT_KEYWORDS,
            ARGUMENT_RESOURCE,
        )


def test_exploit_coder_case_rejected():
    """A coder pseudo-protocol written in upper case is refused (bug 8)."""
    r = check_file(EXPLOITS / "exploit_coder_case.json")
    assert_clean_rejection(r, "coder_case", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_coder_case_rejected(tmp_path):
    """Forbidden options and coder schemes are caught in any letter case (bug 3, bug 8)."""
    marker = uuid.uuid4().hex
    for arg in (
        f"MSL:/tmp/{marker}.msl",
        f"Label:@/tmp/{marker}",
        f"+Write /tmp/{marker}.txt",
    ):
        assert_clean_rejection(
            check_spec([{"name": "resize", "argument": arg}], tmp_path),
            "generated_coder_case",
            ARGUMENT_KEYWORDS,
            ARGUMENT_RESOURCE,
        )


def test_exploit_hash_key_rejected():
    """A forbidden option used as an object key is refused (bug 4)."""
    r = check_file(EXPLOITS / "exploit_hash_key.json")
    assert_clean_rejection(r, "hash_key", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_hash_key_rejected(tmp_path):
    """A freshly minted forbidden-option-as-key spec is refused (bug 4)."""
    marker = uuid.uuid4().hex
    spec = [{"name": "resize", "argument": {"-write": f"/tmp/{marker}.txt"}}]
    assert_clean_rejection(
        check_spec(spec, tmp_path),
        "generated_hash_key",
        ARGUMENT_KEYWORDS,
        ARGUMENT_RESOURCE,
    )


def test_hash_scan_validates_keys():
    """validation/hash_scan.rb scans object keys as well as values (bug 4)."""
    assert _hash_scan_scans_keys(_read(HASH_SCAN)), (
        "hash_scan.rb must pass each object key through the scan, not only the value."
    )


def test_exploit_nested_list_rejected():
    """A forbidden option hidden in a nested array is refused (bug 5)."""
    r = check_file(EXPLOITS / "exploit_nested_list.json")
    assert_clean_rejection(r, "nested_list", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_nested_list_rejected(tmp_path):
    """A freshly minted deeply nested forbidden-option spec is refused (bug 5)."""
    marker = uuid.uuid4().hex
    spec = [{"name": "resize", "argument": ["10x10", ["-write", f"/tmp/{marker}.txt"]]}]
    assert_clean_rejection(
        check_spec(spec, tmp_path),
        "generated_nested",
        ARGUMENT_KEYWORDS,
        ARGUMENT_RESOURCE,
    )


def test_list_scan_recurses_into_nested_arguments():
    """validation/list_scan.rb recurses into nested arrays and objects (bug 5)."""
    assert _list_scan_recurses(_read(LIST_SCAN)), (
        "list_scan.rb must dispatch each array element back through the recursive "
        "argument scan rather than scanning only top-level strings."
    )


def test_exploit_mixed_nesting_rejected():
    """A forbidden option inside an object nested in an array is refused (bug 5)."""
    r = check_file(EXPLOITS / "exploit_mixed_nesting.json")
    assert_clean_rejection(r, "mixed_nesting", ARGUMENT_KEYWORDS, ARGUMENT_RESOURCE)


def test_generated_mixed_nesting_rejected(tmp_path):
    """Forbidden options in an object nested inside an array, as key or value, are
    refused (bug 5)."""
    marker = uuid.uuid4().hex
    specs = (
        [{"name": "resize", "argument": ["10x10", {"-write": f"/tmp/{marker}.txt"}]}],
        [
            {
                "name": "resize",
                "argument": ["10x10", {"to": f"-write /tmp/{marker}.txt"}],
            }
        ],
    )
    for spec in specs:
        assert_clean_rejection(
            check_spec(spec, tmp_path),
            "generated_mixed_nesting",
            ARGUMENT_KEYWORDS,
            ARGUMENT_RESOURCE,
        )


def test_policy_stays_in_library():
    """The CLI driver stays a thin dispatcher; no policy lives in bin/variform."""
    cli = _strip_ruby_comments(BIN.read_text())
    forbidden = [
        "ALLOWED",
        "FORBIDDEN",
        "downcase",
        "include?",
        "MethodGate",
        "MethodAllowlist",
        "ArgumentScan",
        "ScalarScan",
        "HashScan",
        "ListScan",
        "ArgumentDenylist",
        "permitted?",
    ]
    leaked = [t for t in forbidden if t in cli]
    assert not leaked, (
        f"bin/variform must stay a dispatcher; policy leaked into the CLI: {leaked}"
    )


def test_security_notes_covers_all_themes():
    """security_notes.md names every subsystem, weakness class, and attribution."""
    notes = ENV / "security_notes.md"
    assert notes.exists(), "security_notes.md was not written to /app/environment."
    body = notes.read_text().lower()
    themes = [
        [
            "allow-list",
            "allow list",
            "allowlist",
            "pass-through",
            "passthrough",
            "apply",
            "loader",
            "saver",
        ],
        [
            "method gate",
            "substring",
            "exact match",
            "exact",
            "exactly",
            "allowlist",
            "allow list",
            "allow-list",
            "whitelist",
            "canonical",
            "normaliz",
            "reduc",
            "split",
            "first token",
            "first word",
        ],
        [
            "canonical",
            "first whitespace",
            "first token",
            "first word",
            "leading",
            "whitespace",
            "token",
            "reduc",
            "split",
        ],
        ["case", "downcase"],
        ["plus form", "plus", "sign", "+write"],
        ["indirection", "coder", "scheme", "msl"],
        ["hash key", "object key", "key was", "keys"],
        ["nested", "recurse", "recursion"],
    ]
    for alternatives in themes:
        assert any(a in body for a in alternatives), (
            f"security_notes.md is missing any of {alternatives}."
        )
    for cwe in ("cwe-77", "cwe-94"):
        assert cwe in body, f"security_notes.md is missing {cwe}."
    assert "inspir" in body and "mit" in body, (
        "security_notes.md must cite the MIT-licensed inspiration."
    )
