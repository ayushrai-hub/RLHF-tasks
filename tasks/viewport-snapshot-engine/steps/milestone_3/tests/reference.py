"""Independent reference for the viewport snapshot engine. Mounted only at verify
time; never shipped in the agent image.

The whole specification is re-derived a second way here. Absolute geometry is
computed by threading an accumulated content origin through an explicit recursion
that records parent pointers; clipping is resolved by collecting the full list of
clipping ancestors and folding their padding boxes together rather than walking a
chain inline; and the binary frame is rebuilt with table-driven CRC and a
separately written varint coder. Fixtures come from fixed integer seeds so
grading is reproducible and are concentrated on the inputs where an obvious but
wrong method diverges: deep box-model accumulation with borders, padding and
scroll at every level, overflow that clips descendants to the padding box, the
half-open viewport edge, reading-order ties broken by string id, and signed
delta varints in the snapshot frame.
"""
import hashlib
import json
import random

CANDIDATE_TAGS = {"a", "button", "input", "select", "textarea"}


def canonical(result):
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


def _rng(seed):
    return random.Random(seed)


# --------------------------------------------------------------------------- #
# absolute layout (accumulated content origin + parent pointers)
# --------------------------------------------------------------------------- #
def _flatten(case):
    flat = []

    def go(node, parent, origin_x, origin_y):
        box = node["box"]
        x = origin_x + int(box[0])
        y = origin_y + int(box[1])
        w = int(box[2])
        h = int(box[3])
        bt, br, bb, bl = (int(v) for v in node.get("border", [0, 0, 0, 0]))
        pt, pr, pb, pl = (int(v) for v in node.get("padding", [0, 0, 0, 0]))
        sx, sy = (int(v) for v in node.get("scroll", [0, 0]))
        me = len(flat)
        flat.append({
            "id": node["id"],
            "tag": node.get("tag", ""),
            "attrs": node.get("attrs", {}),
            "text": node.get("text", ""),
            "border_box": [x, y, w, h],
            "padding_box": [x + bl, y + bt, w - bl - br, h - bt - bb],
            "overflow_clip": node.get("overflow", "visible") == "clip",
            "parent": parent,
        })
        child_origin_x = x + bl + pl - sx
        child_origin_y = y + bt + pt - sy
        for kid in node.get("children", []):
            go(kid, me, child_origin_x, child_origin_y)
    go(case["root"], -1, 0, 0)
    return flat


def run_milestone_1(case):
    return {n["id"]: list(n["border_box"]) for n in _flatten(case)}


# --------------------------------------------------------------------------- #
# clipping by overflow ancestors + viewport
# --------------------------------------------------------------------------- #
def _clip_two(r, s):
    rx, ry, rw, rh = r
    sx, sy, sw, sh = s
    nx, ny = max(rx, sx), max(ry, sy)
    nw = min(rx + rw, sx + sw) - nx
    nh = min(ry + rh, sy + sh) - ny
    return [nx, ny, max(0, nw), max(0, nh)]


def _ancestor_clips(flat, i):
    rects = []
    cur = flat[i]["parent"]
    while cur != -1:
        if flat[cur]["overflow_clip"]:
            rects.append(flat[cur]["padding_box"])
        cur = flat[cur]["parent"]
    return rects


def _resolve_clip(case):
    flat = _flatten(case)
    vw, vh = int(case["viewport"][0]), int(case["viewport"][1])
    for i, n in enumerate(flat):
        region = [0, 0, vw, vh]
        for clip in _ancestor_clips(flat, i):
            region = _clip_two(region, clip)
        vis = _clip_two(n["border_box"], region)
        on = vis[2] > 0 and vis[3] > 0
        n["onscreen"] = on
        n["visible"] = vis if on else [0, 0, 0, 0]
    return flat


def run_milestone_2(case):
    return {n["id"]: {"onscreen": n["onscreen"], "rect": list(n["visible"])}
            for n in _resolve_clip(case)}


# --------------------------------------------------------------------------- #
# ordered interactive snapshot records
# --------------------------------------------------------------------------- #
def _label(text):
    return " ".join(str(text).split())[:50]


