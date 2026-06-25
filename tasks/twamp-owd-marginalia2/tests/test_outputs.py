"""Verifier for the TWAMP OWD audit task.

Builds the binary from /app source, runs it against the primary fixture,
re-runs against an alt fixture via env-var redirect, and asserts the
report shape, exact per-row values, anti-cheat invariants, and
determinism guarantees.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess

import pytest

APP_DIR = "/app"
APP_DATA = "/app/data"
APP_OUT_DIR = "/app/output"
APP_OUT = "/app/output/report.json"
APP_BIN = "/app/bin/auditor"
MAIN_GO = "/app/cmd/auditor/main.go"
ALT_DATA = "/tests/fixtures/alt_data"
TMP_DIR = "/tmp/twamp_test"

EXPECTED_DATA_DIGEST = "2f55ce3dad08b038403d75bb7fcd39484e1a5eab652f052244da733b28060e3a"
EXPECTED_ALT_DIGEST = "00e4a07355de8f692b244bcc47b8dab9c6e3b02e29f56605f53f079a8e7a3f52"
EXPECTED_PRIMARY_REPORT_DIGEST = (
    "7ce09d0dde975afd4891bb8a80082e0e1ed539cc2fefebea7ffaa9aba93e4c59"
)
EXPECTED_ALT_REPORT_DIGEST = (
    "ce17d6e9074dad71756f37dd469e69d7dc0f34e08579d54a752fdcfb6aee46d9"
)

ALL_VERDICTS = [
    "JITTER_FLAGGED",
    "LOSS_DETECTED",
    "OWD_ANOMALY",
    "QUIET_SUPPRESSED",
    "REFLECTOR_OFFLINE",
    "STALE_MEASUREMENT",
    "WITHIN_BOUNDS",
]


def tree_digest(root):
    h = hashlib.sha256()
    paths = []
    for d, _, fs in os.walk(root):
        for f in fs:
            paths.append(os.path.join(d, f))
    paths.sort()
    for p in paths:
        rel = os.path.relpath(p, root)
        with open(p, "rb") as fh:
            content = fh.read()
        h.update(rel.encode())
        h.update(b"\x00")
        h.update(hashlib.sha256(content).hexdigest().encode())
        h.update(b"\x00")
    return h.hexdigest()


def _go_env():
    """Return a process env where the Go toolchain is reachable.

    Defends against shells / sandboxes that strip PATH before invoking
    pytest. The Dockerfile installs Go at /usr/local/go/bin; we
    re-export it here so `make build` and direct `go build` calls
    always succeed regardless of how this test binary was launched.
    """
    env = os.environ.copy()
    path = env.get("PATH", "")
    if "/usr/local/go/bin" not in path:
        env["PATH"] = "/usr/local/go/bin:" + (path or "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
    env.setdefault("HOME", "/root")
    env.setdefault("GOCACHE", "/tmp/go-cache")
    env.setdefault("GOPATH", "/tmp/go-path")
    env.setdefault("GOFLAGS", "-mod=mod")
    env.setdefault("GOPROXY", "off")
    env.setdefault("GOSUMDB", "off")
    env.setdefault("GOTOOLCHAIN", "local")
    env.setdefault("CGO_ENABLED", "0")
    env.setdefault("XDG_CACHE_HOME", "/tmp")
    return env


def _build():
    if os.path.exists("/app/bin"):
        shutil.rmtree("/app/bin", ignore_errors=True)
    r = subprocess.run(
        ["make", "build"], cwd=APP_DIR, capture_output=True, text=True,
        env=_go_env(),
    )
    assert r.returncode == 0, f"build failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"


def _clear_output_dir():
    os.makedirs(APP_OUT_DIR, exist_ok=True)
    for e in os.listdir(APP_OUT_DIR):
        p = os.path.join(APP_OUT_DIR, e)
        if os.path.isfile(p):
            os.remove(p)


def _run(data_dir=APP_DATA, out_path=APP_OUT):
    env = _go_env()
    env["TWAMP_AUDIT_DATA_DIR"] = data_dir
    env["TWAMP_AUDIT_OUT_PATH"] = out_path
    r = subprocess.run([APP_BIN], env=env, capture_output=True, text=True)
    assert r.returncode == 0, f"auditor failed: rc={r.returncode}, stderr={r.stderr}"
    return r


@pytest.fixture(scope="module")
def primary_report():
    os.makedirs(TMP_DIR, exist_ok=True)
    pre = tree_digest(APP_DATA)
    _build()
    _clear_output_dir()
    # plant stale file to verify removal
    with open(os.path.join(APP_OUT_DIR, "stale.txt"), "w") as f:
        f.write("stale")
    _run()
    post = tree_digest(APP_DATA)
    assert pre == post, "input tree mutated by run"
    with open(APP_OUT, "rb") as f:
        raw = f.read()
    report = json.loads(raw)
    return report, raw


@pytest.fixture(scope="module")
def alt_report():
    alt_out = os.path.join(TMP_DIR, "alt_report.json")
    os.makedirs(TMP_DIR, exist_ok=True)
    if os.path.exists(alt_out):
        os.remove(alt_out)
    pre = tree_digest(ALT_DATA)
    _run(data_dir=ALT_DATA, out_path=alt_out)
    post = tree_digest(ALT_DATA)
    assert pre == post, "alt input tree mutated"
    with open(alt_out, "rb") as f:
        raw = f.read()
    return json.loads(raw), raw


# ---------- anti-cheat layer ----------

def test_input_tree_digest_primary():
    """A1: bake the primary data tree digest and re-verify at test time."""
    assert tree_digest(APP_DATA) == EXPECTED_DATA_DIGEST


def test_input_tree_digest_alt():
    """A1: bake the alt data tree digest and re-verify at test time."""
    assert tree_digest(ALT_DATA) == EXPECTED_ALT_DIGEST


def test_elf_magic(primary_report):
    """A6: built binary starts with the ELF magic header."""
    with open(APP_BIN, "rb") as f:
        head = f.read(4)
    assert head == b"\x7fELF", f"binary is not ELF: {head!r}"


def test_main_go_source_present():
    """A7: cmd/auditor/main.go must exist and be non-empty."""
    assert os.path.exists(MAIN_GO)
    assert os.path.getsize(MAIN_GO) > 0


def test_no_python_files_in_app():
    """No .py files may exist under /app outside expected locations."""
    bad = []
    for d, _, fs in os.walk(APP_DIR):
        for f in fs:
            if f.endswith(".py"):
                bad.append(os.path.join(d, f))
    assert bad == [], f"unexpected .py files under /app: {bad}"


def test_no_scaffolding_filenames():
    """No CLAUDE.md, AGENTS.md, skills.md, SKILLS.md anywhere under /app."""
    banned = {"CLAUDE.md", "AGENTS.md", "skills.md", "SKILLS.md", "BUGS.md", "TODO.md", "FIXME.md", "HINTS.md"}
    found = []
    for d, _, fs in os.walk(APP_DIR):
        for f in fs:
            if f in banned:
                found.append(os.path.join(d, f))
    assert found == [], f"banned scaffolding files found: {found}"


# ---------- determinism layer ----------

def test_idempotent_byte_identical(primary_report):
    """B1: re-running the binary must produce byte-identical output."""
    _, first = primary_report
    _clear_output_dir()
    _run()
    with open(APP_OUT, "rb") as f:
        second = f.read()
    assert first == second, "non-deterministic output"


def test_output_directory_exclusive(primary_report):
    """B2: /app/output contains exactly one file."""
    files = sorted(os.listdir(APP_OUT_DIR))
    assert files == ["report.json"], f"output dir not exclusive: {files}"


def test_stale_file_removed(primary_report):
    """B3: a planted stale.txt must be removed by the run."""
    assert not os.path.exists(os.path.join(APP_OUT_DIR, "stale.txt"))


def test_stale_directory_removed():
    """B3 extended: a planted stale subdirectory under /app/output must be removed by the run."""
    _clear_output_dir()
    stale_dir = os.path.join(APP_OUT_DIR, "stale_dir")
    os.makedirs(stale_dir, exist_ok=True)
    with open(os.path.join(stale_dir, "leftover.json"), "w") as f:
        f.write("{}")
    _run()
    assert sorted(os.listdir(APP_OUT_DIR)) == ["report.json"], (
        f"output dir not exclusive after stale dir plant: {os.listdir(APP_OUT_DIR)}"
    )


def test_build_from_clean_works():
    """B4: rebuilding from scratch produces a working binary."""
    if os.path.exists("/app/bin"):
        shutil.rmtree("/app/bin", ignore_errors=True)
    r = subprocess.run(["make", "build"], cwd=APP_DIR, capture_output=True, text=True)
    assert r.returncode == 0, f"clean build failed: {r.stderr}"
    assert os.path.exists(APP_BIN)


def test_input_files_immutable_post_run(primary_report):
    """A3: the input tree digest matches its pre-run snapshot."""
    assert tree_digest(APP_DATA) == EXPECTED_DATA_DIGEST


# ---------- output shape pins ----------

def test_trailing_newline(primary_report):
    """C1: file ends with exactly one trailing newline."""
    _, raw = primary_report
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_no_tabs(primary_report):
    """C: no tab characters anywhere in the report."""
    _, raw = primary_report
    assert b"\t" not in raw


def test_no_dot_zero_int_format(primary_report):
    """C4: no `.0` integer formatting on numeric JSON values."""
    _, raw = primary_report
    # match a JSON numeric value (not a string) ending in .0
    bad = re.search(rb":\s*-?\d+\.0(?=[,\}\]\s\n])", raw)
    assert bad is None, f"found .0 float-encoded integer at byte {bad.start() if bad else -1}"


def test_closed_enum_set(primary_report):
    """C6: by_verdict contains all seven verdict kinds."""
    rep, _ = primary_report
    assert set(rep["summary"]["by_verdict"].keys()) == set(ALL_VERDICTS)


def test_by_verdict_keys_lex_order(primary_report):
    """C2: by_verdict keys appear in lexical order."""
    _, raw = primary_report
    text = raw.decode()
    by_verdict_block = re.search(r'"by_verdict":\s*{([^}]*)}', text, re.DOTALL).group(1)
    keys = re.findall(r'"([A-Z_]+)":', by_verdict_block)
    assert keys == sorted(keys), f"by_verdict keys not lex: {keys}"


def test_top_level_key_order(primary_report):
    """top-level key order pinned: schema_version, summary, reflectors, cycles, probes, report_digest."""
    _, raw = primary_report
    text = raw.decode()
    # find top-level keys in order of appearance at column 0
    keys = re.findall(r'^  "([a-z_]+)":', text, re.MULTILINE)
    assert keys[:6] == ["schema_version", "summary", "reflectors", "cycles", "probes", "report_digest"], keys


def test_sum_cross_check(primary_report):
    """C7: sum of by_verdict counts equals total_probes."""
    rep, _ = primary_report
    s = sum(rep["summary"]["by_verdict"].values())
    assert s == rep["summary"]["total_probes"], (s, rep["summary"]["total_probes"])


def test_jitter_share_sums_to_1000(primary_report):
    """jitter_share_permille values must sum to exactly 1000."""
    rep, _ = primary_report
    total = sum(rep["summary"]["jitter_share_permille"].values())
    assert total == 1000


def test_jitter_share_numeric_suffix_order(primary_report):
    """C11: jitter_share_permille keys appear in numeric-suffix order (R1, R2, R3, R10, R11)."""
    _, raw = primary_report
    text = raw.decode()
    block = re.search(r'"jitter_share_permille":\s*{([^}]*)}', text, re.DOTALL).group(1)
    keys = re.findall(r'"(R[0-9]+)":', block)
    assert keys == ["R1", "R2", "R3", "R10", "R11"], keys


def test_report_digest_self_binding(primary_report):
    """C12: summary.report_digest equals top-level report_digest."""
    rep, _ = primary_report
    assert rep["summary"]["report_digest"] == rep["report_digest"]


def test_report_digest_exact(primary_report):
    """C12: report_digest matches the baked expected hex."""
    rep, _ = primary_report
    assert rep["report_digest"] == EXPECTED_PRIMARY_REPORT_DIGEST


# ---------- summary exact values ----------

def test_total_probes_exact(primary_report):
    """summary.total_probes equals the canonicalized + synthetic count."""
    rep, _ = primary_report
    assert rep["summary"]["total_probes"] == 16


def test_aligned_good_exact(primary_report):
    """summary.aligned_good counts WITHIN_BOUNDS probes."""
    rep, _ = primary_report
    assert rep["summary"]["aligned_good"] == 8


def test_cycles_count_exact(primary_report):
    """summary.cycles equals the number of distinct cycle_ids."""
    rep, _ = primary_report
    assert rep["summary"]["cycles"] == 3


def test_by_verdict_counts_exact(primary_report):
    """by_verdict per-kind counts match expected."""
    rep, _ = primary_report
    expected = {
        "JITTER_FLAGGED": 1,
        "LOSS_DETECTED": 1,
        "OWD_ANOMALY": 2,
        "QUIET_SUPPRESSED": 1,
        "REFLECTOR_OFFLINE": 2,
        "STALE_MEASUREMENT": 1,
        "WITHIN_BOUNDS": 8,
    }
    assert rep["summary"]["by_verdict"] == expected


def test_jitter_share_exact(primary_report):
    """jitter_share_permille exact distribution."""
    rep, _ = primary_report
    assert rep["summary"]["jitter_share_permille"] == {
        "R1": 250, "R2": 250, "R3": 250, "R10": 83, "R11": 167,
    }


# ---------- per-probe exact values ----------

def _probe(rep, pid):
    for p in rep["probes"]:
        if p["probe_id"] == pid:
            return p
    return None


def test_p1_within_bounds(primary_report):
    """P1 has owd_us 180 and is WITHIN_BOUNDS."""
    rep, _ = primary_report
    p = _probe(rep, "P1")
    assert p is not None
    assert p["owd_us"] == 180
    assert p["verdict"] == "WITHIN_BOUNDS"


def test_p2_owd_anomaly_canonical(primary_report):
    """P2 owd is recv_ts - send_ts - tx_ts (canonical), classified OWD_ANOMALY."""
    rep, _ = primary_report
    p = _probe(rep, "P2")
    assert p["owd_us"] == 900
    assert p["verdict"] == "OWD_ANOMALY"


def test_p3_magnitude_routing(primary_report):
    """P3 send_ts is in picoseconds; after routing the OWD matches the canonical."""
    rep, _ = primary_report
    p = _probe(rep, "P3")
    assert p is not None
    assert p["owd_us"] == 300
    assert p["verdict"] == "WITHIN_BOUNDS"


def test_p4_loss_detected(primary_report):
    """P4 has loss_flag=true so verdict is LOSS_DETECTED."""
    rep, _ = primary_report
    p = _probe(rep, "P4")
    assert p["verdict"] == "LOSS_DETECTED"


def test_p5_dedup_earliest_wins(primary_report):
    """P5 appears in both shards; the earliest send_ts wins (owd=350, not 400)."""
    rep, _ = primary_report
    p = _probe(rep, "P5")
    assert p is not None
    assert p["owd_us"] == 350
    assert p["verdict"] == "WITHIN_BOUNDS"


def test_p6_owd_anomaly_after_cascade(primary_report):
    """P6 owd is 450 > halved threshold 400, so OWD_ANOMALY after cascade."""
    rep, _ = primary_report
    p = _probe(rep, "P6")
    assert p["owd_us"] == 450
    assert p["verdict"] == "OWD_ANOMALY"


def test_p8_jitter_flagged(primary_report):
    """P8 has owd 50 in a cycle whose WITHIN_BOUNDS mean is 270; jitter > 150 → JITTER_FLAGGED."""
    rep, _ = primary_report
    p = _probe(rep, "P8")
    assert p["verdict"] == "JITTER_FLAGGED"


def test_p12_quiet_suppressed(primary_report):
    """P12 would be OWD_ANOMALY but is muted by a valid quiet_period marker."""
    rep, _ = primary_report
    p = _probe(rep, "P12")
    assert p["verdict"] == "QUIET_SUPPRESSED"


def test_pr1_strict_int_reject(primary_report):
    """PR1 has seq_no 42.5 and must be silently discarded at load time."""
    rep, _ = primary_report
    assert _probe(rep, "PR1") is None


def test_pout_validity_window_reject(primary_report):
    """POUT has send_ts past validity_window_end_us and must be silently dropped."""
    rep, _ = primary_report
    assert _probe(rep, "POUT") is None


def test_pstale_stale_measurement(primary_report):
    """PSTALE has recv_ts - send_ts > stale_max_us → STALE_MEASUREMENT."""
    rep, _ = primary_report
    p = _probe(rep, "PSTALE")
    assert p is not None
    assert p["verdict"] == "STALE_MEASUREMENT"


def test_synthetic_offline_rows_present(primary_report):
    """Synthetic REFLECTOR_OFFLINE rows are emitted for offline (cycle, reflector) pairs."""
    rep, _ = primary_report
    ids = {p["probe_id"] for p in rep["probes"]}
    assert "OFFLINE-R10-2" in ids
    assert "OFFLINE-R11-0" in ids


# ---------- per-cycle exact values ----------

def test_cycle_thresholds_cascade(primary_report):
    """Per-cycle thresholds: default 800, halved to 400 after cycle 0, halved to 200 after cycle 1."""
    rep, _ = primary_report
    by_cyc = {c["cycle_id"]: c for c in rep["cycles"]}
    assert by_cyc[0]["threshold_owd_us"] == 800
    assert by_cyc[1]["threshold_owd_us"] == 400
    assert by_cyc[2]["threshold_owd_us"] == 200


def test_cycle_contributors_numeric_suffix(primary_report):
    """Cycle contributors sorted by reflector_id numeric suffix."""
    rep, _ = primary_report
    by_cyc = {c["cycle_id"]: c for c in rep["cycles"]}
    assert by_cyc[1]["contributors"] == ["R1", "R2", "R3", "R10", "R11"]
    assert by_cyc[2]["contributors"] == ["R1", "R2", "R3", "R11"]


def test_cycle_counts_exact(primary_report):
    """Cycle probe_count, loss_count, anomaly_count exact values."""
    rep, _ = primary_report
    by_cyc = {c["cycle_id"]: c for c in rep["cycles"]}
    assert by_cyc[0]["probe_count"] == 4
    assert by_cyc[0]["loss_count"] == 1
    assert by_cyc[0]["anomaly_count"] == 1
    assert by_cyc[2]["anomaly_count"] == 0  # muted


# ---------- per-reflector exact values ----------

def test_reflector_rows_order(primary_report):
    """Reflector rows sorted by numeric suffix: R1, R2, R3, R10, R11."""
    rep, _ = primary_report
    ids = [r["reflector_id"] for r in rep["reflectors"]]
    assert ids == ["R1", "R2", "R3", "R10", "R11"]


def test_reflector_r2_anomaly_count(primary_report):
    """R2 anomaly_count is 2 (P2 + P6 both OWD_ANOMALY)."""
    rep, _ = primary_report
    r2 = next(r for r in rep["reflectors"] if r["reflector_id"] == "R2")
    assert r2["anomaly_count"] == 2
    assert r2["probe_count"] == 4


def test_reflector_r3_quiet_suppressed(primary_report):
    """R3 has one quiet_period_suppressed (P12)."""
    rep, _ = primary_report
    r3 = next(r for r in rep["reflectors"] if r["reflector_id"] == "R3")
    assert r3["quiet_period_suppressed"] == 1


def test_reflector_offline_observed(primary_report):
    """R10 and R11 each have at least one cycle with zero surviving probes."""
    rep, _ = primary_report
    r10 = next(r for r in rep["reflectors"] if r["reflector_id"] == "R10")
    r11 = next(r for r in rep["reflectors"] if r["reflector_id"] == "R11")
    assert r10["offline_observed"] is True
    assert r11["offline_observed"] is True


# ---------- probe ordering ----------

def test_probes_sorted_by_numeric_suffix(primary_report):
    """Probes array sorted by probe_id numeric suffix asc, lex within ties."""
    rep, _ = primary_report
    ids = [p["probe_id"] for p in rep["probes"]]

    def key(s):
        m = re.search(r"(\d+)$", s)
        return (int(m.group(1)) if m else 0, s)

    assert ids == sorted(ids, key=key)


# ---------- alt fixture (A5) ----------

def test_alt_report_digest(alt_report):
    """Alt fixture report digest matches baked alt expected."""
    rep, _ = alt_report
    assert rep["report_digest"] == EXPECTED_ALT_REPORT_DIGEST


def test_alt_descending_tiebreak(alt_report):
    """Alt fixture has reflectors offline → tiebreak descending → R3=445, R2=444."""
    rep, _ = alt_report
    shares = rep["summary"]["jitter_share_permille"]
    assert shares["R3"] == 445
    assert shares["R2"] == 444
    assert shares["R1"] == 111
    assert shares["R7"] == 0


def test_alt_closed_enum_set(alt_report):
    """Alt fixture also contains all 7 verdict kinds even when most are zero."""
    rep, _ = alt_report
    assert set(rep["summary"]["by_verdict"].keys()) == set(ALL_VERDICTS)
    assert rep["summary"]["by_verdict"]["JITTER_FLAGGED"] == 0
    assert rep["summary"]["by_verdict"]["STALE_MEASUREMENT"] == 0


# ---------- dynamic in-test mutation (A4) ----------

def test_dynamic_mutation_changes_output():
    """A4: appending a new probe row mutates the report; restore afterwards."""
    shard_b = os.path.join(APP_DATA, "probes_shard_b.ndjson")
    with open(shard_b, "rb") as f:
        backup = f.read()
    snap = tree_digest(APP_DATA)
    try:
        extra = (
            b'{"probe_id": "PEXTRA", "session_id": "S1", "cycle_id": 0, '
            b'"reflector_id": "R11", "send_ts": 50000004500, '
            b'"recv_ts": 50000004700, "tx_ts": 0, "seq_no": 99, '
            b'"recv_minus_send": 200, "loss_flag": false, "kind": "probe"}\n'
        )
        with open(shard_b, "ab") as f:
            f.write(extra)
        _clear_output_dir()
        _run()
        with open(APP_OUT) as f:
            rep = json.load(f)
        ids = {p["probe_id"] for p in rep["probes"]}
        assert "PEXTRA" in ids, "added probe must appear in report"
        # OFFLINE-R11-0 should now NOT exist (R11 has a cycle-0 probe)
        assert "OFFLINE-R11-0" not in ids, "synthetic offline must drop"
    finally:
        with open(shard_b, "wb") as f:
            f.write(backup)
        assert tree_digest(APP_DATA) == snap
        _clear_output_dir()
        _run()


# ---------- spec-source agreement ----------

def test_loader_no_float_fallback():
    """Loader strict-int must not silently accept floats (no ParseFloat fallback)."""
    with open("/app/internal/loader/loader.go") as f:
        src = f.read()
    assert "ParseFloat" not in src, "loader must not fall back to ParseFloat for strict-int fields"


def test_digest_separator_correct():
    """Digest module joins probe-ledger and reflector-ledger with the '##' separator."""
    with open("/app/internal/digest/digest.go") as f:
        src = f.read()
    assert '"\\n##\\n"' in src or "`\\n##\\n`" in src or '"\n##\n"' in src, "digest must use ## separator"
