"""Milestone 1: gateway admission control — token buckets, policy reload, routing."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ENV = Path("/app/environment")
SESSIONS = Path("/app/sessions")

API_WEB = {
    "backends": {
        "api": {"weight": 2, "capacity": 500},
        "web": {"weight": 1, "capacity": 300},
    }
}

API_ONLY = {
    "backends": {
        "api": {"weight": 1, "capacity": 500},
    }
}

API_REFILL = {
    "backends": {
        "api": {"weight": 1, "capacity": 100, "refill_rate": 10},
    }
}


def _run(session_dir: Path, request: dict) -> dict:
    session_dir.mkdir(parents=True, exist_ok=True)
    req_path = session_dir / "request.json"
    req_path.write_text(json.dumps(request))
    subprocess.run(
        ["go", "run", "main.go", str(session_dir), str(req_path)],
        cwd=str(ENV),
        check=True,
    )
    return json.loads((session_dir / "output.json").read_text())


def _load_meta(session_dir: Path) -> dict:
    return json.loads((session_dir / "meta.json").read_text())


def _load_state(session_dir: Path) -> dict:
    return json.loads((session_dir / "state.json").read_text())


def _load_checkpoint(session_dir: Path) -> dict:
    return json.loads((session_dir / "checkpoint.json").read_text())


def reference_bucket_fingerprint(session_dir: Path) -> str:
    """Recompute checkpoint bucket_fingerprint from persisted token counts."""
    state = _load_state(session_dir)
    buckets = {bid: int(b["tokens"]) for bid, b in state.get("buckets", {}).items()}
    raw = json.dumps({k: buckets[k] for k in sorted(buckets)}, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def reference_state_digest(session_dir: Path) -> str:
    """Recompute state_digest from persisted state + meta (anti-cheat)."""
    state = _load_state(session_dir)
    meta = _load_meta(session_dir)
    scope = int(state.get("scope_gen", 0))
    reload_scope = int(meta.get("reload_scope", scope))
    pending = len(meta.get("pending_reloads", []))
    if reload_scope != scope:
        pending = 0
    buckets = {bid: int(b["tokens"]) for bid, b in state.get("buckets", {}).items()}
    payload = {
        "buckets": {k: buckets[k] for k in sorted(buckets)},
        "config_gen": int(state.get("config_gen", 0)),
        "route_counter": int(state.get("route_counter", 0)),
        "scope_gen": scope,
        "seq": int(meta.get("seq", 0)),
        "pending_reload_count": pending,
    }
    raw = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


GENESIS_CHECKPOINT_DIGEST = "0" * 64

BIND_NAME = "admission-bind.json"


def reference_scope_epoch(ledger: dict) -> str:
    """Recompute scope_epoch per admission-bind.md from ledger fields."""
    tokens = ledger["bucket_tokens"]
    payload = {
        "admit_seal": ledger["admit_seal"],
        "bucket_tokens": {k: int(tokens[k]) for k in sorted(tokens)},
        "config_gen": int(ledger["config_gen"]),
        "scope_gen": int(ledger["scope_gen"]),
        "seq": int(ledger["seq"]),
    }
    raw = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def reference_checkpoint_digest(cp: dict) -> str:
    """Recompute checkpoint_digest per checkpoint-chain.md."""
    payload = {
        "bucket_fingerprint": cp["bucket_fingerprint"],
        "config_gen": int(cp["config_gen"]),
        "run_id": cp["run_id"],
        "schema_version": int(cp["schema_version"]),
        "scope_gen": int(cp["scope_gen"]),
        "seq": int(cp["seq"]),
    }
    raw = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _run_expect_fail(session_dir: Path, request: dict) -> subprocess.CompletedProcess:
    session_dir.mkdir(parents=True, exist_ok=True)
    req_path = session_dir / "request.json"
    req_path.write_text(json.dumps(request))
    return subprocess.run(
        ["go", "run", "main.go", str(session_dir), str(req_path)],
        cwd=str(ENV),
        capture_output=True,
        text=True,
    )


def _seed_meta(
    session_dir: Path,
    pending: list[dict],
    reload_scope: int = 1,
    seq: int = 3,
) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "meta.json").write_text(
        json.dumps(
            {
                "pending_reloads": pending,
                "reload_scope": reload_scope,
                "last_run_id": "stale",
                "seq": seq,
            }
        )
    )


def _seed_state(
    session_dir: Path,
    scope_gen: int = 1,
    route_counter: int = 0,
    config_gen: int = 0,
    last_refill_seq: int = 0,
) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "state.json").write_text(
        json.dumps(
            {
                "buckets": {},
                "config_gen": config_gen,
                "route_counter": route_counter,
                "scope_gen": scope_gen,
                "last_refill_seq": last_refill_seq,
                "active_config": {"backends": {}},
            }
        )
    )


def _assert_m1_output_envelope(
    out: dict,
    *,
    run_id: str,
    config_gen: int,
    scope_gen: int = 0,
    accepted: bool = True,
    selected_backend: str = "",
    tokens_left: int = 0,
    pending_count: int = 0,
) -> None:
    for key in (
        "accepted",
        "selected_backend",
        "tokens_left",
        "pending_count",
        "last_run_id",
        "config_gen",
        "scope_gen",
    ):
        assert key in out
    assert out["accepted"] is accepted
    assert out["selected_backend"] == selected_backend
    assert out["tokens_left"] == tokens_left
    assert out["pending_count"] == pending_count
    assert out["last_run_id"] == run_id
    assert out["config_gen"] == config_gen
    assert out["scope_gen"] == scope_gen


def _load_snapshot(session_dir: Path) -> dict:
    return json.loads((session_dir / "admission-snapshot.json").read_text())


def _load_ledger(session_dir: Path) -> dict:
    return json.loads((session_dir / "enforcement-ledger.json").read_text())


def reference_admit_seal(
    run_id: str,
    bucket_tokens: dict[str, int],
    config_gen: int,
    scope_gen: int,
    route_counter: int,
    seq: int,
    digest_pending_count: int,
) -> str:
    """Independent admit_seal per enforcement-ledger.md."""
    tokens = {k: bucket_tokens[k] for k in sorted(bucket_tokens)}
    payload = {
        "bucket_tokens": tokens,
        "config_gen": config_gen,
        "digest_pending_count": digest_pending_count,
        "route_counter": route_counter,
        "run_id": run_id,
        "scope_gen": scope_gen,
        "seq": seq,
    }
    raw = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def reference_snapshot_bucket_tokens(session_dir: Path) -> dict:
    state = _load_state(session_dir)
    buckets = {bid: int(b["tokens"]) for bid, b in state.get("buckets", {}).items()}
    return {k: buckets[k] for k in sorted(buckets)}


def test_admission_snapshot_written_after_run() -> None:
    """Every run must persist admission-snapshot.json before export."""
    session = SESSIONS / "snapshot-present"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    snap_path = session / "admission-snapshot.json"
    assert snap_path.is_file()
    snap = _load_snapshot(session)
    assert snap["schema_version"] == 1
    assert snap["run_id"] == "boot"


def test_enforcement_ledger_written_after_run() -> None:
    """Every run must persist enforcement-ledger.json after the admission snapshot."""
    session = SESSIONS / "ledger-present"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    ledger_path = session / "enforcement-ledger.json"
    assert ledger_path.is_file()
    ledger = _load_ledger(session)
    assert ledger["schema_version"] == 1
    assert ledger["run_id"] == "boot"


def test_ledger_bucket_tokens_match_snapshot() -> None:
    """Ledger bucket_tokens must equal admission-snapshot.bucket_tokens."""
    session = SESSIONS / "ledger-snapshot-align"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
    )
    snap = _load_snapshot(session)
    ledger = _load_ledger(session)
    assert ledger["bucket_tokens"] == snap["bucket_tokens"]


def test_ledger_admit_seal_matches_reference() -> None:
    """admit_seal must hash the ledger seal payload per enforcement-ledger.md."""
    session = SESSIONS / "ledger-seal"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_WEB})
    _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 10}},
    )
    ledger = _load_ledger(session)
    expected = reference_admit_seal(
        ledger["run_id"],
        ledger["bucket_tokens"],
        ledger["config_gen"],
        ledger["scope_gen"],
        ledger["route_counter"],
        ledger["seq"],
        ledger["digest_pending_count"],
    )
    assert ledger["admit_seal"] == expected


def test_ledger_sealed_after_refill_not_pre_refill() -> None:
    """Ledger must capture post-refill token counts, not pre-refill balances."""
    session = SESSIONS / "ledger-post-refill"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
    _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 60}})
    _run(session, {"run_id": "idle", "fresh_start": False})
    snap = _load_snapshot(session)
    ledger = _load_ledger(session)
    assert ledger["bucket_tokens"]["api"] == snap["bucket_tokens"]["api"] == 50


def test_admission_snapshot_bucket_tokens_match_state() -> None:
    """Snapshot bucket_tokens must mirror live token counts from state.json."""
    session = SESSIONS / "snapshot-tokens"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
    )
    snap = _load_snapshot(session)
    assert snap["bucket_tokens"] == reference_snapshot_bucket_tokens(session)


def test_checkpoint_fingerprint_uses_snapshot_tokens() -> None:
    """checkpoint bucket_fingerprint must hash snapshot bucket_tokens, not capacity."""
    session = SESSIONS / "snapshot-checkpoint"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 40}},
    )
    cp = _load_checkpoint(session)
    assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)


def test_reload_preserves_existing_backend_tokens() -> None:
    """Hot reload must not zero token buckets for backends that remain in the config."""
    session = SESSIONS / "preserve"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    out = _run(
        session,
        {"run_id": "r2", "fresh_start": False, "consume": {"backend": "api", "cost": 50}},
    )
    assert out["accepted"] is True
    assert out["tokens_left"] == 450
    _run(session, {"run_id": "r3", "fresh_start": False, "reload": API_ONLY})
    state = _load_state(session)
    assert state["buckets"]["api"]["tokens"] == 450

def test_reload_clamps_tokens_to_new_capacity() -> None:
    """Reload lowers token level when new capacity is below the current bucket."""
    session = SESSIONS / "clamp"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "a", "fresh_start": True, "reload": API_ONLY})
    _run(session, {"run_id": "b", "fresh_start": False, "consume": {"backend": "api", "cost": 100}})
    smaller = {"backends": {"api": {"weight": 1, "capacity": 50}}}
    _run(session, {"run_id": "c", "fresh_start": False, "reload": smaller})
    state = _load_state(session)
    assert state["buckets"]["api"]["tokens"] == 50

def test_refill_applies_before_consume_same_run() -> None:
    """Token refill for the current seq tick must occur before consume deducts tokens."""
    session = SESSIONS / "refill-order"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
    _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 60}})
    _run(session, {"run_id": "idle", "fresh_start": False})
    out = _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 55}},
    )
    assert out["accepted"] is True
    assert out["tokens_left"] == 5

def test_refill_accumulates_across_idle_runs() -> None:
    """Idle runs advance seq and accumulate refill tokens before the next consume."""
    session = SESSIONS / "refill-idle"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
    _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 80}})
    _run(session, {"run_id": "idle1", "fresh_start": False})
    _run(session, {"run_id": "idle2", "fresh_start": False})
    state = _load_state(session)
    assert state["buckets"]["api"]["tokens"] == 40


def test_refill_tokens_cap_at_bucket_capacity() -> None:
    """Refill must not raise token counts above the backend capacity ceiling."""
    session = SESSIONS / "refill-cap"
    if session.exists():
        shutil.rmtree(session)
    high_rate = {
        "backends": {
            "api": {"weight": 1, "capacity": 20, "refill_rate": 50},
        }
    }
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": high_rate})
    _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 15}})
    assert _load_state(session)["buckets"]["api"]["tokens"] == 5
    _run(session, {"run_id": "idle", "fresh_start": False})
    assert _load_state(session)["buckets"]["api"]["tokens"] == 20

def test_reload_resets_refill_anchor() -> None:
    """Applying reload resets last_refill_seq so idle ticks after reload do not over-refill."""
    session = SESSIONS / "refill-anchor"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
    _run(session, {"run_id": "use", "fresh_start": False, "consume": {"backend": "api", "cost": 70}})
    _run(session, {"run_id": "reload", "fresh_start": False, "reload": API_REFILL})
    _run(session, {"run_id": "idle", "fresh_start": False})
    state = _load_state(session)
    assert state["buckets"]["api"]["tokens"] == 40
    assert state["last_refill_seq"] == _load_meta(session)["seq"]

def test_consume_rejects_without_refill_recovery() -> None:
    """Consumption fails when cost exceeds tokens and refill_rate is zero."""
    session = SESSIONS / "reject"
    if session.exists():
        shutil.rmtree(session)
    tiny = {"backends": {"api": {"weight": 1, "capacity": 10, "refill_rate": 0}}}
    _run(session, {"run_id": "a", "fresh_start": True, "reload": tiny})
    out = _run(
        session,
        {"run_id": "b", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
    )
    _assert_m1_output_envelope(
        out,
        run_id="b",
        config_gen=1,
        accepted=False,
        tokens_left=10,
    )
    assert _load_state(session)["buckets"]["api"]["tokens"] == 10


def test_consume_rejects_unknown_backend() -> None:
    """Consumption fails when the named backend is absent from active config."""
    session = SESSIONS / "reject-unknown"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    out = _run(
        session,
        {"run_id": "miss", "fresh_start": False, "consume": {"backend": "missing", "cost": 1}},
    )
    _assert_m1_output_envelope(
        out,
        run_id="miss",
        config_gen=1,
        accepted=False,
        tokens_left=0,
    )


def test_consume_reject_preserves_tokens_left() -> None:
    """Rejected consume must report unchanged tokens_left and leave the bucket intact."""
    session = SESSIONS / "reject-preserve"
    if session.exists():
        shutil.rmtree(session)
    tiny = {"backends": {"api": {"weight": 1, "capacity": 10, "refill_rate": 0}}}
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": tiny})
    _run(session, {"run_id": "use", "fresh_start": False, "consume": {"backend": "api", "cost": 3}})
    out = _run(
        session,
        {"run_id": "fail", "fresh_start": False, "consume": {"backend": "api", "cost": 8}},
    )
    _assert_m1_output_envelope(
        out,
        run_id="fail",
        config_gen=1,
        accepted=False,
        tokens_left=7,
    )
    assert _load_state(session)["buckets"]["api"]["tokens"] == 7


def test_consume_rejects_when_one_token_short() -> None:
    """Consumption fails when cost is exactly one token above the available balance."""
    session = SESSIONS / "reject-short"
    if session.exists():
        shutil.rmtree(session)
    tiny = {"backends": {"api": {"weight": 1, "capacity": 10, "refill_rate": 0}}}
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": tiny})
    out = _run(
        session,
        {"run_id": "short", "fresh_start": False, "consume": {"backend": "api", "cost": 11}},
    )
    _assert_m1_output_envelope(
        out,
        run_id="short",
        config_gen=1,
        accepted=False,
        tokens_left=10,
    )


def test_config_gen_zero_on_idle_run_before_reload() -> None:
    """config_gen stays zero until the first reload is applied."""
    session = SESSIONS / "config-gen-zero-idle"
    if session.exists():
        shutil.rmtree(session)
    out = _run(session, {"run_id": "idle", "fresh_start": False})
    _assert_m1_output_envelope(out, run_id="idle", config_gen=0)


def test_config_gen_zero_after_fresh_start_reset() -> None:
    """fresh_start without reload resets config_gen back to zero in the output."""
    session = SESSIONS / "config-gen-zero-reset"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    _run(session, {"run_id": "again", "fresh_start": False, "reload": API_WEB})
    out = _run(session, {"run_id": "reset", "fresh_start": True})
    _assert_m1_output_envelope(out, run_id="reset", config_gen=0, scope_gen=0)


def test_checkpoint_matches_persisted_buckets() -> None:
    """checkpoint.json bucket_fingerprint must hash live token counts from state.json."""
    session = SESSIONS / "checkpoint-m1"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 40}},
    )
    state = _load_state(session)
    cp = _load_checkpoint(session)
    assert cp["schema_version"] == 1
    assert cp["config_gen"] == state["config_gen"]
    assert cp["scope_gen"] == state["scope_gen"]
    assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)


def test_m1_fresh_start_keeps_scope_gen_zero() -> None:
    """Milestone 1 fresh_start must leave scope_gen at zero."""
    session = SESSIONS / "m1-scope-zero"
    if session.exists():
        shutil.rmtree(session)
    out = _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    assert out["scope_gen"] == 0
    _run(session, {"run_id": "again", "fresh_start": False, "reload": API_WEB})
    reset = _run(session, {"run_id": "reset", "fresh_start": True})
    assert reset["scope_gen"] == 0


def test_output_fields_after_reload_and_explicit_consume() -> None:
    """Output envelope reflects reload generation, run id, and explicit consume results."""
    session = SESSIONS / "output-envelope-explicit"
    if session.exists():
        shutil.rmtree(session)
    boot = _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    _assert_m1_output_envelope(boot, run_id="boot", config_gen=1)
    out = _run(
        session,
        {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 100}},
    )
    _assert_m1_output_envelope(
        out,
        run_id="take",
        config_gen=1,
        accepted=True,
        tokens_left=400,
    )


def test_output_fields_on_routed_consume() -> None:
    """Routed consume fills selected_backend and tokens_left while leaving scope_gen at zero."""
    session = SESSIONS / "output-envelope-routed"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_WEB})
    out = _run(
        session,
        {"run_id": "route", "fresh_start": False, "consume": {"backend": "", "cost": 5}},
    )
    _assert_m1_output_envelope(
        out,
        run_id="route",
        config_gen=1,
        accepted=True,
        selected_backend="api",
        tokens_left=495,
    )


def test_weighted_backend_selection() -> None:
    """Empty backend on consume uses weighted round-robin selection."""
    session = SESSIONS / "weighted"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "a", "fresh_start": True, "reload": API_WEB})
    first = _run(
        session,
        {"run_id": "b", "fresh_start": False, "consume": {"backend": "", "cost": 1}},
    )
    second = _run(
        session,
        {"run_id": "c", "fresh_start": False, "consume": {"backend": "", "cost": 1}},
    )
    third = _run(
        session,
        {"run_id": "d", "fresh_start": False, "consume": {"backend": "", "cost": 1}},
    )
    assert first["selected_backend"] == "api"
    assert second["selected_backend"] == "api"
    assert third["selected_backend"] == "web"

def test_reload_drops_removed_backend() -> None:
    """Backends absent from a reload config are removed from state."""
    session = SESSIONS / "drop"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "a", "fresh_start": True, "reload": API_WEB})
    _run(session, {"run_id": "b", "fresh_start": False, "reload": API_ONLY})
    state = _load_state(session)
    assert "web" not in state["buckets"]

def test_explicit_backend_does_not_advance_route_counter() -> None:
    """Explicit consume.backend must not advance weighted round-robin counter."""
    session = SESSIONS / "explicit-route"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "a", "fresh_start": True, "reload": API_WEB})
    _run(
        session,
        {"run_id": "b", "fresh_start": False, "consume": {"backend": "web", "cost": 1}},
    )
    routed = _run(
        session,
        {"run_id": "c", "fresh_start": False, "consume": {"backend": "", "cost": 1}},
    )
    assert routed["selected_backend"] == "api"

def test_explicit_backend_empty_selected_backend() -> None:
    """When consume.backend is set, selected_backend must be empty."""
    session = SESSIONS / "explicit-selected"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "a", "fresh_start": True, "reload": API_ONLY})
    out = _run(
        session,
        {"run_id": "b", "fresh_start": False, "consume": {"backend": "api", "cost": 1}},
    )
    assert out["selected_backend"] == ""
    assert out["accepted"] is True

def test_new_backend_starts_full_on_reload() -> None:
    """Backends appearing only in the new config start at full capacity."""
    session = SESSIONS / "new-backend"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "a", "fresh_start": True, "reload": API_ONLY})
    _run(session, {"run_id": "b", "fresh_start": False, "reload": API_WEB})
    state = _load_state(session)
    assert state["buckets"]["web"]["tokens"] == 300

def test_same_run_reload_then_consume_preserves_tokens() -> None:
    """Immediate reload and consume in one run deduct after reload bucket preservation."""
    session = SESSIONS / "same-run"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
    _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 95}})
    out = _run(
        session,
        {
            "run_id": "combo",
            "fresh_start": False,
            "reload": API_REFILL,
            "consume": {"backend": "api", "cost": 4},
        },
    )
    assert out["accepted"] is True
    assert out["tokens_left"] == 1


def test_refill_idle_tick_advances_tokens() -> None:
    """Idle runs must accrue one inclusive refill tick per refill-anchor.md."""
    session = SESSIONS / "refill-inclusive-idle"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
    _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 60}})
    assert _load_state(session)["buckets"]["api"]["tokens"] == 40
    _run(session, {"run_id": "idle", "fresh_start": False})
    assert _load_state(session)["buckets"]["api"]["tokens"] == 50


def test_checkpoint_chain_genesis_on_first_run() -> None:
    """First export must link prev_checkpoint_digest to genesis per checkpoint-chain.md."""
    session = SESSIONS / "chain-genesis"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
    cp = _load_checkpoint(session)
    assert cp["prev_checkpoint_digest"] == GENESIS_CHECKPOINT_DIGEST
    assert cp["checkpoint_digest"] == reference_checkpoint_digest(cp)
    assert cp["seq"] == _load_meta(session)["seq"]


def test_checkpoint_chain_links_after_multi_run() -> None:
    """Multi-run sessions must form a valid digest chain across archived checkpoints."""
    session = SESSIONS / "chain-multi"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    first = _load_checkpoint(session)
    _run(session, {"run_id": "r2", "fresh_start": False})
    second = _load_checkpoint(session)
    _run(session, {"run_id": "r3", "fresh_start": False})
    third = _load_checkpoint(session)

    archived_first = json.loads((session / "checkpoints" / f"{first['seq']}.json").read_text())
    archived_second = json.loads((session / "checkpoints" / f"{second['seq']}.json").read_text())

    assert archived_first["prev_checkpoint_digest"] == GENESIS_CHECKPOINT_DIGEST
    assert archived_second["prev_checkpoint_digest"] == archived_first["checkpoint_digest"]
    assert third["prev_checkpoint_digest"] == archived_second["checkpoint_digest"]
    for cp in (archived_first, archived_second, third):
        assert cp["checkpoint_digest"] == reference_checkpoint_digest(cp)


def test_checkpoint_archived_when_superseded() -> None:
    """Export must archive the prior head to checkpoints/<seq>.json before writing a new head."""
    session = SESSIONS / "chain-archive"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    first_seq = _load_checkpoint(session)["seq"]
    _run(session, {"run_id": "r2", "fresh_start": False})
    assert (session / "checkpoints" / f"{first_seq}.json").is_file()
    assert _load_checkpoint(session)["seq"] > first_seq


def test_export_rejects_broken_checkpoint_chain() -> None:
    """Export must abort when an archived checkpoint has a broken prev_checkpoint_digest link."""
    session = SESSIONS / "chain-broken"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    _run(session, {"run_id": "r2", "fresh_start": False})
    head = _load_checkpoint(session)
    archive_path = session / "checkpoints" / f"{head['seq'] - 1}.json"
    archived = json.loads(archive_path.read_text())
    archived["prev_checkpoint_digest"] = "f" * 64
    archive_path.write_text(json.dumps(archived, indent=2))
    proc = _run_expect_fail(session, {"run_id": "r3", "fresh_start": False})
    assert proc.returncode != 0
    out = json.loads((session / "output.json").read_text())
    assert out["last_run_id"] == "r2"


def test_fresh_start_clears_checkpoint_chain() -> None:
    """fresh_start must wipe checkpoint history so the next export restarts at genesis."""
    session = SESSIONS / "chain-fresh-reset"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    _run(session, {"run_id": "r2", "fresh_start": False})
    assert (session / "checkpoints").is_dir()
    _run(session, {"run_id": "reset", "fresh_start": True, "reload": API_ONLY})
    assert not (session / "checkpoints").exists()
    cp = _load_checkpoint(session)
    assert cp["prev_checkpoint_digest"] == GENESIS_CHECKPOINT_DIGEST


def test_admission_bind_staging_written() -> None:
    """Admit must emit admission-bind.json with scope_epoch derived from the ledger."""
    session = SESSIONS / "bind-staging"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    bind_path = session / BIND_NAME
    assert bind_path.is_file()
    bind = json.loads(bind_path.read_text())
    ledger = json.loads((session / "enforcement-ledger.json").read_text())
    assert bind["schema_version"] == 1
    assert bind["admit_seal_ref"] == ledger["admit_seal"]
    assert bind["seq"] == ledger["seq"]
    assert bind["scope_epoch"] == reference_scope_epoch(ledger)


def test_fresh_start_rebinds_admission_scope_epoch() -> None:
    """fresh_start must clear stale bind staging and re-derive scope_epoch from the new ledger."""
    session = SESSIONS / "bind-fresh-rebind"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    _run(
        session,
        {"run_id": "r2", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
    )
    ledger_before = json.loads((session / "enforcement-ledger.json").read_text())
    epoch_before = reference_scope_epoch(ledger_before)
    _run(session, {"run_id": "reset", "fresh_start": True, "reload": API_ONLY})
    bind = json.loads((session / BIND_NAME).read_text())
    ledger_after = json.loads((session / "enforcement-ledger.json").read_text())
    assert bind["admit_seal_ref"] == ledger_after["admit_seal"]
    assert bind["scope_epoch"] == reference_scope_epoch(ledger_after)
    assert bind["scope_epoch"] != epoch_before


def test_bind_scope_epoch_tracks_token_levels() -> None:
    """scope_epoch must change when ledger bucket_tokens change, not only bucket count."""
    session = SESSIONS / "bind-token-drift"
    if session.exists():
        shutil.rmtree(session)
    _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
    ledger_boot = json.loads((session / "enforcement-ledger.json").read_text())
    epoch_boot = reference_scope_epoch(ledger_boot)
    _run(
        session,
        {"run_id": "r2", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
    )
    ledger_after = json.loads((session / "enforcement-ledger.json").read_text())
    epoch_after = reference_scope_epoch(ledger_after)
    assert epoch_after != epoch_boot
    bind = json.loads((session / BIND_NAME).read_text())
    assert bind["scope_epoch"] == epoch_after