def _candidate(n):
    if n["tag"] in CANDIDATE_TAGS:
        return True
    return "role" in n["attrs"] or "onclick" in n["attrs"]


def _records(case):
    flat = _resolve_clip(case)
    chosen = [n for n in flat if n["onscreen"] and _candidate(n)]
    chosen.sort(key=lambda n: (n["visible"][1], n["visible"][0], n["id"]))
    out = []
    for i, n in enumerate(chosen):
        out.append({
            "index": i,
            "id": n["id"],
            "tag": n["tag"],
            "role": str(n["attrs"].get("role", "")),
            "rect": list(n["visible"]),
            "label": _label(n["text"]),
        })
    return out


def run_milestone_3(case):
    return {"records": _records(case)}


# --------------------------------------------------------------------------- #
# checksummed binary snapshot frame
# --------------------------------------------------------------------------- #
def _uleb(n):
    parts = bytearray()
    while True:
        chunk = n & 0x7F
        n >>= 7
        if n:
            parts.append(chunk | 0x80)
        else:
            parts.append(chunk)
            return bytes(parts)


def _sleb(n):
    parts = bytearray()
    more = True
    while more:
        chunk = n & 0x7F
        n >>= 7
        sign = chunk & 0x40
        if (n == 0 and not sign) or (n == -1 and sign):
            more = False
            parts.append(chunk)
        else:
            parts.append(chunk | 0x80)
    return bytes(parts)


def _lp(s):
    raw = s.encode("utf-8")
    return _uleb(len(raw)) + raw


_CRC_POLY = 0x814141AB
_CRC_TABLE = []
for _b in range(256):
    _c = _b << 24
    for _ in range(8):
        _c = ((_c << 1) ^ _CRC_POLY) & 0xFFFFFFFF if _c & 0x80000000 else (_c << 1) & 0xFFFFFFFF
    _CRC_TABLE.append(_c)


def crc32_msb(data):
    """Table-driven MSB-first CRC-32 with poly 0x814141AB, init/xorout all ones.
    Equivalent to the bit-at-a-time reference but a separate implementation."""
    reg = 0xFFFFFFFF
    for byte in data:
        reg = ((reg << 8) ^ _CRC_TABLE[((reg >> 24) ^ byte) & 0xFF]) & 0xFFFFFFFF
    return reg ^ 0xFFFFFFFF


def build_frame(records):
    buf = bytearray()
    buf += b"DVS1"
    buf.append(0x01)
    flags = 0
    if len(records) & 1:
        flags |= 0x01
    if any(r["role"] != "" for r in records):
        flags |= 0x02
    if any(r["label"] != "" for r in records):
        flags |= 0x04
    buf.append(flags)
    buf += _uleb(len(records))
    last = [0, 0, 0, 0]
    for r in records:
        buf += _lp(r["id"])
        buf += _lp(r["tag"])
        buf += _lp(r["role"])
        buf += _lp(r["label"])
        rect = r["rect"]
        for k in range(4):
            buf += _sleb(rect[k] - last[k])
        last = rect
    crc = crc32_msb(bytes(buf))
    buf += crc.to_bytes(4, "big")
    return bytes(buf), crc


def run_milestone_4(case):
    records = _records(case)
    frame, crc = build_frame(records)
    return {
        "sha256": hashlib.sha256(frame).hexdigest(),
        "crc": crc,
        "length": len(frame),
        "records": len(records),
    }


# --------------------------------------------------------------------------- #
# fixture generators
# --------------------------------------------------------------------------- #
TAGS_PLAIN = ["div", "span", "section", "p", "li", "ul"]
TAGS_INTER = ["a", "button", "input", "select", "textarea"]
ROLES = ["button", "link", "tab", "menuitem", "checkbox"]
TEXTS = ["", "Save", "  Log   in  ", "Submit form", "x", "Next page",
         "A rather long caption that certainly exceeds the fifty character limit by quite a lot"]


def _rand_quad(rng, hi):
    return [rng.randint(0, hi) for _ in range(4)]


