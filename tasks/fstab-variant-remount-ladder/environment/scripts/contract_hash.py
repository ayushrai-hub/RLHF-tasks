#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

def opt_digest(opt: dict) -> str:
    return hashlib.sha256(json.dumps(opt, sort_keys=True).encode()).hexdigest()[:8]

def state_digest(rows: list[dict], blk_path: Path) -> str:
    parts = []
    for r in sorted(rows, key=lambda x: x["slot_id"]):
        od = opt_digest(r["option_map"])
        parts.append(
            f"{r['slot_id']}|{r['parent_slot']}|{r['attach_path']}|{r['band_class']}|{od}"
        )
    normalized = "\n".join(parts)
    blk_part = blk_path.read_bytes()[:32].hex()
    return hashlib.sha256((normalized + "|" + blk_part).encode()).hexdigest()[:8]

if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text())
    blk = Path(sys.argv[2])
    print(state_digest(data, blk))
