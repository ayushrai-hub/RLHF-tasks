#!/usr/bin/env python3
"""Reference implementation of the SFmt contract and corpus generator.

This module is the source of truth for the held-out conformance corpus. It is
never shipped into the agent environment. It renders each vector with a faithful
Python implementation of docs/sfmt-spec.md and writes the exact expected bytes
next to each input, so the corpus is trustworthy independent of the C code.
"""

import os
import sys

DIGITS_MAX = 4
PAD_MAX = 4096


class SpecError(Exception):
    def __init__(self, token):
        self.token = token


ERR_BAD_SPEC = "@ERR:BAD_SPEC"
ERR_MIX = "@ERR:MIX"
ERR_ARG_COUNT = "@ERR:ARG_COUNT"
ERR_ARG_TYPE = "@ERR:ARG_TYPE"
ERR_PERCENT_N = "@ERR:PERCENT_N"
ERR_BAD_UTF8 = "@ERR:BAD_UTF8"
ERR_BAD_SCALAR = "@ERR:BAD_SCALAR"

FLAG_BYTES = set(b"-+ #0'")
DECIMAL = ("d", "i", "u")
NUMERIC = ("d", "i", "u", "x", "X", "o", "b")
CONVS = set("diuxXobcCsn%")

REQUIRED_TYPE = {
    "d": "i",
    "i": "i",
    "u": "u",
    "x": "u",
    "X": "u",
    "o": "u",
    "b": "u",
    "c": "c",
    "C": "C",
    "s": "s",
}


def group_from_right(d):
    if not d:
        return d
    out = []
    n = len(d)
    for i, c in enumerate(d):
        if i > 0 and (n - i) % 3 == 0:
            out.append("_")
        out.append(c)
    return "".join(out)


def grouped_zero_fill(sig, F):
    """Zero-pad and group `sig` so the result is exactly F chars, no leading _."""
    n = len(sig) if sig else 1
    while n + (n - 1) // 3 < F:
        n += 1
    digits = sig.rjust(n, "0") if sig else "0" * n
    g = group_from_right(digits)
    if len(g) > F:
        g = g[len(g) - F :]
        if g and g[0] == "_":
            g = "0" + g[1:]
    return g


def _pad(prefix, body, flags, width):
    full = prefix + body
    if width is None or len(full) >= width:
        return full
    pad = width - len(full)
    if "-" in flags:
        return full + " " * pad
    return " " * pad + full


def _render_numeric(conv, arg, flags, width, precision):
    if conv in ("d", "i"):
        v = arg[1]
        neg = v < 0
        sig = str(-v if neg else v)
    else:
        v = arg[1]
        neg = False
        sig = format(v, {"u": "d", "x": "x", "X": "X", "o": "o", "b": "b"}[conv])

    if precision is not None:
        if precision == 0 and v == 0:
            sig = ""
        elif len(sig) < precision:
            sig = sig.rjust(precision, "0")

    is_dec = conv in DECIMAL
    grouped = is_dec and "'" in flags

    if conv in ("d", "i"):
        prefix = (
            "-" if neg else ("+" if "+" in flags else (" " if " " in flags else ""))
        )
    else:
        prefix = (
            {"x": "0x", "X": "0X", "o": "0o", "b": "0b"}[conv]
            if ("#" in flags and v != 0 and conv != "u")
            else ""
        )

    zero = ("0" in flags) and ("-" not in flags) and (precision is None)
    grouped_body = group_from_right(sig) if grouped else sig
    natural = len(prefix) + len(grouped_body)

    if width is not None and width > natural and zero:
        F = width - len(prefix)
        body = grouped_zero_fill(sig, F) if grouped else sig.rjust(F, "0")
        return (prefix + body).encode("ascii")

    return _pad(prefix, grouped_body, flags, width).encode("ascii")


def _pad_bytes(token, flags, width):
    if width is None or len(token) >= width:
        return token
    pad = b" " * (width - len(token))
    return token + pad if "-" in flags else pad + token


def render(fmt: bytes, args: list) -> bytes:
    try:
        return _render(fmt, args)
    except SpecError as e:
        return e.token.encode("ascii")


def _read_int_run(fmt, i):
    start = i
    while i < len(fmt) and 0x30 <= fmt[i] <= 0x39:
        i += 1
    return fmt[start:i], i


