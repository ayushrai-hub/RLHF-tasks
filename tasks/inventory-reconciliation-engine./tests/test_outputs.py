"""Verifier for the quota ledger CLI (ledgerctl)."""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

APP_ROOT = Path("/app")
SEED_BATCH = APP_ROOT / "data" / "batches" / "seed.jsonl"
REPORT = APP_ROOT / "output" / "quota_report.json"
AUDIT = APP_ROOT / "output" / "audit_trail.json"
GENERATED_FROM = "quota-ledger-v2"
LEDGERCTL = APP_ROOT / "bin" / "ledgerctl"

ALLOWED_FIELDS = frozenset(
    {
        "event_id",
        "account_id",
        "operation",
        "amount",
        "logical_time",
        "source_replica",
        "seq",
        "epoch",
        "target_event_id",
        "expires_at",
    }
)

AMOUNT_OPS = frozenset({"RESERVE", "CONSUME", "RELEASE", "CORRECTION"})
REJECTION_RANKS = {
    "missing_required": 1,
    "unexpected_fields": 2,
    "invalid_types": 3,
    "invalid_event_id": 4,
    "invalid_account_id": 5,
    "invalid_source_replica": 6,
    "invalid_operation": 7,
    "invalid_logical_time": 8,
    "invalid_seq": 9,
    "invalid_epoch": 10,
    "invalid_amount": 11,
    "missing_target": 12,
    "invalid_target": 13,
    "duplicate_event_id": 14,
    "stale_seq": 15,
    "account_suspended": 16,
    "account_not_suspended": 17,
    "resume_replica_mismatch": 18,
    "insufficient_quota": 19,
    "replica_conflict": 20,
    "reversal_account_suspended": 21,
    "reversal_self": 22,
    "reversal_replica_mismatch": 23,
    "reversal_cross_account": 24,
    "reversal_target_missing": 25,
    "reversal_target_not_applied": 26,
    "reversal_already_reversed": 27,
    "reversal_invalid_target": 28,
}

EVENT_ID_RE = re.compile(r"^QE-[A-Z0-9]{6}$")
ACCOUNT_ID_RE = re.compile(r"^ACC-[A-Z0-9]{4,8}$")
REPLICA_RE = re.compile(r"^REP-[A-Z0-9]{3,6}$")

if not SEED_BATCH.is_file():
    pytest.skip("no seed batch", allow_module_level=True)


def normalize_id(raw: str) -> str:
    return raw.strip().upper()


