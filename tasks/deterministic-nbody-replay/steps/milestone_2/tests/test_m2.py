"""Tests for Milestone 2: complete checkpointing (Kahan + vhx carry + MXCSR + CRC)."""

import binascii
import os
import struct
import subprocess
from pathlib import Path

NBODY = "/app/build/nbody"
SCENARIO_TWO = "/app/data/scenarios/two_body_grazing.icbin"
OUT_DIR = "/app/out"

# Two-body trajectory record: uint64 step + 2 * 6 doubles = 104 bytes
RECORD_SIZE_2 = 8 + 2 * 6 * 8   # 104

# Checkpoint header layout (all field-by-field, no padding):
#   char[4] magic  +  uint8 version  +  int32 body_count  +  uint64 step  +  uint32 mxcsr
#   = 4 + 1 + 4 + 8 + 4 = 21 bytes
CHK_HEADER_SIZE = 21

# Per body in checkpoint: 12 doubles = 96 bytes
CHK_BODY_SIZE = 12 * 8   # 96

# Trailer: uint32 CRC32 = 4 bytes
CHK_TRAILER_SIZE = 4


def _run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def _crc32_canonical(data: bytes) -> int:
    """Compute CRC32 using the standard zlib/ISO-3309 polynomial (same as binascii.crc32)."""
    return binascii.crc32(data) & 0xFFFFFFFF


def _parse_chk_header(data: bytes):
    """Return (body_count, step, mxcsr) from a checkpoint byte string."""
    assert data[0:4] == b"NBCK", f"Bad checkpoint magic: {data[0:4]!r}"
    version = data[4]
    assert version == 1, f"Unexpected checkpoint version: {version}"
    body_count = struct.unpack_from("<i", data, 5)[0]
    step = struct.unpack_from("<Q", data, 9)[0]
    mxcsr = struct.unpack_from("<I", data, 17)[0]
    return body_count, step, mxcsr