def _render(fmt: bytes, args: list) -> bytes:
    out = bytearray()
    i = 0
    n = len(fmt)
    mode = None
    cursor = 0
    referenced = set()

    def take_seq():
        nonlocal cursor
        if cursor >= len(args):
            raise SpecError(ERR_ARG_COUNT)
        a = args[cursor]
        cursor += 1
        return a

    while i < n:
        b = fmt[i]
        if b != 0x25:
            out.append(b)
            i += 1
            continue

        i += 1
        if i >= n:
            raise SpecError(ERR_BAD_SPEC)

        index = None
        run, j = _read_int_run(fmt, i)
        if run and j < n and fmt[j] == 0x24:
            if len(run) > DIGITS_MAX:
                raise SpecError(ERR_BAD_SPEC)
            index = int(run)
            i = j + 1

        flags = set()
        while i < n and fmt[i] in FLAG_BYTES:
            flags.add(chr(fmt[i]))
            i += 1

        width = None
        width_star = False
        if i < n and fmt[i] == 0x2A:  # '*'
            width_star = True
            i += 1
        else:
            wrun, i = _read_int_run(fmt, i)
            if len(wrun) > DIGITS_MAX:
                raise SpecError(ERR_BAD_SPEC)
            width = int(wrun) if wrun else None

        precision = None
        prec_star = False
        if i < n and fmt[i] == 0x2E:
            i += 1
            if i < n and fmt[i] == 0x2A:
                prec_star = True
                i += 1
            else:
                prun, i = _read_int_run(fmt, i)
                if len(prun) > DIGITS_MAX:
                    raise SpecError(ERR_BAD_SPEC)
                precision = int(prun) if prun else 0

        if i >= n:
            raise SpecError(ERR_BAD_SPEC)
        conv = chr(fmt[i])
        i += 1

        if conv == "%":
            if (
                index is not None
                or flags
                or width is not None
                or width_star
                or precision is not None
                or prec_star
            ):
                raise SpecError(ERR_BAD_SPEC)
            out.append(0x25)
            continue
        if conv not in CONVS:
            raise SpecError(ERR_BAD_SPEC)
        if conv == "n":
            raise SpecError(ERR_PERCENT_N)

        if (width_star or prec_star) and index is not None:
            raise SpecError(ERR_BAD_SPEC)

        if index is not None:
            if mode == "seq":
                raise SpecError(ERR_MIX)
            mode = "pos"
        else:
            if mode == "pos":
                raise SpecError(ERR_MIX)
            mode = "seq"

        eff_flags = set(flags)
        if width_star:
            wa = take_seq()
            if wa[0] != "i":
                raise SpecError(ERR_ARG_TYPE)
            wv = wa[1]
            if wv < 0:
                eff_flags.add("-")
                width = -wv
            else:
                width = wv
            if width > PAD_MAX:
                raise SpecError(ERR_BAD_SPEC)
        if prec_star:
            pa = take_seq()
            if pa[0] != "i":
                raise SpecError(ERR_ARG_TYPE)
            pv = pa[1]
            precision = None if pv < 0 else pv
            if precision is not None and precision > PAD_MAX:
                raise SpecError(ERR_BAD_SPEC)

        if index is not None:
            if index < 1 or index > len(args):
                raise SpecError(ERR_ARG_COUNT)
            referenced.add(index)
            arg = args[index - 1]
        else:
            arg = take_seq()

        if arg[0] != REQUIRED_TYPE[conv]:
            raise SpecError(ERR_ARG_TYPE)

        if conv in NUMERIC:
            out += _render_numeric(conv, arg, eff_flags, width, precision)
        elif conv == "c":
            out += _pad_bytes(bytes([arg[1]]), eff_flags, width)
        elif conv == "C":
            sv = arg[1]
            if sv > 0x10FFFF or 0xD800 <= sv <= 0xDFFF:
                raise SpecError(ERR_BAD_SCALAR)
            out += _pad_bytes(chr(sv).encode("utf-8"), eff_flags, width)
        elif conv == "s":
            raw = arg[1]
            if precision is None:
                token = raw
            else:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    raise SpecError(ERR_BAD_UTF8)
                token = (
                    text[:precision].encode("utf-8") if len(text) > precision else raw
                )
            out += _pad_bytes(token, eff_flags, width)

    if mode == "pos":
        for k in range(1, len(args) + 1):
            if k not in referenced:
                raise SpecError(ERR_ARG_COUNT)
    else:
        if cursor != len(args):
            raise SpecError(ERR_ARG_COUNT)

    return bytes(out)


