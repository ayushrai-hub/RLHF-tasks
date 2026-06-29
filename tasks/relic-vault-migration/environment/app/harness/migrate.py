#!/usr/bin/env python3
"""Relic Vault archive migration harness (PARTIALLY IMPLEMENTED).

This harness normalises the mixed season-archive and emits two artifacts:

    python migrate.py schema --archive <dir> --out <dir>   ->  <out>/schema_report.json
    python migrate.py pack   --archive <dir> --out <dir>   ->  <out>/vault.pack

The reading/normalisation scaffolding is in place, but the schema report and the
binary pack writer are unfinished. Recover the exact rules from
/app/docs/chronicle.md (Appendices I-III) and complete the TODOs below.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import polars as pl

_C1 = re.compile(r"(.)([A-Z][a-z]+)")
_C2 = re.compile(r"([a-z0-9])([A-Z])")


def to_snake(name: str) -> str:
    s1 = _C1.sub(r"\1_\2", name)
    s2 = _C2.sub(r"\1_\2", s1)
    return s2.replace("__", "_").lower()


def _normalise(df: pl.DataFrame) -> list[dict]:
    df = df.rename({c: to_snake(c) for c in df.columns})
    return df.to_dicts()


def read_tables(archive: str | Path) -> dict[str, list[dict]]:
    base = Path(archive)
    rooms = _normalise(pl.read_csv(base / "rooms.csv"))
    monsters = _normalise(pl.read_parquet(base / "monsters.parquet"))
    relics = _normalise(pl.read_json(base / "relics.json"))
    # TODO: the tiles/ directory still needs to be normalised into a
    #       {room_id, hazard_count} table (see Appendix I, Rule I.3).
    tiles: list[dict] = []
    return {"rooms": rooms, "monsters": monsters, "relics": relics, "tiles": tiles}


def write_schema(archive, out):
    tables = read_tables(archive)
    # TODO: build the canonical schema report (columns, dtypes, row_count,
    #       fingerprint) per Appendix I and write <out>/schema_report.json.
    raise NotImplementedError(
        f"schema report for {len(tables)} tables not implemented yet"
    )


def write_pack(archive, out):
    tables = read_tables(archive)
    # TODO: derive the chambers (Appendix II) and serialise vault.pack in the
    #       binder's binary format (Appendix III).
    raise NotImplementedError(
        f"vault.pack writer for {len(tables)} tables not implemented yet"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Relic Vault migration harness")
    parser.add_argument("command", choices=["schema", "pack"])
    parser.add_argument("--archive", default="/app/archive")
    parser.add_argument("--out", default="/app/out")
    args = parser.parse_args(argv)
    if args.command == "schema":
        print(write_schema(args.archive, args.out))
    else:
        print(write_pack(args.archive, args.out))


if __name__ == "__main__":
    main()
