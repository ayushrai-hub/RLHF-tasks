"""Generate sample and verifier MSEQ binary fixtures."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

MAGIC = b"MQ"
TYPE_WAYPOINT = 0x01
TYPE_FOOTER = 0xFE
CRC_EXTRA = 0x4D


def crc_accumulate(data: int, crc: int) -> int:
    tmp = (data ^ (crc & 0xFF)) & 0xFF
    tmp = (tmp ^ ((tmp << 4) & 0xFF)) & 0xFF
    return ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF


def x25_crc(data: bytes, crc_extra: int | None = None) -> int:
    crc = 0xFFFF
    for b in data:
        crc = crc_accumulate(b, crc)
    if crc_extra is not None:
        crc = crc_accumulate(crc_extra, crc)
    return crc


def waypoint_body(
    upload_id: str,
    seq: int,
    lat_e7: int,
    lon_e7: int,
    alt_mm: int,
    frame: int,
    flags: int,
) -> bytes:
    uid = upload_id.encode()
    body = bytes([1, TYPE_WAYPOINT, len(uid)]) + uid
    body += struct.pack(">H", seq)
    body += struct.pack(">i", lat_e7)
    body += struct.pack(">i", lon_e7)
    body += struct.pack(">i", alt_mm)
    body += bytes([frame, flags])
    extra = CRC_EXTRA if flags & 0x01 else None
    crc = x25_crc(body, extra)
    return MAGIC + body + struct.pack(">H", crc)


def footer_body(upload_id: str, expected_count: int) -> bytes:
    uid = upload_id.encode()
    body = bytes([1, TYPE_FOOTER, len(uid)]) + uid
    body += struct.pack(">H", expected_count)
    crc = x25_crc(body, None)
    return MAGIC + body + struct.pack(">H", crc)


def patch_footer_expected_count(log: bytes, bad_count: int) -> bytes:
    marker = bytes([1, TYPE_FOOTER])
    footer_off = log.rfind(marker)
    if footer_off < 0:
        raise ValueError("footer record not found")
    uid_len = log[footer_off + 2]
    count_off = footer_off + 3 + uid_len
    out = bytearray(log)
    out[count_off : count_off + 2] = struct.pack(">H", bad_count)
    body = bytes(out[footer_off : count_off + 2])
    crc = x25_crc(body, None)
    out[count_off + 2 : count_off + 4] = struct.pack(">H", crc)
    return bytes(out)


def patch_footer_upload_id(log: bytes, wrong_upload_id: str) -> bytes:
    marker = bytes([1, TYPE_FOOTER])
    footer_off = log.rfind(marker)
    if footer_off < 2:
        raise ValueError("footer record not found")
    magic_off = footer_off - 2
    uid_len = log[footer_off + 2]
    count_off = footer_off + 3 + uid_len
    expected_count = struct.unpack(">H", log[count_off : count_off + 2])[0]
    new_footer = footer_body(wrong_upload_id, expected_count)
    return log[:magic_off] + new_footer


def build_log(upload_id: str, waypoints: list[dict], noise_prefix: bytes = b"") -> bytes:
    chunks = [noise_prefix]
    for wp in waypoints:
        chunks.append(
            waypoint_body(
                upload_id,
                wp["seq"],
                wp["lat_e7"],
                wp["lon_e7"],
                wp["alt_mm"],
                wp["frame"],
                wp.get("flags", 0x01),
            )
        )
    chunks.append(footer_body(upload_id, len(waypoints)))
    return b"".join(chunks)


def alpha_waypoints() -> list[dict]:
    return [
        {
            "seq": 0,
            "lat_e7": 377749000,
            "lon_e7": -1224194000,
            "alt_mm": 170500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 377750000,
            "lon_e7": -1224180000,
            "alt_mm": 175000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 2,
            "lat_e7": 377752000,
            "lon_e7": -1224170000,
            "alt_mm": 180000,
            "frame": 0,
            "flags": 0x01,
        },
    ]


def write_sample(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = build_log("alpha-01", alpha_waypoints(), noise_prefix=b"\x00\xff\x00")
    (out_dir / "sample-alpha.mseq").write_bytes(sample)


def write_verifier_fixtures(fixtures_dir: Path) -> None:
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    beta_wps = [
        {
            "seq": 0,
            "lat_e7": 512000000,
            "lon_e7": -1000000,
            "alt_mm": 95000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 512010000,
            "lon_e7": -990000,
            "alt_mm": 100000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "beta_clean.mseq").write_bytes(build_log("beta-02", beta_wps))
    (fixtures_dir / "beta_replay.mseq").write_bytes(build_log("beta-02", beta_wps))

    gamma_wps = alpha_waypoints()[:2]
    gamma = build_log("gamma-bad", gamma_wps)
    corrupt = bytearray(gamma)
    corrupt[-4] ^= 0xFF
    (fixtures_dir / "gamma_corrupt.mseq").write_bytes(bytes(corrupt))

    delta_wps = [
        {
            "seq": 2,
            "lat_e7": 377760000,
            "lon_e7": -1224100000,
            "alt_mm": 160000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 0,
            "lat_e7": 377749000,
            "lon_e7": -1224194000,
            "alt_mm": 170500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 377755000,
            "lon_e7": -1224150000,
            "alt_mm": 172000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "delta_out_of_order.mseq").write_bytes(build_log("delta-03", delta_wps))

    echo_wps = [
        {
            "seq": 0,
            "lat_e7": 400000000,
            "lon_e7": -740000000,
            "alt_mm": 200000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "echo_upload_a.mseq").write_bytes(build_log("echo-a", echo_wps))
    echo_b = [
        {
            "seq": 0,
            "lat_e7": 410000000,
            "lon_e7": -750000000,
            "alt_mm": 210000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "echo_upload_b.mseq").write_bytes(build_log("echo-b", echo_b))

    foxtrot_wps = [
        {
            "seq": 0,
            "lat_e7": 377748000,
            "lon_e7": -1224200000,
            "alt_mm": 165000,
            "frame": 3,
            "flags": 0x00,
        },
        {
            "seq": 1,
            "lat_e7": 377751000,
            "lon_e7": -1224185000,
            "alt_mm": 168000,
            "frame": 0,
            "flags": 0x00,
        },
    ]
    (fixtures_dir / "foxtrot_flags_zero.mseq").write_bytes(build_log("foxtrot-00", foxtrot_wps))

    hotel_wps = alpha_waypoints()[:2]
    hotel_log = build_log("hotel-04", hotel_wps)
    (fixtures_dir / "hotel_footer_count.mseq").write_bytes(
        patch_footer_expected_count(hotel_log, 99)
    )

    india_wps = alpha_waypoints()[:1]
    india_log = build_log("india-04", india_wps)
    (fixtures_dir / "india_upload_id.mseq").write_bytes(
        patch_footer_upload_id(india_log, "india-wrong")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", type=Path, default=Path("/app/data"))
    parser.add_argument("--fixtures-dir", type=Path, default=None)
    args = parser.parse_args()
    write_sample(args.sample_dir)
    if args.fixtures_dir is not None:
        write_verifier_fixtures(args.fixtures_dir)


if __name__ == "__main__":
    main()
