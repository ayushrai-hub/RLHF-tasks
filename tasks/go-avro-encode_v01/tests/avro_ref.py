"""Independent reference Avro binary encoder + hidden grading battery.

Mirrors the encoding contract in docs/format.md (Apache Avro 1.11 binary
encoding) to the same behavior as the editable Go files. build_battery() returns
(input_obj, expected_obj) where expected is computed here. Nothing here ships in
the task image.
"""
import struct

PRIMITIVES = {"null", "boolean", "int", "long", "float", "double", "bytes", "string"}


class EncErr(Exception):
    pass


# ---- schema (mirror src/schema.go) ----
def parse_schema(j):
    if isinstance(j, str):
        if j in PRIMITIVES:
            return {"type": j}
        raise EncErr("unknown type")
    if isinstance(j, list):
        return {"type": "union", "branches": [parse_schema(b) for b in j]}
    if isinstance(j, dict):
        tn = j.get("type")
        if tn == "record":
            fields = [{"name": f["name"], "type": parse_schema(f["type"])}
                      for f in j.get("fields", [])]
            return {"type": "record", "name": j.get("name", ""), "fields": fields}
        if tn == "enum":
            return {"type": "enum", "name": j.get("name", ""), "symbols": list(j.get("symbols", []))}
        if tn == "array":
            return {"type": "array", "items": parse_schema(j["items"])}
        if tn == "map":
            return {"type": "map", "values": parse_schema(j["values"])}
        if tn == "fixed":
            return {"type": "fixed", "name": j.get("name", ""), "size": int(j["size"])}
        if tn in PRIMITIVES:
            return {"type": tn}
        raise EncErr("unknown type")
    raise EncErr("invalid schema")


# ---- encoding (mirror src oracle) ----
def write_varint(out, u):
    while u >= 0x80:
        out.append((u & 0x7F) | 0x80)
        u >>= 7
    out.append(u)


def write_long(out, n):
    write_varint(out, (n << 1) ^ (n >> 63))


def _branch_name(s):
    return s["name"] if s["type"] in ("record", "enum", "fixed") else s["type"]


def encode_value(out, s, v):
    t = s["type"]
    if t == "null":
        if v is not None:
            raise EncErr("expected null")
    elif t == "boolean":
        if not isinstance(v, bool):
            raise EncErr("expected boolean")
        out.append(1 if v else 0)
    elif t in ("int", "long"):
        if not isinstance(v, int) or isinstance(v, bool):
            raise EncErr("expected integer")
        write_long(out, v)
    elif t == "float":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise EncErr("expected number")
        out += struct.pack("<f", float(v))
    elif t == "double":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise EncErr("expected number")
        out += struct.pack("<d", float(v))
    elif t == "bytes":
        data = _hex(v)
        write_long(out, len(data))
        out += data
    elif t == "string":
        if not isinstance(v, str):
            raise EncErr("expected string")
        b = v.encode("utf-8")
        write_long(out, len(b))
        out += b
    elif t == "fixed":
        data = _hex(v)
        if len(data) != s["size"]:
            raise EncErr("fixed length mismatch")
        out += data
    elif t == "enum":
        if not isinstance(v, str):
            raise EncErr("expected enum symbol")
        if v not in s["symbols"]:
            raise EncErr("symbol not in enum")
        write_long(out, s["symbols"].index(v))
    elif t == "record":
        if not isinstance(v, dict):
            raise EncErr("expected record object")
        for f in s["fields"]:
            if f["name"] not in v:
                raise EncErr("missing field")
            encode_value(out, f["type"], v[f["name"]])
    elif t == "array":
        if not isinstance(v, list):
            raise EncErr("expected array")
        if len(v) > 0:
            write_long(out, len(v))
            for it in v:
                encode_value(out, s["items"], it)
        write_long(out, 0)
    elif t == "map":
        if not isinstance(v, dict):
            raise EncErr("expected map object")
        if len(v) > 0:
            write_long(out, len(v))
            for k in sorted(v.keys()):
                kb = k.encode("utf-8")
                write_long(out, len(kb))
                out += kb
                encode_value(out, s["values"], v[k])
        write_long(out, 0)
    elif t == "union":
        if v is None:
            for i, b in enumerate(s["branches"]):
                if b["type"] == "null":
                    write_long(out, i)
                    return
            raise EncErr("null not in union")
        if not isinstance(v, dict) or len(v) != 1:
            raise EncErr("expected union wrapper")
        name = next(iter(v))
        for i, b in enumerate(s["branches"]):
            if _branch_name(b) == name:
                write_long(out, i)
                encode_value(out, b, v[name])
                return
        raise EncErr("branch not in union")
    else:
        raise EncErr("unknown type")


