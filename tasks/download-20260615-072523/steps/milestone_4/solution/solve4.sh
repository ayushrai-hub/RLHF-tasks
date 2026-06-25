#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve3.sh"

python3 - <<'PY'
from pathlib import Path

path = Path("/app/tools/entitlement_audit.py")
text = path.read_text(encoding="utf-8")

if "def apply_remediation_command(" not in text:
    apply_code = '''

CHANGE_ORDER = ["remove_app_groups", "remove_associated_domains", "set_push_environment"]


def selected_entitlement_path(row: dict[str, Any]) -> Path | None:
    return entitlement_path(Path(row["path"]), row["executable"])


def apply_update(row: dict[str, Any], action: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any] | None:
    ent_path = selected_entitlement_path(row)
    if ent_path is None:
        return None
    effective = effective_policy(row, policy)
    entitlements = load_plist(ent_path)
    changes: list[str] = []

    app_groups = as_sorted_strings(entitlements.get("com.apple.security.application-groups"))
    kept_groups = [
        group
        for group in app_groups
        if group.startswith(effective["required_app_group_prefix"])
    ]
    removed_groups = sorted(group for group in app_groups if group not in kept_groups)
    if removed_groups:
        entitlements["com.apple.security.application-groups"] = kept_groups
        changes.append("remove_app_groups")

    domains = as_sorted_strings(entitlements.get("com.apple.developer.associated-domains"))
    kept_domains = [
        domain
        for domain in domains
        if has_allowed_domain(domain, effective["allowed_associated_domain_suffixes"])
    ]
    removed_domains = sorted(domain for domain in domains if domain not in kept_domains)
    if removed_domains:
        entitlements["com.apple.developer.associated-domains"] = kept_domains
        changes.append("remove_associated_domains")

    set_push = None
    expected_push = effective["expected_push_environment"]
    if (
        "push environment profile mismatch" in action["reasons"]
        and expected_push is not None
        and entitlements.get("aps-environment") != expected_push
    ):
        entitlements["aps-environment"] = expected_push
        set_push = expected_push
        changes.append("set_push_environment")

    if not changes:
        return None
    with ent_path.open("wb") as fh:
        plistlib.dump(entitlements, fh, sort_keys=False)
    changes.sort(key=CHANGE_ORDER.index)
    return {
        "bundle_id": row["bundle_id"],
        "path": str(ent_path),
        "changes": changes,
        "removed_app_groups": removed_groups,
        "removed_associated_domains": removed_domains,
        "set_aps_environment": set_push,
    }


def apply_remediation_command(bundles_dir: Path, policy_path: Path, output_path: Path) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    inventory = build_inventory(bundles_dir)
    rows = {row["bundle_id"]: row for row in inventory["bundles"]}
    actions = [classify(row, policy) for row in inventory["bundles"]]
    applied: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for action in sorted(actions, key=lambda item: item["bundle_id"]):
        row = rows[action["bundle_id"]]
        if action["action"] == "block":
            ent_path = selected_entitlement_path(row)
            blocked.append(
                {
                    "bundle_id": row["bundle_id"],
                    "path": str(ent_path) if ent_path is not None else None,
                    "reasons": action["reasons"],
                    "unchanged": True,
                }
            )
        elif action["action"] == "update":
            applied_row = apply_update(row, action, policy)
            if applied_row is not None:
                applied.append(applied_row)
    summary = {
        "applied_count": len(applied),
        "blocked_count": len(blocked),
        "files_changed": len(applied),
        "app_groups_removed": sum(len(row["removed_app_groups"]) for row in applied),
        "associated_domains_removed": sum(len(row["removed_associated_domains"]) for row in applied),
        "push_environments_set": sum(row["set_aps_environment"] is not None for row in applied),
    }
    write_json(output_path, {"applied": applied, "blocked": blocked, "summary": summary})
'''
    text = text.replace("\n\ndef main() -> None:\n", apply_code + "\n\ndef main() -> None:\n")

main_start = text.index("def main() -> None:")
main_end = text.index('\n\n\nif __name__ == "__main__":', main_start)
new_main = '''def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inv = subparsers.add_parser("inventory")
    inv.add_argument("bundles_dir")
    inv.add_argument("output_path")
    plan = subparsers.add_parser("plan")
    plan.add_argument("bundles_dir")
    plan.add_argument("policy_path")
    plan.add_argument("output_path")
    rem = subparsers.add_parser("remediate")
    rem.add_argument("bundles_dir")
    rem.add_argument("policy_path")
    rem.add_argument("output_path")
    apply = subparsers.add_parser("apply-remediation")
    apply.add_argument("bundles_dir")
    apply.add_argument("policy_path")
    apply.add_argument("output_path")
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_command(Path(args.bundles_dir), Path(args.output_path))
    elif args.command == "plan":
        plan_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    elif args.command == "remediate":
        remediate_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    else:
        apply_remediation_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))'''

text = text[:main_start] + new_main + text[main_end:]
path.write_text(text, encoding="utf-8")
path.chmod(0o755)
PY

python3 /app/tools/entitlement_audit.py apply-remediation /app/bundles /app/policy/signing-policy.json /app/out/entitlement-apply.json