# ---------------------------------------------------------------------------
# Vector encoding (must match the C CLI decoder)
# ---------------------------------------------------------------------------


def enc_bytes(b: bytes) -> str:
    out = []
    for x in b:
        if x == 0x5C:
            out.append("\\\\")
        elif x == 0x0A:
            out.append("\\n")
        elif x == 0x09:
            out.append("\\t")
        elif x == 0x0D:
            out.append("\\r")
        elif x == 0x00:
            out.append("\\0")
        elif 0x20 <= x < 0x7F:
            out.append(chr(x))
        else:
            out.append("\\x%02x" % x)
    return "".join(out)


def vec_text(fmt: bytes, args: list) -> str:
    lines = ["fmt\t" + enc_bytes(fmt)]
    for a in args:
        if a[0] == "s":
            lines.append("arg\ts\t" + enc_bytes(a[1]))
        else:
            lines.append("arg\t%s\t%d" % (a[0], a[1]))
    return "\n".join(lines) + "\n"


def sarg(text_or_bytes):
    if isinstance(text_or_bytes, str):
        return ("s", text_or_bytes.encode("utf-8"))
    return ("s", text_or_bytes)


# ---------------------------------------------------------------------------
# Corpus definition
# ---------------------------------------------------------------------------

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1
UINT64_MAX = 2**64 - 1


