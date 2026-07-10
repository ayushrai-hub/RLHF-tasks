"""Self-contained reference + held-out generator for warmcache-perl-2.

An edge-CDN "warm cache" planner reconstructs its warm-up plan from a framed descriptor file
(/app/warmcache.dat) whose only spec is a long migration chronicle (five descriptor revisions;
only the current one is live, and its rules are settled across an amendment history rather than
stated in one block). Three compounding stages:

  decode    -- validate/decode canonical base64 frames -> OBJ (key, prerequisites) and HIT
               (key, weight) records, plus an invalid list. CRC is the POSIX cksum of the
               DECODED bytes; base64url/base32/hex/non-canonical payloads are rejected.
  reconcile -- inner-join OBJ against HIT on key, then assign each joined object a DISPOSITION
               by the current policy, resolved by PRECEDENCE  PIN > QUARANTINE > COLD > WARM:
                 * PIN        the key is a pinned key (its second character is the pin marker);
                              always warmed, overriding quarantine and cold.
                 * QUARANTINE the object's zone (its key's first character) is a quarantined
                              zone; excluded, unless pinned.
                 * COLD       the object's weight is below the cold threshold and its zone is
                              not a hot zone; excluded, unless pinned.
                 * WARM       otherwise; warmed.
               The warm-up PLAN is the topological order of the warmed objects (PIN or WARM),
               ties broken by C-locale key. A prerequisite of a warmed object that is not itself
               warmed is dangling.
  rollup    -- group the warmed objects by zone; a zone is RETAINED if its warmed count reaches
               the retain minimum OR it is a priority zone, else it overflows. The digest is the
               POSIX cksum of the canonical retained-zone block.

Every policy value (the pin marker, quarantined zones, cold threshold, hot zones, retain
minimum, priority zones) is what the chronicle's amendment chain settles; build/validate.py
cross-checks cksum/base64 against the real coreutils.
"""
import base64
import re

# ---- policy in force (what the chronicle's amendment chain settles) --------
PIN_MARK = "0"                       # a key is pinned iff its 2nd character is this marker
QUARANTINE_ZONES = frozenset("QX")   # zones (key first char) that are quarantined
COLD_THRESHOLD = 90000               # weight strictly below this is cold...
HOT_ZONES = frozenset("H")           # ...unless the zone is hot
RETAIN_MIN = 2                       # a zone is retained if warmed count >= this...
PRIORITY_ZONES = frozenset("W")      # ...or the zone is a priority zone

