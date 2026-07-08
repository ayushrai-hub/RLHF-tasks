"""Build formation hypothesis staging from depth epochs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

APP = Path("/app")
EPOCHS = APP / "state" / "depth-epoch-ledger.json"
CATALOG = APP / "state" / "survey-ingest-catalog.json"
POLICY = APP / "data" / "policies" / "formation-governance.json"
OUT = APP / "state" / "formation-compose-staging.json"

EVIDENCE_BY_SOURCE = {
    "seismic": "wave-anomaly",
    "gravity": "density-deficit",
    "magnetic": "susceptibility-peak",
    "borehole": "lithology-break",
    "geochem": "pathfinder-spike",
    "hyperspectral": "alteration-halo",
}


def epoch_digest(epochs: list[dict]) -> str:
    lines = [
        f"epoch|{ep['epoch_id']}|{ep['block_id']}|{len(ep['sample_ids'])}"
        for ep in epochs
    ]
    lines.sort()
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def main() -> None:
    epochs_doc = json.loads(EPOCHS.read_text())
    catalog = json.loads(CATALOG.read_text())
    policy = json.loads(POLICY.read_text())
    by_id = {o["sample_id"]: o for o in catalog["traces"]}
    epoch_by_block = {ep["block_id"]: ep["sample_ids"] for ep in epochs_doc["epochs"]}
    compose = []
    for block in policy["hypothesis_priority"]:
        if block not in epoch_by_block:
            continue
        steps = []
        for idx, obs_id in enumerate(epoch_by_block[block], start=1):
            src = by_id[obs_id]["source"]
            steps.append(
                {
                    "step": idx,
                    "sample_id": obs_id,
                    "evidence_kind": EVIDENCE_BY_SOURCE[src],
                }
            )
        compose.append({"block_id": block, "steps": steps})
    ep_digest = epoch_digest(epochs_doc["epochs"])
    lines = [f"compose|epoch|{ep_digest}"]
    for sc in compose:
        for step in sc["steps"]:
            lines.append(
                f"compose|{sc['block_id']}|{step['step']}|{step['sample_id']}|{step['evidence_kind']}"
            )
    lines.sort()
    plan_digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    staging = {
        "compose": compose,
        "formation_compose_digest": plan_digest,
        "bound_epoch_digest": ep_digest,
        "plan_source": "branch-planner",
    }
    OUT.write_text(json.dumps(staging, indent=2) + "\n")


if __name__ == "__main__":
    main()
