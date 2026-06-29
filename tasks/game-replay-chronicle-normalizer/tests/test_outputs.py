"""Behavioral verifier for game replay chronicle normalizer."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import struct
import subprocess
import zlib
from pathlib import Path

CLI = "/app/bin/replay-chronicle"
PACK = "/app/scripts/replay-pack.sh"
UNPACK = "/app/scripts/replay-unpack.sh"
PUBLIC_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "public"
HIDDEN_ROOT = Path("/opt/verifier-fixtures")


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _build_shard(
    shard_id: int,
    drift_ms: int,
    events: list[tuple[int, int, int, bytes]],
) -> bytes:
    body = bytearray()
    body.append(1)
    body += struct.pack("<I", shard_id)
    body += struct.pack("<i", drift_ms)
    body += struct.pack("<I", len(events))
    for seq, raw_tick, ev_type, payload in events:
        body += struct.pack("<II", seq, raw_tick)
        body += struct.pack("<HH", ev_type, len(payload))
        body += payload
    footer = struct.pack("<I", _crc32(bytes(body)))
    return b"GRSH" + bytes(body) + footer


def _reference_normalize(shard_dir: Path) -> dict:
    shards_meta: list[dict] = []
    collected: list[dict] = []
    read_order = 0
    for path in sorted(shard_dir.glob("*.grsh")):
        data = path.read_bytes()
        assert data[:4] == b"GRSH"
        body = data[4:-4]
        stored_crc = struct.unpack("<I", data[-4:])[0]
        assert _crc32(body) == stored_crc
        version = body[0]
        assert version == 1
        shard_id = struct.unpack("<I", body[1:5])[0]
        drift_ms = struct.unpack("<i", body[5:9])[0]
        count = struct.unpack("<I", body[9:13])[0]
        off = 13
        shards_meta.append({"shard_id": shard_id, "drift_ms": drift_ms})
        for _ in range(count):
            seq, raw_tick = struct.unpack("<II", body[off : off + 8])
            ev_type, plen = struct.unpack("<HH", body[off + 8 : off + 12])
            off += 12
            payload = body[off : off + plen]
            off += plen
            tick = max(0, raw_tick - drift_ms)
            collected.append(
                {
                    "seq": seq,
                    "tick": tick,
                    "type": ev_type,
                    "payload_hex": payload.hex(),
                    "_order": read_order,
                }
            )
            read_order += 1
    collected.sort(key=lambda e: (e["tick"], e["seq"], e["_order"]))
    # Dedup keeps earliest read-order row per (tick, seq).
    seen: set[tuple[int, int]] = set()
    events: list[dict] = []
    for ev in collected:
        key = (ev["tick"], ev["seq"])
        if key in seen:
            continue
        seen.add(key)
        events.append(
            {
                "seq": ev["seq"],
                "tick": ev["tick"],
                "type": ev["type"],
                "payload_hex": ev["payload_hex"],
            }
        )
    shards_meta.sort(key=lambda s: s["shard_id"])
    integrity = _reference_integrity(events)
    return {
        "version": 1,
        "shards": shards_meta,
        "events": events,
        "integrity": integrity,
    }


def _reference_integrity(events: list[dict]) -> str:
    parts = [
        f"{e['seq']}:{e['tick']}:{e['type']}:{e['payload_hex']};" for e in events
    ]
    return hashlib.sha256("".join(parts).encode()).hexdigest()


def _reference_pack(chronicle: dict) -> bytes:
    payload = json.dumps(chronicle, separators=(",", ":")).encode()
    gz = gzip.compress(payload, compresslevel=9, mtime=0)
    header = b"\x01" + struct.pack("<I", len(gz))
    hdr_crc = struct.pack("<I", _crc32(header))
    return b"GRPL" + header + hdr_crc + gz


def _run_cli(args: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [CLI, *args],
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


def _write_shards(tmp: Path, specs: list[tuple[int, int, list]]) -> None:
    for i, (shard_id, drift, events) in enumerate(specs):
        blob = _build_shard(shard_id, drift, events)
        (tmp / f"shard_{i}.grsh").write_bytes(blob)


class TestNormalizePublic:
    """Public fixture normalization checks."""

    def test_normalize_basic_two_shards(self, tmp_path: Path) -> None:
        """Multi-shard normalize must merge, sort by tick then seq, and match reference integrity."""
        _write_shards(
            tmp_path,
            [
                (2, 10, [(1, 120, 1, b"aa"), (2, 100, 2, b"")]),
                (1, 0, [(1, 50, 3, b"ff")]),
            ],
        )
        out = tmp_path / "out.json"
        rc = _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)])
        assert rc.returncode == 0, rc.stderr
        got = json.loads(out.read_text())
        want = _reference_normalize(tmp_path)
        assert got["events"] == want["events"]
        assert got["integrity"] == want["integrity"]
        assert got["shards"] == want["shards"]

    def test_normalize_out_of_order_seq(self, tmp_path: Path) -> None:
        """Events with higher seq but lower tick must sort before high-tick rows per chronicle-schema.md."""
        _write_shards(tmp_path, [(1, 0, [(5, 200, 1, b"x"), (1, 100, 1, b"y")])])
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        got = json.loads(out.read_text())
        want = _reference_normalize(tmp_path)
        assert got["events"] == want["events"]

    def test_normalize_duplicate_frames_deduped(self, tmp_path: Path) -> None:
        """Duplicate (tick, seq) pairs keep only the first read-order frame."""
        _write_shards(
            tmp_path,
            [(1, 0, [(1, 100, 1, b"a"), (2, 100, 2, b"b"), (1, 100, 9, b"z")])],
        )
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        got = json.loads(out.read_text())
        want = _reference_normalize(tmp_path)
        assert got["events"] == want["events"]
        assert len(got["events"]) == 2

    def test_normalize_drift_subtraction(self, tmp_path: Path) -> None:
        """Per-shard drift_ms is subtracted from raw ticks per drift-policy.md."""
        _write_shards(tmp_path, [(3, 25, [(1, 125, 4, b"dr")])])
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        got = json.loads(out.read_text())
        assert got["events"][0]["tick"] == 100

    def test_validate_accepts_good_chronicle(self, tmp_path: Path) -> None:
        """validate exits zero when integrity matches chronicle-schema.md digest rules."""
        _write_shards(tmp_path, [(1, 0, [(1, 10, 1, b"")])])
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        assert _run_cli(["validate", "--input", str(out)]).returncode == 0

    def test_validate_rejects_tampered_integrity(self, tmp_path: Path) -> None:
        """validate must fail when integrity field is altered."""
        _write_shards(tmp_path, [(1, 0, [(1, 10, 1, b"")])])
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        ch = json.loads(out.read_text())
        ch["integrity"] = "0" * 64
        out.write_text(json.dumps(ch) + "\n")
        assert _run_cli(["validate", "--input", str(out)]).returncode != 0

    def test_rejects_corrupted_crc_shard(self, tmp_path: Path) -> None:
        """Shards with footer CRC mismatch are rejected per replay-format.md."""
        blob = bytearray(_build_shard(1, 0, [(1, 1, 1, b"a")]))
        blob[-1] ^= 0xFF
        (tmp_path / "bad.grsh").write_bytes(blob)
        out = tmp_path / "c.json"
        rc = _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)])
        assert rc.returncode != 0

    def test_rejects_bad_magic_shard(self, tmp_path: Path) -> None:
        """Non-GRSH magic bytes must be rejected at ingest."""
        blob = bytearray(_build_shard(1, 0, [(1, 1, 1, b"a")]))
        blob[0:4] = b"GRPL"
        (tmp_path / "bad.grsh").write_bytes(blob)
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode != 0

    def test_public_bundled_fixture_matches_reference(self, tmp_path: Path) -> None:
        """Bundled public shards normalize to the independent reference chronicle."""
        out = tmp_path / "out.json"
        rc = _run_cli(
            ["normalize", "--input-dir", str(PUBLIC_FIXTURES), "--output", str(out)]
        )
        assert rc.returncode == 0, rc.stderr
        got = json.loads(out.read_text())
        want = _reference_normalize(PUBLIC_FIXTURES)
        assert got == want


class TestPackRoundTrip:
    """GRPL pack/unpack transport checks."""

    def test_pack_unpack_roundtrip(self, tmp_path: Path) -> None:
        """replay-pack.sh and replay-unpack.sh must round-trip chronicle JSON per pack-contract.md."""
        _write_shards(tmp_path, [(1, 5, [(1, 55, 2, b"ab")])])
        chronicle = tmp_path / "c.json"
        packed = tmp_path / "t.grpl"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(chronicle)]).returncode == 0
        rc = subprocess.run([PACK, str(chronicle), str(packed)], capture_output=True, text=True)
        assert rc.returncode == 0, rc.stderr
        up = subprocess.run([UNPACK, str(packed)], capture_output=True, text=True)
        assert up.returncode == 0, up.stderr
        assert json.loads(up.stdout) == json.loads(chronicle.read_text())

    def test_pack_header_crc_enforced_on_unpack(self, tmp_path: Path) -> None:
        """Unpack must reject GRPL files whose header_crc does not cover version and payload_len."""
        _write_shards(tmp_path, [(1, 0, [(1, 1, 1, b"")])])
        chronicle = tmp_path / "c.json"
        packed = tmp_path / "t.grpl"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(chronicle)]).returncode == 0
        subprocess.run([PACK, str(chronicle), str(packed)], check=True)
        data = bytearray(packed.read_bytes())
        data[10] ^= 0x01
        packed.write_bytes(data)
        rc = subprocess.run([UNPACK, str(packed)], capture_output=True, text=True)
        assert rc.returncode != 0

    def test_unpack_rejects_bad_magic(self, tmp_path: Path) -> None:
        """Unpack rejects containers without GRPL magic."""
        _write_shards(tmp_path, [(1, 0, [(1, 1, 1, b"")])])
        chronicle = tmp_path / "c.json"
        packed = tmp_path / "t.grpl"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(chronicle)]).returncode == 0
        subprocess.run([PACK, str(chronicle), str(packed)], check=True)
        data = bytearray(packed.read_bytes())
        data[0:4] = b"XXXX"
        packed.write_bytes(data)
        assert subprocess.run([UNPACK, str(packed)], capture_output=True).returncode != 0

    def test_reference_pack_matches_unpack(self, tmp_path: Path) -> None:
        """Reference-packed GRPL must unpack through replay-unpack.sh to the same events."""
        ch = _reference_normalize(PUBLIC_FIXTURES)
        blob = _reference_pack(ch)
        packed = tmp_path / "r.grpl"
        packed.write_bytes(blob)
        up = subprocess.run([UNPACK, str(packed)], capture_output=True, text=True)
        assert up.returncode == 0, up.stderr
        assert json.loads(up.stdout)["events"] == ch["events"]


class TestHiddenFixtures:
    """Verifier-only fixtures under /opt/verifier-fixtures."""

    def test_staging_snapshot_matches_export(self, tmp_path: Path) -> None:
        """Staging buffer snapshot events must equal exported chronicle events after normalize."""
        _write_shards(tmp_path, [(1, 0, [(1, 10, 1, b"st")])])
        out = tmp_path / "staging.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        events = json.loads(out.read_text())["events"]
        assert events == _reference_normalize(tmp_path)["events"]

    def test_hidden_cross_shard_drift_and_dup(self, tmp_path: Path) -> None:
        """Hidden cross-shard fixtures require drift, dedupe, and ordering together."""
        hidden = HIDDEN_ROOT / "cross_shard"
        assert hidden.is_dir(), "hidden fixture missing"
        out = tmp_path / "h.json"
        rc = _run_cli(
            ["normalize", "--input-dir", str(hidden), "--output", str(out)],
        )
        assert rc.returncode == 0, rc.stderr
        got = json.loads(out.read_text())
        want = _reference_normalize(hidden)
        assert got["events"] == want["events"]
        assert got["integrity"] == want["integrity"]

    def test_hidden_tb3_fixture_root_override(self, tmp_path: Path) -> None:
        """TB3_FIXTURE_ROOT must override --input-dir for normalize per instruction."""
        hidden = HIDDEN_ROOT / "tb3_poison"
        assert hidden.is_dir()
        out = tmp_path / "tb3.json"
        rc = _run_cli(
            ["normalize", "--output", str(out)],
            env={"TB3_FIXTURE_ROOT": str(hidden)},
        )
        assert rc.returncode == 0, rc.stderr
        want = _reference_normalize(hidden)
        got = json.loads(out.read_text())
        assert got == want

    def test_hidden_corrupted_footer_rejected(self, tmp_path: Path) -> None:
        """Hidden corrupt footer shard must be rejected by ingest validation."""
        bad = HIDDEN_ROOT / "corrupt_footer.grsh"
        assert bad.is_file()
        work = tmp_path / "one"
        work.mkdir()
        (work / "x.grsh").write_bytes(bad.read_bytes())
        out = tmp_path / "o.json"
        assert _run_cli(["normalize", "--input-dir", str(work), "--output", str(out)]).returncode != 0

    def test_hidden_pack_roundtrip_integrity(self, tmp_path: Path) -> None:
        """Hidden chronicle pack/unpack preserves integrity across transport."""
        hidden = HIDDEN_ROOT / "cross_shard"
        out = tmp_path / "c.json"
        assert _run_cli(["normalize", "--input-dir", str(hidden), "--output", str(out)]).returncode == 0
        packed = tmp_path / "p.grpl"
        subprocess.run([PACK, str(out), str(packed)], check=True)
        up = subprocess.run([UNPACK, str(packed)], capture_output=True, text=True)
        assert up.returncode == 0
        assert json.loads(up.stdout)["integrity"] == json.loads(out.read_text())["integrity"]

    def test_hidden_same_tick_different_seq_preserved(self, tmp_path: Path) -> None:
        """Hidden fixture keeps distinct seq values that share the same tick."""
        hidden = HIDDEN_ROOT / "same_tick_multi_seq"
        out = tmp_path / "s.json"
        assert _run_cli(["normalize", "--input-dir", str(hidden), "--output", str(out)]).returncode == 0
        got = json.loads(out.read_text())
        want = _reference_normalize(hidden)
        assert len(got["events"]) == len(want["events"])
        assert got["events"] == want["events"]


class TestEdgeCases:
    """Additional behavioral coverage."""

    def test_empty_payload_hex(self, tmp_path: Path) -> None:
        """Zero-length payloads emit an empty payload_hex string."""
        _write_shards(tmp_path, [(1, 0, [(7, 7, 0, b"")])])
        out = tmp_path / "e.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        ev = json.loads(out.read_text())["events"][0]
        assert ev["payload_hex"] == ""

    def test_multi_shard_sort_by_shard_id_in_meta(self, tmp_path: Path) -> None:
        """shards array is sorted ascending by shard_id in the output JSON."""
        _write_shards(
            tmp_path,
            [
                (9, 0, [(1, 1, 1, b"")]),
                (2, 0, [(1, 2, 1, b"")]),
            ],
        )
        out = tmp_path / "m.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        shards = json.loads(out.read_text())["shards"]
        assert [s["shard_id"] for s in shards] == [2, 9]

    def test_large_payload_roundtrip(self, tmp_path: Path) -> None:
        """Large binary payloads survive normalize and hex encoding."""
        payload = bytes(range(256)) * 3
        _write_shards(tmp_path, [(1, 0, [(1, 1, 99, payload)])])
        out = tmp_path / "l.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out)]).returncode == 0
        assert json.loads(out.read_text())["events"][0]["payload_hex"] == payload.hex()

    def test_normalize_idempotent_output(self, tmp_path: Path) -> None:
        """Repeated normalize runs on the same shards yield identical output bytes."""
        _write_shards(tmp_path, [(1, 0, [(1, 5, 1, b"z")])])
        out1 = tmp_path / "a.json"
        out2 = tmp_path / "b.json"
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out1)]).returncode == 0
        assert _run_cli(["normalize", "--input-dir", str(tmp_path), "--output", str(out2)]).returncode == 0
        assert out1.read_text() == out2.read_text()
