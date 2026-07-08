"""Shared rebuild and reference helpers for GeoSynth verifier tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
MODALITY_WEIGHTS = APP / "data" / "policies" / "modality-weights.json"
FORMATION_POLICY = APP / "data" / "policies" / "formation-governance.json"
CATALOG_SOURCE = Path("/app/state/survey-ingest-catalog.json").stem

REF_LANE_TABLE = (
    ("surveys/seismic", "traces.jsonl"),
    ("surveys/gravity", "anomalies.jsonl"),
    ("surveys/magnetic", "field.jsonl"),
    ("surveys/borehole", "logs.jsonl"),
    ("surveys/geochem", "samples.jsonl"),
    ("surveys/hyperspectral", "tiles.jsonl"),
)

EVIDENCE_CHANNEL = {
    "seismic": "wave-anomaly",
    "gravity": "density-deficit",
    "magnetic": "susceptibility-peak",
    "borehole": "lithology-break",
    "geochem": "pathfinder-spike",
    "hyperspectral": "alteration-halo",
}


def reference_load_traces() -> list[dict]:
    rows: list[dict] = []
    for lane, fname in REF_LANE_TABLE:
        path = APP / "data" / lane / fname
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    rows.sort(key=lambda r: r["sample_id"])
    return rows


def reference_feed_fingerprint(traces: list[dict]) -> str:
    lines = [
        f"geo|{t['sample_id']}|{CATALOG_SOURCE}|{t['block_id']}|{t['seq']}|{t['recorded_at']}|{t['formation_node']}"
        for t in traces
    ]
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def reference_seq_book(traces: list[dict]) -> str:
    by_block: dict[str, list[dict]] = {}
    for t in traces:
        by_block.setdefault(t["block_id"], []).append(t)
    lines = []
    for token in sorted(by_block):
        rows = by_block[token]
        lines.append(f"seqbook|{token}|{max(r['seq'] for r in rows)}|{len(rows)}")
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def reference_depth_epochs(traces: list[dict]) -> list[dict]:
    ordered = sorted(traces, key=lambda t: (t["recorded_at"], t["sample_id"]))
    out: list[dict] = []
    bucket: list[dict] = []
    block = ""
    n = 0
    for row in ordered:
        if not bucket:
            block = row["block_id"]
            bucket = [row]
            continue
        if row["block_id"] != block:
            n += 1
            out.append(
                {
                    "epoch_id": f"dep-{n:03}",
                    "block_id": block,
                    "sample_ids": [r["sample_id"] for r in bucket],
                }
            )
            block = row["block_id"]
            bucket = [row]
        else:
            bucket.append(row)
    if bucket:
        n += 1
        out.append(
            {
                "epoch_id": f"dep-{n:03}",
                "block_id": block,
                "sample_ids": [r["sample_id"] for r in bucket],
            }
        )
    return out


def reference_epoch_fingerprint(epochs: list[dict]) -> str:
    lines = [f"epoch|{e['epoch_id']}|{e['block_id']}|{len(e['sample_ids'])}" for e in epochs]
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def reference_voxel_edges(traces: list[dict]) -> list[dict]:
    weights = json.loads(MODALITY_WEIGHTS.read_text())
    bore, seismic, gravity, magnetic = (
        weights["borehole"],
        weights["seismic"],
        weights["gravity"],
        weights["magnetic"],
    )
    by_id = {t["sample_id"]: t for t in traces}
    grouped: dict[str, list[tuple[int, str]]] = {}
    for t in traces:
        grouped.setdefault(t["block_id"], []).append((t["seq"], t["sample_id"]))
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for block, rows in grouped.items():
        rows.sort()
        ids = [sid for _, sid in rows]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pair = (ids[i], ids[j])
                if pair in seen:
                    continue
                seen.add(pair)
                src_i = by_id[ids[i]]["source"]
                src_j = by_id[ids[j]]["source"]
                if src_i == "borehole" or src_j == "borehole":
                    w = bore
                elif src_i == "seismic" or src_j == "seismic":
                    w = seismic
                elif src_i == "gravity" or src_j == "gravity":
                    w = gravity
                else:
                    w = magnetic
                edges.append(
                    {
                        "from": ids[i],
                        "to": ids[j],
                        "block_id": block,
                        "weight": w,
                        "forward_span": j - i,
                    }
                )
    edges.sort(key=lambda e: (e["from"], e["to"]))
    return edges


def reference_voxel_fingerprint(edges: list[dict]) -> str:
    lines = [f"voxel|{e['from']}|{e['to']}|{e['block_id']}|{e['weight']}" for e in edges]
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def reference_compose_plan(traces: list[dict], epochs: list[dict]) -> dict:
    policy = json.loads(FORMATION_POLICY.read_text())
    by_id = {t["sample_id"]: t for t in traces}
    by_block = {e["block_id"]: e["sample_ids"] for e in epochs}
    branches = []
    for block in policy["hypothesis_priority"]:
        if block not in by_block:
            continue
        steps = []
        for n, sid in enumerate(by_block[block], start=1):
            steps.append(
                {
                    "step": n,
                    "sample_id": sid,
                    "evidence_kind": EVIDENCE_CHANNEL[by_id[sid]["source"]],
                }
            )
        branches.append({"block_id": block, "steps": steps})
    ed = reference_epoch_fingerprint(epochs)
    lines = [f"compose|epoch|{ed}"]
    for br in branches:
        for st in br["steps"]:
            lines.append(f"compose|{br['block_id']}|{st['step']}|{st['sample_id']}|{st['evidence_kind']}")
    lines.sort()
    return {
        "compose": branches,
        "formation_compose_digest": hashlib.sha256("\n".join(lines).encode()).hexdigest(),
    }


def reference_confidence_margins(traces: list[dict], epochs: list[dict], floor: float) -> list[dict]:
    by_id = {t["sample_id"]: t for t in traces}
    margins: list[dict] = []
    for epoch in epochs:
        prospects = [by_id[sid]["prospect_index"] for sid in epoch["sample_ids"]]
        mean = sum(prospects) / len(prospects)
        margin = max(1.0 - mean, floor)
        margins.append({"block_id": epoch["block_id"], "confidence_margin": margin})
    return margins


def reference_margin_table_digest(margins: list[dict]) -> str:
    lines = [f"conf|{m['block_id']}|{m['confidence_margin']:.4f}" for m in margins]
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def reference_chain_fingerprint(branches: list[dict]) -> str:
    lines = [f"chain|{b['block_id']}|{s['step']}|{s['sample_id']}" for b in branches for s in b["steps"]]
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


PIPELINE = (
    "load-surveys",
    "depth-epoch",
    "fuse-voxels",
    "guard-hypotheses",
    "score-confidence",
    "branch-formations",
    "export-discovery",
    "discovery-seal",
)


@pytest.fixture(scope="session", autouse=True)
def _seed_verifier_fixtures() -> None:
    src = Path("/tests/verifier-fixtures")
    if src.is_dir():
        dest = Path("/opt/verifier-fixtures")
        dest.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)


@pytest.fixture(scope="session", autouse=True)
def _rebuild_geosynth_engine() -> None:
    proc = subprocess.run(
        ["bash", "/app/scripts/rebuild-geosynth-engine.sh"],
        cwd=str(APP),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
