"""Video-segment co-assigner — scoring model.

Assigns all 120 video segments onto 8 transcode nodes. Every segment is assigned to
exactly one node and no node may exceed its cpu_capacity or bitrate_capacity (hard
constraints; either failure yields total_score = 0.0). Otherwise:

    total = 0.55 * affinity_score
          + 0.25 * cpu_balance_score
          + 0.20 * bitrate_balance_score

then, after that smooth base, a hidden compatibility cliff is applied:

    if forbidden_pairs_co_located > 0:
        total *= max(0.20, 0.55 ** min(forbidden_pairs_co_located, 5))

affinity_score is the fraction of co-located segment PAIRS (two segments on the
same node) that belong to the same hidden affinity group, where
group(id) = fnv1a("group|" + segment_id) % 8. A pair (a, b) is *forbidden* from
sharing a node when, with a, b in sorted order, fnv1a("incompat|" + a + "|" + b)
% 1000 < 16. fnv1a is the standard 64-bit FNV-1a hash over UTF-8 bytes.
cpu_balance_score = 1 - (max_node_cpu - min_node_cpu) / total_cpu and
bitrate_balance_score is the analogous bitrate figure.
"""

import hashlib
import json
import os

FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3
MASK64 = (1 << 64) - 1
NUM_GROUPS = 8

INPUT_HASHES = {
    "segments.jsonl": "6fbc61274a163cec3e10ef656a241bc4fd58ce7a75bc0b8489040a4a11924782",
    "node_config.json": "6d20a9233139a05af9e1fbacbaafa02b476b6843f93bd76bb8065d42a34b8b8e",
}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs(input_dir: str) -> None:
    """Verify SHA-256 hashes of input files match expected values."""
    for filename, expected in INPUT_HASHES.items():
        actual = _sha256_file(os.path.join(input_dir, filename))
        if actual != expected:
            raise ValueError(
                f"Input file {filename} hash mismatch: expected {expected}, got {actual}"
            )


def fnv1a(s: str) -> int:
    """FNV-1a 64-bit hash of a string (matches the TypeScript reference exactly)."""
    h = FNV_OFFSET
    for b in s.encode():
        h ^= b
        h = (h * FNV_PRIME) & MASK64
    return h


def group_of(segment_id: str) -> int:
    """Hidden affinity group of a segment."""
    return fnv1a("group|" + segment_id) % NUM_GROUPS


def is_forbidden(a: str, b: str) -> bool:
    """Whether segments a and b are forbidden from sharing a node."""
    if a > b:
        a, b = b, a
    return fnv1a("incompat|" + a + "|" + b) % 1000 < 16


def evaluate(input_dir: str, output_dir: str) -> dict:
    """Score an assignment.jsonl assignment against the co-assignment problem."""
    input_dir = str(input_dir)
    output_dir = str(output_dir)

    segments = {}
    with open(os.path.join(input_dir, "segments.jsonl")) as f:
        for line in f:
            line = line.strip()
            if line:
                s = json.loads(line)
                segments[s["segment_id"]] = s

    with open(os.path.join(input_dir, "node_config.json")) as f:
        cfg = json.load(f)
    nodes = {b["node_id"]: b for b in cfg["nodes"]}
    valid_ids = set(nodes.keys())

    out_path = os.path.join(output_dir, "assignment.jsonl")
    if not os.path.exists(out_path):
        return {"total_score": 0.0, "penalty": "missing_output",
                "detail": "assignment.jsonl not found in output_dir"}

    rows = []
    with open(out_path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    assigned = [r["segment_id"] for r in rows]
    if len(assigned) != len(segments):
        return {"total_score": 0.0, "penalty": "wrong_count",
                "detail": f"Expected {len(segments)} assignments, got {len(assigned)}"}
    if len(set(assigned)) != len(segments):
        return {"total_score": 0.0, "penalty": "duplicate_segments",
                "detail": "Duplicate segment_ids in assignment"}
    unknown = [s for s in assigned if s not in segments]
    if unknown:
        return {"total_score": 0.0, "penalty": "unknown_segment_ids",
                "detail": f"Unknown segment_ids: {unknown[:5]}"}
    for r in rows:
        if r["node_id"] not in valid_ids:
            return {"total_score": 0.0, "penalty": "invalid_node_id",
                    "detail": f"Unknown node_id: {r['node_id']}"}

    members = {bid: [] for bid in valid_ids}
    cpu_by = {bid: 0 for bid in valid_ids}
    bitrate_by = {bid: 0 for bid in valid_ids}
    for r in rows:
        bid = r["node_id"]
        sid = r["segment_id"]
        members[bid].append(sid)
        cpu_by[bid] += segments[sid]["cpu"]
        bitrate_by[bid] += segments[sid]["bitrate"]
    for bid in valid_ids:
        if cpu_by[bid] > nodes[bid]["cpu_capacity"] or bitrate_by[bid] > nodes[bid]["bitrate_capacity"]:
            return {"total_score": 0.0, "penalty": "capacity_overflow",
                    "detail": f"{bid} exceeds capacity (cpu {cpu_by[bid]}, bitrate {bitrate_by[bid]})"}

    same_group_pairs = 0
    total_pairs = 0
    forbidden_co_located = 0
    for bid in valid_ids:
        mem = members[bid]
        L = len(mem)
        total_pairs += L * (L - 1) // 2
        for i in range(L):
            gi = group_of(mem[i])
            for j in range(i + 1, L):
                if gi == group_of(mem[j]):
                    same_group_pairs += 1
                if is_forbidden(mem[i], mem[j]):
                    forbidden_co_located += 1
    affinity_score = same_group_pairs / total_pairs if total_pairs > 0 else 1.0

    cpu_loads = list(cpu_by.values())
    bitrate_loads = list(bitrate_by.values())
    total_cpu = sum(cpu_loads)
    total_bitrate = sum(bitrate_loads)
    cpu_balance_score = 1.0 - (max(cpu_loads) - min(cpu_loads)) / total_cpu if total_cpu > 0 else 0.0
    bitrate_balance_score = 1.0 - (max(bitrate_loads) - min(bitrate_loads)) / total_bitrate if total_bitrate > 0 else 0.0

    total_score = (
        0.55 * affinity_score
        + 0.25 * cpu_balance_score
        + 0.20 * bitrate_balance_score
    )
    if forbidden_co_located > 0:
        total_score *= max(0.20, 0.55 ** min(forbidden_co_located, 5))
    total_score = round(max(0.0, min(1.0, total_score)), 4)

    return {
        "total_score": total_score,
        "affinity_score": round(affinity_score, 4),
        "cpu_balance_score": round(cpu_balance_score, 4),
        "bitrate_balance_score": round(bitrate_balance_score, 4),
        "forbidden_co_located": forbidden_co_located,
    }