def parse_logical_time(raw: str) -> datetime:
    if not raw.endswith("Z"):
        raise ValueError("bad suffix")
    return datetime.strptime(raw[:-1], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def reset_state() -> None:
    state = APP_ROOT / "state"
    if state.exists():
        shutil.rmtree(state)
    (state / "journal" / "batches").mkdir(parents=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if REPORT.exists():
        REPORT.unlink()
    if AUDIT.exists():
        AUDIT.unlink()


def run_workflow(events_path: Path, batch_name: str = "seed") -> None:
    reset_state()
    subprocess.run(
        [str(LEDGERCTL), "import", "--batch", batch_name, "--events", str(events_path)],
        check=True,
        cwd=APP_ROOT,
    )
    subprocess.run([str(LEDGERCTL), "rebuild"], check=True, cwd=APP_ROOT)
    subprocess.run(
        [str(LEDGERCTL), "report", "--out", str(REPORT)],
        check=True,
        cwd=APP_ROOT,
    )
    subprocess.run(
        [str(LEDGERCTL), "audit", "--out", str(AUDIT)],
        check=True,
        cwd=APP_ROOT,
    )


def digest_of(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "snapshot_digest"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_payload(obj: dict) -> dict:
    out: dict = {}
    for key in sorted(obj.keys()):
        if key not in ALLOWED_FIELDS:
            continue
        value = obj[key]
        if value is None:
            out[key] = None
        elif key in {"event_id", "account_id", "source_replica", "target_event_id"}:
            out[key] = normalize_id(str(value))
        elif key == "operation":
            out[key] = str(value).strip().upper()
        else:
            out[key] = value
    return out


@dataclass
class AccountState:
    limit: int = 1000
    available: int = 0
    held: int = 0
    suspended: bool = False
    suspended_by_replica: str = ""
    epoch: int = 1
    last_event_id: str = ""
    last_logical_time: str = ""


@dataclass
class EngineState:
    accounts: dict[str, AccountState] = field(default_factory=dict)
    seen_event_ids: dict[str, dict] = field(default_factory=dict)
    applied: dict[str, dict] = field(default_factory=dict)
    rejected_ids: set[str] = field(default_factory=set)
    reversed: set[str] = field(default_factory=set)
    seq_highwater: dict[tuple[str, str], int] = field(default_factory=dict)
    correction_at_time: dict[tuple[str, str], str] = field(default_factory=dict)
    correction_prev_amt: dict[str, int] = field(default_factory=dict)
    reserve_expires: dict[str, str] = field(default_factory=dict)


def load_events(path: Path) -> tuple[list[tuple[int, dict]], int, int]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    parsed: list[tuple[int, dict]] = []
    malformed = 0
    for index, line in enumerate(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(payload, dict):
            malformed += 1
            continue
        parsed.append((index, payload))
    return parsed, len(lines), malformed


def apply_legacy(engine_state: EngineState) -> None:
    legacy_path = APP_ROOT / "data" / "legacy" / "snapshot_v0.json"
    if not legacy_path.is_file():
        return
    snap = json.loads(legacy_path.read_text(encoding="utf-8"))
    if snap.get("format") != "quota-v0":
        return
    for row in snap.get("accounts", []):
        acct = engine_state.accounts.setdefault(row["account_id"], AccountState())
        if acct.last_event_id == "":
            acct.available = row["balance"]
            acct.epoch = row["epoch"]
            acct.last_event_id = "LEGACY-IMPORT"
            acct.last_logical_time = "1970-01-01T00:00:00Z"


def validate_event(obj: dict) -> tuple[dict | None, dict | None]:
    required = ("event_id", "account_id", "operation", "logical_time", "source_replica", "seq", "epoch")
    for req in required:
        if obj.get(req) is None:
            return None, _row(obj, "missing_required")
    extra = set(obj.keys()) - ALLOWED_FIELDS
    if extra:
        return None, _row(obj, "unexpected_fields")
    for field_name in ("event_id", "account_id", "source_replica", "operation", "logical_time"):
        if not isinstance(obj[field_name], str):
            return None, _row(obj, "invalid_types")
    seq = obj["seq"]
    epoch = obj["epoch"]
    if isinstance(seq, bool) or not isinstance(seq, int):
        return None, _row(obj, "invalid_types")
    if isinstance(epoch, bool) or not isinstance(epoch, int):
        return None, _row(obj, "invalid_types")

    event_id = normalize_id(obj["event_id"])
    account_id = normalize_id(obj["account_id"])
    replica = normalize_id(obj["source_replica"])
    operation = obj["operation"].strip().upper()

    if not EVENT_ID_RE.fullmatch(event_id):
        return None, _row_ids(event_id, account_id, "invalid_event_id")
    if not ACCOUNT_ID_RE.fullmatch(account_id):
        return None, _row_ids(event_id, account_id, "invalid_account_id")
    if not REPLICA_RE.fullmatch(replica):
        return None, _row_ids(event_id, account_id, "invalid_source_replica")
    if operation not in {
        "RESERVE", "CONSUME", "RELEASE", "REVERSAL", "SUSPEND", "RESUME", "CORRECTION", "CARRY_FORWARD",
    }:
        return None, _row_ids(event_id, account_id, "invalid_operation")
    try:
        logical_time = parse_logical_time(obj["logical_time"])
    except ValueError:
        return None, _row_ids(event_id, account_id, "invalid_logical_time")
    if seq < 1:
        return None, _row_ids(event_id, account_id, "invalid_seq")
    if epoch < 1:
        return None, _row_ids(event_id, account_id, "invalid_epoch")

    normalized: dict = {
        "event_id": event_id,
        "account_id": account_id,
        "operation": operation,
        "logical_time": logical_time,
        "source_replica": replica,
        "seq": seq,
        "epoch": epoch,
    }
    if operation in AMOUNT_OPS:
        amount = obj.get("amount")
        if amount is None or isinstance(amount, bool) or not isinstance(amount, int):
            return None, _row_ids(event_id, account_id, "invalid_amount")
        if operation == "CORRECTION" and amount < 0:
            return None, _row_ids(event_id, account_id, "invalid_amount")
        if operation != "CORRECTION" and amount < 1:
            return None, _row_ids(event_id, account_id, "invalid_amount")
        normalized["amount"] = amount
    elif obj.get("amount") is not None:
        return None, _row_ids(event_id, account_id, "invalid_amount")

    if operation == "REVERSAL":
        target = obj.get("target_event_id")
        if target is None:
            return None, _row_ids(event_id, account_id, "missing_target")
        if not isinstance(target, str):
            return None, _row_ids(event_id, account_id, "invalid_types")
        target_id = normalize_id(target)
        if not EVENT_ID_RE.fullmatch(target_id):
            return None, _row_ids(event_id, account_id, "invalid_target")
        normalized["target_event_id"] = target_id
    elif obj.get("target_event_id") is not None:
        return None, _row_ids(event_id, account_id, "unexpected_fields")

    if obj.get("expires_at"):
        normalized["expires_at"] = obj["expires_at"]
    return normalized, None


def _row(obj: dict, reason: str) -> dict:
    return {
        "event_id": str(obj.get("event_id", "")),
        "account_id": str(obj.get("account_id", "")),
        "reason": reason,
        "priority_rank": REJECTION_RANKS[reason],
    }


def _row_ids(event_id: str, account_id: str, reason: str) -> dict:
    return {
        "event_id": event_id,
        "account_id": account_id,
        "reason": reason,
        "priority_rank": REJECTION_RANKS[reason],
    }


def _reject(rejections: list, rejected_ids: set[str], event_id: str, account_id: str, reason: str) -> None:
    rejections.append(
        {"event_id": event_id, "account_id": account_id, "reason": reason, "priority_rank": REJECTION_RANKS[reason]}
    )
    if event_id:
        rejected_ids.add(event_id)


def reference_reconcile(events_path: Path, *, apply_legacy_import: bool = True, now: datetime | None = None) -> dict:
    parsed, line_count, malformed = load_events(events_path)
    state = EngineState()
    if apply_legacy_import:
        apply_legacy(state)
    rejections: list[dict] = []
    applied_count = 0
    rejected_count = 0
    skipped = 0
    now = now or datetime(2099, 1, 1, tzinfo=timezone.utc)

    sortable = []
    for line_index, payload in parsed:
        event_id = str(payload.get("event_id", ""))
        lt = str(payload.get("logical_time", "1970-01-01T00:00:00Z"))
        try:
            logical_time = parse_logical_time(lt)
        except ValueError:
            logical_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
        sortable.append((logical_time, normalize_id(event_id) if event_id else "", line_index, payload))
    sortable.sort(key=lambda row: (row[0], row[1], row[2]))

    for _lt, _eid, _idx, payload in sortable:
        normalized, rejection = validate_event(payload)
        if rejection is not None:
            rejections.append(rejection)
            rejected_count += 1
            if rejection["event_id"]:
                state.rejected_ids.add(rejection["event_id"])
            continue
        assert normalized is not None
        event_id = normalized["event_id"]
        account_id = normalized["account_id"]
        operation = normalized["operation"]
        lt_str = normalized["logical_time"].strftime("%Y-%m-%dT%H:%M:%SZ")
        canon = canonical_payload(payload)
        if event_id in state.seen_event_ids:
            if state.seen_event_ids[event_id] != canon:
                _reject(rejections, state.rejected_ids, event_id, account_id, "duplicate_event_id")
                rejected_count += 1
            else:
                skipped += 1
            continue
        state.seen_event_ids[event_id] = canon

        acct_view = state.accounts.get(account_id, AccountState())
        if operation in {"RESERVE", "CONSUME", "RELEASE", "CORRECTION"} and acct_view.suspended:
            _reject(rejections, state.rejected_ids, event_id, account_id, "account_suspended")
            rejected_count += 1
            continue
        if operation == "RESUME":
            if not acct_view.suspended:
                _reject(rejections, state.rejected_ids, event_id, account_id, "account_not_suspended")
                rejected_count += 1
                continue
            if acct_view.suspended_by_replica and acct_view.suspended_by_replica != normalized["source_replica"]:
                _reject(rejections, state.rejected_ids, event_id, account_id, "resume_replica_mismatch")
                rejected_count += 1
                continue

        sk = (account_id, normalized["source_replica"])
        if normalized["seq"] <= state.seq_highwater.get(sk, 0):
            _reject(rejections, state.rejected_ids, event_id, account_id, "stale_seq")
            rejected_count += 1
            continue

        if operation == "CORRECTION":
            ck = (account_id, lt_str)
            winner = state.correction_at_time.get(ck)
            if winner is not None and winner != normalized["source_replica"]:
                _reject(rejections, state.rejected_ids, event_id, account_id, "replica_conflict")
                rejected_count += 1
                continue

        if operation == "REVERSAL":
            if acct_view.suspended:
                _reject(rejections, state.rejected_ids, event_id, account_id, "reversal_account_suspended")
                rejected_count += 1
                continue
            target_id = normalized["target_event_id"]
            if target_id == event_id:
                _reject(rejections, state.rejected_ids, event_id, account_id, "reversal_self")
                rejected_count += 1
                continue
            if target_id in state.reversed:
                _reject(rejections, state.rejected_ids, event_id, account_id, "reversal_already_reversed")
                rejected_count += 1
                continue
            target = state.applied.get(target_id)
            if target is None:
                reason = "reversal_target_not_applied" if target_id in state.rejected_ids else "reversal_target_missing"
                _reject(rejections, state.rejected_ids, event_id, account_id, reason)
                rejected_count += 1
                continue
            if target["source_replica"] != normalized["source_replica"]:
                _reject(rejections, state.rejected_ids, event_id, account_id, "reversal_replica_mismatch")
                rejected_count += 1
                continue
            if target["account_id"] != account_id:
                _reject(rejections, state.rejected_ids, event_id, account_id, "reversal_cross_account")
                rejected_count += 1
                continue
            if target["operation"] in {"SUSPEND", "RESUME", "REVERSAL", "CARRY_FORWARD"}:
                _reject(rejections, state.rejected_ids, event_id, account_id, "reversal_invalid_target")
                rejected_count += 1
                continue

        if operation == "CONSUME" and acct_view.available + acct_view.held - normalized["amount"] < 0:
            _reject(rejections, state.rejected_ids, event_id, account_id, "insufficient_quota")
            rejected_count += 1
            continue
        if operation == "RESERVE" and acct_view.available - normalized["amount"] < 0:
            _reject(rejections, state.rejected_ids, event_id, account_id, "insufficient_quota")
            rejected_count += 1
            continue
        if operation == "RELEASE" and acct_view.held - normalized["amount"] < 0:
            _reject(rejections, state.rejected_ids, event_id, account_id, "insufficient_quota")
            rejected_count += 1
            continue

        acct = state.accounts.setdefault(account_id, AccountState(epoch=normalized["epoch"]))
        if operation == "REVERSAL":
            target = state.applied[normalized["target_event_id"]]
            top = target["operation"]
            if top == "RESERVE":
                acct.held -= target["amount"]
                acct.available += target["amount"]
            elif top == "CONSUME":
                need = target["amount"]
                from_held = min(need, acct.held)
                acct.held += from_held
                acct.available += need - from_held
            elif top == "RELEASE":
                acct.held += target["amount"]
                acct.available -= target["amount"]
            elif top == "CORRECTION":
                acct.available = state.correction_prev_amt[normalized["target_event_id"]]
            state.reversed.add(normalized["target_event_id"])
        elif operation == "RESERVE":
            acct.available -= normalized["amount"]
            acct.held += normalized["amount"]
            if normalized.get("expires_at"):
                state.reserve_expires[event_id] = normalized["expires_at"]
        elif operation == "CONSUME":
            need = normalized["amount"]
            from_held = min(need, acct.held)
            acct.held -= from_held
            acct.available -= need - from_held
        elif operation == "RELEASE":
            acct.held -= normalized["amount"]
            acct.available += normalized["amount"]
        elif operation == "CORRECTION":
            state.correction_prev_amt[event_id] = acct.available
            acct.available = normalized["amount"]
            state.correction_at_time[(account_id, lt_str)] = normalized["source_replica"]
        elif operation == "SUSPEND":
            acct.suspended = True
            acct.suspended_by_replica = normalized["source_replica"]
        elif operation == "RESUME":
            acct.suspended = False
            acct.suspended_by_replica = ""
        elif operation == "CARRY_FORWARD":
            acct.available += acct.available
            acct.held = 0
            acct.epoch = normalized["epoch"]

        acct.last_event_id = event_id
        acct.last_logical_time = lt_str
        state.applied[event_id] = normalized
        state.seq_highwater[sk] = normalized["seq"]
        applied_count += 1

    exp_rows = []
    for eid, exp_str in state.reserve_expires.items():
        if eid in state.reversed:
            continue
        ev = state.applied[eid]
        if ev["operation"] != "RESERVE":
            continue
        exp = parse_logical_time(exp_str)
        if now >= exp:
            exp_rows.append((exp, eid, ev))
    exp_rows.sort(key=lambda row: (row[0], row[1]))
    for _exp, eid, ev in exp_rows:
        acct = state.accounts[ev["account_id"]]
        release = min(ev["amount"], acct.held)
        acct.held -= release
        acct.available += release
        del state.reserve_expires[eid]

    accounts = []
    for account_id in sorted(state.accounts.keys()):
        acct = state.accounts[account_id]
        if acct.suspended or not acct.last_event_id:
            continue
        accounts.append(
            {
                "account_id": account_id,
                "available": acct.available,
                "held": acct.held,
                "limit": acct.limit,
                "epoch": acct.epoch,
                "last_event_id": acct.last_event_id,
                "last_logical_time": acct.last_logical_time,
            }
        )

    rejections.sort(key=lambda row: (row["priority_rank"], row["event_id"]))
    snapshot = {
        "generated_from": GENERATED_FROM,
        "event_line_count": line_count,
        "parsed_count": len(parsed),
        "malformed_line_count": malformed,
        "processed_count": applied_count + rejected_count,
        "applied_count": applied_count,
        "rejected_count": rejected_count,
        "skipped_idempotent_count": skipped,
        "rejections": rejections,
        "accounts": accounts,
    }
    body = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    snapshot["snapshot_digest"] = hashlib.sha256(body).hexdigest()
    return snapshot


@pytest.fixture(scope="module")
def baseline_report() -> dict:
    run_workflow(SEED_BATCH)
    assert REPORT.is_file()
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_report_schema_and_digest(baseline_report: dict) -> None:
    assert baseline_report["generated_from"] == GENERATED_FROM
    assert baseline_report["snapshot_digest"] == digest_of(baseline_report)


def test_seed_matches_reference(baseline_report: dict) -> None:
    expected = reference_reconcile(SEED_BATCH)
    for key in (
        "event_line_count", "parsed_count", "malformed_line_count", "processed_count",
        "applied_count", "rejected_count", "skipped_idempotent_count",
    ):
        assert baseline_report[key] == expected[key], key
    assert baseline_report["accounts"] == expected["accounts"]
    assert baseline_report["rejections"] == expected["rejections"]


def test_audit_matches_report_digest(baseline_report: dict) -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert audit["projection_digest"] == baseline_report["snapshot_digest"]
    assert audit["batch_count"] >= 1


def test_idempotent_import_and_rebuild() -> None:
    run_workflow(SEED_BATCH)
    first = json.loads(REPORT.read_text(encoding="utf-8"))
    subprocess.run(
        [str(LEDGERCTL), "import", "--batch", "seed", "--events", str(SEED_BATCH)],
        check=True,
        cwd=APP_ROOT,
    )
    subprocess.run([str(LEDGERCTL), "rebuild"], check=True, cwd=APP_ROOT)
    subprocess.run([str(LEDGERCTL), "report", "--out", str(REPORT)], check=True, cwd=APP_ROOT)
    second = json.loads(REPORT.read_text(encoding="utf-8"))
    assert second["snapshot_digest"] == first["snapshot_digest"]


def test_reversal_consume_and_correction(tmp_path: Path) -> None:
    """Preserved anchor: reversal must invert CONSUME and CORRECTION distinctly."""
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-RB0001", "account_id": "ACC-RB01", "operation": "CORRECTION", "amount": 10,
         "logical_time": "2026-06-03T10:00:00Z", "source_replica": "REP-RBX", "seq": 1, "epoch": 1},
        {"event_id": "QE-RB0002", "account_id": "ACC-RB01", "operation": "CONSUME", "amount": 4,
         "logical_time": "2026-06-03T11:00:00Z", "source_replica": "REP-RBX", "seq": 2, "epoch": 1},
        {"event_id": "QE-RB0003", "account_id": "ACC-RB01", "operation": "REVERSAL", "target_event_id": "QE-RB0002",
         "logical_time": "2026-06-03T12:00:00Z", "source_replica": "REP-RBX", "seq": 3, "epoch": 1},
        {"event_id": "QE-RB0004", "account_id": "ACC-RB01", "operation": "REVERSAL", "target_event_id": "QE-RB0001",
         "logical_time": "2026-06-03T13:00:00Z", "source_replica": "REP-RBX", "seq": 4, "epoch": 1},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "rev")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(events)
    assert payload == expected


def test_chronological_order_beats_file_order(tmp_path: Path) -> None:
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-LATE01", "account_id": "ACC-ORDER", "operation": "RESERVE", "amount": 5,
         "logical_time": "2026-06-04T12:00:00Z", "source_replica": "REP-ORD", "seq": 2, "epoch": 1},
        {"event_id": "QE-EARLY1", "account_id": "ACC-ORDER", "operation": "CORRECTION", "amount": 20,
         "logical_time": "2026-06-04T10:00:00Z", "source_replica": "REP-ORD", "seq": 1, "epoch": 1},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "ord")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(events)
    assert payload == expected


