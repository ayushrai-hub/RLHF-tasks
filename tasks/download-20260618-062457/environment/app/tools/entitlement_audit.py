#!/usr/bin/env python3
"""Small starter CLI for auditing Apple-style bundle entitlements."""

from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path


def load_plist(path: Path) -> dict:
    with path.open("rb") as fh:
        return plistlib.load(fh)


def inventory(bundles_dir: Path, output_path: Path) -> None:
    rows = []
    for info_path in sorted(bundles_dir.glob("*/Info.plist")):
        info = load_plist(info_path)
        rows.append(
            {
                "path": str(info_path.parent),
                "bundle_id": info.get("CFBundleIdentifier", ""),
                "display_name": info.get("CFBundleDisplayName", ""),
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"bundles": rows}, indent=2), encoding="utf-8")


def plan(bundles_dir: Path, policy_path: Path, output_path: Path) -> None:
    _ = policy_path
    inventory(bundles_dir, Path("/tmp/entitlement-inventory.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"actions": []}, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    inv = subparsers.add_parser("inventory")
    inv.add_argument("bundles_dir")
    inv.add_argument("output_path")
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("bundles_dir")
    plan_parser.add_argument("policy_path")
    plan_parser.add_argument("output_path")
    args = parser.parse_args()
    if args.command == "inventory":
        inventory(Path(args.bundles_dir), Path(args.output_path))
    else:
        plan(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))


if __name__ == "__main__":
    main()
