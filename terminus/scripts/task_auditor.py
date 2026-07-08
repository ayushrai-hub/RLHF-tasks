#!/usr/bin/env python3
"""CLI entry point for the Terminus Edition 2 task quality auditor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from task_audit.auditor import TaskAuditor  # noqa: E402
from task_audit.report import format_json, format_markdown, portal_check_uncheck  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Terminus Edition 2 task quality audit (55-item checklist)",
    )
    parser.add_argument("task_dir", type=Path, help="Path to task directory")
    parser.add_argument("--report", type=Path, help="Submission export (entire-report.txt) for rubric/agent stats")
    parser.add_argument("--rubric", type=Path, help="Platform rubric file")
    parser.add_argument("-o", "--output", type=Path, help="Write audit report (default: <task-dir>/audit-report.md)")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    parser.add_argument("--stdout", action="store_true", help="Also print report to stdout")
    args = parser.parse_args()

    auditor = TaskAuditor(args.task_dir, report_path=args.report, rubric_path=args.rubric)
    report = auditor.run()

    output_path = args.output
    if output_path is None and not args.json:
        output_path = args.task_dir / "audit-report.md"

    md = format_markdown(report)
    if args.json:
        print(format_json(report))
    if output_path and not args.json:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
        print(f"Wrote audit report: {output_path}")

    if args.stdout or (args.json and not output_path):
        print(md)

    check, uncheck = portal_check_uncheck(report)
    if not args.json:
        print(f"\nVerdict: {report.verdict.value}")
        print(f"CHECK: {', '.join(str(i) for i in check) or 'none'}")
        print(f"UNCHECK: {', '.join(str(i) for i in uncheck) or 'none'}")

    exit_code = 0
    if report.verdict.value in ("REQUIRES CHANGES", "REJECTED"):
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
