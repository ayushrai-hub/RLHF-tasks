"""Self-contained reference + held-out generator for warmcache-perl tests.

The task: an edge-CDN "warm cache" planner reconstructs its warm-up plan from a framed
descriptor file (/app/warmcache.dat) whose only surviving spec is a long migration chronicle
(five descriptor-format revisions R1..R5; only R5 is current). Three compounding stages:

  decode  -- validate/decode base64 frames -> objects (OBJ) with prerequisites and hit weights
             (HIT), plus an invalid list.
  order   -- inner-join OBJ against HIT on key; topologically order so prerequisites warm first,
             breaking ties by C-locale (bytewise) key order; report dangling prerequisites.
  digest  -- a deterministic plan digest over the order: a djb2 rolling hash, the total hit
             weight, and the POSIX cksum of the newline-joined order.

Fidelity points (each a "lift the wrong revision" trap): PAYLOAD is CANONICAL RFC-4648 base64
of the DECODED record bytes (older revisions used hex / base32 / base64url); CRC is the POSIX
cksum of the DECODED bytes (an older revision checksummed the base64 transport); ordering is a
bytewise C-locale comparison, not a numeric or locale sort.
"""
import base64
import re

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
_B64 = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")   # canonical RFC-4648 alphabet with '=' padding


def _is_canonical_b64(s):
    """Canonical RFC-4648 base64: standard alphabet, correct '=' padding, length % 4 == 0,
    and it must re-encode to itself (rejects non-canonical trailing bits)."""
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
    """text is the decoded record string. Return (kind, key, payload, None) or (.,.,.,code)."""
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


def stage2_order(text):
    objs, hits = _decode_maps(text)
    joined = sorted(k for k in objs if k in hits)      # inner join, C-locale key order
    jset = set(joined)
    adj = {n: [] for n in joined}                      # n -> prerequisites within the join
    dangling = []
    for n in joined:
        for d in objs[n]:
            if d in jset:
                adj[n].append(d)
            else:
                dangling.append((n, d))
    indeg = {n: len(adj[n]) for n in joined}
    rev = {n: [] for n in joined}
    for n in joined:
        for d in adj[n]:
            rev[d].append(n)
    ready = sorted(n for n in joined if indeg[n] == 0)
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
    resolvable = len(order) == len(joined)
    return {
        "resolvable": resolvable,
        "order": order if resolvable else [],
        "joined": joined,
        "dangling": [[a, b] for (a, b) in dangling],
    }


def stage3_digest(text):
    o = stage2_order(text)
    _objs, hits = _decode_maps(text)
    if not o["resolvable"]:
        return {"plan_hash": None, "hit_sum": None, "order_crc": None}
    h = 5381                                            # djb2
    hit_sum = 0
    blob = []
    for key in o["order"]:
        for ch in key.encode("ascii"):
            h = ((h * 33) ^ ch) & 0xFFFFFFFF
        hit_sum += hits[key]
        blob.append(key)
    order_crc = cksum_crc(("\n".join(blob) + "\n").encode("ascii") if blob else b"")
    return {"plan_hash": h, "hit_sum": hit_sum, "order_crc": order_crc}


# ---------------------------------------------------------------------------
# held-out generator: builds a valid warmcache.dat plus malformed frames
# ---------------------------------------------------------------------------
import random  # noqa: E402


def _frame(seq, rec_bytes):
    payload = base64.b64encode(rec_bytes).decode()
    return "%d %s %d" % (seq, payload, cksum_crc(rec_bytes))


def _key(rng):
    n = rng.randint(2, 6)
    s = rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    for _ in range(n - 1):
        s += rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789")
    return s


def generate(seed):
    rng = random.Random(seed)
    nkeys = rng.randint(3, 9)
    keys = []
    while len(keys) < nkeys:
        k = _key(rng)
        if k not in keys:
            keys.append(k)
    lines = []
    seq = rng.randint(1, 5)
    # OBJ records with acyclic prerequisites (prereqs among earlier keys, sometimes dangling)
    for i, k in enumerate(keys):
        pre = []
        for j in range(i):
            if rng.random() < 0.35:
                pre.append(keys[j])
        if rng.random() < 0.15:
            pre.append(_key(rng))                       # possibly-dangling prereq
        rest = "-" if not pre else ",".join(pre)
        lines.append(_frame(seq, ("OBJ %s %s" % (k, rest)).encode()))
        seq += rng.randint(1, 3)
    # HIT records (some keys, so the inner join is a strict subset)
    for k in keys:
        if rng.random() < 0.8:
            lines.append(_frame(seq, ("HIT %s %d" % (k, rng.randint(0, 999999))).encode()))
            seq += rng.randint(1, 3)
    # malformed frames exercising each code
    bad = []
    if rng.random() < 0.85:
        for _ in range(rng.randint(1, 5)):
            kind = rng.choice(["frame", "b64", "crc", "kind", "key", "pre", "hits", "dup", "url"])
            g = ("HIT %s 3" % keys[0]).encode()
            if kind == "frame":
                bad.append("%d onlytwo" % seq)
            elif kind == "b64":
                bad.append("%d not*base64* %d" % (seq, 123))
            elif kind == "crc":
                bad.append("%d %s %d" % (seq, base64.b64encode(g).decode(), cksum_crc(g) ^ 5))
            elif kind == "kind":
                r = b"XYZ AB 1"
                bad.append(_frame(seq, r))
            elif kind == "key":
                r = b"OBJ lower -"
                bad.append(_frame(seq, r))
            elif kind == "pre":
                r = b"OBJ AB x1,Y2"
                bad.append(_frame(seq, r))
            elif kind == "hits":
                r = b"HIT AB 1.5"
                bad.append(_frame(seq, r))
            elif kind == "dup":
                bad.append(_frame(seq, ("OBJ %s -" % keys[0]).encode()))
            elif kind == "url":
                # base64url (- _ instead of + /) of some bytes -> not canonical standard base64
                raw = bytes([251, 255, 191])
                u = base64.urlsafe_b64encode(raw).decode()
                if "-" in u or "_" in u:
                    bad.append("%d %s %d" % (seq, u, cksum_crc(raw)))
                else:
                    bad.append("%d %s %d" % (seq, base64.b64encode(g).decode(), cksum_crc(g) ^ 1))
            seq += rng.randint(1, 3)
    all_lines = lines + bad
    rng.shuffle(all_lines)
    # occasional blank lines (skipped, still fine)
    out = []
    for ln in all_lines:
        out.append(ln)
        if rng.random() < 0.1:
            out.append("")
    return "\n".join(out) + "\n"
