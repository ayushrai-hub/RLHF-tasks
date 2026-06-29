"""Verifier for hardened forge stage replay, recovery, state, and cache semantics."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

APP = Path("/app")
SOURCE_BIN = APP / "bin" / "forge_stage"
FIXTURE_DIR = APP / "fixtures"
OUT = APP / "output"
VERIFIER_BIN = Path("/tmp/verifier_bin/forge_stage")
FORGE_LOG = OUT / "forge_log.jsonl"
FORGE_REPORT = OUT / "forge_report.json"
EDITABLE_ROOT = APP / "src"
HIDDEN_SEED = 20260626
DEFAULT_DIE_ROOT = APP / "data" / "dies"
DEFAULT_SNAPSHOT = APP / "snapshot" / "forge_baseline.json"
DEFAULT_STATE_DIR = OUT / "state"


# ---------------------------------------------------------------------------
# Digest and FDIE helpers
# ---------------------------------------------------------------------------


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def additive_checksum(data: bytes) -> int:
    return sum(data) & 0xFFFFFFFF


def die_root_digest(root: Path) -> str:
    parts: dict[str, str] = {}
    if root.is_dir():
        for entry in sorted(root.iterdir(), key=lambda p: p.name):
            if entry.is_file():
                parts[entry.name] = sha256_hex(entry.read_bytes())
    return sha256_hex(json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def write_fdie_v1(path: Path, die_id: str, tonnage: int, *, corrupt: bool = False) -> int:
    """Write an FDIE v1 block and return the additive checksum."""
    payload = f"{die_id}|{tonnage}".encode("utf-8")
    checksum = additive_checksum(payload)
    stored = checksum ^ 0x5A if corrupt else checksum
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"FDIE" + struct.pack("<I", len(payload)) + payload + struct.pack("<I", stored)
    )
    return checksum


def write_fdie_v2(
    path: Path,
    die_id: str,
    nominal_tonnage: int,
    measured_tonnage: int | None = None,
    *,
    revision: int | None = None,
    corrupt: bool = False,
) -> int:
    """Write an FDIE v2 block and return the additive checksum."""
    header_obj: dict[str, object] = {"die_id": die_id, "nominal_tonnage": nominal_tonnage}
    if revision is not None:
        header_obj["revision"] = revision
    header = json.dumps(header_obj, sort_keys=True).encode("utf-8")
    payload_obj: dict[str, object] = {}
    if measured_tonnage is not None:
        payload_obj["measured_tonnage"] = measured_tonnage
    payload = json.dumps(payload_obj, sort_keys=True).encode("utf-8")
    checksum_input = header + struct.pack("<I", len(payload)) + payload
    checksum = additive_checksum(checksum_input)
    stored = checksum ^ 0xA5 if corrupt else checksum
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"FD2E"
        + struct.pack("<H", len(header))
        + header
        + struct.pack("<I", len(payload))
        + payload
        + struct.pack("<I", stored)
    )
    return checksum


def write_fdie_v3(
    path: Path,
    die_id: str,
    nominal: int,
    *,
    scale_milli: int = 1000,
    revision: int = 3,
    measured: int | None = None,
    delta: int | None = None,
    chunks: list[bytes] | None = None,
    corrupt_footer: bool = False,
) -> str:
    """Write an FDIE v3 block and return the footer digest hex."""
    header = json.dumps(
        {
            "die_id": die_id,
            "nominal_tonnage": nominal,
            "scale_milli": scale_milli,
            "revision": revision,
            "source_lot": "A-17",
        },
        sort_keys=True,
    ).encode("utf-8")
    if chunks is None:
        payload_obj: dict[str, object] = {}
        if measured is not None:
            payload_obj["measured_tonnage"] = measured
        if delta is not None:
            payload_obj["tonnage_delta"] = delta
        chunks = [json.dumps(payload_obj, sort_keys=True).encode("utf-8")]
    digest_input = bytearray(header)
    digest_input.extend(struct.pack("<H", len(chunks)))
    for chunk in chunks:
        digest_input.extend(struct.pack("<I", len(chunk)))
        digest_input.extend(chunk)
    footer = bytes.fromhex(sha256_hex(bytes(digest_input)))
    if corrupt_footer:
        footer = bytes(b ^ 0xFF for b in footer)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = bytearray(b"FD3E")
    body.extend(struct.pack("<H", len(header)))
    body.extend(header)
    body.extend(struct.pack("<H", len(chunks)))
    for chunk in chunks:
        body.extend(struct.pack("<I", len(chunk)))
        body.extend(chunk)
    body.extend(footer)
    path.write_bytes(body)
    return sha256_hex(bytes(digest_input))


def read_fdie_block(path: Path) -> tuple[str, int, int, str, int | None, str]:
    """Parse any FDIE version and return (die_id, tonnage, checksum, source_format, revision, digest_hex)."""
    data = path.read_bytes()
    if data[:4] == b"FDIE":
        payload_len = int.from_bytes(data[4:8], "little")
        payload = data[8 : 8 + payload_len]
        stored = int.from_bytes(data[8 + payload_len : 8 + payload_len + 4], "little")
        expected = additive_checksum(payload)
        assert stored == expected, f"fixture block checksum mismatch for {path}"
        die_id, tonnage_raw = payload.decode("utf-8").split("|", 1)
        return die_id, int(tonnage_raw), expected, "v1", None, f"{expected:08x}"
    if data[:4] == b"FD2E":
        header_len = int.from_bytes(data[4:6], "little")
        header = data[6 : 6 + header_len]
        payload_len = int.from_bytes(data[6 + header_len : 6 + header_len + 4], "little")
        payload = data[6 + header_len + 4 : 6 + header_len + 4 + payload_len]
        stored = int.from_bytes(
            data[6 + header_len + 4 + payload_len : 6 + header_len + 4 + payload_len + 4], "little"
        )
        checksum_input = header + struct.pack("<I", payload_len) + payload
        expected = additive_checksum(checksum_input)
        assert stored == expected, f"fixture block checksum mismatch for {path}"
        header_obj = json.loads(header.decode("utf-8"))
        payload_obj = json.loads(payload.decode("utf-8"))
        nominal = int(header_obj["nominal_tonnage"])
        measured = payload_obj.get("measured_tonnage")
        tonnage = int(measured) if measured is not None else nominal
        revision = header_obj.get("revision")
        return (
            str(header_obj["die_id"]),
            tonnage,
            expected,
            "v2",
            int(revision) if revision else None,
            f"{expected:08x}",
        )
    if data[:4] == b"FD3E":
        header_len = int.from_bytes(data[4:6], "little")
        header = data[6 : 6 + header_len]
        offset = 6 + header_len
        chunk_count = int.from_bytes(data[offset : offset + 2], "little")
        offset += 2
        digest_input = bytearray(header)
        digest_input.extend(struct.pack("<H", chunk_count))
        chunk_payload = bytearray()
        for _ in range(chunk_count):
            chunk_len = int.from_bytes(data[offset : offset + 4], "little")
            offset += 4
            digest_input.extend(struct.pack("<I", chunk_len))
            chunk = data[offset : offset + chunk_len]
            digest_input.extend(chunk)
            chunk_payload.extend(chunk)
            offset += chunk_len
        stored = data[offset : offset + 32]
        expected_hex = sha256_hex(bytes(digest_input))
        assert stored == bytes.fromhex(expected_hex), f"fixture v3 footer mismatch for {path}"
        header_obj = json.loads(header.decode("utf-8"))
        payload_obj = json.loads(chunk_payload.decode("utf-8"))
        nominal = int(header_obj["nominal_tonnage"])
        scale_milli = int(header_obj.get("scale_milli", 1000))
        measured = payload_obj.get("measured_tonnage")
        delta = int(payload_obj.get("tonnage_delta", 0))
        base = int(measured) if measured is not None else nominal + delta
        assert base >= 0, "negative tonnage"
        scaled = base * scale_milli
        tonnage = scaled // 1000
        revision = header_obj.get("revision")
        checksum = int.from_bytes(bytes.fromhex(expected_hex)[:4], "little")
        return (
            str(header_obj["die_id"]),
            tonnage,
            checksum,
            "v3",
            int(revision) if revision is not None else None,
            expected_hex,
        )
    raise AssertionError(f"bad fdie magic: {path}")


# ---------------------------------------------------------------------------
# Journal parsing, collapse, and digests
# ---------------------------------------------------------------------------


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if "forge_tier" in out and "forge_epoch" not in out:
        out["forge_epoch"] = out["forge_tier"]
    op = str(out.get("op", ""))
    if op == "die_seal":
        out["op"] = "die_sealed"
    elif op == "forge_purge":
        out["op"] = "forge_purged"
    return out


def ordering_key(entry: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        int(entry["ancestry_index"]),
        int(entry["seq"]),
        int(entry["journal_revision"]),
        int(entry["shard_index"]),
        int(entry["line_number"]),
    )


def parse_jsonl_file(
    path: Path, shard_index: int, ancestry_index: int, default_tag: str
) -> tuple[list[dict[str, Any]], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    non_empty = [idx for idx, line in enumerate(lines, start=1) if line.strip()]
    last_line = non_empty[-1] if non_empty else 0
    for line_no, line in enumerate(lines, start=1):
        text = line.strip()
        if not text:
            continue
        try:
            row = normalize_row(json.loads(text))
        except json.JSONDecodeError as exc:
            if line_no == last_line and entries:
                warnings.append(f"truncated journal row in {path}: {exc}")
                continue
            raise
        row["journal_revision"] = int(row.get("journal_revision", 1))
        row["op_id"] = str(row.get("op_id") or f"{row['seq']}-{line_no}")
        row["scenario_tag"] = str(row.get("scenario_tag") or default_tag)
        row["shard_index"] = shard_index
        row["line_number"] = line_no
        row["ancestry_index"] = ancestry_index
        row.setdefault("die_id", "")
        row.setdefault("forge_epoch", 0)
        entries.append(row)
    return entries, warnings


def collapse_entries(raw: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_op_id: dict[str, dict[str, Any]] = {}
    for entry in raw:
        existing = by_op_id.get(entry["op_id"])
        if existing is None or ordering_key(entry) > ordering_key(existing):
            by_op_id[entry["op_id"]] = entry
    tombstone_audit: list[dict[str, Any]] = []
    surviving: list[dict[str, Any]] = []
    for entry in by_op_id.values():
        if entry["op"] == "op_tombstone":
            tombstone_audit.append(entry)
        else:
            surviving.append(entry)
    surviving.sort(key=ordering_key)
    return surviving, tombstone_audit


def journal_stream_digest(entries: list[dict[str, Any]]) -> str:
    rows = [
        f"{e['scenario_tag']}|{e['seq']}|{e['journal_revision']}|{e['op']}|{e.get('die_id', '')}|{e['op_id']}"
        for e in entries
    ]
    rows.sort()
    return sha256_hex("\n".join(rows).encode("utf-8"))


def lineage_digest_hex(packs: list[dict[str, Any]], surviving_op_ids: list[str]) -> str:
    payload = {
        "packs": [
            {
                "id": p["id"],
                "parent": p["parent"],
                "generation": p["generation"],
                "journal_digest": p["journal_digest"],
            }
            for p in packs
        ],
        "surviving_op_ids": sorted(surviving_op_ids),
    }
    return sha256_hex(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_pack_rows(pack_dir: Path, ancestry_index: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    raw: list[dict[str, Any]] = []
    warnings: list[str] = []
    for shard_index, shard in enumerate(manifest["shards"]):
        shard_path = pack_dir / shard["path"]
        if ".." in Path(shard["path"]).parts:
            raise ValueError(f"shard path escapes pack directory: {shard['path']}")
        rows, row_warnings = parse_jsonl_file(
            shard_path, shard_index, ancestry_index, str(manifest["scenario_tag"])
        )
        raw.extend(rows)
        warnings.extend(row_warnings)
    return manifest, raw, warnings


def load_bundle_ordered_packs(bundle_dir: Path) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Path, int]]]:
    bundle = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in bundle["packs"]}
    children: dict[str, str] = {}
    for pack in bundle["packs"]:
        parent = pack.get("parent")
        if parent:
            if parent in children:
                raise ValueError("bundle parent chain is not linear")
            children[parent] = pack["id"]
        joined = bundle_dir / pack["path"]
        if ".." in Path(pack["path"]).parts:
            raise ValueError(f"pack path escapes bundle: {pack['path']}")
        if not joined.is_dir():
            raise FileNotFoundError(f"missing pack directory: {joined}")
    ordered_ids = [bundle["root_pack"]]
    while ordered_ids[-1] in children:
        ordered_ids.append(children[ordered_ids[-1]])
    if len(ordered_ids) != len(bundle["packs"]):
        raise ValueError("bundle parent chain does not include all packs")
    ordered: list[tuple[dict[str, Any], Path, int]] = []
    for ancestry_index, pack_id in enumerate(ordered_ids):
        pack_ref = by_id[pack_id]
        ordered.append((pack_ref, bundle_dir / pack_ref["path"], ancestry_index))
    return bundle, ordered


def load_replay_input(input_path: Path, die_root: Path) -> dict[str, Any]:
    warnings: list[str] = []
    raw: list[dict[str, Any]] = []
    lineage_packs: list[dict[str, Any]] = []
    scenario_tag = "default"
    pack_generation = 0

    if input_path.is_dir() and (input_path / "bundle.json").is_file():
        bundle, ordered = load_bundle_ordered_packs(input_path)
        scenario_tag = str(bundle["scenario_tag"])
        max_generation = 0
        for pack_ref, pack_dir, ancestry_index in ordered:
            _manifest, pack_rows, pack_warnings = load_pack_rows(pack_dir, ancestry_index)
            pack_digest = journal_stream_digest(pack_rows)
            lineage_packs.append(
                {
                    "id": pack_ref["id"],
                    "parent": pack_ref.get("parent"),
                    "generation": int(pack_ref["generation"]),
                    "journal_digest": pack_digest,
                }
            )
            max_generation = max(max_generation, int(pack_ref["generation"]))
            raw.extend(pack_rows)
            warnings.extend(pack_warnings)
        pack_generation = max_generation
    elif input_path.is_dir() and (input_path / "manifest.json").is_file():
        manifest, pack_rows, warnings = load_pack_rows(input_path, 0)
        scenario_tag = str(manifest["scenario_tag"])
        pack_generation = int(manifest["pack_generation"])
        pack_digest = journal_stream_digest(pack_rows)
        lineage_packs = [
            {
                "id": "pack",
                "parent": None,
                "generation": pack_generation,
                "journal_digest": pack_digest,
            }
        ]
        raw = pack_rows
    else:
        rows, warnings = parse_jsonl_file(input_path, 0, 0, "default")
        pack_digest = journal_stream_digest(rows)
        lineage_packs = [
            {"id": "file", "parent": None, "generation": 0, "journal_digest": pack_digest}
        ]
        raw = rows
        scenario_tag = str(rows[0]["scenario_tag"]) if rows else "default"

    entries, tombstone_audit = collapse_entries(raw)
    journal_digest = journal_stream_digest(entries)
    surviving_op_ids = [e["op_id"] for e in entries]
    lineage = lineage_digest_hex(lineage_packs, surviving_op_ids)
    root_digest = die_root_digest(die_root)

    return {
        "scenario_tag": scenario_tag,
        "pack_generation": pack_generation,
        "journal_digest": journal_digest,
        "lineage_digest_hex": lineage,
        "die_root_digest_hex": root_digest,
        "die_root": str(die_root),
        "entries": entries,
        "tombstone_audit": tombstone_audit,
        "warnings": warnings,
        "lineage_packs": lineage_packs,
    }


def ledger_digest_hex(
    dies: dict[str, dict[str, Any]],
    journal_digest: str,
    root_digest: str,
    lineage_digest: str,
    snapshot_id: str = "",
) -> str:
    rows = []
    for die_id in sorted(dies.keys()):
        rec = dies[die_id]
        rows.append(
            f"{die_id}|{rec['checksum']}|{rec['tonnage']}|{rec['forge_epoch']}|"
            f"{journal_digest}|{root_digest}|{lineage_digest}|{snapshot_id}"
        )
    return sha256_hex("\n".join(rows).encode("utf-8"))


def reference_replay(
    input_path: Path,
    *,
    die_root: Path = DEFAULT_DIE_ROOT,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    recover: bool = False,
) -> dict[str, Any]:
    meta = load_replay_input(input_path, die_root)
    entries = meta["entries"]
    tombstone_audit = meta["tombstone_audit"]
    journal_digest = meta["journal_digest"]
    lineage_digest = meta["lineage_digest_hex"]
    root_digest = meta["die_root_digest_hex"]

    dies: dict[str, dict[str, Any]] = {}
    forge_epoch = 0
    journal_revision = 0
    snapshot_id: str | None = None
    rollback = False
    rollback_reason: str | None = None
    dies_sealed = 0
    dies_tombstoned = len(tombstone_audit)
    log_rows: list[dict[str, Any]] = []
    op_seq = 1
    current_epoch = 0

    baseline_dies: dict[str, dict[str, Any]] = {}
    if recover and snapshot_path.is_file():
        baseline = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot_id = baseline.get("snapshot_id")
        if baseline.get("schema_version") == 2:
            parent_lineage = baseline.get("parent_lineage_digest_hex", "")
            if parent_lineage != lineage_digest:
                return {
                    "scenario_tag": meta["scenario_tag"],
                    "forge_epoch": 0,
                    "journal_revision": 0,
                    "dies_bound": 0,
                    "dies_sealed": 0,
                    "dies_tombstoned": dies_tombstoned,
                    "tonnage_recorded": 0,
                    "rollback_performed": True,
                    "rollback_reason": "snapshot_lineage_mismatch",
                    "ready": False,
                    "ledger_digest_hex": ledger_digest_hex(
                        {}, journal_digest, root_digest, lineage_digest, snapshot_id or ""
                    ),
                    "bound_dies": [],
                    "log_rows": [],
                    "warnings": meta["warnings"],
                    "meta": meta,
                    "snapshot_id": snapshot_id,
                    "state_generation": 0,
                }
        dies = {
            str(rec["die_id"]): {
                "die_id": str(rec["die_id"]),
                "checksum": int(rec["checksum"]),
                "tonnage": int(rec["tonnage"]),
                "forge_epoch": int(rec["forge_epoch"]),
                "source_format": str(rec.get("source_format", "v1")),
                "revision": rec.get("revision"),
                "digest_hex": str(rec.get("digest_hex", "")),
            }
            for rec in baseline.get("dies", {}).values()
        }
        forge_epoch = int(baseline.get("forge_epoch", 0))
        journal_revision = int(baseline.get("journal_revision", 0))
        baseline_dies = {k: dict(v) for k, v in dies.items()}
        current_epoch = forge_epoch

    def emit(kind: str, entry: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
        nonlocal op_seq
        row: dict[str, Any] = {
            "kind": kind,
            "scenario_tag": entry["scenario_tag"],
            "seq": op_seq,
            "journal_revision": journal_revision,
            "forge_epoch": forge_epoch,
        }
        if extra:
            row.update(extra)
        log_rows.append(row)
        op_seq += 1

    for tomb in tombstone_audit:
        emit("op_tombstoned", tomb, {"op_id": tomb["op_id"]})

    for entry in entries:
        op = str(entry["op"])
        try:
            if op == "forge_start":
                current_epoch = int(entry.get("forge_epoch", 0))
                forge_epoch = current_epoch
                journal_revision += 1
                emit("forge_started", entry, {"forge_epoch": current_epoch})
            elif op == "die_bind":
                block_path = die_root / f"{entry['die_id']}.bin"
                die_id, tonnage, checksum, source_format, revision, digest_hex = read_fdie_block(
                    block_path
                )
                existing = dies.get(die_id)
                if existing and int(existing["checksum"]) == checksum:
                    continue
                dies[die_id] = {
                    "die_id": die_id,
                    "checksum": checksum,
                    "tonnage": tonnage,
                    "forge_epoch": current_epoch,
                    "source_format": source_format,
                    "revision": revision,
                    "digest_hex": digest_hex,
                }
                journal_revision += 1
                emit("die_bound", entry, {"die_id": die_id, "forge_epoch": current_epoch})
            elif op == "die_sealed":
                dies_sealed += 1
                emit("die_sealed", entry, {"forge_epoch": int(entry.get("forge_epoch", current_epoch))})
            elif op == "forge_purged":
                dies = {
                    did: rec for did, rec in dies.items() if int(rec["forge_epoch"]) == current_epoch
                }
                journal_revision += 1
                emit("forge_purged", entry, {"forge_epoch": current_epoch})
            else:
                raise ValueError(f"unknown op: {op}")
        except Exception as exc:
            if not recover:
                raise
            rollback = True
            rollback_reason = "fdie failure"
            meta["warnings"].append(str(exc))
            dies = {k: dict(v) for k, v in baseline_dies.items()}
            snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
            forge_epoch = int(snap.get("forge_epoch", 0))
            journal_revision = int(snap.get("journal_revision", 0))
            log_rows = [{"kind": "recovery_rollback", "scenario_tag": entry["scenario_tag"], "seq": 1}]
            break

    bound_dies = sorted(dies.values(), key=lambda rec: rec["die_id"])
    bound_report = []
    for rec in bound_dies:
        row: dict[str, Any] = {
            "die_id": rec["die_id"],
            "checksum_or_digest": rec["digest_hex"] if rec["digest_hex"] else rec["checksum"],
            "tonnage": rec["tonnage"],
            "forge_epoch": rec["forge_epoch"],
            "source_format": rec["source_format"],
        }
        if rec.get("revision") is not None:
            row["revision"] = rec["revision"]
        bound_report.append(row)

    return {
        "schema_version": 2,
        "scenario_tag": meta["scenario_tag"],
        "forge_epoch": forge_epoch,
        "journal_revision": journal_revision,
        "pack_generation": meta["pack_generation"],
        "dies_bound": len(dies),
        "dies_sealed": dies_sealed,
        "dies_tombstoned": dies_tombstoned,
        "tonnage_recorded": sum(int(rec["tonnage"]) for rec in dies.values()),
        "rollback_performed": rollback,
        "rollback_reason": rollback_reason,
        "ready": (not rollback) and bool(dies),
        "journal_digest_hex": journal_digest,
        "lineage_digest_hex": lineage_digest,
        "die_root_digest_hex": root_digest,
        "snapshot_id": snapshot_id,
        "ledger_digest_hex": ledger_digest_hex(
            dies, journal_digest, root_digest, lineage_digest, snapshot_id or ""
        ),
        "bound_dies": bound_report,
        "log_rows": log_rows,
        "warnings": meta["warnings"],
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# Bundle builders
# ---------------------------------------------------------------------------


def write_pack(
    pack_dir: Path,
    scenario_tag: str,
    pack_generation: int,
    shards: list[tuple[str, str]],
    *,
    journal_revision: int = 1,
) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    manifest_shards = []
    for shard_id, rel_path in shards:
        manifest_shards.append({"id": shard_id, "path": rel_path})
    (pack_dir / "manifest.json").write_text(
        json.dumps(
            {
                "scenario_tag": scenario_tag,
                "pack_generation": pack_generation,
                "journal_revision": journal_revision,
                "shards": manifest_shards,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_bundle(
    bundle_dir: Path,
    scenario_tag: str,
    root_pack: str,
    packs: list[dict[str, Any]],
) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    pack_specs = []
    for spec in packs:
        pack_specs.append(
            {
                "id": spec["id"],
                "path": spec["path"],
                "parent": spec.get("parent"),
                "generation": spec["generation"],
            }
        )
    (bundle_dir / "bundle.json").write_text(
        json.dumps(
            {
                "bundle_schema": 2,
                "scenario_tag": scenario_tag,
                "root_pack": root_pack,
                "packs": pack_specs,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def hidden_root(tmp_path: Path, name: str) -> Path:
    root = tmp_path / f"hidden_{HIDDEN_SEED}" / name
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# Driver helpers
# ---------------------------------------------------------------------------


def build_driver() -> None:
    if not (APP / "Cargo.toml").is_file():
        raise AssertionError("missing /app/Cargo.toml")
    proc = subprocess.run(
        ["/usr/local/cargo/bin/cargo", "build", "--release", "--locked"],
        cwd=str(APP),
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError("driver build failed:\n" + proc.stdout + "\n" + proc.stderr)
    built = APP / "target" / "release" / "forge_stage"
    if not built.is_file():
        raise AssertionError("missing release binary after build")
    VERIFIER_BIN.parent.mkdir(parents=True, exist_ok=True)
    VERIFIER_BIN.write_bytes(built.read_bytes())
    VERIFIER_BIN.chmod(0o755)


def run_checked(cmd: list[str], *, timeout: int = 180, expect_fail: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    if expect_fail:
        if proc.returncode == 0:
            raise AssertionError(
                f"command unexpectedly succeeded: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        return proc
    if proc.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def drive_stage(
    input_path: Path,
    log_path: Path,
    report_path: Path | None = None,
    *,
    recover: bool = False,
    die_root: Path | None = None,
    state_dir: Path | None = None,
    snapshot: Path | None = None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.unlink()
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if report_path.exists():
            report_path.unlink()
    mode = "--stage-recover" if recover else "--stage"
    cmd = [str(VERIFIER_BIN), mode, str(input_path), "--emit-log", str(log_path)]
    if report_path is not None:
        cmd += ["--emit-report", str(report_path)]
    if die_root is not None:
        cmd += ["--die-root", str(die_root)]
    if state_dir is not None:
        cmd += ["--state-dir", str(state_dir)]
    if recover and snapshot is not None:
        cmd += ["--snapshot", str(snapshot)]
    run_checked(cmd)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    body = path.read_text(encoding="utf-8").strip()
    if not body:
        return []
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def die_sealed_before_purge(rows: list[dict[str, Any]]) -> bool:
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_tag[str(row["scenario_tag"])].append(row)
    for events in by_tag.values():
        seals = [int(e["seq"]) for e in events if e.get("kind") == "die_sealed"]
        purges = [int(e["seq"]) for e in events if e.get("kind") == "forge_purged"]
        if seals and purges and min(seals) >= min(purges):
            return False
    return True


def read_state_generation(state_dir: Path) -> int | None:
    state_path = state_dir / "forge_state.json"
    if not state_path.is_file():
        return None
    body = json.loads(state_path.read_text(encoding="utf-8"))
    if body.get("schema_version") == 2:
        return int(body["commit_generation"])
    return None


@pytest.fixture(scope="session", autouse=True)
def build_once() -> None:
    build_driver()


@pytest.fixture(autouse=True)
def clear_output_dir() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in OUT.iterdir():
        if path.is_file():
            path.unlink()


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestStaticContract:
    """Static contract checks for sources, binary rebuild, and report schema."""

    def test_release_binary_rebuilt_from_rust_sources(self) -> None:
        """Release artifact must be a rebuilt ELF binary, not a wrapper script."""
        assert SOURCE_BIN.is_file()
        build_driver()
        assert VERIFIER_BIN.is_file()
        binary = VERIFIER_BIN.read_bytes()
        assert binary.startswith(b"\x7fELF")
        assert not binary.startswith(b"#!")
        assert len(binary) > 64_000

    def test_report_v2_schema_and_digest_fields(self) -> None:
        """Emitted reports must satisfy schema v2 and match dynamically computed digests."""
        journal = FIXTURE_DIR / "run_alpha.jsonl"
        drive_stage(journal, FORGE_LOG, FORGE_REPORT)
        report = json.loads(FORGE_REPORT.read_text(encoding="utf-8"))
        expected = reference_replay(journal)

        required = {
            "schema_version": int,
            "ready": bool,
            "rollback_performed": bool,
            "scenario_tag": str,
            "forge_epoch": int,
            "journal_revision": int,
            "state_generation": int,
            "pack_generation": int,
            "dies_bound": int,
            "dies_sealed": int,
            "dies_tombstoned": int,
            "tonnage_recorded": int,
            "journal_digest_hex": str,
            "lineage_digest_hex": str,
            "die_root_digest_hex": str,
            "ledger_digest_hex": str,
            "bound_dies": list,
        }
        assert report["schema_version"] == 2
        for key, typ in required.items():
            assert key in report, f"missing report field {key}"
            assert isinstance(report[key], typ), f"{key} has wrong type"
        assert len(report["journal_digest_hex"]) == 64
        assert len(report["lineage_digest_hex"]) == 64
        assert len(report["die_root_digest_hex"]) == 64
        assert len(report["ledger_digest_hex"]) == 64
        assert report["journal_digest_hex"] == expected["journal_digest_hex"]
        assert report["lineage_digest_hex"] == expected["lineage_digest_hex"]
        assert report["die_root_digest_hex"] == expected["die_root_digest_hex"]
        assert report["ledger_digest_hex"] == expected["ledger_digest_hex"]
        assert report["dies_bound"] == expected["dies_bound"]
        assert report["tonnage_recorded"] == expected["tonnage_recorded"]
        for rec in report["bound_dies"]:
            assert "die_id" in rec
            assert "checksum_or_digest" in rec
            assert "tonnage" in rec
            assert "forge_epoch" in rec
            assert "source_format" in rec

    def test_instruction_contract_paths_exist(self) -> None:
        """Instruction-referenced contract paths and editable Rust modules must exist."""
        required_paths = [
            APP / "docs" / "forge_stage_contract.md",
            APP / "Cargo.toml",
            APP / "config" / "forge.toml",
            FIXTURE_DIR / "run_alpha.jsonl",
            FIXTURE_DIR / "run_beta.jsonl",
            FIXTURE_DIR / "run_gamma.jsonl",
            FIXTURE_DIR / "bundle_delta",
            FIXTURE_DIR / "bundle_tombstone",
            FIXTURE_DIR / "bundle_recovery",
            FIXTURE_DIR / "states" / "legacy_empty_v1.json",
            FIXTURE_DIR / "states" / "legacy_ambiguous_v1.json",
            FIXTURE_DIR / "snapshots" / "snapshot_v2_stale_parent.json",
            DEFAULT_SNAPSHOT,
            DEFAULT_DIE_ROOT,
        ]
        for path in required_paths:
            assert path.exists(), f"missing contract path {path}"
        for name in (
            "fdie.rs",
            "registry.rs",
            "journal.rs",
            "replay.rs",
            "recovery.rs",
            "report.rs",
            "state.rs",
            "bundle.rs",
            "digest.rs",
            "tonnage.rs",
        ):
            assert (EDITABLE_ROOT / name).is_file(), f"missing editable source {name}"


class TestBundleLineage:
    """Bundle parent-chain ordering, tombstones, collapse, digests, and manifest safety."""

    def test_bundle_replay_uses_parent_chain_before_filename_order(self, tmp_path: Path) -> None:
        """Parent packs must replay entirely before child packs regardless of global seq ordering."""
        root = hidden_root(tmp_path, "ancestry_order")
        die_root = root / "dies"
        write_fdie_v1(die_root / "parent_die.bin", "parent_die", 10000)
        write_fdie_v1(die_root / "child_die.bin", "child_die", 20000)

        bundle_dir = root / "bundle"
        pack_a = bundle_dir / "pack-a"
        pack_b = bundle_dir / "pack-b"
        write_pack(pack_a, "chain", 1, [(20, "zzz.jsonl"), (3, "aaa.jsonl")])
        (pack_a / "zzz.jsonl").write_text(
            '{"seq":100,"journal_revision":1,"op_id":"pa1","op":"forge_start","scenario_tag":"chain","forge_epoch":1}\n'
            '{"seq":200,"journal_revision":1,"op_id":"pa2","op":"die_bind","die_id":"parent_die","scenario_tag":"chain","forge_epoch":1}\n',
            encoding="utf-8",
        )
        (pack_a / "aaa.jsonl").write_text("", encoding="utf-8")
        write_pack(pack_b, "chain", 2, [(1, "early.jsonl")])
        (pack_b / "early.jsonl").write_text(
            '{"seq":5,"journal_revision":1,"op_id":"pb1","op":"die_bind","die_id":"child_die","scenario_tag":"chain","forge_epoch":1}\n',
            encoding="utf-8",
        )
        write_bundle(
            bundle_dir,
            "chain",
            "pack-a",
            [
                {"id": "pack-a", "path": "pack-a", "parent": None, "generation": 1},
                {"id": "pack-b", "path": "pack-b", "parent": "pack-a", "generation": 2},
            ],
        )

        report_path = root / "chain.report.json"
        drive_stage(bundle_dir, root / "chain.log.jsonl", report_path, die_root=die_root)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(bundle_dir, die_root=die_root)
        assert report["dies_bound"] == expected["dies_bound"] == 2
        assert report["tonnage_recorded"] == 30000
        rows = load_jsonl(root / "chain.log.jsonl")
        bind_seqs = [r["seq"] for r in rows if r.get("kind") == "die_bound"]
        assert bind_seqs.index(
            next(r["seq"] for r in rows if r.get("kind") == "die_bound" and r.get("die_id") == "parent_die")
        ) < bind_seqs.index(
            next(r["seq"] for r in rows if r.get("kind") == "die_bound" and r.get("die_id") == "child_die")
        )

    def test_op_tombstone_suppresses_parent_bind_before_side_effects(self) -> None:
        """Surviving tombstones must suppress parent binds without emitting die_bound side effects."""
        bundle = FIXTURE_DIR / "bundle_tombstone"
        log_path = OUT / "tomb.log.jsonl"
        report_path = OUT / "tomb.report.json"
        drive_stage(bundle, log_path, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(bundle)
        assert report["dies_bound"] == expected["dies_bound"] == 0
        assert report["dies_tombstoned"] >= 1
        rows = load_jsonl(log_path)
        assert not any(r.get("kind") == "die_bound" for r in rows)
        assert any(r.get("kind") == "op_tombstoned" for r in rows)

    def test_duplicate_op_id_collapses_across_packs_not_per_shard(self, tmp_path: Path) -> None:
        """Duplicate op_id resolution must consider all packs, not collapse per shard only."""
        root = hidden_root(tmp_path, "opid_collapse")
        die_root = root / "dies"
        write_fdie_v1(die_root / "first_die.bin", "first_die", 11111)
        write_fdie_v1(die_root / "second_die.bin", "second_die", 22222)

        bundle_dir = root / "bundle"
        pack_a = bundle_dir / "pack-a"
        pack_b = bundle_dir / "pack-b"
        write_pack(pack_a, "dup", 1, [(1, "a.jsonl")])
        (pack_a / "a.jsonl").write_text(
            '{"seq":1,"journal_revision":1,"op_id":"start","op":"forge_start","scenario_tag":"dup","forge_epoch":1}\n'
            '{"seq":5,"journal_revision":1,"op_id":"dup-op","op":"die_bind","die_id":"first_die","scenario_tag":"dup","forge_epoch":1}\n',
            encoding="utf-8",
        )
        write_pack(pack_b, "dup", 2, [(1, "b.jsonl")])
        (pack_b / "b.jsonl").write_text(
            '{"seq":10,"journal_revision":2,"op_id":"dup-op","op":"die_bind","die_id":"second_die","scenario_tag":"dup","forge_epoch":1}\n',
            encoding="utf-8",
        )
        write_bundle(
            bundle_dir,
            "dup",
            "pack-a",
            [
                {"id": "pack-a", "path": "pack-a", "parent": None, "generation": 1},
                {"id": "pack-b", "path": "pack-b", "parent": "pack-a", "generation": 2},
            ],
        )

        report_path = root / "dup.report.json"
        drive_stage(bundle_dir, root / "dup.log.jsonl", report_path, die_root=die_root)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(bundle_dir, die_root=die_root)
        assert report["dies_bound"] == expected["dies_bound"] == 1
        assert report["bound_dies"][0]["die_id"] == "second_die"
        assert report["tonnage_recorded"] == 22222

    def test_equivalent_bundle_layouts_share_lineage_digest(self, tmp_path: Path) -> None:
        """Equivalent shard layouts in separate packs must yield identical lineage digests."""
        root = hidden_root(tmp_path, "lineage_digest")
        die_root = root / "dies"
        write_fdie_v1(die_root / "eq_die.bin", "eq_die", 42000)

        journal_text = (
            '{"seq":1,"journal_revision":1,"op_id":"a","op":"forge_start","scenario_tag":"eq","forge_epoch":1}\n'
            '{"seq":2,"journal_revision":1,"op_id":"b","op":"die_bind","die_id":"eq_die","scenario_tag":"eq","forge_epoch":1}\n'
        )

        def build_variant(name: str, shard_path: str, shard_id: int) -> Path:
            bundle_dir = root / name
            pack = bundle_dir / "only-pack"
            write_pack(pack, "eq", 3, [(shard_id, shard_path)])
            (pack / shard_path).write_text(journal_text, encoding="utf-8")
            write_bundle(
                bundle_dir,
                "eq",
                "only-pack",
                [{"id": "only-pack", "path": "only-pack", "parent": None, "generation": 3}],
            )
            return bundle_dir

        bundle_a = build_variant("layout_a", "first.jsonl", 1)
        bundle_b = build_variant("layout_b", "second.jsonl", 9)

        meta_a = load_replay_input(bundle_a, die_root)
        meta_b = load_replay_input(bundle_b, die_root)
        assert meta_a["lineage_digest_hex"] == meta_b["lineage_digest_hex"]

        report_a = root / "a.report.json"
        report_b = root / "b.report.json"
        drive_stage(bundle_a, root / "a.log.jsonl", report_a, die_root=die_root)
        drive_stage(bundle_b, root / "b.log.jsonl", report_b, die_root=die_root)
        body_a = json.loads(report_a.read_text(encoding="utf-8"))
        body_b = json.loads(report_b.read_text(encoding="utf-8"))
        assert body_a["lineage_digest_hex"] == body_b["lineage_digest_hex"]
        assert body_a["ledger_digest_hex"] == body_b["ledger_digest_hex"]

    def test_manifest_rejects_escaping_shard_paths(self, tmp_path: Path) -> None:
        """Manifest shard paths that escape the pack directory must be rejected."""
        root = hidden_root(tmp_path, "escape")
        die_root = root / "dies"
        write_fdie_v1(die_root / "esc.bin", "esc", 1000)
        pack_dir = root / "pack"
        write_pack(pack_dir, "esc", 1, [(1, "../outside.jsonl")])
        outside = root / "outside.jsonl"
        outside.write_text(
            '{"seq":1,"journal_revision":1,"op_id":"x","op":"forge_start","scenario_tag":"esc","forge_epoch":1}\n',
            encoding="utf-8",
        )
        report_path = root / "esc.report.json"
        run_checked(
            [
                str(VERIFIER_BIN),
                "--stage",
                str(pack_dir),
                "--emit-log",
                str(root / "esc.log.jsonl"),
                "--emit-report",
                str(report_path),
                "--die-root",
                str(die_root),
            ],
            expect_fail=True,
        )


class TestFdieV3:
    """FDIE v3 parsing, scaling, mixed-format totals, and corrupt recovery."""

    def test_fdie_v3_chunk_digest_includes_chunk_lengths(self, tmp_path: Path) -> None:
        """Footer digest must incorporate chunk lengths; wrong lengths must fail verification."""
        root = hidden_root(tmp_path, "v3_digest")
        die_root = root / "dies"
        good = die_root / "good_v3.bin"
        write_fdie_v3(good, "good_v3", 5000, delta=100)

        journal = root / "v3.jsonl"
        journal.write_text(
            '{"seq":1,"op":"forge_start","forge_epoch":1,"scenario_tag":"v3d","op_id":"s1","journal_revision":1}\n'
            '{"seq":2,"op":"die_bind","die_id":"good_v3","scenario_tag":"v3d","op_id":"b1","journal_revision":1,"forge_epoch":1}\n',
            encoding="utf-8",
        )
        report_path = root / "good.report.json"
        drive_stage(journal, root / "good.log.jsonl", report_path, die_root=die_root)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(journal, die_root=die_root)
        assert report["dies_bound"] == 1
        assert report["tonnage_recorded"] == expected["tonnage_recorded"] == 5100

        bad = die_root / "bad_len_v3.bin"
        data = bytearray(good.read_bytes())
        chunk_len_offset = data.index(b"{") - 4
        data[chunk_len_offset : chunk_len_offset + 4] = struct.pack("<I", 9999)
        bad.write_bytes(data)
        journal_bad = root / "bad.jsonl"
        journal_bad.write_text(
            '{"seq":1,"op":"forge_start","forge_epoch":1,"scenario_tag":"v3bad","op_id":"s1","journal_revision":1}\n'
            '{"seq":2,"op":"die_bind","die_id":"bad_len_v3","scenario_tag":"v3bad","op_id":"b1","journal_revision":1,"forge_epoch":1}\n',
            encoding="utf-8",
        )
        run_checked(
            [
                str(VERIFIER_BIN),
                "--stage",
                str(journal_bad),
                "--emit-log",
                str(root / "bad.log.jsonl"),
                "--emit-report",
                str(root / "bad.report.json"),
                "--die-root",
                str(die_root),
            ],
            expect_fail=True,
        )

    def test_fdie_v3_scaled_delta_tonnage_truncates_toward_zero(self, tmp_path: Path) -> None:
        """Bundled v3 scaled die applies scale_milli with truncation toward zero."""
        die_path = DEFAULT_DIE_ROOT / "die_v3_scaled.bin"
        assert die_path.is_file()
        die_id, tonnage, _, source_format, _, _ = read_fdie_block(die_path)
        assert source_format == "v3"
        assert die_id == "die_v3_scaled"
        assert tonnage == 1500

        root = hidden_root(tmp_path, "scaled_probe")
        journal = root / "scaled.jsonl"
        journal.write_text(
            '{"seq":1,"op":"forge_start","forge_epoch":1,"scenario_tag":"scaled","op_id":"s1","journal_revision":1}\n'
            '{"seq":2,"op":"die_bind","die_id":"die_v3_scaled","scenario_tag":"scaled","op_id":"b1","journal_revision":1,"forge_epoch":1}\n',
            encoding="utf-8",
        )
        report_path = root / "scaled.report.json"
        drive_stage(journal, root / "scaled.log.jsonl", report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["tonnage_recorded"] == 1500
        assert report["bound_dies"][0]["source_format"] == "v3"

    def test_fdie_v1_v2_v3_mix_uses_u64_total(self, tmp_path: Path) -> None:
        """Mixed FDIE versions must sum tonnage in u64 without truncation."""
        root = hidden_root(tmp_path, "mix_u64")
        die_root = root / "dies"
        v1_t = 3_000_000_000
        v2_t = 2_500_000_000
        write_fdie_v1(die_root / "mix_v1.bin", "mix_v1", v1_t)
        write_fdie_v2(die_root / "mix_v2.bin", "mix_v2", v2_t)
        write_fdie_v3(die_root / "mix_v3.bin", "mix_v3", 1000, scale_milli=2000, measured=500_000_000)

        journal = root / "mix.jsonl"
        journal.write_text(
            '{"seq":1,"op":"forge_start","forge_epoch":1,"scenario_tag":"mix","op_id":"s1","journal_revision":1}\n'
            '{"seq":2,"op":"die_bind","die_id":"mix_v1","scenario_tag":"mix","op_id":"b1","journal_revision":1,"forge_epoch":1}\n'
            '{"seq":3,"op":"die_bind","die_id":"mix_v2","scenario_tag":"mix","op_id":"b2","journal_revision":1,"forge_epoch":1}\n'
            '{"seq":4,"op":"die_bind","die_id":"mix_v3","scenario_tag":"mix","op_id":"b3","journal_revision":1,"forge_epoch":1}\n',
            encoding="utf-8",
        )
        report_path = root / "mix.report.json"
        drive_stage(journal, root / "mix.log.jsonl", report_path, die_root=die_root)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(journal, die_root=die_root)
        assert report["dies_bound"] == 3
        assert report["tonnage_recorded"] == expected["tonnage_recorded"]
        assert report["tonnage_recorded"] == v1_t + v2_t + 1_000_000_000

    def test_corrupt_v3_recovery_has_no_partial_bind_log(self) -> None:
        """Corrupt v3 bind during recovery must roll back without partial die_bound log rows."""
        bundle = FIXTURE_DIR / "bundle_recovery"
        log_path = OUT / "recv3.log.jsonl"
        report_path = OUT / "recv3.report.json"
        drive_stage(bundle, log_path, report_path, recover=True, snapshot=DEFAULT_SNAPSHOT)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(bundle, recover=True, snapshot_path=DEFAULT_SNAPSHOT)
        assert report["rollback_performed"] is True
        assert report["ready"] is False
        assert report["dies_bound"] == expected["dies_bound"]
        rows = load_jsonl(log_path)
        bound = [r for r in rows if r.get("kind") == "die_bound"]
        assert not bound
        assert any(r.get("kind") == "recovery_rollback" for r in rows)


class TestStateAndRecovery:
    """Persisted state migration, quarantine, recovery snapshots, and generation bumps."""

    def test_legacy_empty_v1_state_migrates_to_v2_generation_one(self, tmp_path: Path) -> None:
        """Empty legacy v1 state with matching metadata migrates to v2 commit_generation 1."""
        root = hidden_root(tmp_path, "empty_v1")
        die_root = DEFAULT_DIE_ROOT
        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        journal = FIXTURE_DIR / "run_alpha.jsonl"
        meta = load_replay_input(journal, die_root)
        legacy = json.loads((FIXTURE_DIR / "states" / "legacy_empty_v1.json").read_text(encoding="utf-8"))
        legacy["die_root"] = str(die_root)
        legacy["journal_digest"] = meta["journal_digest"]
        legacy["scenario_tag"] = meta["scenario_tag"]
        legacy["pack_generation"] = meta["pack_generation"]
        (state_dir / "forge_state.json").write_text(json.dumps(legacy), encoding="utf-8")

        report_path = root / "alpha.report.json"
        drive_stage(
            journal,
            root / "alpha.log.jsonl",
            report_path,
            die_root=die_root,
            state_dir=state_dir,
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["state_generation"] == 1
        state = json.loads((state_dir / "forge_state.json").read_text(encoding="utf-8"))
        assert state["schema_version"] == 2
        assert state["commit_generation"] == 1
        assert state["lineage_digest_hex"] == meta["lineage_digest_hex"]

    def test_legacy_ambiguous_v1_state_is_quarantined_and_rebuilt(self, tmp_path: Path) -> None:
        """Non-empty ambiguous v1 state must be quarantined and replay rebuilt from journal."""
        root = hidden_root(tmp_path, "ambiguous_v1")
        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            FIXTURE_DIR / "states" / "legacy_ambiguous_v1.json",
            state_dir / "forge_state.json",
        )
        journal = FIXTURE_DIR / "run_alpha.jsonl"
        report_path = root / "alpha.report.json"
        drive_stage(
            journal,
            root / "alpha.log.jsonl",
            report_path,
            state_dir=state_dir,
        )
        assert list(state_dir.glob("forge_state.quarantined.*"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(journal)
        assert report["dies_bound"] == expected["dies_bound"]
        assert report["tonnage_recorded"] == expected["tonnage_recorded"]

    def test_stale_tmp_state_is_quarantined_before_replay(self, tmp_path: Path) -> None:
        """Stale forge_state.json.tmp must be quarantined before replay proceeds."""
        root = hidden_root(tmp_path, "stale_tmp")
        die_root = root / "dies"
        state_dir = root / "state"
        write_fdie_v1(die_root / "tmp_die.bin", "tmp_die", 15000)
        journal = root / "tmp.jsonl"
        journal.write_text(
            '{"seq":1,"op":"forge_start","scenario_tag":"tmp","forge_epoch":1,"op_id":"s1","journal_revision":1}\n'
            '{"seq":2,"op":"die_bind","die_id":"tmp_die","scenario_tag":"tmp","op_id":"b1","journal_revision":1,"forge_epoch":1}\n',
            encoding="utf-8",
        )
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "forge_state.json.tmp").write_text('{"partial": true}', encoding="utf-8")
        report_path = root / "tmp.report.json"
        drive_stage(
            journal,
            root / "tmp.log.jsonl",
            report_path,
            die_root=die_root,
            state_dir=state_dir,
        )
        assert list(state_dir.glob("forge_state.quarantined.*.tmp"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(journal, die_root=die_root)
        assert report["dies_bound"] == expected["dies_bound"] == 1

    def test_recovery_snapshot_lineage_mismatch_reports_safe_rollback(self, tmp_path: Path) -> None:
        """Snapshots whose parent lineage digest mismatches input must safe-rollback empty."""
        root = hidden_root(tmp_path, "lineage_mismatch")
        bundle = FIXTURE_DIR / "bundle_recovery"
        snapshot = FIXTURE_DIR / "snapshots" / "snapshot_v2_stale_parent.json"
        log_path = root / "mm.log.jsonl"
        report_path = root / "mm.report.json"
        drive_stage(
            bundle,
            log_path,
            report_path,
            recover=True,
            snapshot=snapshot,
            state_dir=root / "state",
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(bundle, recover=True, snapshot_path=snapshot)
        assert report["rollback_performed"] is True
        assert report["rollback_reason"] == "snapshot_lineage_mismatch"
        assert report["ready"] is False
        assert report["dies_bound"] == expected["dies_bound"] == 0
        assert not any(r.get("kind") == "die_bound" for r in load_jsonl(log_path))

    def test_recovery_good_snapshot_preserves_snapshot_counts_and_digest(self, tmp_path: Path) -> None:
        """Recovery with matching lineage snapshot preserves baseline counts and ledger digest."""
        root = hidden_root(tmp_path, "good_snapshot")
        bundle = FIXTURE_DIR / "bundle_recovery"
        meta = load_replay_input(bundle, DEFAULT_DIE_ROOT)
        baseline = json.loads(DEFAULT_SNAPSHOT.read_text(encoding="utf-8"))
        snapshot = root / "snapshot_v2_ok.json"
        snapshot.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "snapshot_id": "snap-ok",
                    "parent_lineage_digest_hex": meta["lineage_digest_hex"],
                    "dies": baseline["dies"],
                    "forge_epoch": baseline["forge_epoch"],
                    "journal_revision": baseline["journal_revision"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        log_path = root / "ok.log.jsonl"
        report_path = root / "ok.report.json"
        drive_stage(
            bundle,
            log_path,
            report_path,
            recover=True,
            snapshot=snapshot,
            state_dir=root / "state",
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(bundle, recover=True, snapshot_path=snapshot)
        assert report["rollback_performed"] is True
        assert report["dies_bound"] == expected["dies_bound"] == len(baseline["dies"])
        assert report["snapshot_id"] == "snap-ok"
        assert report["ledger_digest_hex"] == expected["ledger_digest_hex"]
        assert not any(r.get("kind") == "die_bound" for r in load_jsonl(log_path))

    def test_replay_twice_increments_state_generation_without_stale_cache(self, tmp_path: Path) -> None:
        """Two sequential replays in one state dir must bump state_generation without stale reuse."""
        root = hidden_root(tmp_path, "twice")
        state_dir = root / "state"
        journal = FIXTURE_DIR / "run_beta.jsonl"
        report1 = root / "first.report.json"
        report2 = root / "second.report.json"
        drive_stage(
            journal,
            root / "first.log.jsonl",
            report1,
            state_dir=state_dir,
        )
        first = json.loads(report1.read_text(encoding="utf-8"))
        drive_stage(
            journal,
            root / "second.log.jsonl",
            report2,
            state_dir=state_dir,
        )
        second = json.loads(report2.read_text(encoding="utf-8"))
        assert first["state_generation"] == 1
        assert second["state_generation"] == 2
        assert second["dies_bound"] == first["dies_bound"]
        assert read_state_generation(state_dir) == 2


class TestCacheProbe:
    """Registry cache probe semantics for lineage and die-root isolation."""

    def test_probe_cache_key_includes_lineage_and_state_generation(self) -> None:
        """Probe output must reflect cache keys keyed by state_generation and lineage fields."""
        proc = run_checked([str(VERIFIER_BIN), "--probe-forge-cache"])
        payload = json.loads(proc.stdout)
        for key in ("first", "second", "migrated", "isolated", "truth"):
            assert key in payload
        first = payload["first"]
        second = payload["second"]
        migrated = payload["migrated"]
        truth = payload["truth"]
        assert first["die_count"] != second["die_count"]
        assert second["die_count"] == truth["die_count"]
        assert migrated["state_generation"] > first["state_generation"]
        for snap in (first, second, migrated, payload["isolated"]):
            assert "state_generation" in snap
            assert "lineage_digest_hex" in snap
            assert "die_root_digest" in snap
            assert "journal_digest" in snap

    def test_probe_cache_isolates_same_lineage_different_die_root(self) -> None:
        """Different die roots must produce distinct cache snapshots even with shared lineage."""
        proc = run_checked([str(VERIFIER_BIN), "--probe-forge-cache"])
        payload = json.loads(proc.stdout)
        second = payload["second"]
        isolated = payload["isolated"]
        assert isolated["die_root_digest"] != second["die_root_digest"]
        assert isolated["die_count"] != second["die_count"]


class TestLegacySmoke:
    """Legacy single-file fixture smoke tests and stage alias compatibility."""

    def test_run_alpha_die_sealed_before_purge(self) -> None:
        """Alpha run must seal dies before purge in emitted log order."""
        drive_stage(FIXTURE_DIR / "run_alpha.jsonl", FORGE_LOG, FORGE_REPORT)
        rows = load_jsonl(FORGE_LOG)
        assert die_sealed_before_purge(rows)
        assert any(r.get("kind") == "die_sealed" for r in rows)
        assert any(r.get("kind") == "die_bound" for r in rows)

    def test_run_alpha_binds_expected_dies(self) -> None:
        """Alpha run binds the dynamically expected die set."""
        journal = FIXTURE_DIR / "run_alpha.jsonl"
        drive_stage(journal, FORGE_LOG, FORGE_REPORT)
        rows = load_jsonl(FORGE_LOG)
        bound = [r["die_id"] for r in rows if r.get("kind") == "die_bound"]
        expected = reference_replay(journal)
        assert set(bound) == {rec["die_id"] for rec in expected["bound_dies"]}

    def test_run_alpha_tonnage_recorded(self) -> None:
        """Alpha tonnage sum must match reference replay."""
        journal = FIXTURE_DIR / "run_alpha.jsonl"
        drive_stage(journal, FORGE_LOG, FORGE_REPORT)
        report = json.loads(FORGE_REPORT.read_text(encoding="utf-8"))
        expected = reference_replay(journal)
        assert report["tonnage_recorded"] == expected["tonnage_recorded"]

    def test_run_beta_duplicate_bind_is_idempotent(self) -> None:
        """Beta duplicate bind of the same die must emit only one die_bound row."""
        journal = FIXTURE_DIR / "run_beta.jsonl"
        drive_stage(journal, FORGE_LOG, FORGE_REPORT)
        rows = load_jsonl(FORGE_LOG)
        bound = [r for r in rows if r.get("kind") == "die_bound"]
        assert sum(1 for row in bound if row.get("die_id") == "die_beta_x") == 1
        report = json.loads(FORGE_REPORT.read_text(encoding="utf-8"))
        assert report["dies_bound"] == 2

    def test_run_gamma_recovery_rolls_back_snapshot(self) -> None:
        """Gamma recovery must roll back corrupt bind attempts to the baseline snapshot."""
        journal = FIXTURE_DIR / "run_gamma.jsonl"
        drive_stage(journal, FORGE_LOG, FORGE_REPORT, recover=True)
        report = json.loads(FORGE_REPORT.read_text(encoding="utf-8"))
        expected = reference_replay(journal, recover=True)
        assert report["rollback_performed"] is True
        assert report["ready"] is False
        assert report["dies_bound"] == expected["dies_bound"]
        bound = [r for r in load_jsonl(FORGE_LOG) if r.get("kind") == "die_bound"]
        assert not any(r.get("die_id") == "die_gamma_bad" for r in bound)

    def test_stage_alias_fixtures_still_work(self) -> None:
        """Stage alias fixtures must remain compatible with normalized journal ops."""
        for name in ("stage_alpha.jsonl", "stage_beta.jsonl"):
            journal = FIXTURE_DIR / name
            log_path = OUT / f"{name}.log.jsonl"
            report_path = OUT / f"{name}.report.json"
            drive_stage(journal, log_path, report_path)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            expected = reference_replay(journal)
            assert report["dies_bound"] == expected["dies_bound"]
            assert report["tonnage_recorded"] == expected["tonnage_recorded"]

        journal = FIXTURE_DIR / "stage_gamma.jsonl"
        log_path = OUT / "stage_gamma.jsonl.log.jsonl"
        report_path = OUT / "stage_gamma.jsonl.report.json"
        drive_stage(journal, log_path, report_path, recover=True)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = reference_replay(journal, recover=True)
        assert report["rollback_performed"] is True
        assert report["dies_bound"] == expected["dies_bound"]
