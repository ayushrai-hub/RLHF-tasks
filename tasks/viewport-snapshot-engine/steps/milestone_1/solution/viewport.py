#!/usr/bin/env python3
"""Viewport snapshot engine for a browser agent.

Usage: python3 /app/viewport.py <scenario.json> <output.json>

Reads a scenario {"milestone": N, "cases": [...]} and writes
{"answers": [...]} as canonical JSON (sorted keys, compact separators),
one answer per case. Standard library only; exact integer arithmetic.

The four milestones build on one another:
  1. resolve every node's absolute border box through the nested box model
  2. clip each node by its scrolling/overflow ancestors and the viewport
  3. assemble the ordered interactive snapshot records
  4. encode the records into a checksummed binary snapshot frame
"""
import hashlib
import json
import sys

CANDIDATE_TAGS = {"a", "button", "input", "select", "textarea"}


# --------------------------------------------------------------------------- #
# shared geometry helpers
# --------------------------------------------------------------------------- #
def _quad(node, key):
    """Return a 4-tuple top/right/bottom/left, defaulting to zeros."""
    v = node.get(key, [0, 0, 0, 0])
    return int(v[0]), int(v[1]), int(v[2]), int(v[3])


def _scroll(node):
    s = node.get("scroll", [0, 0])
    return int(s[0]), int(s[1])


def _intersect(a, b):
    """Half-open intersection of two [x, y, w, h] rectangles."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x = max(ax, bx)
    y = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    return [x, y, max(0, right - x), max(0, bottom - y)]


def _layout(case):
    """Pre-order walk returning, for each node, its absolute border box plus the
    bookkeeping the later stages need (parent, overflow, padding box)."""
    out = []

    def walk(node, parent, ox, oy):
        bx, by, bw, bh = (int(node["box"][0]), int(node["box"][1]),
                          int(node["box"][2]), int(node["box"][3]))
        x, y = ox + bx, oy + by
        bt, br, bb, bl = _quad(node, "border")
        pt, pr, pb, pl = _quad(node, "padding")
        sx, sy = _scroll(node)
        pad_box = [x + bl, y + bt, bw - bl - br, bh - bt - bb]
        idx = len(out)
        out.append({
            "id": node["id"],
            "tag": node.get("tag", ""),
            "attrs": node.get("attrs", {}),
            "text": node.get("text", ""),
            "border_box": [x, y, bw, bh],
            "pad_box": pad_box,
            "clips": node.get("overflow", "visible") == "clip",
            "parent": parent,
        })
        # content origin for children = padding-box top-left minus this node's scroll
        cox = x + bl + pl - sx
        coy = y + bt + pt - sy
        for child in node.get("children", []):
            walk(child, idx, cox, coy)
    walk(case["root"], -1, 0, 0)
    return out


# --------------------------------------------------------------------------- #
# milestone 1 - absolute border boxes
# --------------------------------------------------------------------------- #
def milestone_1(case):
    return {n["id"]: list(n["border_box"]) for n in _layout(case)}


# --------------------------------------------------------------------------- #
# milestone 2 - clip by ancestors + viewport
# --------------------------------------------------------------------------- #
def _clipped(case):
    nodes = _layout(case)
    vw, vh = int(case["viewport"][0]), int(case["viewport"][1])
    viewport = [0, 0, vw, vh]
    for n in nodes:
        clip = viewport
        anc = nodes[n["parent"]] if n["parent"] >= 0 else None
        while anc is not None:
            if anc["clips"]:
                clip = _intersect(clip, anc["pad_box"])
            anc = nodes[anc["parent"]] if anc["parent"] >= 0 else None
        vis = _intersect(n["border_box"], clip)
        n["visible"] = vis if vis[2] > 0 and vis[3] > 0 else [0, 0, 0, 0]
        n["onscreen"] = vis[2] > 0 and vis[3] > 0
    return nodes


def milestone_2(case):
    out = {}
    for n in _clipped(case):
        out[n["id"]] = {"onscreen": n["onscreen"], "rect": list(n["visible"])}
    return out


# --------------------------------------------------------------------------- #
# milestone 3 - ordered interactive snapshot records
# --------------------------------------------------------------------------- #
def _label(text):
    s = " ".join(str(text).split())
    return s[:50]


def _is_candidate(n):
    if n["tag"] in CANDIDATE_TAGS:
        return True
    attrs = n["attrs"]
    return "role" in attrs or "onclick" in attrs


def _records(case):
    nodes = _clipped(case)
    picked = [n for n in nodes if n["onscreen"] and _is_candidate(n)]
    picked.sort(key=lambda n: (n["visible"][1], n["visible"][0], n["id"]))
    records = []
    for i, n in enumerate(picked):
        records.append({
            "index": i,
            "id": n["id"],
            "tag": n["tag"],
            "role": str(n["attrs"].get("role", "")),
            "rect": list(n["visible"]),
            "label": _label(n["text"]),
        })
    return records


def milestone_3(case):
    return {"records": _records(case)}


# --------------------------------------------------------------------------- #
# milestone 4 - checksummed binary snapshot frame
# --------------------------------------------------------------------------- #
def _uleb(value):
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        out.append(b | 0x80 if value else b)
        if not value:
            return bytes(out)


def _sleb(value):
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if (value == 0 and not (b & 0x40)) or (value == -1 and (b & 0x40)):
            out.append(b)
            return bytes(out)
        out.append(b | 0x80)


def _str_field(s):
    data = s.encode("utf-8")
    return _uleb(len(data)) + data


CRC_POLY = 0x814141AB


def _crc(data):
    """Custom MSB-first CRC-32 (poly 0x814141AB, init/xorout all ones)."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ CRC_POLY) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


def _frame(records):
    body = bytearray(b"DVS1")
    body.append(0x01)
    flags = 0
    if len(records) % 2 == 1:
        flags |= 0x01
    if any(r["role"] for r in records):
        flags |= 0x02
    if any(r["label"] for r in records):
        flags |= 0x04
    body.append(flags)
    body += _uleb(len(records))
    prev = [0, 0, 0, 0]
    for r in records:
        body += _str_field(r["id"])
        body += _str_field(r["tag"])
        body += _str_field(r["role"])
        body += _str_field(r["label"])
        for j in range(4):
            body += _sleb(r["rect"][j] - prev[j])
        prev = r["rect"]
    crc = _crc(bytes(body))
    body += bytes([(crc >> 24) & 0xFF, (crc >> 16) & 0xFF,
                   (crc >> 8) & 0xFF, crc & 0xFF])
    return bytes(body), crc


def milestone_4(case):
    records = _records(case)
    frame, crc = _frame(records)
    return {
        "sha256": hashlib.sha256(frame).hexdigest(),
        "crc": crc,
        "length": len(frame),
        "records": len(records),
    }


# --------------------------------------------------------------------------- #
MILESTONES = {1: milestone_1, 2: milestone_2, 3: milestone_3, 4: milestone_4}


def main():
    with open(sys.argv[1]) as f:
        scenario = json.load(f)
    fn = MILESTONES[int(scenario["milestone"])]
    answers = [fn(case) for case in scenario["cases"]]
    payload = json.dumps({"answers": answers}, sort_keys=True, separators=(",", ":"))
    with open(sys.argv[2], "w") as f:
        f.write(payload)


if __name__ == "__main__":
    main()
