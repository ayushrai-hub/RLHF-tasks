"""Independent reference implementation of the Relic Vault migration + expedition.

This module is the ground truth used by the milestone verifiers. It reads the
raw mixed archive, reproduces the canonical schema report, the migrated
``vault.pack`` binary image, and the scripted expedition transcript -- using only
the Python standard library plus ``polars`` for reading the parquet asset.

Nothing here trusts the agent's harness; every artifact is recomputed from the
raw archive (or, for the expedition, from a freshly parsed pack image).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import struct
from pathlib import Path

# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_CAMEL_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_2 = re.compile(r"([a-z0-9])([A-Z])")


def to_snake(name: str) -> str:
    """Convert a PascalCase / camelCase identifier to snake_case."""
    s1 = _CAMEL_1.sub(r"\1_\2", name)
    s2 = _CAMEL_2.sub(r"\1_\2", s1)
    return s2.replace("__", "_").lower()


def _coerce(value):
    """Integer-typed if the value is a whole number, else a stripped string."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return str(value)
    s = str(value).strip()
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


# ---------------------------------------------------------------------------
# Archive readers -> normalised tables (list[dict] with snake_case keys)
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row = {to_snake(k): _coerce(v) for k, v in raw.items()}
            rows.append(row)
    return rows


def _read_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [{to_snake(k): _coerce(v) for k, v in obj.items()} for obj in data]


def _read_parquet(path: Path) -> list[dict]:
    import polars as pl  # runtime dependency, present in the image

    frame = pl.read_parquet(path)
    rows: list[dict] = []
    for raw in frame.to_dicts():
        rows.append({to_snake(k): _coerce(v) for k, v in raw.items()})
    return rows