def test_generated_seed_workflow(tmp_path: Path) -> None:
    rng = random.Random(0x51EE42)
    events = tmp_path / "gen.jsonl"
    rows = []
    for i in range(8):
        rows.append({
            "event_id": f"QE-{rng.randint(0, 999999):06d}",
            "account_id": f"ACC-G{i:04d}",
            "operation": "CORRECTION",
            "amount": rng.randint(1, 50),
            "logical_time": f"2026-07-{10+i:02d}T10:00:00Z",
            "source_replica": f"REP-{rng.randint(100,999):03d}",
            "seq": 1,
            "epoch": 1,
        })
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "gen")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(events)
    assert payload["accounts"] == expected["accounts"]
    assert payload["snapshot_digest"] == expected["snapshot_digest"]


def test_legacy_migration_only_account(tmp_path: Path) -> None:
    events = tmp_path / "empty.jsonl"
    events.write_text("", encoding="utf-8")
    run_workflow(events, "empty")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    legacy_row = next(r for r in payload["accounts"] if r["account_id"] == "ACC-LEGACY")
    assert legacy_row["available"] == 42
    assert legacy_row["epoch"] == 3


def test_truncated_batch_durable_prefix(tmp_path: Path) -> None:
    """Import durable prefix excludes an incomplete trailing record."""
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-TR0001", "account_id": "ACC-TRUNC", "operation": "CORRECTION", "amount": 7,
         "logical_time": "2026-06-05T10:00:00Z", "source_replica": "REP-TRN", "seq": 1, "epoch": 1},
        {"event_id": "QE-TR0002", "account_id": "ACC-TRUNC", "operation": "CONSUME", "amount": 2,
         "logical_time": "2026-06-05T11:00:00Z", "source_replica": "REP-TRN", "seq": 2, "epoch": 1},
    ]
    good = "\n".join(json.dumps(r) for r in rows) + "\n"
    partial = '{"event_id":"QE-PART1","account_id":"ACC-TRUNC"'
    events.write_text(good + partial, encoding="utf-8")
    run_workflow(events, "trunc")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    # Reference parses partial as malformed third line; durable-prefix import must ignore it entirely.
    assert payload["parsed_count"] == 2
    assert payload["malformed_line_count"] == 0
    good_only = tmp_path / "good.jsonl"
    good_only.write_text(good, encoding="utf-8")
    ref_good = reference_reconcile(good_only)
    assert payload["accounts"] == ref_good["accounts"]
    assert payload["snapshot_digest"] == ref_good["snapshot_digest"]


