from __future__ import annotations

import argparse

def normalize_command(args: argparse.Namespace) -> int:
    raise NotImplementedError("normalize command is not implemented yet")


def plan_command(args: argparse.Namespace) -> int:
    raise NotImplementedError("plan command is not implemented yet")


def actions_command(args: argparse.Namespace) -> int:
    raise NotImplementedError("actions command is not implemented yet")


def audit_command(args: argparse.Namespace) -> int:
    raise NotImplementedError("audit command is not implemented yet")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clinicflow")
    sub = parser.add_subparsers(dest="command", required=True)

    normalize = sub.add_parser("normalize")
    normalize.add_argument("--input", default="/app/data/appointments.csv")
    normalize.add_argument("--rules", default="/app/data/service_rules.json")
    normalize.add_argument("--output", default="/app/output/m1_clean.json")
    normalize.set_defaults(func=normalize_command)

    plan = sub.add_parser("plan")
    plan.add_argument("--clean", default="/app/output/m1_clean.json")
    plan.add_argument("--rules", default="/app/data/service_rules.json")
    plan.add_argument("--output", default="/app/output/m2_plan.json")
    plan.set_defaults(func=plan_command)

    actions = sub.add_parser("actions")
    actions.add_argument("--plan", default="/app/output/m2_plan.json")
    actions.add_argument("--rules", default="/app/data/service_rules.json")
    actions.add_argument("--output", default="/app/output/m3_actions.json")
    actions.set_defaults(func=actions_command)

    audit = sub.add_parser("audit")
    audit.add_argument("--clean", default="/app/output/m1_clean.json")
    audit.add_argument("--plan", default="/app/output/m2_plan.json")
    audit.add_argument("--actions", default="/app/output/m3_actions.json")
    audit.add_argument("--rules", default="/app/data/service_rules.json")
    audit.add_argument("--policy", default="/app/data/review_policy.json")
    audit.add_argument("--output", default="/app/output/m4_audit.json")
    audit.set_defaults(func=audit_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except NotImplementedError as exc:
        print(str(exc))
        return 2