class TestMilestone2:

    def test_m2_binary_still_builds(self):
        """Binary must rebuild successfully after M2 source changes."""
        build_dir = "/app/build"
        os.makedirs(build_dir, exist_ok=True)

        r = _run(
            ["cmake", "-S", "/app", "-B", "/app/build", "-DCMAKE_BUILD_TYPE=Release"],
            timeout=120,
        )
        assert r.returncode == 0, (
            f"cmake failed (exit {r.returncode}):\n"
            f"stdout: {r.stdout.decode(errors='replace')}\n"
            f"stderr: {r.stderr.decode(errors='replace')}"
        )

        r = _run(["cmake", "--build", "/app/build", "--parallel", "4"], timeout=300)
        assert r.returncode == 0, (
            f"make failed (exit {r.returncode}):\n"
            f"stdout: {r.stdout.decode(errors='replace')}\n"
            f"stderr: {r.stderr.decode(errors='replace')}"
        )

        assert Path(NBODY).exists(), f"Binary not found at {NBODY}"

    def test_m2_checkpoint_byte_stable_across_runs(self):
        """Two chkpt runs must produce byte-identical checkpoint files."""
        os.makedirs(OUT_DIR, exist_ok=True)

        chk1 = f"{OUT_DIR}/chk.bin"
        chk2 = f"{OUT_DIR}/chk2.bin"
        traj_full = f"{OUT_DIR}/traj_full.bin"

        # First run
        r1 = _run([
            NBODY, "chkpt",
            "--scenario", SCENARIO_TWO,
            "--steps", "1000",
            "--chk-at", "500",
            "--output", traj_full,
            "--chk-out", chk1,
        ])
        assert r1.returncode == 0, (
            f"First chkpt run failed (exit {r1.returncode}): "
            f"{r1.stderr.decode(errors='replace')}"
        )

        # Second run — must produce identical checkpoint
        r2 = _run([
            NBODY, "chkpt",
            "--scenario", SCENARIO_TWO,
            "--steps", "1000",
            "--chk-at", "500",
            "--output", f"{OUT_DIR}/traj_full2_throwaway.bin",
            "--chk-out", chk2,
        ])
        assert r2.returncode == 0, (
            f"Second chkpt run failed (exit {r2.returncode}): "
            f"{r2.stderr.decode(errors='replace')}"
        )

        data1 = Path(chk1).read_bytes()
        data2 = Path(chk2).read_bytes()

        assert len(data1) > 0, "chk.bin is empty"
        assert len(data2) > 0, "chk2.bin is empty"
        assert data1 == data2, (
            f"Checkpoint files differ between runs: "
            f"chk.bin={len(data1)} bytes, chk2.bin={len(data2)} bytes"
        )

    def test_m2_checkpoint_crc_matches(self):
        """The CRC32 stored at the end of chk.bin must match the recomputed CRC."""
        chk_path = f"{OUT_DIR}/chk.bin"
        data = Path(chk_path).read_bytes()

        body_count, step, mxcsr = _parse_chk_header(data)
        assert body_count == 2, f"Expected 2 bodies in checkpoint, got {body_count}"
        assert step == 500, f"Expected checkpoint at step 500, got step {step}"

        payload_len = CHK_HEADER_SIZE + body_count * CHK_BODY_SIZE
        assert len(data) == payload_len + CHK_TRAILER_SIZE, (
            f"Unexpected checkpoint size: {len(data)} bytes "
            f"(expected {payload_len + CHK_TRAILER_SIZE})"
        )

        payload = data[:payload_len]
        stored_crc = struct.unpack_from("<I", data, payload_len)[0]
        computed_crc = _crc32_canonical(payload)

        assert stored_crc == computed_crc, (
            f"CRC32 mismatch: stored=0x{stored_crc:08X}, "
            f"computed=0x{computed_crc:08X}"
        )

    def test_m2_resume_tail_byte_identical(self):
        """Restored run (steps 501-1000) must be byte-identical to the tail of the full run."""
        traj_full = f"{OUT_DIR}/traj_full.bin"
        chk = f"{OUT_DIR}/chk.bin"
        traj_resumed = f"{OUT_DIR}/traj_resumed.bin"

        r = _run([
            NBODY, "restore",
            "--scenario", SCENARIO_TWO,
            "--chk", chk,
            "--steps", "500",
            "--output", traj_resumed,
        ])
        assert r.returncode == 0, (
            f"restore run failed (exit {r.returncode}): "
            f"{r.stderr.decode(errors='replace')}"
        )

        full_data = Path(traj_full).read_bytes()
        resumed_data = Path(traj_resumed).read_bytes()

        # traj_full.bin has 1001 records (steps 0-1000); tail is steps 501-1000
        # = 500 records starting at offset 501 * RECORD_SIZE_2
        tail_start = 501 * RECORD_SIZE_2
        tail_len = 500 * RECORD_SIZE_2
        full_tail = full_data[tail_start: tail_start + tail_len]

        assert len(full_tail) == tail_len, (
            f"traj_full.bin too short to extract tail: {len(full_data)} bytes"
        )
        assert len(resumed_data) == tail_len, (
            f"traj_resumed.bin has wrong size: {len(resumed_data)} bytes "
            f"(expected {tail_len} for 500 records)"
        )
        assert resumed_data == full_tail, (
            "traj_resumed.bin does not match the tail of traj_full.bin — "
            "checkpoint restore does not reproduce the original trajectory"
        )

    def test_m2_ftz_denormal_segment(self):
        """Steps 490-510 of the full run and resumed run must be byte-identical."""
        traj_full = f"{OUT_DIR}/traj_full.bin"
        traj_resumed = f"{OUT_DIR}/traj_resumed.bin"

        full_data = Path(traj_full).read_bytes()
        resumed_data = Path(traj_resumed).read_bytes()

        # From full run: steps 490-510, covering the grazing-encounter window
        # Step 490 is at offset 490 * RECORD_SIZE_2 in traj_full.bin
        # Steps 501-510 are in both files (full and resumed)
        # Check the overlapping window: steps 501-510 (10 records)
        for step in range(501, 511):
            # In full run: record at offset step * RECORD_SIZE_2
            full_offset = step * RECORD_SIZE_2
            full_record = full_data[full_offset: full_offset + RECORD_SIZE_2]

            # In resumed run: the file starts at step 501, so step N is at
            # offset (N - 501) * RECORD_SIZE_2
            res_offset = (step - 501) * RECORD_SIZE_2
            res_record = resumed_data[res_offset: res_offset + RECORD_SIZE_2]

            assert full_record == res_record, (
                f"Step {step} differs between full run and resumed run — "
                f"MXCSR FTZ state is likely not preserved across checkpoint/restore"
            )

    def test_m2_rule_of_five(self):
        """chkpt mode must exit cleanly (no crash, no memory errors detectable from exit code)."""
        os.makedirs(OUT_DIR, exist_ok=True)

        r = _run([
            NBODY, "chkpt",
            "--scenario", SCENARIO_TWO,
            "--steps", "1000",
            "--chk-at", "500",
            "--output", f"{OUT_DIR}/traj_rof_check.bin",
            "--chk-out", f"{OUT_DIR}/chk_rof_check.bin",
        ])
        assert r.returncode == 0, (
            f"chkpt exited with code {r.returncode}: "
            f"{r.stderr.decode(errors='replace')}"
        )
        assert Path(f"{OUT_DIR}/chk_rof_check.bin").exists(), (
            "Checkpoint file was not created"
        )
