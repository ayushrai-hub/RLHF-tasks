"""Independent expected-value computation for vault hot-reload audit exports."""

from __future__ import annotations

import hashlib
import json
from typing import Any

SOURCE_RANK = {"env": 3, "vault_file": 2, "sidecar_mount": 1}
EPOCH_BASE_DEFAULT = 1_700_000_000


def source_rank(source: str) -> int:
    return SOURCE_RANK.get(source, 0)


def replay_shard_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda r: (r["shard_seq"], r["shard_id"]))
    winners: dict[tuple[int, str], dict[str, Any]] = {}
    latest_by_workload: dict[str, dict[str, Any]] = {}
    workload_versions: dict[str, str] = {}
    leaks: list[dict[str, Any]] = []

    for sh in ordered:
        preview = sh.get("preview")
        if not sh["log_redacted"] and preview:
            leaks.append(
                {
                    "workload_id": sh["workload_id"],
                    "shard_seq": sh["shard_seq"],
                    "detail": "unredacted_preview",
                }
            )
        key = (sh["shard_seq"], sh["workload_id"])
        rank = source_rank(sh["material_source"])
        cur = winners.get(key)
        if cur is None or rank > source_rank(cur["effective_source"]):
            winners[key] = {
                "shard_seq": sh["shard_seq"],
                "workload_id": sh["workload_id"],
                "effective_source": sh["material_source"],
                "secret_version": sh["secret_version"],
            }
        latest_by_workload[sh["workload_id"]] = sh
        if sh["reload_applied"]:
            workload_versions[sh["workload_id"]] = sh["secret_version"]

    workloads: list[dict[str, Any]] = []
    for wl in sorted(latest_by_workload):
        latest = latest_by_workload[wl]
        workloads.append(
            {
                "workload_id": wl,
                "active_version": workload_versions.get(wl, ""),
                "reload_pending": "false" if latest["reload_applied"] else "true",
            }
        )

    shard_list = [winners[k] for k in sorted(winners)]
    leaks.sort(key=lambda x: (x["shard_seq"], x["workload_id"]))
    max_seq = max((r["shard_seq"] for r in ordered), default=0)
    return {
        "shards": shard_list,
        "workloads": workloads,
        "leak_rows": leaks,
        "max_shard_seq": max_seq,
    }


def compact_report_body(
    tenant_id: str,
    replay: dict[str, Any],
    shard_count: int,
    duplicate_skipped: int,
    reported_at_unix: int,
) -> str:
    body = {
        "tenant_id": tenant_id,
        "shards": replay["shards"],
        "workloads": replay["workloads"],
        "leak_rows": replay["leak_rows"],
        "stats": {
            "shard_count": shard_count,
            "duplicate_shards_skipped": duplicate_skipped,
            "workload_count": len(replay["workloads"]),
            "reported_at_unix": reported_at_unix,
        },
    }
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False) + "\n"


def audit_hash_from_body(compact_with_newline: str) -> str:
    return hashlib.sha256(compact_with_newline.encode("utf-8")).hexdigest()


def expected_report(
    tenant_id: str,
    rows: list[dict[str, Any]],
    *,
    shard_count: int,
    duplicate_skipped: int,
    epoch_base: int = EPOCH_BASE_DEFAULT,
) -> dict[str, Any]:
    replay = replay_shard_rows(rows)
    reported_at = epoch_base + replay["max_shard_seq"]
    compact = compact_report_body(
        tenant_id, replay, shard_count, duplicate_skipped, reported_at
    )
    body = json.loads(compact.rstrip("\n"))
    body["audit_hash"] = audit_hash_from_body(compact)
    return body


def build_report(
    tenant_id: str,
    rows: list[dict[str, Any]],
    *,
    duplicate_skipped: int = 0,
    epoch_base: int = EPOCH_BASE_DEFAULT,
) -> dict[str, Any]:
    return expected_report(
        tenant_id,
        rows,
        shard_count=len(rows),
        duplicate_skipped=duplicate_skipped,
        epoch_base=epoch_base,
    )
