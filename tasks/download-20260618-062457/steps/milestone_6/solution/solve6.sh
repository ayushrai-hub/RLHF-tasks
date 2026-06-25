#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve5.sh"

python3 - <<'PY'
from pathlib import Path

path = Path("/app/tools/entitlement_audit.py")
text = path.read_text(encoding="utf-8")

if "def risk_register_command(" not in text:
    risk_code = '''

CAPABILITY_ORDER = ["push", "app_group", "associated_domain", "keychain"]
RISK_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CAPABILITY_MARKERS = {
    "push": ["registerForRemoteNotifications", "UNUserNotificationCenter"],
    "app_group": ["containerURLForSecurityApplicationGroupIdentifier", "initWithSuiteName"],
    "associated_domain": ["NSUserActivityTypeBrowsingWeb", "continueUserActivity"],
    "keychain": ["SecItemAdd", "SecItemCopyMatching"],
}


def source_files(bundle_dir: Path) -> list[Path]:
    files: list[Path] = []
    for suffix in ("*.m", "*.mm", "*.h"):
        files.extend(bundle_dir.glob(suffix))
    return sorted(files, key=lambda item: str(item.relative_to(bundle_dir)))


def scan_source_usage(bundle_dir: Path) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    matched_files: set[str] = set()
    for source_path in source_files(bundle_dir):
        rel = str(source_path.relative_to(bundle_dir))
        try:
            lines = source_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for capability in CAPABILITY_ORDER:
                for marker in CAPABILITY_MARKERS[capability]:
                    if marker in line:
                        matched_files.add(rel)
                        evidence.append(
                            {
                                "capability": capability,
                                "file": rel,
                                "line": line_no,
                                "marker": marker,
                            }
                        )
    evidence.sort(key=lambda row: (CAPABILITY_ORDER.index(row["capability"]), row["file"], row["line"], row["marker"]))
    capabilities = [capability for capability in CAPABILITY_ORDER if any(row["capability"] == capability for row in evidence)]
    return capabilities, sorted(matched_files), evidence


def missing_runtime_support(capabilities: list[str], current: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if "push" in capabilities and current["aps_environment"] is None:
        missing.append("push")
    if "app_group" in capabilities and not current["app_groups"]:
        missing.append("app_group")
    if "associated_domain" in capabilities and not current["associated_domains"]:
        missing.append("associated_domain")
    if "keychain" in capabilities and not current.get("keychain_groups", []):
        missing.append("keychain")
    return missing


def risk_level(status: str, capabilities: list[str], missing: list[str]) -> str:
    if missing or (status == "blocked" and capabilities):
        return "critical"
    if status == "drift" and capabilities:
        return "high"
    if status in {"blocked", "drift"}:
        return "medium"
    return "low"


def risk_register_command(bundles_dir: Path, policy_path: Path, output_path: Path) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    inventory = build_inventory(bundles_dir)
    actions = {row["bundle_id"]: classify(row, policy) for row in inventory["bundles"]}
    risks: list[dict[str, Any]] = []
    source_index: dict[str, list[str]] = {capability: [] for capability in CAPABILITY_ORDER}
    for row in inventory["bundles"]:
        action = actions[row["bundle_id"]]
        verify = verify_row(row, action, policy)
        capabilities, files, evidence = scan_source_usage(Path(row["path"]))
        current = dict(verify["current"])
        current["keychain_groups"] = row["entitlements"]["keychain_groups"]
        missing = missing_runtime_support(capabilities, current)
        level = risk_level(verify["status"], capabilities, missing)
        for capability in capabilities:
            source_index[capability].append(row["bundle_id"])
        risks.append(
            {
                "bundle_id": row["bundle_id"],
                "status": verify["status"],
                "risk_level": level,
                "capabilities_used": capabilities,
                "missing_runtime_support": missing,
                "policy_conflicts": action["reasons"],
                "remediation_required": verify["status"] != "compliant" or bool(missing),
                "source_files": files,
                "evidence": evidence,
            }
        )
    risks.sort(key=lambda row: (RISK_PRIORITY[row["risk_level"]], row["bundle_id"]))
    by_risk_level = {level: 0 for level in RISK_PRIORITY}
    by_status = {"blocked": 0, "drift": 0, "compliant": 0}
    for row in risks:
        by_risk_level[row["risk_level"]] += 1
        by_status[row["status"]] += 1
    summary = {
        "total": len(risks),
        "by_risk_level": by_risk_level,
        "by_status": by_status,
        "bundles_with_source_usage": sum(bool(row["capabilities_used"]) for row in risks),
        "missing_runtime_support_count": sum(len(row["missing_runtime_support"]) for row in risks),
        "policy_conflict_count": sum(len(row["policy_conflicts"]) for row in risks),
    }
    source_index = {capability: sorted(bundle_ids) for capability, bundle_ids in source_index.items()}
    write_json(output_path, {"risks": risks, "summary": summary, "source_index": source_index})
'''
    text = text.replace("\n\ndef main() -> None:\n", risk_code + "\n\ndef main() -> None:\n")

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
    risk = subparsers.add_parser("risk-register")
    risk.add_argument("bundles_dir")
    risk.add_argument("policy_path")
    risk.add_argument("output_path")
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_command(Path(args.bundles_dir), Path(args.output_path))
    elif args.command == "plan":
        plan_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    elif args.command == "remediate":
        remediate_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    elif args.command == "apply-remediation":
        apply_remediation_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    elif args.command == "verify-remediation":
        verify_remediation_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))
    else:
        risk_register_command(Path(args.bundles_dir), Path(args.policy_path), Path(args.output_path))'''

text = text[:main_start] + new_main + text[main_end:]
path.write_text(text, encoding="utf-8")
path.chmod(0o755)
PY

python3 /app/tools/entitlement_audit.py risk-register /app/bundles /app/policy/signing-policy.json /app/out/entitlement-risk-register.json