def _read_tiles(tiles_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for tile_path in tiles_dir.glob("room_*.txt"):
        room_id = int(tile_path.stem.split("_")[1])
        hazard = tile_path.read_text(encoding="utf-8").count("^")
        rows.append({"room_id": room_id, "hazard_count": hazard})
    return rows


def synthetic_tables() -> dict[str, list[dict]]:
    """A disjoint synthetic dataset (different ids/names/values from the real
    archive) used to drive the agent's harness and engine on unseen data so a
    hardcoded answer cannot pass. Exercises every biome, a chamber with no
    guardian, a chamber with no relic, and a range of hazard counts."""
    # Rooms 73 and 74 share depth 4 -> exercises the Rule II.0 tie-break
    # (room_id descending: 74 takes the earlier chamber_index, then 73) on data
    # the agent never saw.
    rooms = [
        {"room_id": 70, "name": "Cobalt Stair",   "depth": 3, "biome": "vault"},
        {"room_id": 71, "name": "Brine Cells",     "depth": 1, "biome": "mire"},
        {"room_id": 72, "name": "Emberforge",      "depth": 2, "biome": "forge"},
        {"room_id": 73, "name": "Pale Reliquary",  "depth": 4, "biome": "crypt"},
        {"room_id": 74, "name": "Drowned Sept",    "depth": 4, "biome": "mire"},
    ]
    # Rooms 71 and 70 list a SECOND, weaker candidate guardian (superseded by the
    # Rule II.3 highest-base_hp selection, so the chosen guardian -- and every
    # chamber -- is unchanged); monster 57 is an ORPHAN (room 88 is not a chamber).
    # The consulted manifest must include 55/56 (examined, superseded) but NOT 57.
    monsters = [
        {"monster_id": 50, "room_id": 71, "species": "nixie",     "base_hp": 5,  "base_atk": 2},
        {"monster_id": 51, "room_id": 72, "species": "slagling",  "base_hp": 8,  "base_atk": 1},
        {"monster_id": 52, "room_id": 70, "species": "cobaltine", "base_hp": 6,  "base_atk": 3},
        {"monster_id": 53, "room_id": 74, "species": "drudge",    "base_hp": 30, "base_atk": 9},
        {"monster_id": 55, "room_id": 71, "species": "nix-fry",   "base_hp": 2,  "base_atk": 1},
        {"monster_id": 56, "room_id": 70, "species": "cobalt-chip","base_hp": 3, "base_atk": 1},
        {"monster_id": 57, "room_id": 88, "species": "stray",     "base_hp": 80, "base_atk": 9},
    ]  # room 73 has no guardian; 57 is an orphan
    relics = [
        {"relic_id": 200, "room_id": 71, "name": "Tideglass",  "base_value": 20, "sigil": "E"},
        {"relic_id": 201, "room_id": 70, "name": "Cobalt Eye", "base_value": 35, "sigil": "A"},
        {"relic_id": 202, "room_id": 73, "name": "Pale Lily",  "base_value": 25, "sigil": "C"},
        {"relic_id": 203, "room_id": 74, "name": "Sept Bell",  "base_value": 15, "sigil": "B"},
        {"relic_id": 210, "room_id": 71, "name": "Tide-shard", "base_value": 5,  "sigil": "C"},
        {"relic_id": 211, "room_id": 89, "name": "Orphan Gem", "base_value": 50, "sigil": "A"},
    ]  # room 72 has no relic; relic 210 is superseded; 211 is an orphan
    tiles = [
        {"room_id": 70, "hazard_count": 1},
        {"room_id": 71, "hazard_count": 0},
        {"room_id": 72, "hazard_count": 2},
        {"room_id": 73, "hazard_count": 0},
        {"room_id": 74, "hazard_count": 4},
    ]
    return {"rooms": rooms, "monsters": monsters, "relics": relics, "tiles": tiles}


def read_archive(archive_dir: str | Path) -> dict[str, list[dict]]:
    """Read every source in the mixed archive into normalised tables."""
    base = Path(archive_dir)
    return {
        "rooms": _read_csv(base / "rooms.csv"),
        "monsters": _read_parquet(base / "monsters.parquet"),
        "relics": _read_json(base / "relics.json"),
        "tiles": _read_tiles(base / "tiles"),
    }


def write_archive(archive_dir: str | Path, tables: dict[str, list[dict]]) -> None:
    """Materialise a mixed archive on disk from normalised tables.

    Used by the verifier to drive the agent's harness against disjoint
    synthetic data (anti-hardcode). The on-disk shapes mirror the real
    archive: PascalCase CSV headers, camelCase JSON keys, a parquet monster
    table, and one tile map per room.
    """
    import polars as pl

    base = Path(archive_dir)
    (base / "tiles").mkdir(parents=True, exist_ok=True)

    with (base / "rooms.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["RoomId", "Name", "Depth", "Biome"])
        for r in tables["rooms"]:
            writer.writerow([r["room_id"], r["name"], r["depth"], r["biome"]])

    relics = [
        {
            "relicId": r["relic_id"],
            "roomId": r["room_id"],
            "name": r["name"],
            "baseValue": r["base_value"],
            "sigil": r["sigil"],
        }
        for r in tables["relics"]
    ]
    (base / "relics.json").write_text(json.dumps(relics, indent=2), encoding="utf-8")

    pl.DataFrame(
        tables["monsters"],
        schema=["monster_id", "room_id", "species", "base_hp", "base_atk"],
    ).write_parquet(base / "monsters.parquet")

    for t in tables["tiles"]:
        # Spikes '^' are the only hazards (Rule I.3). The '~' (water) and '*'
        # (rubble) glyphs are decoys an over-eager counter must ignore.
        spikes = "^" * t["hazard_count"]
        body = (
            "#######\n"
            "#~*.*~#\n"
            "#" + spikes + "#\n"
            "#*~.~*#\n"
            "#######\n"
        )
        (base / "tiles" / f"room_{t['room_id']}.txt").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Milestone 1 -- canonical schema report
# ---------------------------------------------------------------------------

PRIMARY_KEY = {
    "rooms": "room_id",
    "monsters": "monster_id",
    "relics": "relic_id",
    "tiles": "room_id",
}


def _column_dtype(rows: list[dict], column: str) -> str:
    # Appendix I Rule I.2: catalogue identifiers (columns whose normalised name
    # ends in "_id") are always "str", even when every value is a whole number.
    if column.endswith("_id"):
        return "str"
    return "int" if all(isinstance(r[column], int) for r in rows) else "str"


def _fingerprint(rows: list[dict], columns: list[str], pkey: str) -> str:
    # Appendix I Rule I.4: rows are ordered by primary key, but the primary-key
    # column is OMITTED from each rendered row string (it orders, never hashes).
    ordered = sorted(rows, key=lambda r: r[pkey])
    lines = []
    for row in ordered:
        cells = [f"{col}={row[col]}" for col in columns if col != pkey]
        lines.append("|".join(cells))
    blob = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def schema_entry(rows: list[dict], pkey: str) -> dict:
    columns = sorted(rows[0].keys())
    dtypes = [_column_dtype(rows, col) for col in columns]
    return {
        "columns": columns,
        "dtypes": dtypes,
        "row_count": len(rows),
        "fingerprint": _fingerprint(rows, columns, pkey),
    }


def schema_report_bytes(tables: dict[str, list[dict]]) -> bytes:
    report = {
        name: schema_entry(rows, PRIMARY_KEY[name])
        for name, rows in tables.items()
    }
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    return text.encode("utf-8")


# ---------------------------------------------------------------------------
# Milestone 2 -- migrated vault.pack image
# ---------------------------------------------------------------------------

BIOME_CODE = {"crypt": 0, "forge": 1, "mire": 2, "vault": 3}
# biome -> (hp_bonus, atk_bonus, worth_mult)
BIOME_RULES = {
    "crypt": (3, 0, 1),
    "forge": (0, 2, 2),
    "mire": (5, 1, 1),
    "vault": (1, 1, 3),
}
SIGIL_NONE = "-"

PACK_MAGIC = b"RVP1"
PACK_FOOTER = b"RVPE"
NAME_WIDTH = 24
SPECIES_WIDTH = 16
RECORD = struct.Struct("<HHhhhBBc24s16s")


def _index_by(rows: list[dict], key: str) -> dict:
    return {row[key]: row for row in rows}


def _group_by_room(rows: list[dict]) -> dict:
    """Group candidate records by room_id (a room may have several candidates)."""
    by_room: dict = {}
    for row in rows:
        by_room.setdefault(row["room_id"], []).append(row)
    return by_room


def _select(candidates: list[dict], rank_key: str, id_key: str):
    """Rule II.3 selection: the candidate with the highest ``rank_key``; ties are
    broken by the lowest ``id_key``. Returns None if there are no candidates."""
    if not candidates:
        return None
    return min(candidates, key=lambda r: (-r[rank_key], r[id_key]))


def build_chambers(tables: dict[str, list[dict]]) -> list[dict]:
    monsters = _group_by_room(tables["monsters"])
    relics = _group_by_room(tables["relics"])
    hazards = {r["room_id"]: r["hazard_count"] for r in tables["tiles"]}

    # Appendix II Rule II.0: order by depth ascending; ties broken by room_id
    # DESCENDING (the higher-numbered room takes the earlier chamber_index).
    rooms = sorted(tables["rooms"], key=lambda r: (r["depth"], -r["room_id"]))
    chambers = []
    for index, room in enumerate(rooms):
        rid = room["room_id"]
        biome = room["biome"]
        hp_bonus, atk_bonus, worth_mult = BIOME_RULES[biome]
        hazard = hazards.get(rid, 0)

        # Rule II.3: a room may list several candidate guardians/relics; select
        # the strongest (highest base_hp / base_value, tie-break lowest id).
        mon = _select(monsters.get(rid, []), "base_hp", "monster_id")
        if mon is not None:
            # Rule II.1: spikes raise both hit points (2 each) and attack
            # (one per full pair, floor division).
            guard_hp = mon["base_hp"] + hp_bonus + 2 * hazard
            guard_atk = mon["base_atk"] + atk_bonus + (hazard // 2)
            species = mon["species"]
        else:
            guard_hp = 0
            guard_atk = 0
            species = "none"

        rel = _select(relics.get(rid, []), "base_value", "relic_id")
        if rel is not None:
            # Rule II.2: the hazard penalty is subtracted from base_value FIRST,
            # then the biome multiplier is applied to that reduced value.
            relic_worth = max(0, (rel["base_value"] - hazard) * worth_mult)
            sigil = rel["sigil"]
        else:
            relic_worth = 0
            sigil = SIGIL_NONE

        chambers.append(
            {
                "room_id": rid,
                "chamber_index": index,
                "name": room["name"],
                "biome": biome,
                "biome_code": BIOME_CODE[biome],
                "sigil": sigil,
                "hazard": hazard,
                "guard_hp": guard_hp,
                "guard_atk": guard_atk,
                "relic_worth": relic_worth,
                "species": species,
            }
        )
    return chambers


def consulted_manifest_bytes(tables: dict[str, list[dict]]) -> bytes:
    """Appendix V -- the migration's *consulted scope* audit (/app/out/consulted.json).

    Records EVERY guardian-candidate and relic-candidate the migration EXAMINED
    while deriving chambers: a candidate is examined iff its ``room_id`` is the
    room of some chamber. This INCLUDES candidates that were examined but not
    selected (superseded by a higher-ranked candidate for the same room); it
    EXCLUDES orphan candidates whose ``room_id`` matches no chamber (those are
    never examined). It is NOT the set of selected guardians/relics.
    """
    chamber_rooms = {room["room_id"] for room in tables["rooms"]}
    guardians = sorted(
        m["monster_id"] for m in tables["monsters"] if m["room_id"] in chamber_rooms
    )
    relics = sorted(
        r["relic_id"] for r in tables["relics"] if r["room_id"] in chamber_rooms
    )
    manifest = {"guardians_consulted": guardians, "relics_consulted": relics}
    return (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _fixed(text: str, width: int) -> bytes:
    raw = text.encode("ascii", "replace")[:width]
    return raw + b"\x00" * (width - len(raw))


def pack_bytes(chambers: list[dict]) -> bytes:
    out = bytearray()
    out += PACK_MAGIC
    out += struct.pack("<I", len(chambers))
    for ch in chambers:
        out += RECORD.pack(
            ch["room_id"],
            ch["chamber_index"],
            ch["guard_hp"],
            ch["guard_atk"],
            ch["relic_worth"],
            ch["hazard"],
            ch["biome_code"],
            ch["sigil"].encode("ascii")[:1],
            _fixed(ch["name"], NAME_WIDTH),
            _fixed(ch["species"], SPECIES_WIDTH),
        )
    out += PACK_FOOTER
    return bytes(out)


def parse_pack(data: bytes) -> list[dict]:
    if data[:4] != PACK_MAGIC:
        raise ValueError("bad magic")
    (count,) = struct.unpack_from("<I", data, 4)
    offset = 8
    chambers = []
    for _ in range(count):
        fields = RECORD.unpack_from(data, offset)
        offset += RECORD.size
        (rid, idx, ghp, gatk, worth, hazard, biome_code, sigil, name, species) = fields
        chambers.append(
            {
                "room_id": rid,
                "chamber_index": idx,
                "guard_hp": ghp,
                "guard_atk": gatk,
                "relic_worth": worth,
                "hazard": hazard,
                "biome_code": biome_code,
                "sigil": sigil.decode("ascii"),
                "name": name.split(b"\x00")[0].decode("ascii"),
                "species": species.split(b"\x00")[0].decode("ascii"),
            }
        )
    if data[offset:offset + 4] != PACK_FOOTER:
        raise ValueError("bad footer")
    return chambers


# ---------------------------------------------------------------------------
# Milestone 3 -- scripted expedition transcript
# ---------------------------------------------------------------------------

START_HP = 25
START_ATK = 4
HP_CAP = 25
BRACE_HEAL = 3


def _step_line(turn, action, pos, hp, atk, score, event) -> str:
    return (
        f"{turn:03d} {action:<7} pos={pos:+03d} hp={hp:03d} "
        f"atk={atk:02d} score={score:05d} | {event}"
    )


def simulate(chambers: list[dict], script: list[str]) -> bytes:
    count = len(chambers)
    guard_rem = [ch["guard_hp"] for ch in chambers]
    hp, atk, score, pos = START_HP, START_ATK, 0, -1
    max_pos = -1
    streak = 0
    taken: set[int] = set()
    lines: list[str] = []
    downed = False

    turn = 0
    for raw in script:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        action = stripped.upper()
        turn += 1
        event = "IDLE"

        if action == "ADVANCE":
            if pos < count - 1:
                pos += 1
                max_pos = max(max_pos, pos)
                event = "enter " + chambers[pos]["name"]
            else:
                event = "EDGE"
        elif action == "STRIKE":
            if 0 <= pos < count and guard_rem[pos] > 0:
                guard_rem[pos] -= atk
                if guard_rem[pos] > 0:
                    dmg = chambers[pos]["guard_atk"]
                    hp -= dmg
                    if hp <= 0:
                        # Downing blow: hp pinned at 0, atk left unchanged.
                        hp = 0
                        downed = True
                        event = f"DOWNED -{dmg}"
                    else:
                        # Survived wound: lose battle momentum, atk -1 floored
                        # at the starting value of 4.
                        atk = max(START_ATK, atk - 1)
                        event = f"TRADE -{dmg}"
                else:
                    # Slain: atk ratchets up by 1.
                    atk += 1
                    event = "SLAIN"
            else:
                event = "EMPTY"
        elif action == "GRAB":
            if (
                0 <= pos < count
                and guard_rem[pos] <= 0
                and chambers[pos]["relic_worth"] > 0
                and pos not in taken
            ):
                worth = chambers[pos]["relic_worth"]
                score += worth
                taken.add(pos)
                event = f"CLAIM +{worth}"
            else:
                event = "WARDED"
        elif action == "BRACE":
            heal = min(HP_CAP, hp + BRACE_HEAL) - hp
            hp += heal
            event = f"BRACE +{heal}"
        else:
            event = "IDLE"

        # Kill-streak / slayer's tithe (Appendix IV): a SLAIN extends the streak
        # and pays the NEW streak value into the score; any other event resets the
        # streak to 0. (Because a kill is always preceded by a non-SLAIN action —
        # an ADVANCE into the chamber or a TRADE on the guardian — the streak is
        # always 1 at the moment of a slaying; the obvious "accumulate across
        # chambers" reading over-scores.)
        if event == "SLAIN":
            streak += 1
            score += streak
        else:
            streak = 0

        lines.append(_step_line(turn, action, pos, hp, atk, score, event))
        if downed:
            break

    cleared = sum(
        1 for i in range(count) if i <= max_pos and guard_rem[i] <= 0
    )
    status = "DOWNED" if downed else "ALIVE"
    lines.append(
        f"RESULT status={status} hp={hp:03d} atk={atk:02d} "
        f"score={score:05d} cleared={cleared:02d} turns={turn:03d}"
    )
    return ("\n".join(lines) + "\n").encode("ascii")