def test_reservation_expiration_at_rebuild(tmp_path: Path) -> None:
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-EX0001", "account_id": "ACC-EXP01", "operation": "CORRECTION", "amount": 20,
         "logical_time": "2020-01-01T10:00:00Z", "source_replica": "REP-EXP", "seq": 1, "epoch": 1},
        {"event_id": "QE-EX0002", "account_id": "ACC-EXP01", "operation": "RESERVE", "amount": 8,
         "logical_time": "2020-01-01T11:00:00Z", "source_replica": "REP-EXP", "seq": 2, "epoch": 1,
         "expires_at": "2020-01-01T12:00:00Z"},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "exp")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    acct = next(r for r in payload["accounts"] if r["account_id"] == "ACC-EXP01")
    assert acct["held"] == 0
    assert acct["available"] == 20


def test_replica_correction_conflict(tmp_path: Path) -> None:
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-SC0001", "account_id": "ACC-CONFL", "operation": "CORRECTION", "amount": 1,
         "logical_time": "2026-06-05T10:00:00Z", "source_replica": "REP-AAA", "seq": 1, "epoch": 1},
        {"event_id": "QE-SC0002", "account_id": "ACC-CONFL", "operation": "CORRECTION", "amount": 9,
         "logical_time": "2026-06-05T10:00:00Z", "source_replica": "REP-ZZZ", "seq": 1, "epoch": 1},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "conf")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(events)
    assert payload == expected


