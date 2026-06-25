"""Independent reference decoder/solver for the quest-capsule-decoder verifier.

Recomputes the expected header, room graph, and winning runs directly from the cartridge,
so tests can compare the agent's CLI output against an authority that does not read the
agent's code. Mirrors the documented QuestCapsule format.
"""
import base64
import json
import os
import sqlite3

APP_DIR = os.environ.get("QCAP_APP_DIR", "/app")
CART_DIR = os.path.join(APP_DIR, "cartridges")
CHK_MOD = 9973


def _db():
    # Resolve the cartridge named by any spec (they all share one db).
    for fn in os.listdir(CART_DIR):
        if fn.endswith(".qcap.json"):
            spec = json.load(open(os.path.join(CART_DIR, fn)))
            return os.path.join(CART_DIR, spec["cartridge"])
    raise RuntimeError("no capsule spec found")


def capsules():
    out = []
    for fn in sorted(os.listdir(CART_DIR)):
        if fn.endswith(".qcap.json"):
            out.append(fn[:-len(".qcap.json")])
    return out


def _conn():
    con = sqlite3.connect(_db())
    con.row_factory = sqlite3.Row
    return con


def glyph_map(con, table_id):
    rows = con.execute("SELECT code, plain FROM glyphs WHERE table_id = ?", (table_id,)).fetchall()
    return {r["code"]: r["plain"] for r in rows}


def decode(payload, gmap):
    if payload is None:
        return None
    if len(payload) % 2 != 0:
        raise ValueError("odd-length glyph payload: %r" % payload)
    out = []
    for i in range(0, len(payload), 2):
        code = payload[i:i + 2]
        if code not in gmap:
            raise ValueError("unknown glyph code: %r" % code)
        out.append(gmap[code])
    return "".join(out)


def spec_header_b64(capsule):
    spec = json.load(open(os.path.join(CART_DIR, capsule + ".qcap.json")))
    return spec["header"]


def parse_header(capsule):
    b64 = spec_header_b64(capsule)
    rec = base64.b64decode(b64).decode()
    fields = {}
    for part in rec.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    g = int(fields["g"])
    con = _conn()
    gmap = glyph_map(con, g)
    con.close()
    entry = int(decode(fields["e"], gmap))
    room_count = int(decode(fields["n"], gmap))
    seed_base = int(decode(fields["s"], gmap))
    checksum = int(decode(fields["k"], gmap))
    computed = (entry + room_count + seed_base) % CHK_MOD
    return {
        "capsule": capsule,
        "entry": entry,
        "room_count": room_count,
        "glyph_table": g,
        "seed_base": seed_base,
        "checksum": checksum,
        "checksum_ok": checksum == computed,
    }


def build_graph(capsule):
    h = parse_header(capsule)
    g = h["glyph_table"]
    con = _conn()
    gmap = glyph_map(con, g)
    rooms = []
    for r in con.execute(
        "SELECT room_id, kind, title_glyph, body_glyph FROM rooms WHERE capsule = ? ORDER BY room_id",
        (capsule,),
    ).fetchall():
        rid = r["room_id"]
        exits = []
        for e in con.execute(
            "SELECT from_room, label_glyph, to_room, guard_glyph FROM edges WHERE capsule = ? AND from_room = ?",
            (capsule, rid),
        ).fetchall():
            guard = decode(e["guard_glyph"], gmap) if e["guard_glyph"] is not None else None
            exits.append({"label": decode(e["label_glyph"], gmap), "to": e["to_room"], "guard": guard})
        exits.sort(key=lambda x: (x["label"], x["to"]))
        rooms.append({
            "id": rid,
            "kind": r["kind"],
            "title": decode(r["title_glyph"], gmap),
            "body": decode(r["body_glyph"], gmap),
            "exits": exits,
        })
    con.close()
    return {"capsule": capsule, "entry": h["entry"], "rooms": rooms}


def _grants(body):
    toks = []
    for part in body.split("."):
        part = part.strip()
        if part.startswith("grant "):
            toks.append(part[len("grant "):].strip())
    return toks


def solve_run(graph, seed_value):
    rooms = {r["id"]: r for r in graph["rooms"]}
    exit_id = next(r["id"] for r in graph["rooms"] if r["kind"] == "exit")
    entry = graph["entry"]

    def dfs(room, visited, inv):
        inv2 = set(inv) | set(_grants(rooms[room]["body"]))
        if room == exit_id:
            return []
        cand = [e for e in rooms[room]["exits"]
                if e["to"] not in visited and (e["guard"] is None or e["guard"] in inv2)]
        cand.sort(key=lambda e: (e["label"], e["to"]))
        if not cand:
            return None
        k = len(cand)
        start = seed_value % k
        order = cand[start:] + cand[:start]
        for e in order:
            res = dfs(e["to"], visited | {e["to"]}, inv2)
            if res is not None:
                return [{"label": e["label"], "to": e["to"]}] + res
        return None

    return dfs(entry, {entry}, set())


def run_text(graph, steps):
    rooms = {r["id"]: r for r in graph["rooms"]}
    lines = [rooms[graph["entry"]]["title"]]
    for s in steps:
        lines.append("%s -> %s" % (s["label"], rooms[s["to"]]["title"]))
    return "\n".join(lines) + "\n"


def seeds(capsule):
    con = _conn()
    rows = con.execute(
        "SELECT seed_id, seed_value FROM seeds WHERE capsule = ? ORDER BY seed_id", (capsule,)
    ).fetchall()
    con.close()
    return [{"seed_id": r["seed_id"], "seed_value": r["seed_value"]} for r in rows]
