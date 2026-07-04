#!/usr/bin/env bash
set -euo pipefail
letterfolio_dir="$1"
collection_path="$2"
python3 - "$letterfolio_dir" "$collection_path" <<'PY'
import json, sys
from pathlib import Path
letterfolio_dir, collection_path = Path(sys.argv[1]), Path(sys.argv[2])
artifacts = []
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
            rec["media_slot"] = abs(int(line.split(None, 1)[1].strip()))
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
collection = json.loads(Path(collection_path).read_text())
print(json.dumps({"artifacts": artifacts, "collection": collection}))
PY
