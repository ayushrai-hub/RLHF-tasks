"""Tests for Milestone 1: deterministic force reduction order and no FMA contraction."""

import math
import os
import struct
import subprocess
from pathlib import Path

NBODY = "/app/build/nbody"
SCENARIO_TWO = "/app/data/scenarios/two_body_grazing.icbin"
OUT_DIR = "/app/out"

# Trajectory record layout for 2-body scenario:
#   uint64 step  +  2 bodies * 6 doubles  =  8 + 96  = 104 bytes per record
# Steps 0 through 1000 inclusive = 1001 records
RECORD_SIZE_2 = 8 + 2 * 6 * 8   # 104
NUM_RECORDS_2 = 1001


def _run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


class TestMilestone1:

    def test_m1_binary_builds(self):
        """The binary must compile cleanly from /app/src via cmake+make."""
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

    def test_m1_two_runs_byte_identical(self):
        """Two independent runs must produce byte-identical trajectory files."""
        os.makedirs(OUT_DIR, exist_ok=True)

        out1 = f"{OUT_DIR}/traj.bin"
        out2 = f"{OUT_DIR}/traj2.bin"

        r1 = _run([
            NBODY, "run",
            "--scenario", SCENARIO_TWO,
            "--steps", "1000",
            "--output", out1,
        ])
        assert r1.returncode == 0, (
            f"First run failed (exit {r1.returncode}): "
            f"{r1.stderr.decode(errors='replace')}"
        )

        r2 = _run([
            NBODY, "run",
            "--scenario", SCENARIO_TWO,
            "--steps", "1000",
            "--output", out2,
        ])
        assert r2.returncode == 0, (
            f"Second run failed (exit {r2.returncode}): "
            f"{r2.stderr.decode(errors='replace')}"
        )

        data1 = Path(out1).read_bytes()
        data2 = Path(out2).read_bytes()

        assert len(data1) >= 100, (
            f"traj.bin is suspiciously small: {len(data1)} bytes"
        )
        assert len(data2) >= 100, (
            f"traj2.bin is suspiciously small: {len(data2)} bytes"
        )
        assert data1 == data2, (
            f"Runs are not byte-identical: "
            f"traj.bin={len(data1)} bytes, traj2.bin={len(data2)} bytes; "
            f"first difference at byte "
            f"{next(i for i,(a,b) in enumerate(zip(data1,data2)) if a!=b) if len(data1)==len(data2) else 'length mismatch'}"
        )

    def test_m1_dump_format_correctness(self):
        """traj.bin must have exactly the right size and correct step counter values."""
        out1 = f"{OUT_DIR}/traj.bin"
        data = Path(out1).read_bytes()

        expected_size = RECORD_SIZE_2 * NUM_RECORDS_2
        assert len(data) == expected_size, (
            f"Expected {expected_size} bytes ({NUM_RECORDS_2} records x "
            f"{RECORD_SIZE_2} bytes), got {len(data)} bytes"
        )

        # Step 0 record: first 8 bytes must be uint64 LE = 0
        step0 = struct.unpack_from("<Q", data, 0)[0]
        assert step0 == 0, f"Step 0 counter should be 0, got {step0}"

        # Step 1000 record: at offset 1000 * RECORD_SIZE_2
        offset_1000 = 1000 * RECORD_SIZE_2
        step1000 = struct.unpack_from("<Q", data, offset_1000)[0]
        assert step1000 == 1000, (
            f"Step 1000 counter should be 1000, got {step1000}"
        )

        # Also verify step 500 record at its expected offset
        offset_500 = 500 * RECORD_SIZE_2
        step500 = struct.unpack_from("<Q", data, offset_500)[0]
        assert step500 == 500, (
            f"Step 500 counter should be 500, got {step500}"
        )

    def test_m1_header_signedness(self):
        """Scenario file header fields must parse as unsigned values, not sign-extended."""
        data = Path(SCENARIO_TWO).read_bytes()

        # magic is bytes 0-3 = "NBIC"
        assert data[0:4] == b"NBIC", f"Bad magic: {data[0:4]!r}"

        # version at byte 4, dim at byte 5 (both uint8)
        version = data[4]
        dim = data[5]
        assert version == 1, f"Expected version=1, got {version}"
        assert dim == 3, f"Expected dim=3, got {dim}"

        # version must not be sign-extended (no 0xFF01 or similar)
        assert 0 <= version <= 127, (
            f"version={version} looks sign-extended or out of range"
        )
        assert 0 <= dim <= 127, (
            f"dim={dim} looks sign-extended or out of range"
        )

        # body_count at bytes 6-9 as int32 LE = 2
        body_count = struct.unpack_from("<i", data, 6)[0]
        assert body_count == 2, f"Expected body_count=2, got {body_count}"

    def test_m1_redherring_energy_unmodified(self):
        """Both runs must record identical velocity bytes at step 500; velocity must be nonzero."""
        out1 = f"{OUT_DIR}/traj.bin"
        out2 = f"{OUT_DIR}/traj2.bin"
        data1 = Path(out1).read_bytes()
        data2 = Path(out2).read_bytes()

        # Step 500 record offset
        offset = 500 * RECORD_SIZE_2

        # Body 1 starts after the step counter (8 bytes) and body 0 (6 doubles = 48 bytes)
        # So body 1 begins at offset + 8 + 48 = offset + 56
        body1_offset = offset + 8 + 6 * 8

        # vx, vy, vz of body 1 are at indices 3,4,5 of the 6 doubles: +24 bytes in
        vel_offset = body1_offset + 3 * 8
        vx, vy, vz = struct.unpack_from("<ddd", data1, vel_offset)

        # Both files must have identical bytes at this location
        chunk1 = data1[vel_offset: vel_offset + 24]
        chunk2 = data2[vel_offset: vel_offset + 24]
        assert chunk1 == chunk2, (
            "Velocity bytes at step 500 body 1 differ between runs — "
            "runs are still non-deterministic"
        )

        # Velocity magnitude must be finite and nonzero
        vmag2 = vx * vx + vy * vy + vz * vz
        assert math.isfinite(vmag2), (
            f"Velocity magnitude squared is not finite: {vmag2}"
        )
        assert vmag2 > 0.0, (
            f"Velocity magnitude squared is zero at step 500 body 1: "
            f"vx={vx}, vy={vy}, vz={vz}"
        )

        # mass of body 1 = 0.001 (from scenario)
        mass1 = 1.0e-3
        ke = 0.5 * mass1 * vmag2
        assert ke > 0.0, f"Kinetic energy should be positive, got {ke}"
