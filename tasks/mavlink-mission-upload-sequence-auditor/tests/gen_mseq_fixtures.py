"""Generate hidden MSEQ logs for verifier anti-cheat."""

from __future__ import annotations

import os
import struct
from pathlib import Path

MAGIC = b"MQ"
TYPE_WAYPOINT = 0x01
TYPE_FOOTER = 0xFE
CRC_EXTRA = 0x4D


def fixture_root() -> Path:
    """Writable directory for generated .mseq logs (Harbor may mount /tests read-only)."""
    env = os.environ.get("MAVLINK_TEST_FIXTURES")
    if env:
        root = Path(env)
        root.mkdir(parents=True, exist_ok=True)
        return root
    for candidate in (
        Path(__file__).resolve().parent / "fixtures" / "logs",
        Path("/tmp/mavlink-mseq-fixtures/logs"),
    ):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue
    raise RuntimeError("no writable fixture directory for mavlink mseq tests")


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
    """Rewrite footer expected_count with a valid CRC (version byte at marker)."""
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
    """Replace footer upload_id (valid CRC) while leaving waypoint records unchanged."""
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


def build_log_with_midstream_noise(upload_id: str, waypoints: list[dict], noise: bytes) -> bytes:
    """Insert noise between the first and second waypoint records."""
    if len(waypoints) < 2:
        raise ValueError("midstream noise requires at least two waypoints")
    first = waypoint_body(
        upload_id,
        waypoints[0]["seq"],
        waypoints[0]["lat_e7"],
        waypoints[0]["lon_e7"],
        waypoints[0]["alt_mm"],
        waypoints[0]["frame"],
        waypoints[0].get("flags", 0x01),
    )
    rest_chunks: list[bytes] = []
    for wp in waypoints[1:]:
        rest_chunks.append(
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
    rest_chunks.append(footer_body(upload_id, len(waypoints)))
    return first + noise + b"".join(rest_chunks)


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


def adversarial_noise_prefix() -> bytes:
    """Deterministic long noise with partial 'M' markers but no contiguous 'MQ'."""
    out = bytearray()
    for i in range(160):
        b = ((i * 37) + 11) & 0xFF
        if b == ord("M"):
            b = ord("N")
        out.append(b)
    # Insert lone 'M' bytes at several offsets to force real scan logic.
    for idx in (3, 29, 61, 97, 143):
        out[idx] = ord("M")
    return bytes(out)


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

    noisy_alpha = build_log("zeta-noise", alpha_waypoints(), adversarial_noise_prefix())
    (fixtures_dir / "zeta_long_noise.mseq").write_bytes(noisy_alpha)

    mid_noise = adversarial_noise_prefix()[:96]
    juliet = build_log_with_midstream_noise("juliet-05", alpha_waypoints(), mid_noise)
    (fixtures_dir / "juliet_midstream_noise.mseq").write_bytes(juliet)

    kilo_wps = [
        {
            "seq": 0,
            "lat_e7": 480000000,
            "lon_e7": -1225000000,
            "alt_mm": 140000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 480050000,
            "lon_e7": -1224950000,
            "alt_mm": 145000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "kilo_cross_batch.mseq").write_bytes(build_log("kilo-06", kilo_wps))

    lima_wps = [
        {
            "seq": 7,
            "lat_e7": 377760000,
            "lon_e7": -1224100000,
            "alt_mm": 155000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "lima_single_wp.mseq").write_bytes(build_log("lima-07", lima_wps))

    beta_mutated = [
        {
            "seq": 0,
            "lat_e7": 512000000,
            "lon_e7": -1000000,
            "alt_mm": 99999,
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
    (fixtures_dir / "mike_replay_mutated.mseq").write_bytes(build_log("beta-02", beta_mutated))

    november_wps = [
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
            "lat_e7": 377750123,
            "lon_e7": -122418123,
            "alt_mm": 172000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 2,
            "lat_e7": 377751456,
            "lon_e7": -122417456,
            "alt_mm": 173500,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "november_rounding_trap.mseq").write_bytes(build_log("november-08", november_wps))

    oscar_wps = [
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
            "frame": 0,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "oscar_mixed_frames.mseq").write_bytes(build_log("oscar-09", oscar_wps))

    papa_dup_wps = [
        {
            "seq": 0,
            "lat_e7": 377749000,
            "lon_e7": -1224194000,
            "alt_mm": 170500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 0,
            "lat_e7": 377750000,
            "lon_e7": -1224180000,
            "alt_mm": 175000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "papa_dup_seq.mseq").write_bytes(build_log("papa-10", papa_dup_wps))

    quebec_wps = alpha_waypoints()[:2]
    quebec_log = build_log("quebec-11", quebec_wps)
    corrupt = bytearray(quebec_log)
    # Flip CRC on the second waypoint record (not the footer).
    magic = b"MQ"
    wp_seen = 0
    idx = 0
    while idx < len(corrupt):
        if idx + 2 <= len(corrupt) and corrupt[idx : idx + 2] == magic:
            rec_type = corrupt[idx + 3]
            if rec_type == 0x01:
                id_len = corrupt[idx + 4]
                rec_len = 2 + 1 + 1 + 1 + id_len + 2 + 4 + 4 + 4 + 1 + 1 + 2
                if wp_seen == 1:
                    corrupt[idx + rec_len - 1] ^= 0xFF
                    break
                wp_seen += 1
                idx += rec_len
                continue
            if rec_type == 0xFE:
                break
        idx += 1
    (fixtures_dir / "quebec_bad_wp_crc.mseq").write_bytes(bytes(corrupt))

    sierra_v1_wps = [
        {
            "seq": 0,
            "lat_e7": 600_000_000,
            "lon_e7": -1_000_000_000,
            "alt_mm": 100_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "sierra_v1.mseq").write_bytes(build_log("sierra-12", sierra_v1_wps))
    sierra_v2_wps = [
        {
            "seq": 0,
            "lat_e7": 600_100_000,
            "lon_e7": -1_001_000_000,
            "alt_mm": 110_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "sierra_v2.mseq").write_bytes(build_log("sierra-12", sierra_v2_wps))

    romeo_wp = {
        "seq": 0,
        "lat_e7": 377_749_000,
        "lon_e7": -1_224_194_000,
        "alt_mm": 170_500,
        "frame": 3,
        "flags": 0x01,
    }
    romeo_log = waypoint_body(
        "body-mismatch",
        romeo_wp["seq"],
        romeo_wp["lat_e7"],
        romeo_wp["lon_e7"],
        romeo_wp["alt_mm"],
        romeo_wp["frame"],
        romeo_wp["flags"],
    ) + footer_body("romeo-12", 1)
    (fixtures_dir / "romeo_body_upload_id.mseq").write_bytes(romeo_log)

    uniform_wps = [
        {
            "seq": 0,
            "lat_e7": 377_749_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 50_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "uniform_negative_alt.mseq").write_bytes(build_log("uniform-13", uniform_wps))

    whiskey_wps = [
        {
            "seq": 3,
            "lat_e7": 480_000_000,
            "lon_e7": -1_230_000_000,
            "alt_mm": 190_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 0,
            "lat_e7": 480_010_000,
            "lon_e7": -1_229_500_000,
            "alt_mm": 185_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 480_020_000,
            "lon_e7": -1_229_000_000,
            "alt_mm": 188_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 2,
            "lat_e7": 480_030_000,
            "lon_e7": -1_228_500_000,
            "alt_mm": 192_000,
            "frame": 0,
            "flags": 0x01,
        },
    ]
    (fixtures_dir / "whiskey.mseq").write_bytes(build_log("whiskey-14", whiskey_wps))


def write_hidden_fixtures(hidden_dir: Path) -> None:
    """Grading-only logs under tests/fixtures/hidden (not shipped in the agent image)."""
    hidden_dir.mkdir(parents=True, exist_ok=True)

    tango_wps = [
        {
            "seq": 0,
            "lat_e7": 400_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 410_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x03,
        },
        {
            "seq": 2,
            "lat_e7": 420_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 0,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "tango_hold.mseq").write_bytes(build_log("tango-15", tango_wps))

    (hidden_dir / "yankee_empty.mseq").write_bytes(build_log("yankee-16", []))

    yankee_all_suppress_wps = [
        {
            "seq": 0,
            "lat_e7": 400_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x04,
        },
        {
            "seq": 1,
            "lat_e7": 400_001_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x04,
        },
        {
            "seq": 2,
            "lat_e7": 400_002_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 3,
            "flags": 0x04,
        },
    ]
    (hidden_dir / "yankee_all_suppress.mseq").write_bytes(
        build_log("yankee-29", yankee_all_suppress_wps)
    )

    xray_wps = [
        {
            "seq": 2,
            "lat_e7": 377_760_000,
            "lon_e7": -1_224_100_000,
            "alt_mm": 160_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 15,
            "lat_e7": 377_770_000,
            "lon_e7": -1_224_000_000,
            "alt_mm": 165_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 7,
            "lat_e7": 377_765_000,
            "lon_e7": -1_224_050_000,
            "alt_mm": 162_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "xray_sparse_seq.mseq").write_bytes(build_log("xray-17", xray_wps))

    victor_wps = [
        {
            "seq": 0,
            "lat_e7": 400_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 500_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x04,
        },
        {
            "seq": 2,
            "lat_e7": 400_010_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "victor_suppress.mseq").write_bytes(build_log("victor-18", victor_wps))

    lima_wps = [
        {
            "seq": 0,
            "lat_e7": 400_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x02,
        },
        {
            "seq": 1,
            "lat_e7": 410_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 2,
            "lat_e7": 420_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "lima_source_hold.mseq").write_bytes(build_log("lima-19", lima_wps))

    papa_wps = [
        {
            "seq": 0,
            "lat_e7": 377_774_900,
            "lon_e7": -1_224_194_300,
            "alt_mm": 150_500,
            "frame": 10,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "papa_frame10.mseq").write_bytes(build_log("papa-20", papa_wps))

    quebec_wps = [
        {
            "seq": 0,
            "lat_e7": 400_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 500_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x06,
        },
        {
            "seq": 2,
            "lat_e7": 400_010_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "quebec_suppress_hold.mseq").write_bytes(build_log("quebec-21", quebec_wps))

    bravo_wps = [
        {
            "seq": 0,
            "lat_e7": 400_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 410_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x04,
        },
        {
            "seq": 2,
            "lat_e7": 420_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 3,
            "flags": 0x02,
        },
    ]
    (hidden_dir / "bravo_suppress_then_hold.mseq").write_bytes(build_log("bravo-22", bravo_wps))

    sierra_wps = [
        {
            "seq": 0,
            "lat_e7": 377_774_900,
            "lon_e7": -1_224_194_300,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 500_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x06,
        },
        {
            "seq": 2,
            "lat_e7": 377_775_900,
            "lon_e7": -1_224_195_300,
            "alt_mm": 200_500,
            "frame": 0,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "sierra_v2_suppress_hold.mseq").write_bytes(build_log("sierra-23", sierra_wps))

    uniform_cap_wps = [
        {
            "seq": 0,
            "lat_e7": 377_749_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 185_500,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "uniform_rel_alt_cap.mseq").write_bytes(build_log("uniform-24", uniform_cap_wps))

    india_route_wps = [
        {
            "seq": 0,
            "lat_e7": 377_749_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 378_469_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "india_long_route.mseq").write_bytes(build_log("india-25", india_route_wps))

    romeo_wps = [
        {
            "seq": 0,
            "lat_e7": 377_749_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 170_500,
            "frame": 0,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "romeo_hash_trap.mseq").write_bytes(build_log("romeo-26", romeo_wps))

    delta_wps = [
        {
            "seq": 0,
            "lat_e7": 377_749_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 55_500,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "delta_negative_rel_band.mseq").write_bytes(build_log("delta-27", delta_wps))

    kilo_nonadj_wps = [
        {
            "seq": 0,
            "lat_e7": 377_749_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 1,
            "lat_e7": 378_469_000,
            "lon_e7": -1_224_194_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 0,
            "lat_e7": 377_751_000,
            "lon_e7": -1_224_195_000,
            "alt_mm": 185_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "kilo_nonadjacent_dup.mseq").write_bytes(build_log("kilo-31", kilo_nonadj_wps))

    zulu_mid_log = (
        waypoint_body("zulu-32", 0, 377_749_000, -1_224_194_000, 170_500, 3, 0x01)
        + waypoint_body("zulu-wrong", 1, 378_469_000, -1_224_194_000, 175_000, 3, 0x01)
        + waypoint_body("zulu-32", 2, 377_775_900, -1_224_195_300, 200_500, 3, 0x01)
        + footer_body("zulu-32", 3)
    )
    (hidden_dir / "zulu_mid_body_upload_id.mseq").write_bytes(zulu_mid_log)

    hotel_wps = [
        {
            "seq": 0,
            "lat_e7": 512_000_000,
            "lon_e7": -1_000_000,
            "alt_mm": -15_050,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "hotel_v2_negative_rel_band.mseq").write_bytes(build_log("hotel-28", hotel_wps))

    tau_a_wps = [
        {
            "seq": 5,
            "lat_e7": 430_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 170_500,
            "frame": 3,
            "flags": 0x01,
        },
        {
            "seq": 0,
            "lat_e7": 431_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 175_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "tau_cross_epoch_a.mseq").write_bytes(build_log("tau-33", tau_a_wps))

    tau_b_wps = [
        {
            "seq": 9,
            "lat_e7": 432_000_000,
            "lon_e7": -1_220_000_000,
            "alt_mm": 180_000,
            "frame": 3,
            "flags": 0x01,
        },
    ]
    (hidden_dir / "tau_cross_epoch_b.mseq").write_bytes(build_log("tau-34", tau_b_wps))


def hidden_fixture_root() -> Path:
    env = os.environ.get("MAVLINK_HIDDEN_FIXTURES")
    if env:
        root = Path(env)
        root.mkdir(parents=True, exist_ok=True)
        return root
    repo_hidden = Path(__file__).resolve().parent / "fixtures" / "hidden"
    try:
        write_hidden_fixtures(repo_hidden)
        return repo_hidden
    except OSError:
        fallback = Path("/tmp/mavlink-mseq-fixtures/hidden")
        write_hidden_fixtures(fallback)
        return fallback


def main() -> Path:
    root = fixture_root()
    write_verifier_fixtures(root)
    hidden_fixture_root()
    return root


if __name__ == "__main__":
    main()
