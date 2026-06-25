#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve1.sh"
bash "$SCRIPT_DIR/solve2.sh"

python3 - <<'PY'
from pathlib import Path

path = Path("/app/tools/entitlement_audit.py")
text = path.read_text(encoding="utf-8")

if "def remediate_command(" not in text:
    remediation_code = '''

def effective_policy(row: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    overrides = policy.get("bundle_overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
    override = overrides.get(row["bundle_id"], {})
    if not isinstance(override, dict):
        override = {}
    if "allowed_profiles" in override:
        allowed_profiles = [str(item) for item in override.get("allowed_profiles") or []]
    else:
        allowed_profiles = list(policy.get("allowed_profiles", {}).get(row["platform"], []))
    if "expected_push_environment" in override:
        expected_push = override.get("expected_push_environment")
    else:
        expected_push = policy.get("push_profile_environments", {}).get(row["profile"])
    return {
        "team_identifier": override.get("required_team_id", policy["required_team_id"]),
        "allowed_profiles": allowed_profiles,
        "expected_push_environment": expected_push,
        "required_app_group_prefix": override.get(
            "required_app_group_prefix", policy["required_app_group_prefix"]
        ),
        "allowed_associated_domain_suffixes": list(
            override.get(
                "allowed_associated_domain_suffixes",
                policy.get("allowed_associated_domain_suffixes", []),
            )
            or []
        ),
    }


def remediation_row(row: dict[str, Any], action: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    effective = effective_policy(row, policy)
    entitlements = row["entitlements"]
    remove_app_groups = sorted(
        group
        for group in entitlements["app_groups"]
        if not group.startswith(effective["required_app_group_prefix"])
    )
    remove_domains = sorted(
        domain
        for domain in entitlements["associated_domains"]
        if not has_allowed_domain(domain, effective["allowed_associated_domain_suffixes"])
    )
    needs_team_fix = any(
        reason in action["reasons"]
        for reason in ["team identifier missing", "team identifier mismatch"]
    )
    return {
        "bundle_id": row["bundle_id"],
        "action": action["action"],
        "reasons": action["reasons"],
        "set_team_identifier": effective["team_identifier"] if needs_team_fix else None,
        "allowed_profiles": effective["allowed_profiles"],
        "expected_push_environment": effective["expected_push_environment"],
        "remove_app_groups": remove_app_groups,
        "remove_associated_domains": remove_domains,
        "blocked": action["action"] == "block",
    }


def remediate_command(bundles_dir: Path, policy_path: Path, output_path: Path) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    inventory = build_inventory(bundles_dir)
    actions = [classify(row, policy) for row in inventory["bundles"]]
    by_bundle = {row["bundle_id"]: row for row in inventory["bundles"]}
    fixes = [
        remediation_row(by_bundle[action["bundle_id"]], action, policy)
        for action in actions
        if action["action"] != "keep"
    ]
    fixes.sort(key=lambda row: row["bundle_id"])
    summary = {
        "fix_count": len(fixes),
        "blocked_count": sum(row["blocked"] for row in fixes),
        "update_count": sum(row["action"] == "update" for row in fixes),
        "team_identifier_fix_count": sum(row["set_team_identifier"] is not None for row in fixes),
        "app_groups_to_remove_count": sum(len(row["remove_app_groups"]) for row in fixes),
        "associated_domains_to_remove_count": sum(len(row["remove_associated_domains"]) for row in fixes),
        "push_environment_fix_count": sum(
            "push environment profile mismatch" in row["reasons"] for row in fixes
        ),
    }
    write_json(output_path, {"fixes": fixes, "summary": summary})
'''
    text = text.replace("\n\ndef main() -> None:\n", remediation_code + "\n\ndef main() -> None:\n")

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
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_command(Path(args.bundles_dir), Path(args.output_path))
    elif args.command == "plan":
        plan_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    else:
        remediate_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))'''

text = text[:main_start] + new_main + text[main_end:]
path.write_text(text, encoding="utf-8")
path.chmod(0o755)
PY

python3 /app/tools/entitlement_audit.py remediate /app/bundles /app/policy/signing-policy.json /app/out/entitlement-remediation.json
