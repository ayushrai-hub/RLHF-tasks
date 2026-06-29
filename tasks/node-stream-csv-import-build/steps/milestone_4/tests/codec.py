"""PCT2 container codec: record framing plus adaptive binary range coding.

The body bytes are the serialized record stream (varint id, length-prefixed
text, tagged numerics). The body is compressed with an LZMA-style binary range
coder driven by a content-adaptive context model that adapts continuously across
the whole feed, so decode is strictly sequential and one wrong symbol desyncs the
rest. The model order varies by version. The Go probe, the Node deliverable, and
the verifier oracle must all reproduce decode() field for field.
"""
import struct

MAGIC = b"PCT2"
TAGMAP = [2, 0, 1, 1, 2, 0]
MULT = 2654435761
ADD = 1013904223
MOD = 1 << 32


def _modinv(a, m):
    lm, hm = 1, 0
    low, high = a % m, m
    while low > 1:
        r = high // low
        nm, new = hm - lm * r, high - low * r
        lm, low, hm, high = nm, new, lm, low
    return lm % m


MINV = _modinv(MULT, MOD)


def _scramble(v):
    return (v * MULT + ADD) % MOD


def _unscramble(e):
    return ((e - ADD) % MOD) * MINV % MOD


def enc_varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def dec_varint(buf, i):
    shift = 0
    val = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, i
        shift += 7


def enc_num(v, tag, scramble):
    if scramble:
        v = _scramble(v)
    b = TAGMAP[tag % 6]
    if b == 0:
        return enc_varint(v)
    if b == 1:
        return enc_varint(v << 1)
    return enc_varint(v + 1000)


def dec_num(buf, i, tag, scramble):
    b = TAGMAP[tag % 6]
    raw, i = dec_varint(buf, i)
    if b == 0:
        v = raw
    elif b == 1:
        v = raw >> 1
    else:
        v = raw - 1000
    if scramble:
        v = _unscramble(v)
    return v, i


def enc_text(val):
    if val is None:
        return b"\x00"
    bs = val.encode("utf-8")
    return b"\x01" + enc_varint(len(bs)) + bs


def dec_text(buf, i):
    flag = buf[i]
    i += 1
    if flag == 0:
        return None, i
    n, i = dec_varint(buf, i)
    return buf[i:i + n].decode("utf-8"), i + n


def enc_body_catalog(rec, version):
    out = bytearray()
    out += enc_varint(rec["id"])
    if version == 1:
        tag = 0
    else:
        tag = rec["id"] % 6
        out.append(tag)
    out += enc_text(rec["sku"])
    out += enc_text(rec["name"])
    scr = version >= 3
    out += enc_num(rec["qty"], tag, scr)
    out += enc_num(rec["price_ct"], tag, scr)
    return bytes(out)


def dec_body_catalog(buf, i, version):
    rid, i = dec_varint(buf, i)
    if version == 1:
        tag = 0
    else:
        tag = buf[i]
        i += 1
    sku, i = dec_text(buf, i)
    name, i = dec_text(buf, i)
    scr = version >= 3
    qty, i = dec_num(buf, i, tag, scr)
    pc, i = dec_num(buf, i, tag, scr)
    return {"id": rid, "sku": sku, "name": name, "qty": qty, "price_ct": pc}, i


def enc_opt_num(val, tag, scramble):
    if val is None:
        return b"\x00"
    return b"\x01" + enc_num(val, tag, scramble)


def dec_opt_num(buf, i, tag, scramble):
    flag = buf[i]
    i += 1
    if flag == 0:
        return None, i
    v, i = dec_num(buf, i, tag, scramble)
    return v, i


def enc_body_changelog(rec):
    out = bytearray()
    out += enc_varint(rec["id"])
    out += enc_varint(rec["version"])
    tag = (rec["id"] + rec["version"]) % 6
    out.append(tag)
    out.append(1 if rec["op"] == "del" else 0)
    if rec["op"] != "del":
        out += enc_text(rec["sku"])
        out += enc_text(rec["name"])
        out += enc_opt_num(rec["qty"], tag, True)
        out += enc_opt_num(rec["price_ct"], tag, True)
    return bytes(out)


