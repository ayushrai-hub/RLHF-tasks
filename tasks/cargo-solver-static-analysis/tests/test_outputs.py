"""Verifier for the WaveBench AWK static-analysis audit task.

The agent must repair /app/scripts/audit.awk so that, when run against the four
workspace Cargo.toml files and /app/docs/validation_dossier.md, it produces three
deterministic TSV reports under /app/reports/:

    feature_gates.tsv     crate, feature_name, feature_deps, external_deps
    cfl_rules.tsv         rule_id, affected_features, constraint_type, bound_value, source
    audit_violations.tsv  crate, feature_name, violation_type, severity, rule_id
    cfl_margins.tsv       crate, feature_name, effective_cfl_max, binding_rule

Violations and CFL margins are determined by resolving each feature's TRANSITIVE
closure through the workspace feature graph, honouring Cargo's per-manifest
weak-dependency (`crate?/feature`) semantics: a weak enable only fires when that
optional crate dependency is also strongly activated within the same manifest. The
manifests use multi-line feature arrays with trailing commas and inline comments, so
the parser must accumulate across lines, not read a single `=` line.

These tests verify the *content* of the reports (the audit conclusions), not the
implementation. Feature-gate facts are re-derived directly from the Cargo manifests
so the agent cannot pass by hardcoding answer tables, and the script is re-run to
confirm the output is byte-for-byte reproducible.
"""

import re
import shutil
import subprocess
from pathlib import Path

APP = Path("/app")
REPORTS = APP / "reports"
SCRIPTS = APP / "scripts"
WORKSPACE = APP / "wavebench"
DOSSIER = APP / "docs" / "validation_dossier.md"

FEATURE_GATES = REPORTS / "feature_gates.tsv"
CFL_RULES = REPORTS / "cfl_rules.tsv"
VIOLATIONS = REPORTS / "audit_violations.tsv"
CFL_MARGINS = REPORTS / "cfl_margins.tsv"

