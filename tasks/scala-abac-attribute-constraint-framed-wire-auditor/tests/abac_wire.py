"""ABWF wire builder shared by fixture generator and expect helpers."""

from __future__ import annotations

import struct
from typing import Iterable


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= (b & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def attr_pair(key: str, val: str) -> bytes:
    kb, vb = key.encode("utf-8"), val.encode("utf-8")
    return struct.pack(">H", len(kb)) + kb + struct.pack(">H", len(vb)) + vb


def build_event(
    tenant: str,
    eval_seq: int,
    policy_id: str,
    decision: int,
    attrs: dict[str, str],
    utc: int,
) -> bytes:
    out = bytearray()
    out.append(0x02)
    out.extend(tenant.encode("ascii"))
    out.extend(struct.pack(">I", eval_seq))
    pid = policy_id.encode("utf-8")
    out.extend(struct.pack(">H", len(pid)))
    out.extend(pid)
    out.append(decision & 0xFF)
    out.append(len(attrs) & 0xFF)
    for k, v in attrs.items():
        out.extend(attr_pair(k, v))
    out.extend(struct.pack(">I", utc & 0xFFFFFFFF))
    return bytes(out)


EventTuple = tuple[str, int, str, int, dict[str, str], int]


def build_abwf(
    tenant: str,
    batch_id: str,
    events: Iterable[EventTuple],
    *,
    correct_crc: bool = True,
) -> bytes:
    out = bytearray(b"ABWF\x01")
    for ev in events:
        out.extend(build_event(*ev))
    footer_start = len(out)
    out.append(0xFF)
    bid = batch_id.encode("utf-8")
    out.extend(struct.pack(">H", len(bid)))
    out.extend(bid)
    bid_len = len(bid)
    if correct_crc:
        crc_body = bytes(out[5 : footer_start + 1 + 2 + bid_len])
    else:
        crc_body = bytes(out[0:footer_start])
    crc = crc16_ccitt(crc_body)
    out.extend(struct.pack(">H", crc))
    return bytes(out)