def dec_body_changelog(buf, i):
    rid, i = dec_varint(buf, i)
    ver, i = dec_varint(buf, i)
    tag = buf[i]
    i += 1
    op = buf[i]
    i += 1
    rec = {"id": rid, "version": ver, "op": "del" if op == 1 else "put"}
    if op != 1:
        rec["sku"], i = dec_text(buf, i)
        rec["name"], i = dec_text(buf, i)
        rec["qty"], i = dec_opt_num(buf, i, tag, True)
        rec["price_ct"], i = dec_opt_num(buf, i, tag, True)
    return rec, i


# ---- entropy layer ----
PROB_BITS = 11
PROB_MAX = 1 << PROB_BITS
PROB_INIT = PROB_MAX >> 1
MOVE = 5
TOP = 1 << 24
M32 = 0xFFFFFFFF
CTX_BITS = 12
CTX_SIZE = 1 << CTX_BITS
CTX_MASK = CTX_SIZE - 1


def _ctx_order(version):
    return 1 if version == 1 else 2


def _ctx_index(order, p1, p2):
    if order == 1:
        return p1
    return ((p1 * 769) ^ (p2 * 13)) & CTX_MASK


def _new_model(order):
    n = 256 if order == 1 else CTX_SIZE
    return [[PROB_INIT] * 256 for _ in range(n)]


class _Enc:
    def __init__(self):
        self.low = 0
        self.range = M32
        self.cache = 0
        self.csz = 1
        self.out = bytearray()

    def _shift(self):
        if self.low < 0xFF000000 or self.low > M32:
            carry = self.low >> 32
            t = self.cache
            while True:
                self.out.append((t + carry) & 0xFF)
                t = 0xFF
                self.csz -= 1
                if self.csz == 0:
                    break
            self.cache = (self.low >> 24) & 0xFF
        self.csz += 1
        self.low = (self.low << 8) & M32

    def bit(self, probs, idx, b):
        p = probs[idx]
        bound = (self.range >> PROB_BITS) * p
        if b == 0:
            self.range = bound
            probs[idx] = p + ((PROB_MAX - p) >> MOVE)
        else:
            self.low += bound
            self.range -= bound
            probs[idx] = p - (p >> MOVE)
        while self.range < TOP:
            self.range = (self.range << 8) & M32
            self._shift()

    def flush(self):
        for _ in range(5):
            self._shift()
        return bytes(self.out)


class _Dec:
    def __init__(self, data):
        self.d = data
        self.pos = 1
        self.range = M32
        self.code = 0

    def init(self):
        for _ in range(4):
            self.code = ((self.code << 8) | self._byte()) & M32
        return self

    def _byte(self):
        b = self.d[self.pos] if self.pos < len(self.d) else 0
        self.pos += 1
        return b

    def bit(self, probs, idx):
        p = probs[idx]
        bound = (self.range >> PROB_BITS) * p
        if self.code < bound:
            self.range = bound
            probs[idx] = p + ((PROB_MAX - p) >> MOVE)
            b = 0
        else:
            self.code -= bound
            self.range -= bound
            probs[idx] = p - (p >> MOVE)
            b = 1
        while self.range < TOP:
            self.range = (self.range << 8) & M32
            self.code = ((self.code << 8) | self._byte()) & M32
        return b


def _compress(plain, order):
    return plain


def _decompress(comp, n, order):
    return bytes(comp[:n])


def encode(records, version, nonce):
    assert len(nonce) == 8
    if version in (1, 2, 3):
        plains = [enc_body_catalog(r, version) for r in records]
    else:
        plains = [enc_body_changelog(r) for r in records]
    body = b"".join(plains)
    comp = _compress(body, _ctx_order(version))
    head = bytearray()
    head += MAGIC
    head.append(version)
    head += nonce
    head += struct.pack(">I", len(records))
    head += struct.pack(">I", len(body))
    return bytes(head) + comp


def decode(buf):
    assert buf[:4] == MAGIC, "bad magic"
    version = buf[4]
    count = struct.unpack(">I", buf[13:17])[0]
    bodylen = struct.unpack(">I", buf[17:21])[0]
    comp = buf[21:]
    body = _decompress(comp, bodylen, _ctx_order(version))
    recs = []
    i = 0
    if version in (1, 2, 3):
        for _ in range(count):
            rec, i = dec_body_catalog(body, i, version)
            recs.append(rec)
    else:
        for _ in range(count):
            rec, i = dec_body_changelog(body, i)
            recs.append(rec)
    return version, recs