CRATES = [
    "wavebench-core",
    "wavebench-adaptive",
    "wavebench-io",
    "wavebench-vis",
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def read_tsv(path: Path):
    """Return (header, rows) where rows is a list of lists of cell strings."""
    assert path.exists(), f"Expected report {path} does not exist"
    text = path.read_text()
    assert text.endswith("\n"), f"{path} must end with a trailing newline"
    lines = text.rstrip("\n").split("\n")
    assert lines, f"{path} is empty"
    header = lines[0].split("\t")
    rows = [ln.split("\t") for ln in lines[1:]]
    return header, rows


def parse_cargo_features():
    """Re-derive the expected feature gate map directly from the Cargo manifests.

    Returns dict: (crate, feature) -> {"feature_deps": [...], "external_deps": [...]}.
    dep:-prefixed entries are external; crate/feat and crate?/feat enables are
    feature deps kept intact.
    """
    out = {}
    for crate in CRATES:
        toml = (WORKSPACE / crate / "Cargo.toml").read_text()
        m = re.search(r"(?ms)^\[features\]\s*$(.*?)(^\[|\Z)", toml)
        assert m, f"no [features] table in {crate}/Cargo.toml"
        # Strip inline comments line-by-line, then match arrays across newlines so
        # multi-line / trailing-comma feature definitions are handled correctly.
        block = "\n".join(re.sub(r"#.*", "", ln) for ln in m.group(1).splitlines())
        for fm in re.finditer(r"([A-Za-z0-9_-]+)\s*=\s*\[(.*?)\]", block, re.S):
            fname = fm.group(1)
            entries = re.findall(r'"([^"]+)"', fm.group(2))
            fdeps, edeps = [], []
            for e in entries:
                if e.startswith("dep:"):
                    edeps.append(e[len("dep:"):])
                else:
                    fdeps.append(e)
            out[(crate, fname)] = {
                "feature_deps": sorted(fdeps),
                "external_deps": sorted(edeps),
            }
    return out


# --------------------------------------------------------------------------- #
# Milestone 1 — feature gate map
# --------------------------------------------------------------------------- #
def test_feature_gates_header():
    """feature_gates.tsv has the exact required column header and order."""
    header, _ = read_tsv(FEATURE_GATES)
    assert header == ["crate", "feature_name", "feature_deps", "external_deps"], header


def test_feature_gates_complete_and_sorted():
    """Every (crate, feature) from all four manifests appears exactly once, and
    rows are sorted by (crate, feature_name)."""
    _, rows = read_tsv(FEATURE_GATES)
    expected = parse_cargo_features()
    seen = [(r[0], r[1]) for r in rows]
    assert len(seen) == len(set(seen)), f"duplicate rows: {seen}"
    assert set(seen) == set(expected.keys()), (
        f"feature set mismatch.\nmissing={set(expected) - set(seen)}\n"
        f"extra={set(seen) - set(expected)}"
    )
    assert seen == sorted(seen), "rows not sorted by (crate, feature_name)"


def test_feature_gates_dep_classification():
    """dep: entries land in external_deps; crate/feat and crate?/feat enables stay
    in feature_deps intact; each dep list is sorted."""
    _, rows = read_tsv(FEATURE_GATES)
    expected = parse_cargo_features()
    for r in rows:
        assert len(r) == 4, f"row has wrong column count: {r}"
        crate, fname, fdeps_s, edeps_s = r
        fdeps = fdeps_s.split(",") if fdeps_s else []
        edeps = edeps_s.split(",") if edeps_s else []
        exp = expected[(crate, fname)]
        assert fdeps == exp["feature_deps"], (
            f"{crate}/{fname} feature_deps {fdeps} != {exp['feature_deps']}"
        )
        assert edeps == exp["external_deps"], (
            f"{crate}/{fname} external_deps {edeps} != {exp['external_deps']}"
        )


def test_optional_dep_syntax_preserved():
    """Every crate?/feature optional-dependency token is preserved verbatim and
    classified as a feature dep, never split on ?/ nor moved to external_deps."""
    _, rows = read_tsv(FEATURE_GATES)
    by_key = {(r[0], r[1]): r for r in rows}
    cases = {
        ("wavebench-vis", "adaptive-preview"): "wavebench-adaptive?/weno5",
        ("wavebench-io", "guarded-stream"): "wavebench-adaptive?/tvd-limiter",
        ("wavebench-vis", "guarded-vis"): "wavebench-adaptive?/tvd-limiter",
    }
    for key, token in cases.items():
        assert key in by_key, f"{key} row missing"
        fdeps = by_key[key][2].split(",")
        assert token in fdeps, f"{key}: optional-dep token mangled, got {fdeps}"


def test_cross_crate_enable_kept_in_feature_deps():
    """A cross-crate enable like wavebench-core/adaptive-cfl belongs in feature_deps."""
    _, rows = read_tsv(FEATURE_GATES)
    row = [r for r in rows if r[0] == "wavebench-io" and r[1] == "streaming-io"][0]
    fdeps = row[2].split(",")
    assert "wavebench-core/adaptive-cfl" in fdeps, fdeps
    assert "async-io" in fdeps, fdeps


# --------------------------------------------------------------------------- #
# Milestone 2 — CFL rule extraction
# --------------------------------------------------------------------------- #
EXPECTED_RULES = {
    "R-001": ["standard-cfl", "max_cfl", "1.0", "section-2.1"],
    "R-002": ["rk4", "max_cfl", "2.8284", "section-3.2"],
    "R-003": ["weno5", "max_cfl", "1.6", "section-3.4"],
    "R-004": ["tvd-limiter", "max_cfl", "1.0", "review-RC-012"],
    "R-005": ["lax-wendroff", "max_cfl", "1.0", "review-RC-019"],
    "R-006": ["gpu-accel+adaptive-cfl", "prohibited_combination", "none", "note-MN-019"],
    "R-007": ["hpc-mode", "requires_guard", "weno5", "note-MN-024"],
    "R-008": ["lax-wendroff+adaptive-cfl", "prohibited_combination", "none", "errata-E-007"],
    "R-009": ["unstable-integrator", "requires_guard", "tvd-limiter", "errata-E-003"],
    "R-010": ["streaming-io", "requires_guard", "tvd-limiter", "errata-E-011"],
    "R-011": ["adaptive-cfl+weno5", "prohibited_combination", "none", "note-MN-031"],
}


def test_cfl_rules_header():
    """cfl_rules.tsv has the exact required column header and order."""
    header, _ = read_tsv(CFL_RULES)
    assert header == [
        "rule_id",
        "affected_features",
        "constraint_type",
        "bound_value",
        "source",
    ], header


def test_cfl_rules_all_present_and_sorted():
    """All eleven active rules (R-001..R-011) are extracted, none missing, none
    extra, and rows are sorted by rule_id. This requires reading rules encoded in
    section headings, reviewer blockquotes, method-note prose, and the errata table."""
    _, rows = read_tsv(CFL_RULES)
    ids = [r[0] for r in rows]
    assert ids == sorted(ids), "rules not sorted by rule_id"
    assert set(ids) == set(EXPECTED_RULES), (
        f"rule id mismatch.\nmissing={set(EXPECTED_RULES) - set(ids)}\n"
        f"extra={set(ids) - set(EXPECTED_RULES)}"
    )


def test_cfl_rules_exact_values():
    """Each extracted rule carries the exact affected_features, constraint_type,
    bound_value, and source recorded in the dossier (errata source is errata-E-NNN)."""
    _, rows = read_tsv(CFL_RULES)
    got = {r[0]: r[1:] for r in rows}
    for rid, exp in EXPECTED_RULES.items():
        assert got[rid] == exp, f"{rid}: {got[rid]} != {exp}"


def test_decoy_rules_excluded():
    """Rules whose annotation status is not 'active' (superseded/withdrawn/rejected/
    draft/example) must NOT be extracted, and the superseded R-002 bound (2.0) must
    not override the authoritative value (2.8284)."""
    _, rows = read_tsv(CFL_RULES)
    got = {r[0]: r[1:] for r in rows}
    for decoy in ("R-014", "R-021", "R-030", "R-040"):
        assert decoy not in got, f"decoy rule {decoy} should not be present"
    assert got["R-002"][2] == "2.8284", "superseded R-002 bound leaked into output"


# --------------------------------------------------------------------------- #
# Milestone 3 — violations (transitive closure + weak-dep semantics)
# --------------------------------------------------------------------------- #
EXPECTED_VIOLATIONS = [
    ["wavebench-core", "experimental", "MISSING_GUARD", "CRITICAL", "R-009"],
    ["wavebench-core", "gpu-accel", "PROHIBITED_COMBINATION", "CRITICAL", "R-006"],
    ["wavebench-core", "hpc-mode", "MISSING_GUARD", "WARNING", "R-007"],
    ["wavebench-core", "unstable-integrator", "MISSING_GUARD", "CRITICAL", "R-009"],
    ["wavebench-io", "guarded-stream", "MISSING_GUARD", "WARNING", "R-010"],
    ["wavebench-io", "streaming-io", "MISSING_GUARD", "WARNING", "R-010"],
    ["wavebench-vis", "lax-wendroff-vis", "PROHIBITED_COMBINATION", "CRITICAL", "R-008"],
]


def test_violations_header():
    """audit_violations.tsv has the exact required column header and order."""
    header, _ = read_tsv(VIOLATIONS)
    assert header == [
        "crate",
        "feature_name",
        "violation_type",
        "severity",
        "rule_id",
    ], header


def test_violations_exact_set():
    """Exactly the seven expected violations are reported, with correct
    violation_type, severity, and rule_id, sorted by (crate, feature_name)."""
    _, rows = read_tsv(VIOLATIONS)
    assert rows == EXPECTED_VIOLATIONS, f"violations mismatch:\n{rows}"


def test_violations_reference_existing_rules():
    """Every violation's rule_id must exist in cfl_rules.tsv (cross-report consistency)."""
    _, vrows = read_tsv(VIOLATIONS)
    _, rrows = read_tsv(CFL_RULES)
    rule_ids = {r[0] for r in rrows}
    for v in vrows:
        assert v[4] in rule_ids, f"violation references unknown rule {v[4]}"


def test_weak_dependency_semantics():
    """Per-manifest weak-dependency (crate?/feature) resolution must be correct:

    - wavebench-io/guarded-stream MUST be flagged (R-010): its `wavebench-adaptive?/
      tvd-limiter` guard does NOT fire because wavebench-io never strongly activates
      its optional wavebench-adaptive dependency, so the tvd-limiter guard is absent.
    - wavebench-vis/guarded-vis MUST NOT be flagged: it strongly activates
      wavebench-adaptive (dep:), so `wavebench-adaptive?/tvd-limiter` fires and the
      guard is satisfied even though it transitively enables unstable-integrator.
    - wavebench-vis/adaptive-preview MUST NOT be flagged: `wavebench-adaptive?/weno5`
      does not fire, so the adaptive-cfl+weno5 combination is never formed.
    """
    _, rows = read_tsv(VIOLATIONS)
    flagged = {(r[0], r[1]) for r in rows}
    assert ("wavebench-io", "guarded-stream") in flagged, (
        "guarded-stream must be flagged: its weak tvd-limiter guard does not fire"
    )
    assert ("wavebench-vis", "guarded-vis") not in flagged, (
        "guarded-vis must NOT be flagged: its weak tvd-limiter guard fires"
    )
    assert ("wavebench-vis", "adaptive-preview") not in flagged, (
        "adaptive-preview must NOT be flagged: its weak weno5 enable does not fire"
    )


def test_no_false_positive_on_safe_features():
    """Features that are safe must not appear as violations."""
    _, rows = read_tsv(VIOLATIONS)
    flagged = {(r[0], r[1]) for r in rows}
    for safe in [
        ("wavebench-adaptive", "weno5"),
        ("wavebench-adaptive", "high-order"),
        ("wavebench-core", "default"),
        ("wavebench-core", "adaptive-cfl"),
        ("wavebench-vis", "plot"),
        ("wavebench-vis", "adaptive-preview"),
        ("wavebench-vis", "guarded-vis"),
        ("wavebench-io", "async-io"),
        ("wavebench-io", "hdf5-output"),
    ]:
        assert safe not in flagged, f"{safe} should not be flagged"


# --------------------------------------------------------------------------- #
# CFL margins — effective ceiling via min-reduction over the transitive closure
# --------------------------------------------------------------------------- #
EXPECTED_MARGINS = {
    ("wavebench-adaptive", "default"): ["", "none"],
    ("wavebench-adaptive", "high-order"): ["1.0000", "R-004"],
    ("wavebench-adaptive", "lax-wendroff"): ["1.0000", "R-005"],
    ("wavebench-adaptive", "mixed-scheme"): ["1.0000", "R-004"],
    ("wavebench-adaptive", "rk4"): ["2.8284", "R-002"],
    ("wavebench-adaptive", "tvd-limiter"): ["1.0000", "R-004"],
    ("wavebench-adaptive", "weno5"): ["1.0000", "R-004"],
    ("wavebench-core", "adaptive-cfl"): ["", "none"],
    ("wavebench-core", "default"): ["1.0000", "R-001"],
    ("wavebench-core", "experimental"): ["", "none"],
    ("wavebench-core", "gpu-accel"): ["", "none"],
    ("wavebench-core", "hpc-mode"): ["", "none"],
    ("wavebench-core", "parallel-io"): ["", "none"],
    ("wavebench-core", "standard-cfl"): ["1.0000", "R-001"],
    ("wavebench-core", "unstable-integrator"): ["", "none"],
    ("wavebench-io", "async-io"): ["", "none"],
    ("wavebench-io", "default"): ["", "none"],
    ("wavebench-io", "guarded-stream"): ["", "none"],
    ("wavebench-io", "hdf5-output"): ["", "none"],
    ("wavebench-io", "streaming-io"): ["", "none"],
    ("wavebench-vis", "adaptive-preview"): ["", "none"],
    ("wavebench-vis", "default"): ["", "none"],
    ("wavebench-vis", "guarded-vis"): ["1.0000", "R-004"],
    ("wavebench-vis", "lax-wendroff-vis"): ["1.0000", "R-005"],
    ("wavebench-vis", "plot"): ["", "none"],
}


def test_cfl_margins_header():
    """cfl_margins.tsv has the exact required column header and order."""
    header, _ = read_tsv(CFL_MARGINS)
    assert header == ["crate", "feature_name", "effective_cfl_max", "binding_rule"], header


def test_cfl_margins_complete_and_sorted():
    """cfl_margins.tsv lists every workspace feature exactly once, sorted by
    (crate, feature_name) — the same set of features as feature_gates.tsv."""
    _, mrows = read_tsv(CFL_MARGINS)
    _, frows = read_tsv(FEATURE_GATES)
    margin_keys = [(r[0], r[1]) for r in mrows]
    gate_keys = [(r[0], r[1]) for r in frows]
    assert margin_keys == sorted(margin_keys), "cfl_margins not sorted"
    assert set(margin_keys) == set(gate_keys), "cfl_margins feature set != feature_gates"


def test_cfl_margins_values():
    """Each feature's effective_cfl_max is the smallest applicable max_cfl bound over
    its transitive closure (4-decimal formatted), with binding_rule the rule_id that
    achieves it; features with no applicable max_cfl rule get empty value + 'none'."""
    _, rows = read_tsv(CFL_MARGINS)
    got = {(r[0], r[1]): r[2:] for r in rows}
    for key, exp in EXPECTED_MARGINS.items():
        assert got[key] == exp, f"{key}: {got[key]} != {exp}"


def test_cfl_margins_tie_break():
    """When several max_cfl rules share the smallest bound, binding_rule is the
    smallest rule_id: mixed-scheme's closure hits both tvd-limiter (R-004) and
    lax-wendroff (R-005) at 1.0, so R-004 must win."""
    _, rows = read_tsv(CFL_MARGINS)
    got = {(r[0], r[1]): r[2:] for r in rows}
    assert got[("wavebench-adaptive", "mixed-scheme")] == ["1.0000", "R-004"], (
        f"tie-break wrong: {got[('wavebench-adaptive', 'mixed-scheme')]}"
    )


def test_cfl_margins_four_decimal_formatting():
    """Every non-empty effective_cfl_max is formatted to exactly four decimals."""
    _, rows = read_tsv(CFL_MARGINS)
    for r in rows:
        val = r[2]
        if val == "":
            assert r[3] == "none", f"empty margin must pair with 'none': {r}"
        else:
            assert re.fullmatch(r"\d+\.\d{4}", val), f"bad CFL formatting: {val!r} in {r}"


# --------------------------------------------------------------------------- #
# Reproducibility / anti-hardcoding
# --------------------------------------------------------------------------- #
def test_idempotent_and_script_driven(tmp_path):
    """Re-running the repaired script regenerates byte-identical reports, proving the
    output is produced by the script (not hand-written) and is deterministic."""
    assert shutil.which("gawk"), "gawk must be installed in the image"
    script = SCRIPTS / "audit.awk"
    assert script.exists(), "/app/scripts/audit.awk missing"

    backup = tmp_path / "backup"
    backup.mkdir()
    for f in (FEATURE_GATES, CFL_RULES, VIOLATIONS, CFL_MARGINS):
        shutil.copy(f, backup / f.name)

    proc = subprocess.run(
        [
            "gawk",
            "-f",
            str(script),
            str(WORKSPACE / "wavebench-core" / "Cargo.toml"),
            str(WORKSPACE / "wavebench-adaptive" / "Cargo.toml"),
            str(WORKSPACE / "wavebench-io" / "Cargo.toml"),
            str(WORKSPACE / "wavebench-vis" / "Cargo.toml"),
            str(DOSSIER),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"re-running audit.awk failed: {proc.stderr}"

    for f in (FEATURE_GATES, CFL_RULES, VIOLATIONS, CFL_MARGINS):
        assert f.read_bytes() == (backup / f.name).read_bytes(), (
            f"{f.name} changed on re-run — output is not deterministic/script-driven"
        )