def test_seq_monotonic_across_operations(tmp_path: Path) -> None:
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-VERS01", "account_id": "ACC-VERS1", "operation": "CORRECTION", "amount": 5,
         "logical_time": "2026-06-07T10:00:00Z", "source_replica": "REP-VER", "seq": 2, "epoch": 1},
        {"event_id": "QE-VERS02", "account_id": "ACC-VERS1", "operation": "RESERVE", "amount": 1,
         "logical_time": "2026-06-07T11:00:00Z", "source_replica": "REP-VER", "seq": 1, "epoch": 1},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "vers")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(events)
    assert payload == expected


def test_resume_replica_mismatch(tmp_path: Path) -> None:
    events = tmp_path / "batch.jsonl"
    rows = [
        {"event_id": "QE-DEL001", "account_id": "ACC-LOCK1", "operation": "CORRECTION", "amount": 4,
         "logical_time": "2026-06-11T10:00:00Z", "source_replica": "REP-OWN", "seq": 1, "epoch": 1},
        {"event_id": "QE-DEL002", "account_id": "ACC-LOCK1", "operation": "SUSPEND",
         "logical_time": "2026-06-11T11:00:00Z", "source_replica": "REP-OWN", "seq": 2, "epoch": 1},
        {"event_id": "QE-DEL003", "account_id": "ACC-LOCK1", "operation": "RESUME",
         "logical_time": "2026-06-11T12:00:00Z", "source_replica": "REP-OTHER", "seq": 1, "epoch": 1},
        {"event_id": "QE-DEL004", "account_id": "ACC-LOCK1", "operation": "RESUME",
         "logical_time": "2026-06-11T13:00:00Z", "source_replica": "REP-OWN", "seq": 3, "epoch": 1},
    ]
    events.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    run_workflow(events, "lock")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(events)
    assert payload == expected


