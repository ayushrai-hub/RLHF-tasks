#!/usr/bin/env python3
"""Generate the Geneve packet fixtures consumed by the Go tests and
the per-milestone verifier scripts.

Each fixture is one binary Geneve packet at /app/testdata/<name>.bin.
Re-run after editing this script:

    python /app/tools/gen_fixtures.py --out /app/testdata
"""

import argparse
import os
import struct
import sys


def fixed_header(opt_len_words: int, *, version: int = 0, oam: bool = False,
                 critical: bool = False, reserved6: int = 0,
                 protocol_type: int = 0x6558, vni: int = 0x010203,
                 reserved8: int = 0) -> bytes:
    """Build the 8-byte Geneve fixed header.

    Layout (RFC 8926 §3.4):
      byte 0: Version(2) | OptLen(6)
      byte 1: O(1) | C(1) | Rsvd(6)
      bytes 2-3: ProtocolType
      bytes 4-6: VNI (24 bits)
      byte 7: Reserved
    """
    if not 0 <= version <= 3:
        raise ValueError(f"version out of 2-bit range: {version}")
    if not 0 <= opt_len_words <= 63:
        raise ValueError(f"opt_len_words out of 6-bit range: {opt_len_words}")
    b0 = ((version & 0x03) << 6) | (opt_len_words & 0x3F)
    b1 = ((0x80 if oam else 0) | (0x40 if critical else 0)
          | (reserved6 & 0x3F))
    return struct.pack(">BBHBBBB",
                       b0, b1, protocol_type,
                       (vni >> 16) & 0xFF, (vni >> 8) & 0xFF, vni & 0xFF,
                       reserved8 & 0xFF)


def option(opt_class: int, type7: int, *, critical: bool = False,
           r_bits: int = 0, payload: bytes = b"") -> bytes:
    """Build one TLV option.

    Layout (RFC 8926 §3.5):
      bytes 0-1: OptClass
      byte 2: C(1) | Type(7)
      byte 3: R(3, MSBs 5..7) | Length(5, LSBs 0..4) — Length in 4-byte words.

    Payload length MUST be a multiple of 4.
    """
    if len(payload) % 4 != 0:
        raise ValueError(f"option payload not a 4-byte multiple: {len(payload)}")
    if not 0 <= r_bits <= 7:
        raise ValueError(f"r_bits out of 3-bit range: {r_bits}")
    length_words = len(payload) // 4
    if not 0 <= length_words <= 31:
        raise ValueError(f"length_words out of 5-bit range: {length_words}")
    byte2 = (0x80 if critical else 0) | (type7 & 0x7F)
    byte3 = ((r_bits & 0x07) << 5) | (length_words & 0x1F)
    return struct.pack(">HBB", opt_class, byte2, byte3) + payload


def build_packet(*, opt_len_words=None, opts=None, inner=b"", **header_kw) -> bytes:
    opts = opts or []
    body = b"".join(opts)
    if opt_len_words is None:
        if len(body) % 4 != 0:
            raise ValueError("body not a 4-byte multiple")
        opt_len_words = len(body) // 4
    return fixed_header(opt_len_words, **header_kw) + body + inner


def write(out_dir: str, name: str, data: bytes) -> None:
    path = os.path.join(out_dir, name)
    with open(path, "wb") as fh:
        fh.write(data)


FIXTURES = {}


def fixture(name):
    def deco(fn):
        FIXTURES[name] = fn
        return fn
    return deco


@fixture("bare_header.bin")
def _bare_header():
    return build_packet(opt_len_words=0, opts=[], inner=b"")


@fixture("two_clean.bin")
def _two_clean():
    # Class 0x0103 = 259 (ietf), types 5 (u32) and 6 (u128).
    o1 = option(259, 5, payload=struct.pack(">I", 0xCAFEBABE))
    o2 = option(259, 6, payload=b"\x00" * 16)
    return build_packet(opts=[o1, o2])


@fixture("rbits_nonzero.bin")
def _rbits_nonzero():
    o = option(259, 5, r_bits=5, payload=struct.pack(">I", 1))
    return build_packet(opts=[o])


@fixture("version_one.bin")
def _version_one():
    return build_packet(opt_len_words=0, version=1)