def build_vectors():
    V = []

    def add(name, fmt, args):
        if isinstance(fmt, str):
            fmt = fmt.encode("utf-8")
        V.append((name, fmt, args))

    for v in (0, 1, 7, 42, -1, -42, 255, 1000, -1000, INT64_MAX, INT64_MIN):
        add("d_%d" % v, "[%d]", [("i", v)])
        add("i_%d" % v, "<%i>", [("i", v)])
    for v in (0, 1, 8, 255, 256, 4095, 65535, UINT64_MAX):
        add("u_%d" % v, "[%u]", [("u", v)])
        add("x_%d" % v, "[%x]", [("u", v)])
        add("X_%d" % v, "[%X]", [("u", v)])
        add("o_%d" % v, "[%o]", [("u", v)])
        add("b_%d" % v, "[%b]", [("u", v)])

    for v in (42, -42, 0):
        add("plus_%d" % v, "[%+d]", [("i", v)])
        add("space_%d" % v, "[% d]", [("i", v)])
        add("plusspace_%d" % v, "[%+ d]", [("i", v)])

    for v in (0, 5, 8, 255, 4096):
        add("altx_%d" % v, "[%#x]", [("u", v)])
        add("altX_%d" % v, "[%#X]", [("u", v)])
        add("alto_%d" % v, "[%#o]", [("u", v)])
        add("altb_%d" % v, "[%#b]", [("u", v)])

    # grouping
    for v in (0, 12, 123, 1234, 1234567, 1000000000, -1234567):
        add("grp_%d" % v, "[%'d]", [("i", v)])
    add("grpprec", "[%'.9d]", [("i", 1234567)])
    add("grpwidth", "[%'15d]", [("i", 1234567)])
    add("grpu", "[%'u]", [("u", 1234567)])

    # grouped zero pad (the glibc fixpoint)
    for w in (6, 8, 9, 10, 11, 12, 15):
        for v in (0, 1, 1234, 1234567, -1234, -99):
            add("gz_%d_%d" % (w, v), "[%%'0%dd]" % w, [("i", v)])
    add("gz_sign", "[%+'015d]", [("i", 1234)])
    add("gz_space", "[% '012d]", [("i", 1234)])
    add("gzu", "[%'016u]", [("u", 1234567)])

    # dynamic width / precision
    for wv in (0, 3, -3, 8, -8, 12):
        for v in (5, -5, 0, 1234):
            add("dw_%d_%d" % (wv, v), "[%*d]", [("i", wv), ("i", v)])
    for pv in (0, 3, 5, -1):
        for v in (0, 7, 42):
            add("dp_%d_%d" % (pv, v), "[%.*d]", [("i", pv), ("i", v)])
    add("dwp1", "[%*.*d]", [("i", 10), ("i", 4), ("i", 42)])
    add("dwp2", "[%*.*x]", [("i", -10), ("i", 6), ("u", 255)])
    add("dw_group", "[%'0*d]", [("i", 15), ("i", 1234)])
    add("dw_s", "[%*s]", [("i", 8), sarg("hi")])
    add("dw_s_neg", "[%*s]", [("i", -8), sarg("hi")])
    add("dp_s", "[%.*s]", [("i", 3), sarg("héllo")])

    # strings / bytes / scalars
    add("s_plain", "[%s]", [sarg("hello")])
    add("s_empty", "[%s]", [sarg("")])
    add("s_w", "[%8s]", [sarg("hi")])
    add("s_wl", "[%-8s]", [sarg("hi")])
    add("s_prec", "[%.3s]", [sarg("hello")])
    add("s_prec_utf8", "[%.3s]", [sarg("héllo")])
    add("s_prec_emoji", "[%.2s]", [sarg("a😀b")])
    add("s_prec_ge_len", "[%.9s]", [sarg("héllo")])
    add("s_bytes_raw", "[%s]", [("s", b"\x00\x01\xff raw")])
    add("s_zeroflag_ignored", "[%08s]", [sarg("hi")])
    for v in (65, 97, 48, 32, 0, 255):
        add("c_%d" % v, "[%c]", [("c", v)])
    add("c_width", "[%4c]", [("c", 65)])
    add("c_left", "[%-4c]", [("c", 65)])
    for sv in (
        0x00,
        0x41,
        0x7F,
        0x80,
        0x7FF,
        0x800,
        0xFFFF,
        0x10000,
        0x1F600,
        0x10FFFF,
    ):
        add("C_%x" % sv, "[%C]", [("C", sv)])
    add("C_width", "[%6C]", [("C", 0x1F600)])

    # positional
    add("pos_swap", "[%2$d %1$d]", [("i", 1), ("i", 2)])
    add("pos_reuse2", "[%1$s-%1$s]", [sarg("x")])
    add("pos_three", "%3$s %2$s %1$s", [sarg("a"), sarg("b"), sarg("c")])
    add("pos_mixtypes", "%1$d/%2$u/%3$s", [("i", -5), ("u", 5), sarg("z")])

    # literals
    add("pct", "100%%done", [])
    add("only_pct", "%%", [])
    add("empty", "", [])
    add("literal_run", "no conversions here", [])
    add("multi", "%d+%d=%d", [("i", 2), ("i", 3), ("i", 5)])
    add("nl_tab", "a\tb\nc", [])

    # boundaries
    add("bd_u64max_x", "[%x]", [("u", UINT64_MAX)])
    add("bd_i64min", "[%d]", [("i", INT64_MIN)])
    add("bd_width_eq", "[%3d]", [("i", 123)])
    add("bd_prec0_zero_hash_o", "[%#.0o]", [("u", 0)])

    # reject vectors
    add("rej_n", "a%nb", [])
    add("rej_n_arg", "%d%n", [("i", 1)])
    add("rej_too_few", "%d%d", [("i", 1)])
    add("rej_too_many", "%d", [("i", 1), ("i", 2)])
    add("rej_none_but_args", "no conv", [("i", 1)])
    add("rej_argtype_du", "%d", [("u", 1)])
    add("rej_argtype_su", "%s", [("u", 1)])
    add("rej_argtype_dc", "%d", [("c", 65)])
    add("rej_mix_ps", "%1$d %d", [("i", 1), ("i", 2)])
    add("rej_mix_sp", "%d %1$d", [("i", 1), ("i", 2)])
    add("rej_pos_gap", "%2$d", [("i", 1), ("i", 2)])
    add("rej_pos_oor", "%3$d", [("i", 1), ("i", 2)])
    add("rej_unknown_conv", "%q", [])
    add("rej_trailing_pct", "abc%", [])
    add("rej_lenmod", "%ld", [("i", 1)])
    add("rej_pct_flags", "%-%", [])
    add("rej_dollar_nodigit", "%$d", [("i", 1)])
    add("rej_scalar_surrogate", "%C", [("C", 0xD800)])
    add("rej_scalar_high", "%C", [("C", 0x110000)])
    add("rej_badutf8_prec", "%.2s", [("s", b"\xff\xfe")])
    add("rej_star_pos", "%1$*d", [("i", 3), ("i", 5)])
    add("rej_star_type", "%*d", [("u", 3), ("i", 5)])
    add("rej_star_few", "%*d", [("i", 3)])
    add("rej_starprec_type", "%.*d", [("u", 3), ("i", 5)])

    return V


