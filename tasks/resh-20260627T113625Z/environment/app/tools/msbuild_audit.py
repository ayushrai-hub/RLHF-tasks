#!/usr/bin/env python3
"""Audit MSBuild project metadata."""

import sys


def main() -> int:
    """Dispatch the MSBuild audit CLI."""
    if len(sys.argv) < 2 or sys.argv[1] not in {"inventory", "plan", "waves", "apply-plan", "verify-apply"}:
        print("usage: msbuild_audit.py inventory <src_root> <packages_props> <out_json> OR plan|waves|apply-plan|verify-apply <src_root> <packages_props> <policy_json> <out_json>", file=sys.stderr)
        return 2
    print("msbuild audit implementation is incomplete", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
