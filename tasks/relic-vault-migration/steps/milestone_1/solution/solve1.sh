#!/bin/bash
# Milestone 1 -- Decode Archive Schema.
# Completes the Polars migration harness, then emits the canonical schema report.
set -euo pipefail
mkdir -p /app/out

cat > /app/harness/migrate.py <<'MIGRATE_PY_EOF'
#!/usr/bin/env python3
"""Relic Vault archive migration harness.

Normalises the mixed season-archive (parquet / CSV / JSON / tile assets) with
Polars and emits two artifacts:

    python migrate.py schema --archive <dir> --out <dir>   ->  <out>/schema_report.json
    python migrate.py pack   --archive <dir> --out <dir>   ->  <out>/vault.pack

The rules are recovered from /app/docs/chronicle.md (Appendices I-III).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

import polars as pl

# --- normalisation ----------------------------------------------------------

_C1 = re.compile(r"(.)([A-Z][a-z]+)")
_C2 = re.compile(r"([a-z0-9])([A-Z])")


def to_snake(name: str) -> str:
    s1 = _C1.sub(r"\1_\2", name)
    s2 = _C2.sub(r"\1_\2", s1)
    return s2.replace("__", "_").lower()


def _coerce(value):
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value) if value.is_integer() else str(value)
    s = str(value).strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else s


def _normalise(df: pl.DataFrame) -> list[dict]:
    df = df.rename({c: to_snake(c) for c in df.columns})
    return [{k: _coerce(v) for k, v in row.items()} for row in df.to_dicts()]


def read_tables(archive: str | Path) -> dict[str, list[dict]]:
    base = Path(archive)
    rooms = _normalise(pl.read_csv(base / "rooms.csv"))
    monsters = _normalise(pl.read_parquet(base / "monsters.parquet"))
    relics = _normalise(pl.read_json(base / "relics.json"))
    tiles = []
    for tile in sorted((base / "tiles").glob("room_*.txt")):
        room_id = int(tile.stem.split("_")[1])
        hazard = tile.read_text(encoding="utf-8").count("^")
        tiles.append({"room_id": room_id, "hazard_count": hazard})
    return {"rooms": rooms, "monsters": monsters, "relics": relics, "tiles": tiles}


# --- milestone 1: schema report ---------------------------------------------

PRIMARY_KEY = {"rooms": "room_id", "monsters": "monster_id",
               "relics": "relic_id", "tiles": "room_id"}


def _dtype(rows, column):
    # Rule I.2: catalogue identifiers (name ends in "_id") are always "str".
    if column.endswith("_id"):
        return "str"
    return "int" if all(isinstance(r[column], int) for r in rows) else "str"


def _fingerprint(rows, columns, pkey):
    # Rule I.4: omit the primary-key column from each rendered row (it only
    # orders the rows; it is never hashed).
    lines = []
    for row in sorted(rows, key=lambda r: r[pkey]):
        lines.append("|".join(f"{c}={row[c]}" for c in columns if c != pkey))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def schema_report(tables) -> dict:
    report = {}
    for name, rows in tables.items():
        columns = sorted(rows[0].keys())
        dtypes = [_dtype(rows, c) for c in columns]
        report[name] = {
            "columns": columns,
            "dtypes": dtypes,
            "row_count": len(rows),
            "fingerprint": _fingerprint(rows, columns, PRIMARY_KEY[name]),
        }
    return report


def write_schema(archive, out):
    tables = read_tables(archive)
    report = schema_report(tables)
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    dest = Path(out) / "schema_report.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


# --- milestone 2: vault.pack ------------------------------------------------

BIOME_CODE = {"crypt": 0, "forge": 1, "mire": 2, "vault": 3}
BIOME_RULES = {"crypt": (3, 0, 1), "forge": (0, 2, 2),
               "mire": (5, 1, 1), "vault": (1, 1, 3)}
NAME_WIDTH = 24
SPECIES_WIDTH = 16
RECORD = struct.Struct("<HHhhhBBc24s16s")


def _group_by_room(rows):
    by_room = {}
    for row in rows:
        by_room.setdefault(row["room_id"], []).append(row)
    return by_room


def _select(candidates, rank_key, id_key):
    # Rule II.3: highest rank_key wins; ties broken by lowest id_key.
    if not candidates:
        return None
    return min(candidates, key=lambda r: (-r[rank_key], r[id_key]))


def build_chambers(tables) -> list[dict]:
    monsters = _group_by_room(tables["monsters"])
    relics = _group_by_room(tables["relics"])
    hazards = {r["room_id"]: r["hazard_count"] for r in tables["tiles"]}
    chambers = []
    # Rule II.0: depth ascending, ties broken by room_id descending.
    ordered = sorted(tables["rooms"], key=lambda r: (r["depth"], -r["room_id"]))
    for index, room in enumerate(ordered):
        rid = room["room_id"]
        hp_bonus, atk_bonus, worth_mult = BIOME_RULES[room["biome"]]
        hazard = hazards.get(rid, 0)
        # Rule II.3: pick the strongest candidate guardian/relic for the room.
        mon = _select(monsters.get(rid, []), "base_hp", "monster_id")
        if mon is not None:
            # Rule II.1: spikes lend +2 hp each and +1 atk per full pair.
            guard_hp = mon["base_hp"] + hp_bonus + 2 * hazard
            guard_atk = mon["base_atk"] + atk_bonus + (hazard // 2)
            species = mon["species"]
        else:
            guard_hp = guard_atk = 0
            species = "none"
        rel = _select(relics.get(rid, []), "base_value", "relic_id")
        if rel is not None:
            # Rule II.2: subtract hazard from base_value FIRST, then multiply.
            relic_worth = max(0, (rel["base_value"] - hazard) * worth_mult)
            sigil = rel["sigil"]
        else:
            relic_worth = 0
            sigil = "-"
        chambers.append({
            "room_id": rid, "chamber_index": index, "name": room["name"],
            "biome_code": BIOME_CODE[room["biome"]], "sigil": sigil,
            "hazard": hazard, "guard_hp": guard_hp, "guard_atk": guard_atk,
            "relic_worth": relic_worth, "species": species,
        })
    return chambers


def _fixed(text, width):
    raw = text.encode("ascii", "replace")[:width]
    return raw + b"\x00" * (width - len(raw))


def pack_bytes(chambers) -> bytes:
    out = bytearray(b"RVP1")
    out += struct.pack("<I", len(chambers))
    for c in chambers:
        out += RECORD.pack(
            c["room_id"], c["chamber_index"], c["guard_hp"], c["guard_atk"],
            c["relic_worth"], c["hazard"], c["biome_code"],
            c["sigil"].encode("ascii")[:1], _fixed(c["name"], NAME_WIDTH),
            _fixed(c["species"], SPECIES_WIDTH),
        )
    out += b"RVPE"
    return bytes(out)


def consulted_manifest(tables) -> dict:
    # Appendix V: every guardian/relic candidate EXAMINED while deriving chambers
    # (selected AND superseded) -- i.e. every candidate whose room_id is a chamber
    # room. Orphan candidates (room_id matching no chamber) are excluded.
    chamber_rooms = {room["room_id"] for room in tables["rooms"]}
    return {
        "guardians_consulted": sorted(
            m["monster_id"] for m in tables["monsters"] if m["room_id"] in chamber_rooms
        ),
        "relics_consulted": sorted(
            r["relic_id"] for r in tables["relics"] if r["room_id"] in chamber_rooms
        ),
    }


def write_pack(archive, out):
    tables = read_tables(archive)
    chambers = build_chambers(tables)
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)
    dest = outdir / "vault.pack"
    dest.write_bytes(pack_bytes(chambers))
    manifest = json.dumps(consulted_manifest(tables), sort_keys=True, indent=2) + "\n"
    (outdir / "consulted.json").write_text(manifest, encoding="utf-8")
    return dest


# --- cli --------------------------------------------------------------------

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
MIGRATE_PY_EOF

python /app/harness/migrate.py schema --archive /app/archive --out /app/out
