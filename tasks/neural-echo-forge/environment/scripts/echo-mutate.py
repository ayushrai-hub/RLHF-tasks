#!/usr/bin/env python3
"""Mutate session shards for adversarial verifier runs."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SESSIONS = Path("/app/data/sessions")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    for path in SESSIONS.glob("*.jsonl"):
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        rng.shuffle(rows)
        text = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
        if text:
            text += "\n"
        path.write_text(text, encoding="utf-8")
    print(f"mutated {len(list(SESSIONS.glob('*.jsonl')))} session shards seed={args.seed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
