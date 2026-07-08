"""Independent neural-echo-forge reference (memory ingest + export)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

DATA_ROOT = Path("/app/data")
PROFILES_PATH = DATA_ROOT / "profiles" / "user-profiles.json"
TOOL_PATH = DATA_ROOT / "tool-calls" / "tool-log.jsonl"
STAGING_PATH = Path("/app/state/ingest-staging.json")
SNAPSHOT_PATH = Path("/app/state/memory-snapshot.json")
RECORDS_PATH = Path("/app/output/memory-records.json")
INDEX_PATH = Path("/app/output/retrieval-index.json")
AUDIT_PATH = Path("/app/output/memory-audit.json")

VALID_TIERS = {"ephemeral", "short", "long"}


def default_sessions_root() -> Path:
    return Path(os.environ.get("NEF_SESSIONS_ROOT", str(DATA_ROOT / "sessions")))


def policy_path() -> Path:
    return Path(
        os.environ.get("NEF_POLICY_PATH", str(DATA_ROOT / "policies" / "memory-policy.json"))
    )


def load_policy() -> dict:
    return json.loads(policy_path().read_text(encoding="utf-8"))


def normalize_object(obj: str) -> str:
    return " ".join(obj.lower().split())


def levenshtein(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def semantic_duplicate(a: dict, b: dict) -> bool:
    if a["subject"] != b["subject"] or a["predicate"] != b["predicate"]:
        return False
    na = normalize_object(a["object"])
    nb = normalize_object(b["object"])
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) >= 6 and longer.startswith(shorter):
        return True
    return levenshtein(na, nb) <= 2


def pick_winner(a: dict, b: dict, conflict_mode: str = "closed") -> dict:
    if conflict_mode == "open":
        if a["confidence"] != b["confidence"]:
            return a if a["confidence"] > b["confidence"] else b
        if a["anchor_ms"] != b["anchor_ms"]:
            return a if a["anchor_ms"] > b["anchor_ms"] else b
    else:
        if a["anchor_ms"] != b["anchor_ms"]:
            return a if a["anchor_ms"] > b["anchor_ms"] else b
        if a["confidence"] != b["confidence"]:
            return a if a["confidence"] > b["confidence"] else b
    return a if a["memory_id"] >= b["memory_id"] else b


def parse_memory_fields(row: dict) -> dict | None:
    subject = row.get("subject", "")
    predicate = row.get("predicate", "")
    if not subject or not predicate:
        return None
    memory_id = row.get("memory_id")
    obj = row.get("object")
    confidence = row.get("confidence")
    tier = row.get("tier")
    if not memory_id or obj is None or confidence is None or tier not in VALID_TIERS:
        return None
    if not 0.0 <= float(confidence) <= 1.0:
        return None
    return {
        "memory_id": memory_id,
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "confidence": float(confidence),
        "tier": tier,
    }


def parse_profile_baseline_fields(row: dict, subject: str) -> dict | None:
    predicate = row.get("predicate", "")
    if not predicate:
        return None
    obj = row.get("object")
    confidence = row.get("confidence")
    tier = row.get("tier")
    if obj is None or confidence is None or tier not in VALID_TIERS:
        return None
    if not 0.0 <= float(confidence) <= 1.0:
        return None
    mem_id = f"profile-{subject.replace(':', '-')}-{predicate}"
    return {
        "memory_id": mem_id,
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "confidence": float(confidence),
        "tier": tier,
    }


def discover_session_shards(root: Path | None = None) -> list[Path]:
    base = root if root is not None else default_sessions_root()
    order_path = base / "load-order.json"
    if order_path.is_file():
        names = json.loads(order_path.read_text(encoding="utf-8"))
    else:
        names = sorted(p.name for p in base.glob("*.jsonl"))
    return [base / name for name in names if (base / name).is_file()]


def resolve_group(candidates: list[dict], conflict_mode: str = "closed") -> tuple[dict, list[dict]]:
    superseded: list[dict] = []
    pending: list[tuple[dict, str]] = []
    rest: list[dict] = []
    for cand in candidates:
        if cand["source"] == "session_correction":
            target = cand.pop("correction_target", cand["memory_id"])
            pending.append((cand, target))
        else:
            rest.append(cand)
    # Corrections resolve to a fixpoint: a correction applies only when its target is
    # currently present among survivors, which may be a memory_id produced by an earlier
    # correction in a chain. Iterate until nothing more applies. Missing, cross-group,
    # and cyclic corrections never become present and are superseded.
    while True:
        progressed = False
        still: list[tuple[dict, str]] = []
        for corr, target in pending:
            if any(r["memory_id"] == target for r in rest):
                kept: list[dict] = []
                for row in rest:
                    if row["memory_id"] == target:
                        superseded.append(row)
                    else:
                        kept.append(row)
                rest = kept
                rest.append(corr)
                progressed = True
            else:
                still.append((corr, target))
        pending = still
        if not progressed or not pending:
            break
    for corr, _target in pending:
        superseded.append(corr)
    if not rest:
        return {}, superseded
    winner = rest[0]
    for cand in rest[1:]:
        nxt = pick_winner(winner, cand, conflict_mode)
        if nxt["memory_id"] != winner["memory_id"]:
            superseded.append(winner)
        else:
            superseded.append(cand)
        winner = nxt
    return winner, superseded


def semantic_dedup(winners: list[dict], conflict_mode: str = "closed") -> tuple[list[dict], list[dict]]:
    superseded: list[dict] = []
    kept: list[dict] = []
    for cand in winners:
        merged_idx = [i for i, existing in enumerate(kept) if semantic_duplicate(cand, existing)]
        if not merged_idx:
            kept.append(cand)
            continue
        pool = [kept[i] for i in merged_idx] + [cand]
        best = pool[0]
        for item in pool[1:]:
            nxt = pick_winner(best, item, conflict_mode)
            if nxt["memory_id"] != best["memory_id"]:
                superseded.append(best)
            else:
                superseded.append(item)
            best = nxt
        for idx in reversed(merged_idx):
            removed = kept.pop(idx)
            if removed["memory_id"] != best["memory_id"]:
                superseded.append(removed)
        merged_from = sorted(
            {s["memory_id"] for s in superseded if semantic_duplicate(s, best)}
        )
        if merged_from:
            best = {**best, "merged_from": merged_from}
        kept.append(best)
    return kept, superseded


def apply_retention(records: list[dict], policy: dict, reference_anchor_ms: int) -> tuple[list[ dict], list[dict]]:
    drop_tiers = set(policy.get("export_drop_tiers", []))
    short_ttl = policy.get("tier_ttl_ms", {}).get("short", 604_800_000)
    max_per = int(policy.get("max_per_predicate", 1))
    vault: list[dict] = []
    active: list[dict] = []
    for rec in records:
        if rec["tier"] in drop_tiers:
            vault.append(rec)
            continue
        if rec["tier"] == "short" and reference_anchor_ms - rec["anchor_ms"] > short_ttl:
            vault.append(rec)
            continue
        active.append(rec)
    grouped: dict[tuple[str, str], list[dict]] = {}
    for rec in active:
        grouped.setdefault((rec["subject"], rec["predicate"]), []).append(rec)
    final_active: list[dict] = []
    for group in grouped.values():
        group.sort(key=lambda r: (-r["anchor_ms"], -r["confidence"], r["memory_id"]))
        for idx, rec in enumerate(group):
            if idx < max_per:
                final_active.append(rec)
            else:
                vault.append(rec)
    final_active.sort(key=lambda r: (r["anchor_ms"], r["memory_id"]))
    vault.sort(key=lambda r: (r["anchor_ms"], r["memory_id"]))
    return final_active, vault


def ingest_all(sessions_root: Path | None = None, prior_seq: int = 0) -> tuple[dict, dict]:
    policy = load_policy()
    export_mode = policy.get("export_mode", "closed")
    conflict_mode = policy.get("conflict_mode", export_mode)
    sources_loaded: list[str] = []
    lines_skipped = 0
    discovery_seq = 0
    candidates: list[dict] = []
    reference_anchor_ms = 0

    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    sources_loaded.append("profiles.json")
    for profile in profiles.get("profiles", []):
        subject = profile.get("subject", "")
        if not subject:
            continue
        for row in profile.get("baseline", []):
            parsed = parse_profile_baseline_fields(row, subject)
            if not parsed:
                lines_skipped += 1
                continue
            candidates.append(
                {
                    **parsed,
                    "anchor_ms": 0,
                    "source": "profile_baseline",
                    "discovery_seq": discovery_seq,
                }
            )
            discovery_seq += 1

    sources_loaded.append("tool-log.jsonl")
    for line in TOOL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            anchor_ms = int(row["anchor_ms"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            lines_skipped += 1
            continue
        reference_anchor_ms = max(reference_anchor_ms, anchor_ms)
        parsed = parse_memory_fields(row)
        if not parsed:
            lines_skipped += 1
            continue
        candidates.append(
            {
                **parsed,
                "anchor_ms": anchor_ms,
                "source": "tool_invoke",
                "discovery_seq": discovery_seq,
            }
        )
        discovery_seq += 1

    root = sessions_root if sessions_root is not None else default_sessions_root()
    for path in discover_session_shards(root):
        sources_loaded.append(path.name)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                anchor_ms = int(row["anchor_ms"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                lines_skipped += 1
                continue
            reference_anchor_ms = max(reference_anchor_ms, anchor_ms)
            if row.get("correction") is not None and row.get("memory") is not None:
                lines_skipped += 1
                continue
            if row.get("correction") is not None:
                corr = dict(row["correction"])
                targets = corr.get("targets", "")
                if not targets:
                    lines_skipped += 1
                    continue
                becomes = corr.get("becomes") or ""
                corr["memory_id"] = becomes if becomes else targets
                parsed = parse_memory_fields(corr)
                if not parsed:
                    lines_skipped += 1
                    continue
                candidates.append(
                    {
                        **parsed,
                        "anchor_ms": anchor_ms,
                        "source": "session_correction",
                        "discovery_seq": discovery_seq,
                        "correction_target": targets,
                    }
                )
                discovery_seq += 1
                continue
            if row.get("memory") is not None:
                parsed = parse_memory_fields(row["memory"])
                if not parsed:
                    lines_skipped += 1
                    continue
                candidates.append(
                    {
                        **parsed,
                        "anchor_ms": anchor_ms,
                        "source": "session_memory",
                        "discovery_seq": discovery_seq,
                    }
                )
                discovery_seq += 1

    grouped: dict[tuple[str, str], list[dict]] = {}
    for cand in candidates:
        grouped.setdefault((cand["subject"], cand["predicate"]), []).append(cand)

    group_winners: list[dict] = []
    superseded: list[dict] = []
    for group in grouped.values():
        winner, losers = resolve_group(group, conflict_mode)
        if winner:
            group_winners.append(winner)
        superseded.extend(losers)

    winners, dedup_losers = semantic_dedup(group_winners, conflict_mode)
    superseded.extend(dedup_losers)
    superseded.sort(key=lambda r: r["discovery_seq"])

    active_memories, retention_vault = apply_retention(
        winners, policy, reference_anchor_ms
    )

    snapshot = {
        "snapshot_version": 1,
        "snapshot_seq": prior_seq + 1,
        "lines_skipped": lines_skipped,
        "reference_anchor_ms": reference_anchor_ms,
        "sources_loaded": sources_loaded,
        "active_memories": active_memories,
        "superseded_memories": superseded,
        "retention_vault": retention_vault,
        "ingest_fingerprint": "",
    }
    snapshot["ingest_fingerprint"] = fingerprint(snapshot)
    staging = build_staging_ledger(
        candidates, conflict_mode, export_mode, snapshot["snapshot_seq"]
    )
    return snapshot, staging


def fingerprint(snapshot: dict) -> str:
    lines = [
        str(snapshot["reference_anchor_ms"]),
        ",".join(snapshot["sources_loaded"]),
    ]
    for rec in snapshot["active_memories"]:
        lines.append(
            f"{rec['memory_id']}:{rec['subject']}:{rec['predicate']}:{rec['object']}:{rec['anchor_ms']}"
        )
    for rec in snapshot["retention_vault"]:
        lines.append(f"{rec['memory_id']}:{rec['subject']}:{rec['predicate']}")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def export_quota(active: list[dict], export_mode: str = "closed") -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for rec in active:
        grouped.setdefault((rec["subject"], rec["predicate"]), []).append(rec)
    records: list[dict] = []
    for group in grouped.values():
        if export_mode == "open":
            group.sort(key=lambda r: (r["confidence"], r["anchor_ms"], r["memory_id"]), reverse=True)
        else:
            group.sort(key=lambda r: (r["anchor_ms"], r["confidence"], r["memory_id"]), reverse=True)
        if group:
            records.append(group[0])
    records.sort(key=lambda r: (r["subject"], r["predicate"], r["memory_id"]))
    return records


def build_retrieval_index(records: list[dict]) -> dict:
    by_subject: dict[str, list[dict]] = {}
    for rec in records:
        by_subject.setdefault(rec["subject"], []).append(rec)
    index: dict[str, dict[str, list[str]]] = {}
    for subject, rows in sorted(by_subject.items()):
        pred_map: dict[str, tuple[int, list[str]]] = {}
        for rec in rows:
            pred = rec["predicate"]
            entry = pred_map.setdefault(pred, (rec["discovery_seq"], []))
            entry = (min(entry[0], rec["discovery_seq"]), entry[1])
            entry[1].append(rec["memory_id"])
            pred_map[pred] = entry
        ordered = sorted(
            ((seq, pred, sorted(ids)) for pred, (seq, ids) in pred_map.items()),
            key=lambda item: (item[0], item[1]),
        )
        index[subject] = {pred: ids for _seq, pred, ids in ordered}
    return index


def candidate_digest(candidates: list[dict]) -> str:
    lines = [f"{c['memory_id']}:{c['discovery_seq']}" for c in candidates]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def build_staging_ledger(
    candidates: list[dict],
    conflict_mode: str,
    export_mode: str,
    staging_seq: int,
) -> dict:
    return {
        "staging_version": 1,
        "staging_seq": staging_seq,
        "conflict_mode": conflict_mode,
        "export_mode": export_mode,
        "candidate_count": len(candidates),
        "candidate_digest_sha256": candidate_digest(candidates),
    }


def export_from_snapshot(
    snapshot: dict,
    staging: dict,
    prior_export_generation: int = 0,
    staging_bytes: bytes | None = None,
) -> tuple[dict, dict, dict]:
    export_mode = staging.get("export_mode", "closed")
    records = export_quota(snapshot["active_memories"], export_mode)
    records_doc = {
        "snapshot_seq": snapshot["snapshot_seq"],
        "reference_anchor_ms": snapshot["reference_anchor_ms"],
        "records": records,
    }
    index = build_retrieval_index(records)
    if staging_bytes is None:
        staging_bytes = (
            json.dumps(staging, indent=2).encode() + b"\n"
        )
    audit = {
        "export_generation": prior_export_generation + 1,
        "active_staged": len(snapshot["active_memories"]),
        "vault_staged": len(snapshot["retention_vault"]),
        "superseded_staged": len(snapshot["superseded_memories"]),
        "exported_records": len(records),
        "lines_skipped": snapshot["lines_skipped"],
        "staging_digest_sha256": hashlib.sha256(staging_bytes).hexdigest(),
    }
    return records_doc, index, audit


def build_outputs(sessions_root: Path | None = None, prior_seq: int = 0) -> tuple[dict, dict, dict, dict, dict]:
    snapshot, staging = ingest_all(sessions_root=sessions_root, prior_seq=prior_seq)
    records_doc, index, audit = export_from_snapshot(snapshot, staging)
    return snapshot, staging, records_doc, index, audit


def digest_snapshot_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
