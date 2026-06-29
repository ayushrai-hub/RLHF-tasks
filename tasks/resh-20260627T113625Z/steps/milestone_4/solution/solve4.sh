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


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text(root: ET.Element, name: str, default: str = "") -> str:
    found = next((node for node in root.iter() if local_name(node.tag) == name), None)
    return (found.text or "").strip() if found is not None else default


def package_versions(props: Path) -> dict[str, str]:
    root = ET.parse(props).getroot()
    versions: dict[str, str] = {}
    for item in root.iter():
        if local_name(item.tag) != "PackageVersion":
            continue
        name = item.attrib.get("Include") or item.attrib.get("Update")
        version = item.attrib.get("Version")
        if name and version:
            versions[name] = version
    return versions


def split_rids(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for raw in value.split("."):
        digits = ""
        for char in raw:
            if char.isdigit():
                digits += char
            else:
                break
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def normalize_project_reference(src: Path, owner: Path, include: str) -> str | None:
    normalized_include = include.replace("\\", "/")
    macro = "$(MSBuildThisFileDirectory)"
    if normalized_include.startswith(macro):
        normalized_include = normalized_include[len(macro):].lstrip("/")
    ref_path = (owner.parent / normalized_include).resolve()
    try:
        return ref_path.relative_to(src.resolve()).as_posix()
    except ValueError:
        return None


def projects(src: Path, props: Path) -> list[dict]:
    central = package_versions(props)
    rows = []
    for csproj in sorted(src.rglob("*.csproj")):
        root = ET.parse(csproj).getroot()
        refs: dict[str, str] = {}
        project_refs: list[str] = []
        for item in root.iter():
            kind = local_name(item.tag)
            if kind == "PackageReference":
                name = item.attrib["Include"]
                refs[name] = item.attrib.get("Version", central.get(name, ""))
            elif kind == "ProjectReference":
                include = item.attrib.get("Include")
                if include:
                    normalized = normalize_project_reference(src, csproj, include)
                    if normalized:
                        project_refs.append(normalized)
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
                "project_references": sorted(dict.fromkeys(project_refs)),
                "runtime_profile": text(root, "RuntimeProfile"),
                "test_only": text(root, "IsTestProject", "false").lower() == "true",
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def inventory(src: Path, props: Path, policy_path: Path) -> dict:
    rows = projects(src, props)
    counts = Counter(row["target_framework"] for row in rows)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    required = set(policy.get("required_rids", []))
    public_rows = [{key: row[key] for key in ["path", "name", "target_framework", "nullable", "runtime_identifiers", "packages", "test_only"]} for row in rows]
    return {
        "projects": public_rows,
        "summary": {
            "total": len(rows),
            "by_framework": dict(sorted(counts.items())),
            "test_projects": sum(1 for row in rows if row["test_only"]),
            "missing_required_rids": sum(1 for row in rows if not row["test_only"] and set(row["runtime_identifiers"]) != required),
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
            reasons.append("target framework is outside the allowed test framework list")
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


def plan_rows(src: Path, props: Path, policy_path: Path) -> tuple[list[dict], list[dict], dict]:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    rows = projects(src, props)
    actions = []
    for row in rows:
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
    return rows, actions, policy


def plan(src: Path, props: Path, policy_path: Path) -> dict:
    _, actions, _ = plan_rows(src, props, policy_path)
    counts = Counter(row["action"] for row in actions)
    return {"actions": actions, "summary": {key: counts.get(key, 0) for key in ["retire", "update", "keep"]}}


def waves(src: Path, props: Path, policy_path: Path) -> dict:
    rows, actions, _ = plan_rows(src, props, policy_path)
    by_path = {row["path"]: row for row in rows}
    action_by_path = {row["path"]: row["action"] for row in actions}
    name_by_path = {row["path"]: row["name"] for row in actions}
    update_paths = {path for path, action in action_by_path.items() if action == "update"}
    retire_paths = sorted(path for path, action in action_by_path.items() if action == "retire")

    blocked: dict[str, list[str]] = {}
    for path in sorted(update_paths):
        for dep in by_path[path]["project_references"]:
            if dep not in action_by_path:
                continue
            if action_by_path[dep] == "retire":
                blocked.setdefault(path, []).append(f"retired dependency: {dep}")

    remaining = set(update_paths) - set(blocked)
    placed: set[str] = set()
    wave_rows = []
    wave_number = 1
    while remaining:
        ready = sorted(
            path
            for path in remaining
            if all(
                dep not in update_paths or dep in placed
                for dep in by_path[path]["project_references"]
                if dep in action_by_path
            )
        )
        if not ready:
            for path in sorted(remaining):
                blocked.setdefault(path, []).append("dependency cycle prevents wave ordering")
            break
        wave_rows.append({"wave": wave_number, "projects": ready})
        placed.update(ready)
        remaining.difference_update(ready)
        wave_number += 1

    blocked_rows = [
        {"path": path, "name": name_by_path[path], "reasons": reasons}
        for path, reasons in sorted(blocked.items())
    ]
    return {
        "waves": wave_rows,
        "blocked": blocked_rows,
        "retire": retire_paths,
        "summary": {
            "wave_count": len(wave_rows),
            "update_projects": len(update_paths),
            "blocked_projects": len(blocked_rows),
            "retire_projects": len(retire_paths),
        },
    }


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "inventory":
        write(Path(sys.argv[4]), inventory(Path(sys.argv[2]), Path(sys.argv[3]), Path("/app/policy/runtime-policy.json")))
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "plan":
        write(Path(sys.argv[5]), plan(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "waves":
        write(Path(sys.argv[5]), waves(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
        return 0
    print(
        "usage: msbuild_audit.py inventory <src_root> <packages_props> <out_json> OR plan <src_root> <packages_props> <policy_json> <out_json> OR waves <src_root> <packages_props> <policy_json> <out_json>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
PY
chmod +x /app/tools/msbuild_audit.py
python3 - <<'PY'
from pathlib import Path

path = Path("/app/tools/msbuild_audit.py")
text = path.read_text(encoding="utf-8")

if "def apply_plan(" not in text:
    apply_code = '''

CHANGE_ORDER = ["target_framework", "nullable", "runtime_identifiers", "package_versions"]


def find_child(root: ET.Element, name: str) -> ET.Element | None:
    for node in root.iter():
        if local_name(node.tag) == name:
            return node
    return None


def property_group(root: ET.Element) -> ET.Element:
    for node in root:
        if local_name(node.tag) == "PropertyGroup":
            return node
    return ET.SubElement(root, "PropertyGroup")


def set_property(root: ET.Element, name: str, value: str) -> bool:
    node = find_child(root, name)
    if node is None:
        node = ET.SubElement(property_group(root), name)
    old = (node.text or "").strip()
    if old == value:
        return False
    node.text = value
    return True


def remove_properties(root: ET.Element, names: set[str]) -> bool:
    changed = False
    for parent in root.iter():
        for child in list(parent):
            if local_name(child.tag) in names:
                parent.remove(child)
                changed = True
    return changed


def update_package_versions(root: ET.Element, row: dict, target_policy: dict) -> dict[str, str]:
    updated: dict[str, str] = {}
    for node in root.iter():
        if local_name(node.tag) != "PackageReference":
            continue
        name = node.attrib.get("Include")
        minimum = target_policy.get("minimum_packages", {}).get(name or "")
        actual = row["packages"].get(name or "")
        if name and minimum and actual and "Version" in node.attrib and version_tuple(actual) < version_tuple(minimum):
            if node.attrib.get("Version") != minimum:
                node.set("Version", minimum)
                updated[name] = minimum
    return dict(sorted(updated.items()))


def apply_project(src: Path, row: dict, action: dict, policy: dict, wave: int) -> dict | None:
    project_path = src / row["path"]
    root = ET.parse(project_path).getroot()
    target_policy, _ = resolved_policy(row, policy)
    changes: list[str] = []
    if set_property(root, "TargetFramework", action["target"]["target_framework"]):
        changes.append("target_framework")
    if set_property(root, "Nullable", action["target"]["nullable"]):
        changes.append("nullable")
    if row["test_only"]:
        if remove_properties(root, {"RuntimeIdentifier", "RuntimeIdentifiers"}):
            changes.append("runtime_identifiers")
    else:
        if remove_properties(root, {"RuntimeIdentifier"}):
            pass
        target_rids = ";".join(action["target"]["runtime_identifiers"])
        if set_property(root, "RuntimeIdentifiers", target_rids):
            changes.append("runtime_identifiers")
    packages_updated = update_package_versions(root, row, target_policy)
    if packages_updated:
        changes.append("package_versions")
    changes = sorted(dict.fromkeys(changes), key=CHANGE_ORDER.index)
    if not changes:
        return None
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(project_path, encoding="unicode", xml_declaration=False)
    with project_path.open("a", encoding="utf-8") as fh:
        fh.write("\\n")
    return {
        "path": row["path"],
        "name": row["name"],
        "wave": wave,
        "changes": changes,
        "target": action["target"],
        "packages_updated": packages_updated,
    }


def apply_plan(src: Path, props: Path, policy_path: Path) -> dict:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    rows, actions, _ = plan_rows(src, props, policy_path)
    rows_by_path = {row["path"]: row for row in rows}
    actions_by_path = {row["path"]: row for row in actions}
    wave_report = waves(src, props, policy_path)
    applied: list[dict] = []
    for wave in wave_report["waves"]:
        for project_path in wave["projects"]:
            row = rows_by_path[project_path]
            action = actions_by_path[project_path]
            applied_row = apply_project(src, row, action, policy, wave["wave"])
            if applied_row is not None:
                applied.append(applied_row)
    blocked = [
        {
            "path": row["path"],
            "name": row["name"],
            "reasons": row["reasons"],
            "unchanged": True,
        }
        for row in wave_report["blocked"]
    ]
    summary = {
        "applied_count": len(applied),
        "blocked_count": len(blocked),
        "retire_count": len(wave_report["retire"]),
        "files_changed": len(applied),
        "package_versions_updated": sum(len(row["packages_updated"]) for row in applied),
        "wave_count": wave_report["summary"]["wave_count"],
    }
    return {
        "applied": applied,
        "blocked": blocked,
        "retire": wave_report["retire"],
        "summary": summary,
    }
'''
    text = text.replace("\n\ndef write(path: Path, payload: dict) -> None:\n", apply_code + "\n\ndef write(path: Path, payload: dict) -> None:\n")

main_start = text.index("def main() -> int:")
main_end = text.index('\n\n\nif __name__ == "__main__":', main_start)
new_main = '''def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "inventory":
        write(Path(sys.argv[4]), inventory(Path(sys.argv[2]), Path(sys.argv[3]), Path("/app/policy/runtime-policy.json")))
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "plan":
        write(Path(sys.argv[5]), plan(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "waves":
        write(Path(sys.argv[5]), waves(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
        return 0
    if len(sys.argv) == 6 and sys.argv[1] == "apply-plan":
        write(Path(sys.argv[5]), apply_plan(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
        return 0
    print(
        "usage: msbuild_audit.py inventory <src_root> <packages_props> <out_json> OR plan <src_root> <packages_props> <policy_json> <out_json> OR waves <src_root> <packages_props> <policy_json> <out_json> OR apply-plan <src_root> <packages_props> <policy_json> <out_json>",
        file=sys.stderr,
    )
    return 2'''

text = text[:main_start] + new_main + text[main_end:]
path.write_text(text, encoding="utf-8")
path.chmod(0o755)
PY
