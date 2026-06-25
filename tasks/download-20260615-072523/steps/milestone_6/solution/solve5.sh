#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve4.sh"

python3 - <<'PY'
from pathlib import Path

path = Path("/app/tools/entitlement_audit.py")
text = path.read_text(encoding="utf-8")

if "def verify_remediation_command(" not in text:
    verify_code = '''

STATUS_PRIORITY = {"blocked": 0, "drift": 1, "compliant": 2}


def current_entitlement_state(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_identifier": row["entitlements"]["team_identifier"],
        "app_groups": row["entitlements"]["app_groups"],
        "associated_domains": row["entitlements"]["associated_domains"],
        "aps_environment": row["entitlements"]["aps_environment"],
    }


def pending_change_set(row: dict[str, Any], action: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    pending = remediation_row(row, action, policy)
    set_aps = None
    if (
        "push environment profile mismatch" in action["reasons"]
        and pending["expected_push_environment"] is not None
        and row["entitlements"]["aps_environment"] != pending["expected_push_environment"]
    ):
        set_aps = pending["expected_push_environment"]
    return {
        "set_team_identifier": pending["set_team_identifier"],
        "remove_app_groups": pending["remove_app_groups"],
        "remove_associated_domains": pending["remove_associated_domains"],
        "set_aps_environment": set_aps,
    }


def verify_row(row: dict[str, Any], action: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    effective = effective_policy(row, policy)
    changes = pending_change_set(row, action, policy)
    safe_change_count = (
        len(changes["remove_app_groups"])
        + len(changes["remove_associated_domains"])
        + (1 if changes["set_aps_environment"] is not None else 0)
    )
    if action["action"] == "block":
        status = "blocked"
    elif action["action"] == "update" and safe_change_count > 0:
        status = "drift"
    else:
        status = "compliant"
    ent_path = selected_entitlement_path(row)
    return {
        "bundle_id": row["bundle_id"],
        "platform": row["platform"],
        "profile": row["profile"],
        "status": status,
        "reasons": action["reasons"],
        "selected_sidecar": str(ent_path) if ent_path is not None else None,
        "needs_changes": status == "drift",
        "blocked": status == "blocked",
        "effective_policy": {
            "team_identifier": effective["team_identifier"],
            "allowed_profiles": effective["allowed_profiles"],
            "expected_push_environment": effective["expected_push_environment"],
            "required_app_group_prefix": effective["required_app_group_prefix"],
            "allowed_associated_domain_suffixes": effective["allowed_associated_domain_suffixes"],
        },
        "current": current_entitlement_state(row),
        "pending_changes": changes,
    }


def verify_remediation_command(bundles_dir: Path, policy_path: Path, output_path: Path) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    inventory = build_inventory(bundles_dir)
    actions = {action["bundle_id"]: action for action in [classify(row, policy) for row in inventory["bundles"]]}
    rows = [verify_row(row, actions[row["bundle_id"]], policy) for row in inventory["bundles"]]
    rows.sort(key=lambda row: (STATUS_PRIORITY[row["status"]], row["bundle_id"]))
    violation_counts = {reason: 0 for reason in REASON_ORDER}
    for row in rows:
        for reason in row["reasons"]:
            violation_counts[reason] += 1
    summary = {
        "total": len(rows),
        "compliant": sum(row["status"] == "compliant" for row in rows),
        "drift": sum(row["status"] == "drift" for row in rows),
        "blocked": sum(row["status"] == "blocked" for row in rows),
        "files_needing_changes": sum(row["status"] == "drift" and row["selected_sidecar"] is not None for row in rows),
        "safe_change_count": sum(
            len(row["pending_changes"]["remove_app_groups"])
            + len(row["pending_changes"]["remove_associated_domains"])
            + (1 if row["pending_changes"]["set_aps_environment"] is not None else 0)
            for row in rows
            if row["status"] == "drift"
        ),
        "blocked_with_sidecar": sum(row["status"] == "blocked" and row["selected_sidecar"] is not None for row in rows),
    }
    write_json(output_path, {"bundles": rows, "summary": summary, "violation_counts": violation_counts})
'''
    text = text.replace("\n\ndef main() -> None:\n", verify_code + "\n\ndef main() -> None:\n")

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
    verify = subparsers.add_parser("verify-remediation")
    verify.add_argument("bundles_dir")
    verify.add_argument("policy_path")
    verify.add_argument("output_path")
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_command(Path(args.bundles_dir), Path(args.output_path))
    elif args.command == "plan":
        plan_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    elif args.command == "remediate":
        remediate_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    elif args.command == "apply-remediation":
        apply_remediation_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    else:
        verify_remediation_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))'''

text = text[:main_start] + new_main + text[main_end:]
path.write_text(text, encoding="utf-8")
path.chmod(0o755)
PY

python3 /app/tools/entitlement_audit.py verify-remediation /app/bundles /app/policy/signing-policy.json /app/out/entitlement-verification.json
