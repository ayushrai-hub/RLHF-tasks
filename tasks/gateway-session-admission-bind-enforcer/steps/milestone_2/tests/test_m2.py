"""Milestone 2: deferred policy scope isolation, replay queue, state digest."""

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


class TestMilestone2:
    def test_admission_snapshot_written_after_run(self) -> None:
        """Every run must persist admission-snapshot.json before export."""
        session = SESSIONS / "snapshot-present-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        snap_path = session / "admission-snapshot.json"
        assert snap_path.is_file()
        snap = _load_snapshot(session)
        assert snap["schema_version"] == 1
        assert snap["run_id"] == "boot"

    def test_enforcement_ledger_written_after_run(self) -> None:
        """Every run must persist enforcement-ledger.json aligned with the snapshot."""
        session = SESSIONS / "ledger-present-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        assert (session / "enforcement-ledger.json").is_file()
        ledger = _load_ledger(session)
        snap = _load_snapshot(session)
        assert ledger["bucket_tokens"] == snap["bucket_tokens"]

    def test_ledger_admit_seal_matches_reference(self) -> None:
        """admit_seal must match independent seal recompute from ledger fields."""
        session = SESSIONS / "ledger-seal-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        _run(session, {"run_id": "queue", "queue_reload": API_WEB})
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
        snap = _load_snapshot(session)
        assert ledger["digest_pending_count"] == snap["digest_pending_count"]

    def test_export_digest_reads_snapshot_pending_scope(self) -> None:
        """state_digest must use snapshot digest_pending_count when scope is stale."""
        session = SESSIONS / "snapshot-digest-scope"
        if session.exists():
            shutil.rmtree(session)
        _seed_state(session, scope_gen=5)
        _seed_meta(session, pending=[API_WEB], reload_scope=2, seq=4)
        _run(session, {"run_id": "noop"})
        snap = _load_snapshot(session)
        assert snap["digest_pending_count"] == 0
        out = json.loads((session / "output.json").read_text())
        assert out["pending_count"] == 1
        assert out["state_digest"] == reference_state_digest(session)

    def test_admission_snapshot_bucket_tokens_match_state(self) -> None:
        """Snapshot bucket_tokens must mirror live token counts from state.json."""
        session = SESSIONS / "snapshot-tokens-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        _run(
            session,
            {"run_id": "take", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
        )
        snap = _load_snapshot(session)
        assert snap["bucket_tokens"] == reference_snapshot_bucket_tokens(session)

    def test_fresh_start_clears_pending_reload_queue(self) -> None:
        """fresh_start must discard queued reload configs from earlier scopes."""
        session = SESSIONS / "fresh-pending"
        if session.exists():
            shutil.rmtree(session)
        stale = {"backends": {"legacy": {"weight": 1, "capacity": 999}}}
        _seed_state(session, scope_gen=1)
        _seed_meta(session, pending=[stale], reload_scope=1)
        _run(session, {"run_id": "scope", "fresh_start": True, "reload": API_ONLY})
        out = _run(session, {"run_id": "replay", "fresh_start": False, "replay_pending": True})
        assert out["pending_count"] == 0
        state = _load_state(session)
        assert "legacy" not in state["buckets"]
        cp = _load_checkpoint(session)
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)

    def test_replay_pending_applies_queued_reload(self) -> None:
        """replay_pending applies deferred config reloads when reload_scope matches scope_gen."""
        session = SESSIONS / "replay"
        if session.exists():
            shutil.rmtree(session)
        _run(
            session,
            {
                "run_id": "queue",
                "fresh_start": True,
                "queue_reload": API_WEB,
            },
        )
        out = _run(session, {"run_id": "apply", "fresh_start": False, "replay_pending": True})
        assert out["config_gen"] == 1
        state = _load_state(session)
        assert "web" in state["buckets"]
        cp = _load_checkpoint(session)
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)


    def test_replay_applies_multiple_queued_configs_in_order(self) -> None:
        """replay_pending applies each queued config in enqueue order with one config_gen step each."""
        session = SESSIONS / "multi-queue-order"
        if session.exists():
            shutil.rmtree(session)
        web_only = {"backends": {"web": {"weight": 1, "capacity": 150}}}
        _run(session, {"run_id": "boot", "fresh_start": True})
        _run(session, {"run_id": "q1", "fresh_start": False, "queue_reload": API_ONLY})
        _run(session, {"run_id": "q2", "fresh_start": False, "queue_reload": API_WEB})
        queued = _run(session, {"run_id": "q3", "fresh_start": False, "queue_reload": web_only})
        assert queued["pending_count"] == 3
        assert len(_load_meta(session)["pending_reloads"]) == 3
        out = _run(session, {"run_id": "replay", "fresh_start": False, "replay_pending": True})
        assert out["config_gen"] == 3
        assert out["pending_count"] == 0
        state = _load_state(session)
        assert "api" not in state["buckets"]
        assert state["buckets"]["web"]["tokens"] == 150
        cp = _load_checkpoint(session)
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)

    def test_multi_step_queue_replay_consume_workflow(self) -> None:
        """Queued reload replay after consumption preserves tokens and enables later consume."""
        session = SESSIONS / "workflow"
        if session.exists():
            shutil.rmtree(session)
        refill_web = {
            "backends": {
                "api": {"weight": 1, "capacity": 500, "refill_rate": 5},
                "web": {"weight": 1, "capacity": 100, "refill_rate": 10},
            }
        }
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        _run(
            session,
            {"run_id": "use", "fresh_start": False, "consume": {"backend": "api", "cost": 40}},
        )
        _run(session, {"run_id": "queue", "fresh_start": False, "queue_reload": refill_web})
        _run(session, {"run_id": "replay", "fresh_start": False, "replay_pending": True})
        mid = _load_state(session)
        assert mid["buckets"]["api"]["tokens"] == 460
        assert mid["buckets"]["web"]["tokens"] == 100
        cp = _load_checkpoint(session)
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)
        out = _run(
            session,
            {"run_id": "web", "fresh_start": False, "consume": {"backend": "web", "cost": 15}},
        )
        assert out["accepted"] is True
        assert out["tokens_left"] == 85
        state = _load_state(session)
        assert state["buckets"]["api"]["tokens"] == 465

    def test_stale_reload_scope_skips_queued_replay(self) -> None:
        """Queued reloads from an older reload_scope must not apply on replay_pending."""
        session = SESSIONS / "stale-scope"
        if session.exists():
            shutil.rmtree(session)
        _seed_state(session, scope_gen=4)
        _seed_meta(session, pending=[API_WEB], reload_scope=1, seq=2)
        out = _run(session, {"run_id": "replay", "fresh_start": False, "replay_pending": True})
        state = _load_state(session)
        assert "web" not in state["buckets"]
        assert out["config_gen"] == 0
        assert out["pending_count"] == 0
        cp = _load_checkpoint(session)
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)

    def test_fresh_start_increments_scope_gen(self) -> None:
        """fresh_start increments scope_gen and aligns reload_scope."""
        session = SESSIONS / "scope-bump"
        if session.exists():
            shutil.rmtree(session)
        _seed_state(session, scope_gen=2, last_refill_seq=5)
        _seed_meta(session, pending=[], reload_scope=2, seq=5)
        out = _run(session, {"run_id": "scope", "fresh_start": True, "reload": API_ONLY})
        assert out["scope_gen"] == 3
        meta = _load_meta(session)
        assert meta["reload_scope"] == 3
        state = _load_state(session)
        assert state["last_refill_seq"] == meta["seq"]

    def test_fresh_start_blocks_cross_scope_refill(self) -> None:
        """fresh_start anchors last_refill_seq without refilling from prior scope seq ticks."""
        session = SESSIONS / "scope-refill"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_REFILL})
        _run(session, {"run_id": "drain", "fresh_start": False, "consume": {"backend": "api", "cost": 90}})
        _run(session, {"run_id": "idle", "fresh_start": False})
        _run(session, {"run_id": "newscope", "fresh_start": True, "reload": API_REFILL})
        state = _load_state(session)
        assert state["buckets"]["api"]["tokens"] == 100

    def test_digest_excludes_stale_pending_reload_count(self) -> None:
        """state_digest pending_reload_count is 0 when reload_scope lags scope_gen."""
        session = SESSIONS / "digest-scope"
        if session.exists():
            shutil.rmtree(session)
        _seed_state(session, scope_gen=5)
        _seed_meta(session, pending=[API_WEB], reload_scope=2, seq=4)
        out = _run(session, {"run_id": "noop"})
        assert out["pending_count"] == 1
        assert out["state_digest"] == reference_state_digest(session)


    def test_digest_includes_nonzero_pending_when_scope_aligned(self) -> None:
        """state_digest pending_reload_count must reflect a non-zero live queue when reload_scope matches scope_gen."""
        session = SESSIONS / "digest-live-pending"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        out = _run(session, {"run_id": "queue", "fresh_start": False, "queue_reload": API_WEB})
        assert out["pending_count"] >= 1
        meta = _load_meta(session)
        state = _load_state(session)
        assert meta["reload_scope"] == state["scope_gen"]
        assert len(meta["pending_reloads"]) >= 1
        scope = int(state["scope_gen"])
        reload_scope = int(meta["reload_scope"])
        assert reload_scope == scope
        pending_in_digest = len(meta["pending_reloads"])
        assert pending_in_digest > 0
        assert out["state_digest"] == reference_state_digest(session)


    def test_state_digest_matches_persisted_files(self) -> None:
        """state_digest in output must match recomputation from state.json + meta.json."""
        session = SESSIONS / "digest-anticheat"
        if session.exists():
            shutil.rmtree(session)
        out = _run(
            session,
            {
                "run_id": "anticheat",
                "fresh_start": True,
                "reload": API_REFILL,
                "consume": {"backend": "api", "cost": 7},
            },
        )
        assert out["state_digest"] == reference_state_digest(session)

    def test_checkpoint_tracks_scope_gen_after_fresh_start(self) -> None:
        """checkpoint.json scope_gen must follow milestone 2 fresh_start increments."""
        session = SESSIONS / "checkpoint-m2-scope"
        if session.exists():
            shutil.rmtree(session)
        out = _run(session, {"run_id": "scope", "fresh_start": True, "reload": API_ONLY})
        state = _load_state(session)
        cp = _load_checkpoint(session)
        assert out["scope_gen"] == 1
        assert cp["scope_gen"] == state["scope_gen"] == 1
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)

    def test_queue_reload_sets_reload_scope_via_deferred_path(self) -> None:
        """queue_reload must stamp meta.reload_scope to the active scope_gen."""
        session = SESSIONS / "queue-scope-stamp"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "boot", "fresh_start": True, "reload": API_ONLY})
        _run(session, {"run_id": "queue", "fresh_start": False, "queue_reload": API_WEB})
        meta = _load_meta(session)
        state = _load_state(session)
        assert meta["reload_scope"] == state["scope_gen"]

    def test_reload_preserves_existing_backend_tokens(self) -> None:
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

    def test_tb3_replay_queue_applies_enqueue_order(self) -> None:
        """TB3 fixture: replay_pending must apply queued configs in enqueue order."""
        fixture = Path("/opt/verifier-fixtures/tb3-sessions/replay-order-trap")
        session = SESSIONS / "tb3-replay-order"
        if session.exists():
            shutil.rmtree(session)
        shutil.copytree(fixture, session)
        out = _run(session, {"run_id": "replay", "fresh_start": False, "replay_pending": True})
        state = _load_state(session)
        assert out["config_gen"] == 3
        assert out["pending_count"] == 0
        assert "api" not in state["buckets"]
        assert state["buckets"]["web"]["tokens"] == 150
        cp = _load_checkpoint(session)
        assert cp["bucket_fingerprint"] == reference_bucket_fingerprint(session)

    def test_hidden_scope_stale_replay_preserves_buckets(self) -> None:
        """Stale reload_scope must skip queued replay without mutating live buckets."""
        fixture = Path("/opt/verifier-fixtures/tb3-sessions/scope-stale-trap")
        session = SESSIONS / "tb3-scope-stale"
        if session.exists():
            shutil.rmtree(session)
        shutil.copytree(fixture, session)
        out = _run(session, {"run_id": "replay", "fresh_start": False, "replay_pending": True})
        state = _load_state(session)
        assert out["pending_count"] == 0
        assert state["config_gen"] == 1
        assert state["buckets"]["api"]["tokens"] == 400
        assert "web" not in state["buckets"]

    def test_fresh_start_clears_checkpoint_chain_m2(self) -> None:
        """Milestone 2 fresh_start scope bump must still reset the checkpoint chain."""
        session = SESSIONS / "chain-fresh-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
        _run(session, {"run_id": "r2", "fresh_start": False})
        assert (session / "checkpoints").is_dir()
        _run(session, {"run_id": "scope", "fresh_start": True, "reload": API_ONLY})
        assert not (session / "checkpoints").exists()
        cp = _load_checkpoint(session)
        assert cp["prev_checkpoint_digest"] == GENESIS_CHECKPOINT_DIGEST
        assert cp["scope_gen"] == _load_state(session)["scope_gen"]

    def test_admission_bind_staging_written(self) -> None:
        """Admit must emit admission-bind.json with scope_epoch derived from the ledger."""
        session = SESSIONS / "bind-staging-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
        bind_path = session / BIND_NAME
        assert bind_path.is_file()
        bind = json.loads(bind_path.read_text())
        ledger = json.loads((session / "enforcement-ledger.json").read_text())
        assert bind["admit_seal_ref"] == ledger["admit_seal"]
        assert bind["scope_epoch"] == reference_scope_epoch(ledger)

    def test_fresh_start_rebinds_admission_scope_epoch(self) -> None:
        """fresh_start must clear stale bind staging and re-derive scope_epoch for the new scope."""
        session = SESSIONS / "bind-fresh-rebind-m2"
        if session.exists():
            shutil.rmtree(session)
        _run(session, {"run_id": "r1", "fresh_start": True, "reload": API_ONLY})
        _run(
            session,
            {"run_id": "r2", "fresh_start": False, "consume": {"backend": "api", "cost": 25}},
        )
        ledger_before = json.loads((session / "enforcement-ledger.json").read_text())
        epoch_before = reference_scope_epoch(ledger_before)
        _run(session, {"run_id": "scope", "fresh_start": True, "reload": API_ONLY})
        bind = json.loads((session / BIND_NAME).read_text())
        ledger_after = json.loads((session / "enforcement-ledger.json").read_text())
        assert bind["scope_epoch"] == reference_scope_epoch(ledger_after)
        assert int(ledger_after["scope_gen"]) > int(ledger_before["scope_gen"])
        assert bind["scope_epoch"] != epoch_before

