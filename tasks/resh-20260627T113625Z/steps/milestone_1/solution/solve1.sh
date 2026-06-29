#!/bin/bash
set -euo pipefail

cat > /app/tools/msbuild_audit.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def text(root: ET.Element, name: str, default: str = "") -> str:
    found = next((node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == name), None)
    return (found.text or "").strip() if found is not None else default


def package_versions(props: Path) -> dict[str, str]:
    root = ET.parse(props).getroot()
    versions: dict[str, str] = {}
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] != "PackageVersion":
            continue
        name = item.attrib.get("Include") or item.attrib.get("Update")
        version = item.attrib.get("Version")
        if name and version:
            versions[name] = version
    return versions


def split_rids(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def required_rids() -> set[str]:
    policy = json.loads(Path("/app/policy/runtime-policy.json").read_text(encoding="utf-8"))
    return set(policy.get("required_rids", []))


def projects(src: Path, props: Path) -> list[dict]:
    central = package_versions(props)
    rows = []
    for csproj in sorted(src.rglob("*.csproj")):
        root = ET.parse(csproj).getroot()
        refs = {}
        for ref in root.iter():
            if ref.tag.rsplit("}", 1)[-1] != "PackageReference":
                continue
            name = ref.attrib["Include"]
            refs[name] = ref.attrib.get("Version", central.get(name))
        rids = split_rids(text(root, "RuntimeIdentifiers") or text(root, "RuntimeIdentifier"))
        rel = csproj.relative_to(src).as_posix()
        rows.append(
            {
                "path": rel,
                "name": csproj.stem,
                "target_framework": text(root, "TargetFramework"),
                "nullable": text(root, "Nullable", "unspecified"),
                "runtime_identifiers": sorted(rids),
                "packages": dict(sorted(refs.items())),
                "test_only": text(root, "IsTestProject", "false").lower() == "true",
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def inventory(src: Path, props: Path) -> dict:
    rows = projects(src, props)
    counts = Counter(row["target_framework"] for row in rows)
    required = required_rids()
    return {
        "projects": rows,
        "summary": {
            "total": len(rows),
            "by_framework": dict(sorted(counts.items())),
            "test_projects": sum(1 for row in rows if row["test_only"]),
            "missing_required_rids": sum(
                1 for row in rows if not row["test_only"] and set(row["runtime_identifiers"]) != required
            ),
        },
    }


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "inventory":
        write(Path(sys.argv[4]), inventory(Path(sys.argv[2]), Path(sys.argv[3])))
        return 0
    print(
        "usage: msbuild_audit.py inventory <src_root> <packages_props> <out_json> OR plan <src_root> <packages_props> <policy_json> <out_json>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
PY
chmod +x /app/tools/msbuild_audit.py
