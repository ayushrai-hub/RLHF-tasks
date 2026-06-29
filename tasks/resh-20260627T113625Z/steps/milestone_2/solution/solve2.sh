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


def version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split(".") if part.isdigit())


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
                "runtime_profile": text(root, "RuntimeProfile"),
                "test_only": text(root, "IsTestProject", "false").lower() == "true",
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def inventory(src: Path, props: Path) -> dict:
    rows = projects(src, props)
    counts = Counter(row["target_framework"] for row in rows)
    policy = json.loads(Path("/app/policy/runtime-policy.json").read_text(encoding="utf-8"))
    required = set(policy.get("required_rids", []))
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


def resolved_policy(row: dict, policy: dict) -> tuple[dict, str]:
    profile_name = row.get("runtime_profile") or ""
    if not profile_name:
        matches = [
            (prefix, name)
            for prefix, name in policy.get("path_profile_overrides", {}).items()
            if row["path"].startswith(prefix)
        ]
        if matches:
            profile_name = sorted(matches, key=lambda item: (-len(item[0]), item[0]))[0][1]
    profile = policy.get("runtime_profiles", {}).get(profile_name, {})
    merged = {
        "required_framework": profile.get("required_framework", policy["required_framework"]),
        "required_nullable": profile.get("required_nullable", policy["required_nullable"]),
        "required_rids": profile.get("required_rids", policy["required_rids"]),
        "minimum_packages": dict(policy.get("minimum_packages", {})),
    }
    merged["minimum_packages"].update(profile.get("minimum_packages", {}))
    return merged, profile_name


def classify(row: dict, policy: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if row["target_framework"] in set(policy["retire_frameworks"]):
        return "retire", ["target framework is on the retire list"]
    target, profile_name = resolved_policy(row, policy)
    profile_note = f" for runtime profile {profile_name}" if profile_name else ""
    if row["test_only"]:
        if row["target_framework"] not in set(policy["allowed_test_frameworks"]):
            reasons.append("test project framework is outside the allowed list")
    elif row["target_framework"] != target["required_framework"]:
        reasons.append(f"target framework does not match the required runtime baseline{profile_note}")
    if row["nullable"] != target["required_nullable"]:
        reasons.append(f"nullable setting does not match policy{profile_note}")
    if not row["test_only"] and set(row["runtime_identifiers"]) != set(target["required_rids"]):
        reasons.append(f"runtime identifiers do not match policy{profile_note}")
    for name, minimum in target.get("minimum_packages", {}).items():
        actual = row["packages"].get(name)
        if actual and version_tuple(actual) < version_tuple(minimum):
            reasons.append(f"{name} is below {minimum}{profile_note}")
    return ("update", reasons) if reasons else ("keep", ["project already matches runtime policy"])


def plan(src: Path, props: Path, policy_path: Path) -> dict:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    actions = []
    for row in projects(src, props):
        target_policy, _ = resolved_policy(row, policy)
        action, reasons = classify(row, policy)
        actions.append(
            {
                "path": row["path"],
                "name": row["name"],
                "action": action,
                "reasons": reasons,
                "target": {
                    "target_framework": target_policy["required_framework"],
                    "nullable": target_policy["required_nullable"],
                    "runtime_identifiers": sorted(target_policy["required_rids"]) if not row["test_only"] else [],
                },
            }
        )
    priority = {"retire": 0, "update": 1, "keep": 2}
    actions.sort(key=lambda row: (priority[row["action"]], row["path"]))
    counts = Counter(row["action"] for row in actions)
    return {"actions": actions, "summary": {key: counts.get(key, 0) for key in ["retire", "update", "keep"]}}


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "inventory":
        write(Path(sys.argv[4]), inventory(Path(sys.argv[2]), Path(sys.argv[3])))
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "plan":
        write(Path(sys.argv[5]), plan(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
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
