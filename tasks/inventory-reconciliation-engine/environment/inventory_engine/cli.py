from __future__ import annotations

import argparse
from pathlib import Path

from inventory_engine.reconcile import run_reconciliation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inventory_engine")
    sub = parser.add_subparsers(dest="command", required=True)
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--events", type=Path, required=True)
    reconcile.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "reconcile":
        run_reconciliation(args.events, args.out)