def expand(vectors):
    """Dense feature-combination coverage under all-or-nothing grading."""
    extra = []
    dspecs = [
        "%d",
        "%+d",
        "% d",
        "%5d",
        "%-5d",
        "%05d",
        "%.3d",
        "%'d",
        "%+08.4d",
        "%'012d",
        "%+'015d",
        "%-'12d",
        "% '010d",
        "%'.6d",
        "%012d",
        "%-8.4d",
        "%+.0d",
    ]
    for si, spec in enumerate(dspecs):
        for v in (0, 3, -3, 99, -99, 1234, -1234, 100000, -100000, 1234567):
            extra.append(
                ("xd_%d_%d" % (si, v), ("[" + spec + "]").encode(), [("i", v)])
            )
    uspecs = [
        "%u",
        "%x",
        "%X",
        "%o",
        "%b",
        "%#x",
        "%#o",
        "%#b",
        "%08x",
        "%.5o",
        "%'u",
        "%#012x",
        "%016o",
        "%-#14x",
        "%.8b",
        "%'014u",
    ]
    for si, spec in enumerate(uspecs):
        for v in (0, 1, 63, 64, 255, 1023, 0xDEADBEEF, 0xFFFF):
            extra.append(
                ("xu_%d_%d" % (si, v), ("[" + spec + "]").encode(), [("u", v)])
            )
    sspecs = ["%s", "%6s", "%-6s", "%.2s", "%.4s", "%8.3s", "%-10.4s"]
    for si, spec in enumerate(sspecs):
        for w in ("a", "ab", "héllo", "😀x", "mix€d", "abcdef"):
            extra.append(
                (
                    "xs_%d_%s" % (si, w.encode().hex()),
                    ("[" + spec + "]").encode(),
                    [sarg(w)],
                )
            )
    # dynamic width/precision cross product
    for wv in (-6, -1, 0, 4, 7, 10):
        for v in (0, 7, -7, 4242):
            extra.append(("xdw_%d_%d" % (wv, v), b"[%*d]", [("i", wv), ("i", v)]))
    for pv in (-1, 0, 2, 5):
        for v in (0, 5, 12345):
            extra.append(("xdp_%d_%d" % (pv, v), b"[%.*x]", [("i", pv), ("u", v)]))

    # Held-out hardening of the grouping edges most often mis-implemented:
    # the grouped-zero-fill boundary (grouped magnitude >= field width, so no
    # zeros are added), small-value grouped zero-fill (< four significant
    # digits), and ' grouping on %u. These stay out of the shipped example set
    # on purpose, so a solution that only self-tests the visible cases still
    # has to reason about the whole rule.
    harden = []
    for w in (5, 6, 7, 8, 9):
        harden.append(("hb_d%d" % w, ("[%%'0%dd]" % w).encode(), [("i", 1234567)]))
        harden.append(("hb_u%d" % w, ("[%%'0%du]" % w).encode(), [("u", 1234567)]))
    for v in (12, 123):
        for w in (4, 6, 8, 10):
            harden.append(("hs_%d_%d" % (w, v), ("[%%'0%dd]" % w).encode(), [("i", v)]))
    for v in (1, 12, 123, 1234, 12345, 999999):
        harden.append(("hgu_%d" % v, b"[%'u]", [("u", v)]))
    return vectors + extra + harden


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    task = os.path.dirname(root)
    corpus_dir = os.path.join(task, "tests", "corpus")
    examples_dir = os.path.join(task, "environment", "testdata", "examples")
    os.makedirs(corpus_dir, exist_ok=True)
    os.makedirs(examples_dir, exist_ok=True)

    for f in os.listdir(corpus_dir):
        os.remove(os.path.join(corpus_dir, f))
    for f in os.listdir(examples_dir):
        os.remove(os.path.join(examples_dir, f))

    selftest()

    vectors = expand(build_vectors())

    example_names = {
        "d_-42",
        "u_255",
        "altX_255",
        "alto_8",
        "grp_1234567",
        "gz_15_1234",
        "gz_15_1234567",
        "dw_-8_5",
        "dwp1",
        "s_prec_utf8",
        "C_1f600",
        "pos_swap",
        "only_pct",
        "rej_n",
        "rej_argtype_du",
        "rej_star_pos",
    }

    seen = set()
    ci = 0
    for name, fmt, args in vectors:
        if name in seen:
            raise SystemExit("duplicate vector name: " + name)
        seen.add(name)
        out = render(fmt, args)
        text = vec_text(fmt, args)
        if name in example_names:
            with open(
                os.path.join(examples_dir, name + ".vec"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                f.write(text)
            with open(os.path.join(examples_dir, name + ".out"), "wb") as f:
                f.write(out)
        stem = "%04d_%s" % (ci, name)
        ci += 1
        with open(
            os.path.join(corpus_dir, stem + ".vec"), "w", encoding="utf-8", newline="\n"
        ) as f:
            f.write(text)
        with open(os.path.join(corpus_dir, stem + ".out"), "wb") as f:
            f.write(out)

    print("corpus vectors:", ci)
    print("visible examples:", len(example_names))


def selftest():
    cases = [
        (b"[%d]", [("i", -42)], b"[-42]"),
        (b"[%05d]", [("i", -42)], b"[-0042]"),
        (b"[%5.3d]", [("i", 7)], b"[  007]"),
        (b"[%'d]", [("i", 1234567)], b"[1_234_567]"),
        (b"[%#o]", [("u", 8)], b"[0o10]"),
        (b"[%#b]", [("u", 5)], b"[0b101]"),
        (b"[%.0d]", [("i", 0)], b"[]"),
        (b"[%-6s]", [sarg("hi")], b"[hi    ]"),
        (b"[%.3s]", [sarg("héllo")], "[hél]".encode("utf-8")),
        (b"[%C]", [("C", 0x1F600)], "[😀]".encode("utf-8")),
        (b"[%2$d %1$d]", [("i", 1), ("i", 2)], b"[2 1]"),
        (b"%%", [], b"%"),
        # grouped zero pad
        (b"[%'015d]", [("i", 1234)], b"[000_000_001_234]"),
        (b"[%'08d]", [("i", 1234)], b"[0001_234]"),
        (b"[%'010d]", [("i", 1234)], b"[00_001_234]"),
        (b"[%+'015d]", [("i", 1234)], b"[+00_000_001_234]"),
        # dynamic width/precision
        (b"[%*d]", [("i", 8), ("i", 42)], b"[      42]"),
        (b"[%*d]", [("i", -8), ("i", 42)], b"[42      ]"),
        (b"[%.*d]", [("i", 4), ("i", 42)], b"[0042]"),
        (b"[%.*d]", [("i", -1), ("i", 42)], b"[42]"),
        (b"[%*.*d]", [("i", 10), ("i", 4), ("i", 42)], b"[      0042]"),
        # rejects
        (b"a%nb", [], b"@ERR:PERCENT_N"),
        (b"%d", [("u", 1)], b"@ERR:ARG_TYPE"),
        (b"%d %1$d", [("i", 1), ("i", 2)], b"@ERR:MIX"),
        (b"%C", [("C", 0xD800)], b"@ERR:BAD_SCALAR"),
        (b"%.2s", [("s", b"\xff\xfe")], b"@ERR:BAD_UTF8"),
        (b"%q", [], b"@ERR:BAD_SPEC"),
        (b"%d%d", [("i", 1)], b"@ERR:ARG_COUNT"),
        (b"%1$*d", [("i", 3), ("i", 5)], b"@ERR:BAD_SPEC"),
        (b"%*d", [("u", 3), ("i", 5)], b"@ERR:ARG_TYPE"),
    ]
    for fmt, args, want in cases:
        got = render(fmt, args)
        if got != want:
            raise SystemExit(
                "SELFTEST FAIL fmt=%r args=%r got=%r want=%r" % (fmt, args, got, want)
            )
    print("selftest: %d spec examples OK" % len(cases), file=sys.stderr)


if __name__ == "__main__":
    main()
