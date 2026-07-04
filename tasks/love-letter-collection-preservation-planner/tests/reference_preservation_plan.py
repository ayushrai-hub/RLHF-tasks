"""Independent reference for love letter collection preservation planning."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def parse_letterfolio_dir(letterfolio_dir: Path, collection_path: Path) -> dict:
    artifacts: list[dict] = []
    for path in sorted(letterfolio_dir.glob("*.letterfolio")):
        rec = {
            "artifact_id": "",
            "keepsake": "",
            "media_slot": 0,
            "era": "",
            "format": "general",
            "redundancy": 1,
            "fragile_with": [],
            "crossref": [],
            "bytes": 0,
            "source_file": path.name,
        }
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("ARTIFACT "):
                rec["artifact_id"] = line.split(None, 1)[1].strip()
            elif line.startswith("KEEPSAKE "):
                rec["keepsake"] = line.split(None, 1)[1].strip()
            elif line.startswith("MEDIA_SLOT "):
                rec["media_slot"] = int(line.split(None, 1)[1].strip())
            elif line.startswith("ERA "):
                rec["era"] = line.split(None, 1)[1].strip()
            elif line.startswith("FORMAT "):
                rec["format"] = line.split(None, 1)[1].strip()
            elif line.startswith("REDUNDANCY "):
                rec["redundancy"] = int(line.split(None, 1)[1].strip())
            elif line.startswith("FRAGILE "):
                rest = line.split(None, 1)[1] if len(line.split()) > 1 else ""
                rec["fragile_with"] = [x for x in rest.replace(",", " ").split() if x]
            elif line.startswith("CROSSREF "):
                rest = line.split(None, 1)[1] if len(line.split()) > 1 else ""
                rec["crossref"] = sorted([x for x in rest.replace(",", " ").split() if x])
            elif line.startswith("BYTES "):
                rec["bytes"] = int(line.split(None, 1)[1].strip())
        artifacts.append(rec)
    artifacts.sort(key=lambda e: e["artifact_id"])
    collection = json.loads(collection_path.read_text())
    return {"artifacts": artifacts, "collection": collection}


def collection_snapshot_hash(artifacts: list[dict], collection: dict) -> str:
    payload = {
        "artifacts": artifacts,
        "collection": {k: collection[k] for k in sorted(collection) if k != "schema_version"},
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def era_pools(artifacts: list[dict]) -> dict[str, list[str]]:
    pools: dict[str, list[str]] = {}
    for e in artifacts:
        pools.setdefault(e["era"], []).append(e["artifact_id"])
    for k in pools:
        pools[k] = sorted(pools[k])
    return dict(sorted(pools.items()))


def priority_score(artifact: dict) -> float:
    return artifact["redundancy"] - len(artifact["crossref"]) - abs(artifact["media_slot"]) / 12.0


def priority_order(artifacts: list[dict]) -> list[str]:
    ranked = sorted(artifacts, key=lambda e: (-priority_score(e), e["artifact_id"]))
    return [e["artifact_id"] for e in ranked]


def index_ledger(artifacts: list[dict], salt: str) -> dict:
    edges: list[str] = []
    for e in artifacts:
        for h in e["crossref"]:
            edges.append("|".join(sorted([e["artifact_id"], h])))
    edges = sorted(set(edges))
    digest = hashlib.sha256((salt + "\n" + "\n".join(edges)).encode()).hexdigest()
    return {"schema_version": 1, "index_edges": edges, "index_digest": digest}


def round1_migrations(queue: list[str], artifacts: list[dict]) -> list[dict]:
    by_id = {e["artifact_id"]: e for e in artifacts}
    n = len(queue)
    if n % 2 != 0:
        raise ValueError("schedule requires even artifact count")
    pairs: list[dict] = []
    for i in range(n // 2):
        a = queue[i]
        b = queue[n - 1 - i]
        if b in by_id[a].get("fragile_with", []) or a in by_id[b].get("fragile_with", []):
            raise ValueError(f"conflict pairing {a} vs {b}")
        pairs.append(
            {
                "migration_id": f"r1-m{i + 1}",
                "primary": a,
                "replica": b,
                "round": 1,
            }
        )
    return pairs


def preservation_waves(
    migration_pairs: list[dict], artifacts: list[dict], band_months: int
) -> list[dict]:
    by_id = {e["artifact_id"]: e for e in artifacts}
    waves: dict[int, list[str]] = {}
    for p in migration_pairs:
        slot_max = max(
            abs(by_id[p["primary"]]["media_slot"]),
            abs(by_id[p["replica"]]["media_slot"]),
        )
        band = slot_max // band_months if band_months > 0 else 0
        waves.setdefault(band, []).append(p["migration_id"])
    return [{"wave_epoch": b, "migration_ids": sorted(waves[b])} for b in sorted(waves)]


def workload_ok(
    migration_pairs: list[dict], artifacts: list[dict], max_parallel_migrations: int
) -> bool:
    counts: dict[str, int] = {}
    for p in migration_pairs:
        for role in ("primary", "replica"):
            counts[p[role]] = counts.get(p[role], 0) + 1
    by_id = {e["artifact_id"]: e for e in artifacts}
    for art, c in counts.items():
        cap = min(by_id[art]["redundancy"], max_parallel_migrations)
        if c > cap:
            return False
    return True


def storage_budget_ok(
    migration_pairs: list[dict], artifacts: list[dict], collection: dict
) -> bool:
    by_id = {e["artifact_id"]: e for e in artifacts}
    used = sum(by_id[p["primary"]]["bytes"] + by_id[p["replica"]]["bytes"] for p in migration_pairs)
    budget = int(collection.get("storage_byte_budget", used))
    return used <= budget


def preservation_staging(artifacts: list[dict], collection: dict) -> dict:
    queue = priority_order(artifacts)
    migration_pairs = round1_migrations(queue, artifacts)
    waves = preservation_waves(migration_pairs, artifacts, int(collection["block_span_months"]))
    within = workload_ok(
        migration_pairs, artifacts, int(collection["max_parallel_migrations"])
    ) and storage_budget_ok(migration_pairs, artifacts, collection)
    body = {
        "schema_version": 1,
        "priority_queue": queue,
        "migration_pairs": migration_pairs,
        "preservation_waves": waves,
        "within_storage_budget": within,
    }
    schedule_hash = hashlib.sha256(
        json.dumps({k: body[k] for k in body}, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    body["schedule_hash"] = schedule_hash
    return body


def redundancy_pools(artifacts: list[dict], snapshot_hash: str) -> dict:
    pools = era_pools(artifacts)
    body = {
        "schema_version": 1,
        "eras": pools,
        "era_count": len(pools),
        "collection_snapshot_hash": snapshot_hash,
    }
    body["redundancy_hash"] = hashlib.sha256(
        json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return body


def migration_rollup(artifacts: list[dict], snapshot_hash: str) -> dict:
    groups: dict[str, list[str]] = {}
    for e in artifacts:
        tag = e.get("format", "general")
        groups.setdefault(tag, []).append(e["artifact_id"])
    for k in groups:
        groups[k] = sorted(groups[k])
    groups = dict(sorted(groups.items()))
    body = {
        "schema_version": 1,
        "format_groups": groups,
        "format_count": len(groups),
        "collection_snapshot_hash": snapshot_hash,
    }
    body["rollup_hash"] = hashlib.sha256(
        json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return body


def ingest_manifest(
    snapshot_hash: str,
    redundancy_hash: str,
    rollup_hash: str,
    index_digest: str,
    schedule_hash: str,
    run_sequence: int,
) -> dict:
    body = {
        "schema_version": 1,
        "collection_snapshot_hash": snapshot_hash,
        "redundancy_hash": redundancy_hash,
        "rollup_hash": rollup_hash,
        "index_digest": index_digest,
        "schedule_hash": schedule_hash,
        "run_sequence": run_sequence,
        "ingest_complete": True,
    }
    body["manifest_hash"] = hashlib.sha256(
        json.dumps({k: body[k] for k in body if k != "manifest_hash"}, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return body


def reference_preservation(archive_root: Path) -> dict:
    letterfolio_dir = archive_root / "letterfolio"
    collection_path = archive_root / "collection.json"
    parsed = parse_letterfolio_dir(letterfolio_dir, collection_path)
    artifacts = parsed["artifacts"]
    collection = parsed["collection"]
    snap_hash = collection_snapshot_hash(artifacts, collection)
    pools = redundancy_pools(artifacts, snap_hash)
    rollup = migration_rollup(artifacts, snap_hash)
    ledger = index_ledger(artifacts, collection["migration_salt"])
    staging = preservation_staging(artifacts, collection)
    manifest = ingest_manifest(
        snap_hash,
        pools["redundancy_hash"],
        rollup["rollup_hash"],
        ledger["index_digest"],
        staging["schedule_hash"],
        1,
    )
    atlas = {
        "schema_version": 1,
        "collection_label": collection["collection_label"],
        "priority_queue": staging["priority_queue"],
        "migration_pairs": staging["migration_pairs"],
        "preservation_waves": staging["preservation_waves"],
        "schedule_hash": staging["schedule_hash"],
        "index_digest": ledger["index_digest"],
    }
    bind = json.dumps(atlas, separators=(",", ":"), sort_keys=True)
    report = {
        "schema_version": 1,
        "artifact_count": len(artifacts),
        "migration_count": len(staging["migration_pairs"]),
        "wave_count": len(staging["preservation_waves"]),
        "report_fingerprint": hashlib.sha256(bind.encode()).hexdigest(),
    }
    return {
        "artifacts": artifacts,
        "collection": collection,
        "collection_snapshot_hash": snap_hash,
        "pools": pools,
        "rollup": rollup,
        "ledger": ledger,
        "staging": staging,
        "manifest": manifest,
        "atlas": atlas,
        "report": report,
    }
