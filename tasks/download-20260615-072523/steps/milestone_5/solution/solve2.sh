#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

path = Path("/app/tools/entitlement_audit.py")
text = path.read_text(encoding="utf-8")

if "def plan_command(" not in text:
    plan_code = '''

REASON_ORDER = [
    "team identifier missing",
    "team identifier mismatch",
    "profile not allowed for platform",
    "app group prefix violation",
    "associated domain not allowed",
    "push environment profile mismatch",
]
ACTION_PRIORITY = {"block": 0, "update": 1, "keep": 2}


def has_allowed_domain(domain: str, suffixes: list[str]) -> bool:
    if not domain.startswith("applinks:"):
        return False
    host = domain.split(":", 1)[1]
    return any(host.endswith(suffix) for suffix in suffixes)


def classify(row: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    entitlements = row["entitlements"]
    platform = row["platform"]
    profile = row["profile"]
    overrides = policy.get("bundle_overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
    override = overrides.get(row["bundle_id"], {})
    if not isinstance(override, dict):
        override = {}
    required_team = override.get("required_team_id", policy["required_team_id"])
    if "allowed_profiles" in override:
        allowed_profiles = [str(item) for item in override.get("allowed_profiles") or []]
    else:
        allowed_profiles = list(policy.get("allowed_profiles", {}).get(platform, []))
    if "expected_push_environment" in override:
        expected_push = override.get("expected_push_environment")
    else:
        expected_push = policy.get("push_profile_environments", {}).get(profile)
    prefix = override.get("required_app_group_prefix", policy["required_app_group_prefix"])
    suffixes = list(
        override.get(
            "allowed_associated_domain_suffixes",
            policy.get("allowed_associated_domain_suffixes", []),
        )
        or []
    )
    reasons: list[str] = []
    team = entitlements["team_identifier"]
    if team is None:
        reasons.append("team identifier missing")
    elif team != required_team:
        reasons.append("team identifier mismatch")
    if profile not in allowed_profiles:
        reasons.append("profile not allowed for platform")
    if any(not group.startswith(prefix) for group in entitlements["app_groups"]):
        reasons.append("app group prefix violation")
    if any(not has_allowed_domain(domain, suffixes) for domain in entitlements["associated_domains"]):
        reasons.append("associated domain not allowed")
    aps_environment = entitlements["aps_environment"]
    if aps_environment is not None and expected_push is not None and aps_environment != expected_push:
        reasons.append("push environment profile mismatch")
    reasons.sort(key=REASON_ORDER.index)
    action = "keep"
    if any(reason in reasons for reason in REASON_ORDER[:3]):
        action = "block"
    elif reasons:
        action = "update"
    return {
        "bundle_id": row["bundle_id"],
        "display_name": row["display_name"],
        "platform": platform,
        "profile": profile,
        "action": action,
        "reasons": reasons,
        "target": {
            "team_identifier": required_team,
            "allowed_profiles": allowed_profiles,
            "expected_push_environment": expected_push,
        },
    }


def plan_command(bundles_dir: Path, policy_path: Path, output_path: Path) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    inventory = build_inventory(bundles_dir)
    actions = [classify(row, policy) for row in inventory["bundles"]]
    actions.sort(key=lambda row: (ACTION_PRIORITY[row["action"]], row["bundle_id"]))
    summary = {"block": 0, "update": 0, "keep": 0}
    for row in actions:
        summary[row["action"]] += 1
    write_json(output_path, {"actions": actions, "summary": summary})
'''
    text = text.replace("\n\ndef main() -> None:\n", plan_code + "\n\ndef main() -> None:\n")

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
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_command(Path(args.bundles_dir), Path(args.output_path))
    else:
        plan_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))'''

text = text[:main_start] + new_main + text[main_end:]
path.write_text(text, encoding="utf-8")
path.chmod(0o755)
PY
python3 /app/tools/entitlement_audit.py plan /app/bundles /app/policy/signing-policy.json /app/out/entitlement-plan.json
