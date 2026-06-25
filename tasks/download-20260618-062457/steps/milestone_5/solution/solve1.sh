#!/bin/bash
set -euo pipefail
cat > /app/tools/entitlement_audit.py <<'PY'
#!/usr/bin/env python3
"""Audit Apple bundle Info.plist and entitlement files."""

from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path
from typing import Any


PLATFORM_MAP = {"iphoneos": "ios", "iphonesimulator": "ios", "macosx": "macos"}
def load_plist(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return plistlib.load(fh)


def as_sorted_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return sorted(str(item) for item in value)
    return [str(value)]


def entitlement_path(bundle_dir: Path, executable: str) -> Path | None:
    preferred = bundle_dir / f"{executable}.entitlements"
    if preferred.exists():
        return preferred
    matches = sorted(bundle_dir.glob("*.entitlements"))
    return matches[0] if matches else None


def normalize_bundle(bundle_dir: Path) -> dict[str, Any] | None:
    info_path = bundle_dir / "Info.plist"
    if not info_path.exists():
        return None
    info = load_plist(info_path)
    executable = str(info.get("CFBundleExecutable") or "")
    entitlements: dict[str, Any] = {}
    ent_path = entitlement_path(bundle_dir, executable)
    if ent_path:
        entitlements = load_plist(ent_path)
    platform = str(info.get("DTPlatformName") or "")
    normalized = PLATFORM_MAP.get(platform, platform)
    entitlement_row = {
        "app_groups": as_sorted_strings(entitlements.get("com.apple.security.application-groups")),
        "keychain_groups": as_sorted_strings(entitlements.get("keychain-access-groups")),
        "associated_domains": as_sorted_strings(
            entitlements.get("com.apple.developer.associated-domains")
        ),
        "aps_environment": entitlements.get("aps-environment"),
        "team_identifier": entitlements.get("com.apple.developer.team-identifier"),
    }
    return {
        "path": str(bundle_dir),
        "bundle_id": str(info.get("CFBundleIdentifier") or ""),
        "display_name": str(info.get("CFBundleDisplayName") or ""),
        "executable": executable,
        "platform": normalized,
        "profile": info.get("ProvisioningProfile"),
        "entitlements": entitlement_row,
    }


def build_inventory(bundles_dir: Path) -> dict[str, Any]:
    rows = [
        row
        for row in (normalize_bundle(path) for path in sorted(bundles_dir.iterdir()) if path.is_dir())
        if row is not None
    ]
    rows.sort(key=lambda row: row["bundle_id"])
    by_platform: dict[str, int] = {}
    with_push = 0
    missing_team = 0
    for row in rows:
        by_platform[row["platform"]] = by_platform.get(row["platform"], 0) + 1
        if row["entitlements"]["aps_environment"] is not None:
            with_push += 1
        if row["entitlements"]["team_identifier"] is None:
            missing_team += 1
    return {
        "bundles": rows,
        "summary": {
            "total": len(rows),
            "by_platform": dict(sorted(by_platform.items())),
            "with_push": with_push,
            "missing_team_identifier": missing_team,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def inventory_command(bundles_dir: Path, output_path: Path) -> None:
    write_json(output_path, build_inventory(bundles_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inv = subparsers.add_parser("inventory")
    inv.add_argument("bundles_dir")
    inv.add_argument("output_path")
    args = parser.parse_args()
    inventory_command(Path(args.bundles_dir), Path(args.output_path))


if __name__ == "__main__":
    main()
PY
chmod +x /app/tools/entitlement_audit.py
python3 /app/tools/entitlement_audit.py inventory /app/bundles /app/out/entitlement-inventory.json
