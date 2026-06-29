"""Verifier for psi4-screening-cache-stale."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

P7_TRACE_OUT = "/app/output/p7_trace.json"
OUT = Path(P7_TRACE_OUT)
RUNTIME = Path("/app/runtime")
WAL = RUNTIME / "wal.log"
SEAL = RUNTIME / "checkpoint.seal"
CASES = Path("/app/cases/seq")
P7_RUN = "/app/environment/tools/p7_run"
P7_EMIT = "/app/environment/tools/p7_emit"
P7_RECOVER = "/app/environment/tools/p7_recover"
P7_INSPECT = "/app/environment/tools/p7_inspect"


def reset_runtime():
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()


def replay(cold=False, scenario=None):
    if scenario is not None and cold:
        subprocess.run(
            [P7_RUN, "--cold", "--scenario", str(scenario)],
            check=True,
            capture_output=True,
            text=True,
        )
    elif scenario is not None:
        subprocess.run(
            [P7_RUN, "--scenario", str(scenario)],
            check=True,
            capture_output=True,
            text=True,
        )
    elif cold:
        subprocess.run([P7_RUN, "--cold"], check=True, capture_output=True, text=True)
    else:
        subprocess.run([P7_RUN], check=True, capture_output=True, text=True)


def emit():
    subprocess.run([P7_EMIT, "--out", P7_TRACE_OUT], check=True, capture_output=True, text=True)


def recover():
    subprocess.run([P7_RECOVER], check=True, capture_output=True, text=True)


def load_trace():
    return json.loads(OUT.read_text())


def body_digest(epochs):
    payload = json.dumps(epochs, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def load_fixture_gen(sid, fname, field):
    text = (CASES / f"s{sid}" / fname).read_text()
    for line in text.splitlines():
        if line.startswith(field + "="):
            return int(line.split("=", 1)[1])
    raise KeyError(field)


def wal_lines():
    if not WAL.exists():
        return []
    return [ln.strip() for ln in WAL.read_text().splitlines() if ln.strip()]


def parse_wal():
    out = []
    for raw in wal_lines():
        parts = raw.split("|")
        if len(parts) != 4:
            continue
        out.append({"seq": int(parts[0]), "opcode": parts[1], "scenario": int(parts[2]), "crc": int(parts[3])})
    return out


def replay_chain_through(max_sid, cold_start=False):
    """Replay scenarios 0..max_sid in order; self-contained setup for partial-chain tests."""
    if cold_start:
        reset_runtime()
        replay(cold=True, scenario=0)
    else:
        replay(cold=True, scenario=0)
    for sid in range(1, max_sid + 1):
        replay(scenario=sid)


def seal_from_wal(lines):
    """Recompute checkpoint seal per instruction checkpoint seal rule."""
    base = 0
    for ln in lines:
        base = (base + ln["crc"]) & 0xFFFFFFFF
    beef = 0
    for prev, cur in zip(lines, lines[1:]):
        if prev["opcode"] == "bust_w3" and cur["opcode"] == "screen_ok":
            beef = (beef + 0xBEEF) & 0xFFFFFFFF
    return (base + beef) & 0xFFFFFFFF


def inspect_counters():
    proc = subprocess.run([P7_INSPECT], check=True, capture_output=True, text=True)
    text = proc.stdout.strip()
    screen = swap = delta = None
    for part in text.split():
        if part.startswith("screen="):
            screen = int(part.split("=", 1)[1])
        elif part.startswith("swap="):
            swap = int(part.split("=", 1)[1])
        elif part.startswith("delta="):
            delta = int(part.split("=", 1)[1])
    return screen, swap, delta


@pytest.fixture(autouse=True)
def fresh_replay():
    """Cold replay s0–s4 then emit before each test (instruction baseline pipeline)."""
    reset_runtime()
    replay(cold=True)
    emit()
    yield


def test_u00_cold_warm_parity():
    """Cold and warm replay of scenario s0 produce identical epochs and body_digest (instruction)."""
    replay(cold=True, scenario=0)
    emit()
    cold_doc = load_trace()
    reset_runtime()
    replay(cold=True, scenario=0)
    replay(scenario=0)
    emit()
    warm_doc = load_trace()
    assert cold_doc["epochs"] == warm_doc["epochs"]
    assert cold_doc["body_digest"] == warm_doc["body_digest"]


def test_u01_beta_skew():
    """Scenario s1 live view includes non-zero action_code and generation gap (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    s1 = [r for r in doc["epochs"] if r["scenario"] == 1]
    live = [r for r in s1 if r["view"] == "live"]
    screen = next(r for r in s1 if r["view"] == "screen")
    swap = next(r for r in s1 if r["view"] == "swap")
    assert live
    assert any(r["action_code"] != 0 for r in live)
    assert live[0]["generation"] > screen["generation"]
    assert live[0]["generation"] > swap["generation"]


def test_u02_gamma_gap():
    """When live generation exceeds tab generation, live rows carry non-zero action_code (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    for sid in range(1, 5):
        rows = [r for r in doc["epochs"] if r["scenario"] == sid]
        tab = next((r for r in rows if r["view"] == "screen"), None)
        live = [r for r in rows if r["view"] == "live"]
        if tab and live and live[0]["generation"] > tab["generation"]:
            assert any(r["action_code"] != 0 for r in live)


def test_u03_delta_bust():
    """WAL records bust_w3 immediately before each screen_ok (instruction WAL integrity)."""
    replay(cold=True)
    lines = parse_wal()
    for prev, cur in zip(lines, lines[1:]):
        if cur["opcode"] == "screen_ok":
            assert prev["opcode"] == "bust_w3"


def test_u04_chain_monotone():
    """WAL sequence numbers strictly increase with no duplicates (p7_contract § WAL append log)."""
    replay(cold=True)
    seqs = [ln["seq"] for ln in parse_wal()]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)


def test_u05_hash_parity():
    """body_digest matches epochs-array recomputation; tab generations match fixtures (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    assert doc["body_digest"] == body_digest(doc["epochs"])
    for sid in range(5):
        tab = next(r for r in doc["epochs"] if r["scenario"] == sid and r["view"] == "screen")
        assert tab["generation"] == load_fixture_gen(sid, "a0.scn", "screen_gen")


def test_u06_repeat_stable():
    """Consecutive p7_emit runs after the same replay yield identical body_digest and seal (instruction)."""
    replay(cold=True)
    emit()
    d1 = load_trace()["body_digest"]
    seal1 = SEAL.read_text().strip()
    emit()
    d2 = load_trace()["body_digest"]
    seal2 = SEAL.read_text().strip()
    assert d1 == d2
    assert seal1 == seal2


def test_u07_s0_survives():
    """Checkpoint poison plus rebuild restores seals and preserves s0 baseline (instruction)."""
    SEAL.write_text("999999\n")
    proc = subprocess.run([P7_EMIT, "--out", P7_TRACE_OUT], check=False, capture_output=True, text=True)
    assert proc.returncode != 0
    recover()
    emit()
    doc = load_trace()
    s0 = [r for r in doc["epochs"] if r["scenario"] == 0]
    assert s0
    assert all(r["generation"] == 1 for r in s0)


def test_u08_step_chain():
    """Repeating scenario s1 is idempotent and WAL retains bust_w3 entries (instruction)."""
    replay(cold=True, scenario=1)
    emit()
    first = load_trace()["epochs"]
    replay(scenario=1)
    emit()
    second = load_trace()["epochs"]
    assert first == second
    lines = parse_wal()
    assert any(ln["opcode"] == "bust_w3" for ln in lines)


def test_u09_denied_case():
    """Scenario s3 live view emits action_code 9 for revocation deny (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    s3 = [r for r in doc["epochs"] if r["scenario"] == 3]
    live = [r for r in s3 if r["view"] == "live"]
    assert live and any(r["action_code"] == 9 for r in live)


def test_u10_abs_shift():
    """Scenario s3 live generation meets or exceeds fixture live_gen (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    s3_live = next(r for r in doc["epochs"] if r["scenario"] == 3 and r["view"] == "live")
    assert s3_live["generation"] >= load_fixture_gen(3, "a0.scn", "live_gen")


def test_u11_double_rebuild_stable():
    """Double p7_recover is idempotent and emit still succeeds (instruction recovery)."""
    replay(cold=True)
    recover()
    recover()
    emit()
    assert OUT.exists()


def test_u12_partial_seal_rejected():
    """Partial replay through s3 omits s4 rows; s4 readopt changes body_digest (instruction)."""
    reset_runtime()
    replay_chain_through(3, cold_start=True)
    emit()
    partial = load_trace()
    assert all(r["scenario"] <= 3 for r in partial["epochs"])
    replay(scenario=4)
    emit()
    full = load_trace()
    assert partial["body_digest"] != full["body_digest"]
    assert any(r["scenario"] == 4 for r in full["epochs"])


def test_u13_delayed_shift():
    """Emit refuses invalid WAL line checksum even when checkpoint seal is forced valid (instruction)."""
    replay(cold=True)
    lines = wal_lines()
    if not lines:
        pytest.skip("no wal")
    parts = lines[0].split("|")
    parts[-1] = "0"
    bad = "|".join(parts)
    WAL.write_text("\n".join([bad] + lines[1:]) + "\n")
    SEAL.write_text("1\n")
    proc = subprocess.run([P7_EMIT, "--out", P7_TRACE_OUT], check=False, capture_output=True, text=True)
    assert proc.returncode != 0


def test_u14_s4_readopt_after_deny():
    """Scenario s4 readopt clears live denies after full chain replay (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    s4_live = [r for r in doc["epochs"] if r["scenario"] == 4 and r["view"] == "live"]
    assert s4_live and all(r["action_code"] != 9 for r in s4_live)


def test_u15_s4_late_wrap():
    """WAL sequence ids start at one on cold replay (p7_contract § WAL append log)."""
    replay(cold=True)
    seqs = [ln["seq"] for ln in parse_wal()]
    assert min(seqs) >= 1
    for a, b in zip(seqs, seqs[1:]):
        assert b > a


def test_u16_cross_scope_monotone():
    """Checkpoint seal equals WAL CRC sum plus 0xBEEF per bust_w3/screen_ok pair (instruction)."""
    replay(cold=True)
    lines = parse_wal()
    seal = int(SEAL.read_text().strip())
    assert seal == seal_from_wal(lines)


def test_u17_sync_gen_alignment():
    """Sync-phase generations align across screen and swap views on s4; inspect counters match (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    s4 = [r for r in doc["epochs"] if r["scenario"] == 4]
    tab = next(r for r in s4 if r["view"] == "screen")
    deploy = next(r for r in s4 if r["view"] == "swap")
    assert tab["generation"] == deploy["generation"]
    assert deploy["generation"] == load_fixture_gen(4, "b0.swp", "swap_gen")
    screen_i, swap_i, delta_i = inspect_counters()
    assert screen_i == tab["generation"]
    assert swap_i == deploy["generation"]
    assert delta_i == 0


def test_u18_triple_repeat_s1_stable():
    """Triple replay of scenario s1 leaves epochs unchanged (instruction idempotence)."""
    replay(cold=True, scenario=1)
    emit()
    first = load_trace()["epochs"]
    replay(scenario=1)
    replay(scenario=1)
    emit()
    third = load_trace()["epochs"]
    assert first == third


def test_u19_narrow_block_rms():
    """Scenario s0 screen-view block_rms stays within narrow T7 tolerance (instruction)."""
    replay(cold=True)
    emit()
    doc = load_trace()
    for row in doc["epochs"]:
        if row["scenario"] == 0:
            assert row["block_rms"] <= 1e-4