@fixture("opt_len_overrun.bin")
def _opt_len_overrun():
    # Fixed header claims OptLen=2 (8 bytes) but body has 4 bytes.
    hdr = fixed_header(2)
    body = option(259, 5, payload=b"\x00\x00\x00\x00")[:4]  # one option header only, 4 bytes
    return hdr + body


@fixture("unknown_crit.bin")
def _unknown_crit():
    # Class 0x9999 type 0x42 critical → not in registry.
    o = option(0x9999, 0x42, critical=True, payload=b"\xDE\xAD\xBE\xEF")
    return build_packet(opts=[o])


@fixture("unknown_noncrit.bin")
def _unknown_noncrit():
    o = option(0x9999, 0x42, critical=False, payload=b"\xDE\xAD\xBE\xEF")
    return build_packet(opts=[o])


@fixture("length_mismatch.bin")
def _length_mismatch():
    # Class 0x0103 type 5 has registered kind u32 (4 bytes). Send 8.
    o = option(259, 5, payload=b"\x00" * 8)
    return build_packet(opts=[o])


@fixture("three_class_0x0103.bin")
def _three_class_0x0103():
    o = option(259, 5, payload=struct.pack(">I", 1))
    return build_packet(opts=[o, o, o])


@fixture("two_class_0x0103_boundary.bin")
def _two_class_0x0103_boundary():
    o = option(259, 5, payload=struct.pack(">I", 1))
    return build_packet(opts=[o, o])


@fixture("experimenter_vendor.bin")
def _experimenter_vendor():
    # OptClass 0xFF00 (experimenter), payload = 4-byte vendor 0x12345678 + 4 bytes.
    vendor = struct.pack(">I", 0x12345678)
    o = option(0xFF00, 0x01, payload=vendor + b"\x00\x00\x00\x00")
    return build_packet(opts=[o])


@fixture("experimenter_vendor_denied.bin")
def _experimenter_vendor_denied():
    vendor = struct.pack(">I", 0xDEADBEEF)
    o = option(0xFF00, 0x01, payload=vendor + b"\x00\x00\x00\x00")
    return build_packet(opts=[o])


@fixture("two_experimenters.bin")
def _two_experimenters():
    v1 = struct.pack(">I", 0x12345678) + b"\x00\x00\x00\x00"
    v2 = struct.pack(">I", 0xABCDABCD) + b"\x00\x00\x00\x00"
    o1 = option(0xFF00, 0x01, payload=v1)
    o2 = option(0xFF00, 0x02, payload=v2)
    return build_packet(opts=[o1, o2])


@fixture("kinds_dispatch.bin")
def _kinds_dispatch():
    struct_payload = struct.pack(">I", 0xCAFEBABE) + b"\x01\x02\x03\x04"
    varbin_payload = b"\xAA\xBB\xCC\xDD"
    opaque_payload = b"\x11\x22\x33\x44"
    o_struct = option(1024, 0x01, payload=struct_payload)
    o_varbin = option(1024, 0x02, payload=varbin_payload)
    o_opaque = option(65520, 0x01, payload=opaque_payload)
    return build_packet(opts=[o_struct, o_varbin, o_opaque])


@fixture("unregistered_ether.bin")
def _unregistered_ether():
    return build_packet(opt_len_words=0, protocol_type=0x9999)


@fixture("oam_unknown_crit.bin")
def _oam_unknown_crit():
    o = option(0x9999, 0x42, critical=True, payload=b"\xDE\xAD\xBE\xEF")
    return build_packet(opts=[o], oam=True)


@fixture("oam_clean.bin")
def _oam_clean():
    o = option(259, 5, payload=struct.pack(">I", 0xCAFEBABE))
    return build_packet(opts=[o], oam=True)


@fixture("reserved8_nonzero.bin")
def _reserved8_nonzero():
    return build_packet(opt_len_words=0, reserved8=0x42)


@fixture("clean_with_inner.bin")
def _clean_with_inner():
    o = option(259, 7, payload=struct.pack(">I", 0xABCDEF01))
    inner = bytes(range(16))  # 16 bytes of inner frame
    return build_packet(opts=[o], inner=inner)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    for name, fn in sorted(FIXTURES.items()):
        write(args.out, name, fn())
        print(f"wrote {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