# ---- POSIX cksum CRC (matches the first field of /usr/bin/cksum) -----------
_CKTAB = []
for _n in range(256):
    _c = _n << 24
    for _ in range(8):
        _c = ((_c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if (_c & 0x80000000) else (_c << 1) & 0xFFFFFFFF
    _CKTAB.append(_c)


def cksum_crc(data):
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CKTAB[((crc >> 24) ^ b) & 0xFF]
    n = len(data)
    while n > 0:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CKTAB[((crc >> 24) ^ (n & 0xFF)) & 0xFF]
        n >>= 8
    return (~crc) & 0xFFFFFFFF


_ID = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")
_B64 = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _is_canonical_b64(s):
    if len(s) == 0 or len(s) % 4 != 0 or not _B64.match(s):
        return None
    try:
        raw = base64.b64decode(s, validate=True)
    except Exception:
        return None
    if base64.b64encode(raw) != s.encode():
        return None
    return raw


def _parse_record(text):
    parts = text.split(" ")
    if len(parts) != 3:
        return None, None, None, "BAD_REC"
    kind, key, rest = parts
    if kind not in ("OBJ", "HIT"):
        return None, None, None, "BAD_KIND"
    if not _ID.match(key):
        return None, None, None, "BAD_KEY"
    if kind == "OBJ":
        if rest == "-":
            pre = []
        else:
            pre = rest.split(",")
            for d in pre:
                if not _ID.match(d):
                    return None, None, None, "BAD_PRE"
        return "OBJ", key, pre, None
    if not re.match(r"^(0|[1-9][0-9]{0,8})$", rest):
        return None, None, None, "BAD_HITS"
    return "HIT", key, int(rest), None


def _seq_of(fields):
    return int(fields[0]) if fields and re.match(r"^[1-9][0-9]*$", fields[0]) else -1


def stage1_decode(text):
    objs, hits, invalid = {}, {}, []
    seen_obj, seen_hit = set(), set()
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if line.strip() == "":
            continue
        f = line.split(" ")
        if len(f) != 3:
            invalid.append((_seq_of(f), "BAD_FRAME"))
            continue
        seqs, payload, crcs = f
        if not re.match(r"^[1-9][0-9]*$", seqs):
            invalid.append((-1, "BAD_FRAME"))
            continue
        seq = int(seqs)
        data = _is_canonical_b64(payload)
        if data is None:
            invalid.append((seq, "BAD_B64"))
            continue
        if crcs != "0" and not re.match(r"^[1-9][0-9]*$", crcs):
            invalid.append((seq, "BAD_CRC"))
            continue
        if int(crcs) != cksum_crc(data):
            invalid.append((seq, "BAD_CRC"))
            continue
        try:
            rec = data.decode("ascii")
        except UnicodeDecodeError:
            invalid.append((seq, "BAD_REC"))
            continue
        kind, key, payload_v, code = _parse_record(rec)
        if code is not None:
            invalid.append((seq, code))
            continue
        if kind == "OBJ":
            if key in seen_obj:
                invalid.append((seq, "DUP"))
            else:
                seen_obj.add(key)
                objs[key] = payload_v
        else:
            if key in seen_hit:
                invalid.append((seq, "DUP"))
            else:
                seen_hit.add(key)
                hits[key] = payload_v
    invalid.sort()
    return {
        "objs": [[k, objs[k]] for k in sorted(objs)],
        "hits": [[k, hits[k]] for k in sorted(hits)],
        "invalid": [[s, c] for (s, c) in invalid],
    }


def _decode_maps(text):
    d = stage1_decode(text)
    return {k: v for k, v in d["objs"]}, {k: v for k, v in d["hits"]}


def _disposition(key, weight):
    """PIN > QUARANTINE > COLD > WARM."""
    zone = key[0]
    if len(key) >= 2 and key[1] == PIN_MARK:
        return "PIN"
    if zone in QUARANTINE_ZONES:
        return "QUARANTINE"
    if weight < COLD_THRESHOLD and zone not in HOT_ZONES:
        return "COLD"
    return "WARM"


def stage2_reconcile(text):
    objs, hits = _decode_maps(text)
    joined = sorted(k for k in objs if k in hits)          # inner join, C-locale key order
    disp = {k: _disposition(k, hits[k]) for k in joined}
    warmed = [k for k in joined if disp[k] in ("PIN", "WARM")]
    wset = set(warmed)
    adj = {n: [] for n in warmed}
    dangling = []
    for n in warmed:
        for d in objs[n]:
            if d in wset:
                adj[n].append(d)
            else:
                dangling.append((n, d))                    # prereq not warmed (or not joined)
    indeg = {n: len(adj[n]) for n in warmed}
    rev = {n: [] for n in warmed}
    for n in warmed:
        for d in adj[n]:
            rev[d].append(n)
    ready = sorted(n for n in warmed if indeg[n] == 0)
    order = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in rev[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
                ready.sort()
    dangling.sort()
    resolvable = len(order) == len(warmed)
    return {
        "joined": joined,
        "disposition": [[k, disp[k]] for k in joined],
        "resolvable": resolvable,
        "plan": order if resolvable else [],
        "dangling": [[a, b] for (a, b) in dangling],
    }


def stage3_rollup(text):
    objs, hits = _decode_maps(text)
    r = stage2_reconcile(text)
    if not r["resolvable"]:
        return {"zones": [], "overflow": None, "total": None, "digest": None}
    warmed = [k for k, d in r["disposition"] if d in ("PIN", "WARM")]
    per = {}
    for k in warmed:
        z = k[0]
        c, w = per.get(z, (0, 0))
        per[z] = (c + 1, w + hits[k])
    zones, ov_c, ov_w, tot_c, tot_w = [], 0, 0, 0, 0
    for z in sorted(per):
        c, w = per[z]
        tot_c += c
        tot_w += w
        if c >= RETAIN_MIN or z in PRIORITY_ZONES:
            zones.append([z, c, w])
        else:
            ov_c += c
            ov_w += w
    block = "".join("%s %d %d\n" % (z, c, w) for z, c, w in zones).encode("ascii")
    return {
        "zones": zones,
        "overflow": {"count": ov_c, "weight": ov_w},
        "total": {"count": tot_c, "weight": tot_w},
        "digest": cksum_crc(block),
    }


def normalize(d):
    import json
    return json.loads(json.dumps(d))


# ---------------------------------------------------------------------------
# held-out generator: forces every disposition and retention branch, seed-varied
# ---------------------------------------------------------------------------
import random  # noqa: E402

_AL = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"


def _frame(seq, rec_bytes):
    return "%d %s %d" % (seq, base64.b64encode(rec_bytes).decode(), cksum_crc(rec_bytes))


def _mk(zone, pinned, rng):
    """Build a key in `zone` (first char) that is or is not pinned (2nd char == PIN_MARK)."""
    second = PIN_MARK if pinned else rng.choice("123456789ABCDEFGHJKLMNP")
    rest = "".join(rng.choice(_AL) for _ in range(rng.randint(0, 3)))
    return zone + second + rest


def generate(seed):
    rng = random.Random(seed)
    keys = []
    used = set()

    def add(zone, pinned):
        for _ in range(20):
            k = _mk(zone, pinned, rng)
            if k not in used and _ID.match(k):
                used.add(k)
                keys.append(k)
                return k
        return None

    plan_zones = "ABCDEFGHW"
    for z in rng.sample(list(plan_zones), rng.randint(4, len(plan_zones))):
        for _ in range(rng.randint(1, 3)):
            add(z, rng.random() < 0.3)
    for z in "QX":
        for _ in range(rng.randint(1, 3)):
            add(z, rng.random() < 0.4)
    for _ in range(rng.randint(1, 3)):
        add("H", rng.random() < 0.3)

    weight = {}
    for k in keys:
        if rng.random() < 0.5:
            weight[k] = rng.randint(0, COLD_THRESHOLD - 1)
        else:
            weight[k] = rng.randint(COLD_THRESHOLD, 250000)

    lines = []
    seq = rng.randint(1, 5)
    for i, k in enumerate(keys):
        pre = [keys[j] for j in range(i) if rng.random() < 0.3]
        if rng.random() < 0.12:
            pre.append(_mk(rng.choice("QX"), False, rng))
        rest = "-" if not pre else ",".join(pre)
        lines.append(_frame(seq, ("OBJ %s %s" % (k, rest)).encode()))
        seq += rng.randint(1, 3)
    for k in keys:
        if rng.random() < 0.82:
            lines.append(_frame(seq, ("HIT %s %d" % (k, weight[k])).encode()))
            seq += rng.randint(1, 3)

    if rng.random() < 0.85:
        for _ in range(rng.randint(1, 5)):
            kind = rng.choice(["frame", "b64", "crc", "kind", "key", "pre", "hits", "dup", "url"])
            g = ("HIT %s 3" % keys[0]).encode()
            if kind == "frame":
                lines.append("%d onlytwo" % seq)
            elif kind == "b64":
                lines.append("%d not*b64* 12" % seq)
            elif kind == "crc":
                lines.append("%d %s %d" % (seq, base64.b64encode(g).decode(), cksum_crc(g) ^ 5))
            elif kind == "kind":
                lines.append(_frame(seq, b"XYZ AB 1"))
            elif kind == "key":
                lines.append(_frame(seq, b"OBJ lower -"))
            elif kind == "pre":
                lines.append(_frame(seq, b"OBJ AB x1,Y2"))
            elif kind == "hits":
                lines.append(_frame(seq, b"HIT AB 1.5"))
            elif kind == "dup":
                lines.append(_frame(seq, ("OBJ %s -" % keys[0]).encode()))
            elif kind == "url":
                raw = bytes([251, 255, 191])
                u = base64.urlsafe_b64encode(raw).decode()
                if "-" in u or "_" in u:
                    lines.append("%d %s %d" % (seq, u, cksum_crc(raw)))
                else:
                    lines.append("%d %s %d" % (seq, base64.b64encode(g).decode(), cksum_crc(g) ^ 1))
            seq += rng.randint(1, 3)
    rng.shuffle(lines)
    out = []
    for ln in lines:
        out.append(ln)
        if rng.random() < 0.08:
            out.append("")
    return "\n".join(out) + "\n"