def _hex(v):
    if not isinstance(v, str):
        raise EncErr("expected hex string")
    try:
        return bytearray.fromhex(v)
    except ValueError as e:
        raise EncErr("bad hex") from e


def encode_case(c):
    res = {"id": c["id"], "status": "error", "hex": ""}
    try:
        s = parse_schema(c["schema"])
        out = bytearray()
        encode_value(out, s, c["value"])
    except EncErr:
        return res
    res["status"] = "ok"
    res["hex"] = out.hex()
    return res


def decode_input(inp):
    return {"cases": [encode_case(c) for c in inp["cases"]]}


# ---------------------------------------------------------------------------
# hidden grading battery
# ---------------------------------------------------------------------------
def _c(cid, schema, value):
    return {"id": cid, "schema": schema, "value": value}


def build_battery():
    """Return (input_obj, expected_obj). expected is what a contract-faithful
    encoder must emit, computed by the reference encoder above."""
    cases = []

    rec_alpha = {"type": "record", "name": "R",
                 "fields": [{"name": "a", "type": "int"}, {"name": "b", "type": "boolean"}]}
    rec_rev = {"type": "record", "name": "R2",
               "fields": [{"name": "z", "type": "int"}, {"name": "a", "type": "int"}]}
    enum_s = {"type": "enum", "name": "Color", "symbols": ["RED", "GREEN", "BLUE"]}

    # ---- clean cases (a contract-conformant encoder and the shipped seed agree) ----
    cases.append(_c("ok_int", "int", 7))
    cases.append(_c("ok_long", "long", 300))
    cases.append(_c("ok_bool_t", "boolean", True))
    cases.append(_c("ok_bool_f", "boolean", False))
    cases.append(_c("ok_null", "null", None))
    cases.append(_c("ok_str_ascii", "string", "hello"))
    cases.append(_c("ok_bytes", "bytes", "cafe1234"))
    cases.append(_c("ok_enum", enum_s, "GREEN"))
    cases.append(_c("ok_record_alpha", rec_alpha, {"a": 5, "b": True}))

    # ---- zig-zag of negative integers ----
    cases.append(_c("neg_int", "int", -5))
    cases.append(_c("neg_long_big", "long", -1234567890))
    cases.append(_c("neg_one", "long", -1))

    # ---- string length is in UTF-8 octets, not characters ----
    cases.append(_c("str_accent", "string", "café"))     # 'é' = 2 octets
    cases.append(_c("str_emoji", "string", "a\U0001f600b"))   # emoji = 4 octets
    cases.append(_c("str_cjk", "string", "中文"))     # 2 CJK = 6 octets

    # ---- float and double are little-endian IEEE 754 ----
    cases.append(_c("float_pi", "float", 3.14))
    cases.append(_c("double_pi", "double", 3.141592653589793))
    cases.append(_c("float_neg", "float", -0.5))

    # ---- arrays and maps end with a zero-count block ----
    cases.append(_c("array_ints", {"type": "array", "items": "int"}, [1, 2, 3]))
    cases.append(_c("array_empty", {"type": "array", "items": "int"}, []))
    cases.append(_c("map_ints", {"type": "map", "values": "int"}, {"x": 1, "y": 2}))

    # ---- record fields follow schema declaration order, not sorted ----
    cases.append(_c("record_reordered", rec_rev, {"z": 9, "a": 1}))

    # ---- a union is the branch index then the value ----
    cases.append(_c("union_null", ["null", "int"], None))
    cases.append(_c("union_int", ["null", "int"], {"int": 42}))
    cases.append(_c("union_str", ["null", "string"], {"string": "hi"}))

    # ---- fixed is raw bytes with no length prefix ----
    cases.append(_c("fixed4", {"type": "fixed", "name": "F", "size": 4}, "deadbeef"))

    # ---- nesting ----
    nested = {"type": "record", "name": "Outer", "fields": [
        {"name": "id", "type": "long"},
        {"name": "tags", "type": {"type": "array", "items": "string"}},
        {"name": "score", "type": "double"},
    ]}
    cases.append(_c("nested", nested, {"id": -2, "tags": ["x", "café"], "score": 1.5}))

    # ---- non-conforming values must be rejected ----
    cases.append(_c("err_type", "int", "not-an-int"))
    cases.append(_c("err_enum", enum_s, "PURPLE"))
    cases.append(_c("err_fixed_len", {"type": "fixed", "name": "F", "size": 4}, "dead"))

    inp = {"cases": cases}
    return inp, decode_input(inp)