def _rand_node(rng, counter, depth):
    nid = "e{}".format(next(counter))
    interactive = rng.random() < 0.55
    tag = rng.choice(TAGS_INTER) if interactive else rng.choice(TAGS_PLAIN)
    w = rng.randint(8, 60)
    h = rng.randint(8, 45)
    x = rng.randint(-12, 60)
    y = rng.randint(-12, 45)
    node = {"id": nid, "tag": tag, "box": [x, y, w, h]}
    if rng.random() < 0.7:
        node["border"] = _rand_quad(rng, 4)
    if rng.random() < 0.7:
        node["padding"] = _rand_quad(rng, 6)
    if rng.random() < 0.5:
        node["scroll"] = [rng.randint(0, 20), rng.randint(0, 20)]
    if rng.random() < 0.4:
        node["overflow"] = "clip"
    attrs = {}
    if interactive and rng.random() < 0.4:
        attrs["role"] = rng.choice(ROLES)
    if not interactive and rng.random() < 0.3:
        attrs["role"] = rng.choice(ROLES)
    if rng.random() < 0.2:
        attrs["onclick"] = "h()"
    if attrs:
        node["attrs"] = attrs
    if rng.random() < 0.7:
        node["text"] = rng.choice(TEXTS)
    if depth < 7 and rng.random() < 0.75:
        node["children"] = [_rand_node(rng, counter, depth + 1)
                            for _ in range(rng.randint(1, 3))]
    return node


def rand_case(rng):
    counter = iter(range(100000))
    vw, vh = rng.randint(60, 120), rng.randint(50, 100)
    root = {"id": "root", "tag": "body",
            "box": [rng.randint(-6, 6), rng.randint(-6, 6),
                    rng.randint(vw - 10, vw + 40), rng.randint(vh - 10, vh + 40)]}
    if rng.random() < 0.6:
        root["padding"] = _rand_quad(rng, 6)
    if rng.random() < 0.5:
        root["border"] = _rand_quad(rng, 4)
    if rng.random() < 0.4:
        root["overflow"] = "clip"
    if rng.random() < 0.4:
        root["scroll"] = [rng.randint(0, 15), rng.randint(0, 15)]
    root["children"] = [_rand_node(rng, counter, 1) for _ in range(rng.randint(2, 4))]
    return {"viewport": [vw, vh], "root": root}


# designed edge cases -------------------------------------------------------- #
def m1_designed():
    # deep chain: border + padding + scroll accumulate at every level
    chain = {"id": "L0", "tag": "div", "box": [4, 6, 80, 80],
             "border": [2, 0, 0, 3], "padding": [5, 0, 0, 7], "scroll": [1, 2]}
    node = chain
    for d in range(1, 6):
        kid = {"id": "L{}".format(d), "tag": "div", "box": [3, 4, 40, 40],
               "border": [1, 1, 1, 2], "padding": [2, 2, 2, 3], "scroll": [2, 1]}
        node["children"] = [kid]
        node = kid
    return [
        {"viewport": [100, 100], "root": chain},
        # scroll only, two children shifted negatively
        {"viewport": [80, 80], "root": {"id": "root", "tag": "div", "box": [0, 0, 60, 60],
            "scroll": [10, 5], "children": [
                {"id": "a", "tag": "div", "box": [0, 0, 20, 20]},
                {"id": "b", "tag": "div", "box": [30, 30, 10, 10]}]}},
        # border + padding only (no scroll): content origin offset
        {"viewport": [80, 80], "root": {"id": "root", "tag": "div", "box": [0, 0, 60, 60],
            "border": [4, 0, 0, 6], "padding": [3, 0, 0, 5], "children": [
                {"id": "c", "tag": "div", "box": [0, 0, 10, 10]}]}},
    ]


