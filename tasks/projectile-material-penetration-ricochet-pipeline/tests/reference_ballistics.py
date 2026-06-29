"""Independent ballistics reference for verifier cross-checks."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

PEN_K = 75_000.0
EPS = 1e-9
SEEDS_PATH = Path("/app/fixtures/seeds.json")
MATERIALS_PATH = Path("/app/fixtures/materials/catalog.json")
STACKS_DIR = Path("/app/fixtures/stacks")
SNAPSHOT_PATH = Path("/app/state/shot-snapshot.json")


class ReplayHistory:
    """Mirrors /app/state/replay-history.json assignment order."""

    def __init__(self) -> None:
        self.counts: dict[tuple[str, int], int] = {}

    def stamp(self, stack: str, seed: int) -> int:
        key = (stack, seed)
        seq = self.counts.get(key, 0)
        self.counts[key] = seq + 1
        return seq


def _round3(v: float) -> float:
    return round(v, 3)


def _round6(v: float) -> float:
    return round(v, 6)


def _vec3(raw: list[float]) -> dict[str, float]:
    return {"x": raw[0], "y": raw[1], "z": raw[2]}


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    return a["x"] * b["x"] + a["y"] * b["y"] + a["z"] * b["z"]


def _mag(v: dict[str, float]) -> float:
    return math.sqrt(_dot(v, v))


def _scale(v: dict[str, float], s: float) -> dict[str, float]:
    return {"x": v["x"] * s, "y": v["y"] * s, "z": v["z"] * s}


def _sub(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {"x": a["x"] - b["x"], "y": a["y"] - b["y"], "z": a["z"] - b["z"]}


def _angle_deg(a: dict[str, float], b: dict[str, float]) -> float:
    denom = _mag(a) * _mag(b)
    if denom <= 1e-12:
        return 0.0
    cos_v = max(-1.0, min(1.0, _dot(a, b) / denom))
    return _round3(math.degrees(math.acos(cos_v)))


def load_materials(path: Path = MATERIALS_PATH) -> dict[int, dict[str, Any]]:
    body = json.loads(path.read_text(encoding="utf-8"))
    return {m["physics_id"]: m for m in body["materials"]}


def load_seeds(path: Path = SEEDS_PATH) -> dict[int, float]:
    body = json.loads(path.read_text(encoding="utf-8"))
    return {entry["seed"]: entry["velocity_scale"] for entry in body["seeds"]}


def apply_seed_scale(seed: int, velocity: list[float], seeds: dict[int, float] | None = None) -> list[float]:
    scales = seeds if seeds is not None else load_seeds()
    scale = scales.get(seed, 1.0)
    v = _vec3(velocity)
    mag = _mag(v)
    if mag <= 0:
        return velocity
    scaled = _scale(v, scale)
    return [scaled["x"], scaled["y"], scaled["z"]]


def compute_ricochet(incident: list[float], normal: list[float]) -> dict[str, Any]:
    v = _vec3(incident)
    n = _vec3(normal)
    v_out = _sub(v, _scale(n, 2.0 * _dot(v, n)))
    return {
        "incident_angle_deg": _angle_deg(v, _scale(n, -1.0)),
        "exit_angle_deg": _angle_deg(v_out, n),
        "velocity_out": [_round3(v_out["x"]), _round3(v_out["y"]), _round3(v_out["z"])],
    }


def trace_digest(trace_ids: list[int], replay_seq: int = 0) -> str:
    """SHA-256 hex of replay_seq|comma-joined physics_ids in traversal order."""
    ids_body = ",".join(str(i) for i in trace_ids)
    body = f"{replay_seq}|{ids_body}"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def reference_snapshot(
    stack_path: Path,
    velocity: list[float],
    energy_j: float,
    seed: int,
    materials: dict[int, dict[str, Any]] | None = None,
    seeds: dict[int, float] | None = None,
    replay_seq: int = 0,
) -> dict[str, Any]:
    """Build staging snapshot fields (pre-export)."""
    mats = materials if materials is not None else load_materials()
    stack = json.loads(stack_path.read_text(encoding="utf-8"))
    vel = apply_seed_scale(seed, velocity, seeds)

    energy = energy_j
    ledger = 0.0
    layers_out: list[dict[str, Any]] = []
    trace_ids: list[int] = []
    ricochet = None
    penetrated = True

    for layer in stack["layers"]:
        mat = mats[layer["physics_id"]]
        max_depth = energy / (mat["hardness"] * PEN_K)
        depth = min(max_depth, layer["thickness_m"])
        trace_ids.append(layer["physics_id"])

        if depth + EPS < layer["thickness_m"]:
            penetrated = False
            ricochet = compute_ricochet(vel, stack["normal"])
            layers_out.append(
                {
                    "physics_id": layer["physics_id"],
                    "depth_m": _round6(depth),
                    "fully_penetrated": False,
                    "energy_after_j": _round3(energy),
                }
            )
            break

        ledger += layer["thickness_m"]
        energy *= mat["falloff"]
        layers_out.append(
            {
                "physics_id": layer["physics_id"],
                "depth_m": _round6(layer["thickness_m"]),
                "fully_penetrated": True,
                "energy_after_j": _round3(energy),
            }
        )

    return {
        "staging_version": 1,
        "stack": stack["name"],
        "seed": seed,
        "replay_seq": replay_seq,
        "path_ledger_m": _round6(ledger),
        "exit_energy_j": _round3(energy),
        "penetrated": penetrated,
        "layers": layers_out,
        "ricochet": ricochet,
        "trace_ids": trace_ids,
    }


def reference_shot(
    stack_path: Path,
    velocity: list[float],
    energy_j: float,
    seed: int,
    materials: dict[int, dict[str, Any]] | None = None,
    seeds: dict[int, float] | None = None,
    replay_hist: ReplayHistory | None = None,
) -> dict[str, Any]:
    """Simulate one shot using contract-correct physics and staged export."""
    stack = json.loads(stack_path.read_text(encoding="utf-8"))
    replay_seq = 0
    if replay_hist is not None:
        replay_seq = replay_hist.stamp(stack["name"], seed)
    snap = reference_snapshot(
        stack_path, velocity, energy_j, seed, materials, seeds, replay_seq=replay_seq
    )
    return {
        "stack": snap["stack"],
        "seed": snap["seed"],
        "path_ledger_m": snap["path_ledger_m"],
        "exit_energy_j": snap["exit_energy_j"],
        "penetrated": snap["penetrated"],
        "layers": snap["layers"],
        "ricochet": snap["ricochet"],
        "trace_digest": trace_digest(snap["trace_ids"], snap["replay_seq"]),
    }


def reference_batch(
    batch_path: Path,
    stacks_dir: Path = STACKS_DIR,
    materials: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Simulate batch with tick grouping, shot_id ordering, and replay history."""
    mats = materials if materials is not None else load_materials()
    spec = json.loads(batch_path.read_text(encoding="utf-8"))
    hist = ReplayHistory()
    by_tick: dict[int, list[dict[str, Any]]] = {}

    for event in spec["events"]:
        stack_path = stacks_dir / f"{event['stack']}.json"
        shot = reference_shot(
            stack_path,
            event["velocity"],
            event["energy_j"],
            event["seed"],
            materials=mats,
            replay_hist=hist,
        )
        hit = {"sim_tick": event["sim_tick"], "shot_id": event["shot_id"], **shot}
        by_tick.setdefault(event["sim_tick"], []).append(hit)

    ticks = []
    for sim_tick in sorted(by_tick):
        hits = sorted(by_tick[sim_tick], key=lambda h: h["shot_id"])
        ticks.append({"sim_tick": sim_tick, "hits": hits})

    return {"batch": spec["name"], "ticks": ticks}


def reference_mutated_stack(
    layer_specs: list[tuple[int, float]],
    velocity: list[float],
    energy_j: float,
    seed: int,
    materials: dict[int, dict[str, Any]] | None = None,
    replay_hist: ReplayHistory | None = None,
) -> dict[str, Any]:
    """Build an ephemeral stack for anti-hardcoding probes."""
    mats = materials if materials is not None else load_materials()
    stack = {
        "name": "mutated",
        "normal": [0.0, 0.0, 1.0],
        "layers": [
            {"physics_id": pid, "thickness_m": thick} for pid, thick in layer_specs
        ],
    }
    tmp = Path("/tmp/mutated-stack.json")
    tmp.write_text(json.dumps(stack), encoding="utf-8")
    return reference_shot(tmp, velocity, energy_j, seed, materials=mats, replay_hist=replay_hist)