def test_multi_batch_replay_order(tmp_path: Path) -> None:
    batch_a = tmp_path / "a.jsonl"
    batch_b = tmp_path / "b.jsonl"
    batch_a.write_text(json.dumps({
        "event_id": "QE-MBA001", "account_id": "ACC-MULTI", "operation": "CORRECTION", "amount": 5,
        "logical_time": "2026-08-01T12:00:00Z", "source_replica": "REP-MBA", "seq": 1, "epoch": 1,
    }) + "\n", encoding="utf-8")
    batch_b.write_text(json.dumps({
        "event_id": "QE-MBB001", "account_id": "ACC-MULTI", "operation": "RESERVE", "amount": 2,
        "logical_time": "2026-08-01T10:00:00Z", "source_replica": "REP-MBA", "seq": 2, "epoch": 1,
    }) + "\n", encoding="utf-8")
    reset_state()
    subprocess.run([str(LEDGERCTL), "import", "--batch", "b", "--events", str(batch_b)], check=True, cwd=APP_ROOT)
    subprocess.run([str(LEDGERCTL), "import", "--batch", "a", "--events", str(batch_a)], check=True, cwd=APP_ROOT)
    subprocess.run([str(LEDGERCTL), "rebuild"], check=True, cwd=APP_ROOT)
    subprocess.run([str(LEDGERCTL), "report", "--out", str(REPORT)], check=True, cwd=APP_ROOT)
    combined = tmp_path / "combined.jsonl"
    combined.write_text(batch_b.read_text() + batch_a.read_text(), encoding="utf-8")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = reference_reconcile(combined)
    assert payload["accounts"] == expected["accounts"]