def m2_designed():
    return [
        # clip to the PADDING box (not border, not content): child at the padding edge
        {"viewport": [200, 200], "root": {"id": "root", "tag": "div", "box": [0, 0, 100, 100],
            "border": [5, 5, 5, 5], "padding": [8, 8, 8, 8], "overflow": "clip", "children": [
                {"id": "edge", "tag": "div", "box": [-3, -3, 6, 6]},
                {"id": "inside", "tag": "div", "box": [0, 0, 40, 40]}]}},
        # nested clips: inner and outer overflow both bite
        {"viewport": [200, 200], "root": {"id": "root", "tag": "div", "box": [0, 0, 120, 120],
            "overflow": "clip", "padding": [4, 4, 4, 4], "children": [
                {"id": "mid", "tag": "div", "box": [10, 10, 40, 40], "overflow": "clip",
                 "border": [2, 2, 2, 2], "children": [
                    {"id": "leaf", "tag": "div", "box": [20, 20, 40, 40]}]}]}},
        # half-open viewport edge: a node flush to the right edge keeps width, one past is gone
        {"viewport": [50, 50], "root": {"id": "root", "tag": "div", "box": [0, 0, 200, 200], "children": [
            {"id": "flush", "tag": "div", "box": [40, 0, 10, 10]},
            {"id": "past", "tag": "div", "box": [50, 0, 10, 10]},
            {"id": "spill", "tag": "div", "box": [45, 20, 20, 10]}]}},
        # a clipping node does NOT clip itself, only its descendants
        {"viewport": [200, 200], "root": {"id": "root", "tag": "div", "box": [0, 0, 200, 200], "children": [
            {"id": "self", "tag": "div", "box": [10, 10, 30, 30], "overflow": "clip",
             "padding": [2, 2, 2, 2], "children": [
                {"id": "child", "tag": "div", "box": [-20, -20, 40, 40]}]}]}},
    ]


def m3_designed():
    return [
        # reading order ties: same y and x, id breaks the tie lexicographically
        {"viewport": [100, 100], "root": {"id": "root", "tag": "div", "box": [0, 0, 100, 100], "children": [
            {"id": "e10", "tag": "button", "box": [5, 5, 20, 10], "text": "ten"},
            {"id": "e2", "tag": "button", "box": [5, 5, 20, 10], "text": "two"},
            {"id": "e1", "tag": "a", "box": [5, 30, 20, 10], "text": "one"}]}},
        # role-only candidate is in, plain div is out, long label truncated
        {"viewport": [100, 100], "root": {"id": "root", "tag": "div", "box": [0, 0, 100, 100], "children": [
            {"id": "plain", "tag": "div", "box": [0, 0, 10, 10], "text": "ignored"},
            {"id": "role", "tag": "div", "box": [0, 20, 10, 10], "attrs": {"role": "button"},
             "text": "A rather long caption that certainly exceeds the fifty character limit by quite a lot"}]}},
        # an offscreen candidate (clipped away) must not appear
        {"viewport": [60, 60], "root": {"id": "root", "tag": "div", "box": [0, 0, 60, 60],
            "overflow": "clip", "children": [
                {"id": "seen", "tag": "button", "box": [0, 0, 20, 20], "text": "ok"},
                {"id": "gone", "tag": "button", "box": [80, 80, 20, 20], "text": "no"}]}},
    ]


def m4_designed():
    cases = []
    cases.extend(m3_designed())
    # no candidates at all -> empty frame
    cases.append({"viewport": [60, 60], "root": {"id": "root", "tag": "div",
        "box": [0, 0, 60, 60], "children": [
            {"id": "p", "tag": "div", "box": [0, 0, 10, 10], "text": "x"}]}})
    # single record
    cases.append({"viewport": [60, 60], "root": {"id": "root", "tag": "div",
        "box": [0, 0, 60, 60], "children": [
            {"id": "solo", "tag": "button", "box": [2, 2, 20, 10], "text": "go"}]}})
    # several records forcing negative x/w/h deltas between rows
    cases.append({"viewport": [120, 120], "root": {"id": "root", "tag": "div",
        "box": [0, 0, 120, 120], "children": [
            {"id": "b0", "tag": "button", "box": [40, 5, 30, 20], "text": "wide top"},
            {"id": "b1", "tag": "a", "box": [4, 40, 10, 8], "attrs": {"role": "link"}, "text": "narrow"},
            {"id": "b2", "tag": "button", "box": [60, 70, 50, 30], "text": "big"}]}})
    return cases


def m1_random(seed, n=6):
    rng = _rng(seed)
    return [rand_case(rng) for _ in range(n)]


def m4_random(seed, n=6):
    rng = _rng(seed)
    return [rand_case(rng) for _ in range(n)]
