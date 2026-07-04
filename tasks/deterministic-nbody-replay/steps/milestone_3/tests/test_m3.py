"""Tests for Milestone 3: late-activated body backfill, unsigned step-gap arithmetic, iterator safety."""

import os
import struct
import subprocess
from pathlib import Path

NBODY = "/app/build/nbody"
SCENARIO_THREE = "/app/data/scenarios/three_body_activated.icbin"
OUT_DIR = "/app/out"

# Three-body trajectory record: uint64 step + 3 bodies * 6 doubles = 8 + 144 = 152 bytes
RECORD_SIZE_3 = 8 + 3 * 6 * 8   # 152

# Checkpoint header: 4 + 1 + 4 + 8 + 4 = 21 bytes
CHK_HEADER_SIZE = 21
# Per body in checkpoint: 12 doubles = 96 bytes
CHK_BODY_SIZE = 12 * 8
# Trailer: uint32 CRC = 4 bytes
CHK_TRAILER_SIZE = 4

# Scenario constants
ACTIVATION_STEP = 200
CHK_STEP_THREE = 100
HORIZON = 1000


def _run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


class TestMilestone3:

    def test_m3_from_scratch_run(self):
        """Full 1000-step run with three-body scenario must produce a correctly-sized traj file."""
        os.makedirs(OUT_DIR, exist_ok=True)

        traj_full3 = f"{OUT_DIR}/traj_full3.bin"
        r = _run([
            NBODY, "run",
            "--scenario", SCENARIO_THREE,
            "--steps", str(HORIZON),
            "--output", traj_full3,
        ])
        assert r.returncode == 0, (
            f"run failed (exit {r.returncode}): {r.stderr.decode(errors='replace')}"
        )

        data = Path(traj_full3).read_bytes()
        # 1001 records (steps 0 through 1000), each 152 bytes
        expected_size = (HORIZON + 1) * RECORD_SIZE_3
        assert len(data) == expected_size, (
            f"traj_full3.bin has wrong size: {len(data)} bytes "
            f"(expected {expected_size} = {HORIZON + 1} records x {RECORD_SIZE_3} bytes)"
        )

        # Verify step counter in first and last record
        step0 = struct.unpack_from("<Q", data, 0)[0]
        assert step0 == 0, f"First record step counter should be 0, got {step0}"

        last_offset = HORIZON * RECORD_SIZE_3
        step_last = struct.unpack_from("<Q", data, last_offset)[0]
        assert step_last == HORIZON, (
            f"Last record step counter should be {HORIZON}, got {step_last}"
        )

    def test_m3_checkpoint_before_activation(self):
        """Checkpoint at step 100 (before activation at 200) must record all 3 bodies."""
        os.makedirs(OUT_DIR, exist_ok=True)

        traj_pre3 = f"{OUT_DIR}/traj_pre3.bin"
        chk3 = f"{OUT_DIR}/chk3.bin"
        r = _run([
            NBODY, "chkpt",
            "--scenario", SCENARIO_THREE,
            "--steps", str(HORIZON),
            "--chk-at", str(CHK_STEP_THREE),
            "--output", traj_pre3,
            "--chk-out", chk3,
        ])
        assert r.returncode == 0, (
            f"chkpt failed (exit {r.returncode}): {r.stderr.decode(errors='replace')}"
        )

        chk_data = Path(chk3).read_bytes()
        assert len(chk_data) > 0, "chk3.bin is empty"

        # Parse header: magic(4) + version(1) + body_count(4i) + step(8Q) + mxcsr(4I)
        assert chk_data[0:4] == b"NBCK", f"Bad checkpoint magic: {chk_data[0:4]!r}"

        body_count = struct.unpack_from("<i", chk_data, 5)[0]
        assert body_count == 3, (
            f"Checkpoint should contain 3 bodies (all bodies, including inactive), "
            f"got {body_count}"
        )

        step_in_chk = struct.unpack_from("<Q", chk_data, 9)[0]
        assert step_in_chk == CHK_STEP_THREE, (
            f"Checkpoint step should be {CHK_STEP_THREE}, got {step_in_chk}"
        )

        # Size check
        expected_size = CHK_HEADER_SIZE + body_count * CHK_BODY_SIZE + CHK_TRAILER_SIZE
        assert len(chk_data) == expected_size, (
            f"chk3.bin has wrong size: {len(chk_data)} bytes "
            f"(expected {expected_size})"
        )

    def test_m3_extended_matches_reference(self):
        """extend from step-100 checkpoint must reproduce steps 101-1000 of the full run."""
        traj_full3 = f"{OUT_DIR}/traj_full3.bin"
        chk3 = f"{OUT_DIR}/chk3.bin"
        extended = f"{OUT_DIR}/extended.bin"

        # Number of steps to run from checkpoint: steps 101-1000 = 900 steps
        extend_steps = HORIZON - CHK_STEP_THREE

        r = _run([
            NBODY, "extend",
            "--scenario", SCENARIO_THREE,
            "--chk", chk3,
            "--steps", str(extend_steps),
            "--output", extended,
        ])
        assert r.returncode == 0, (
            f"extend failed (exit {r.returncode}): {r.stderr.decode(errors='replace')}"
        )

        ext_data = Path(extended).read_bytes()
        full_data = Path(traj_full3).read_bytes()

        # extended.bin contains step records 101-1000 (900 records)
        expected_ext_size = extend_steps * RECORD_SIZE_3
        assert len(ext_data) == expected_ext_size, (
            f"extended.bin has wrong size: {len(ext_data)} bytes "
            f"(expected {expected_ext_size} = {extend_steps} records x {RECORD_SIZE_3} bytes)"
        )

        # Extract corresponding tail from full run:
        # Steps 101-1000 are records at offsets 101*RECORD_SIZE_3 through 1000*RECORD_SIZE_3
        tail_start = (CHK_STEP_THREE + 1) * RECORD_SIZE_3
        tail_len = extend_steps * RECORD_SIZE_3
        full_tail = full_data[tail_start: tail_start + tail_len]

        assert len(full_tail) == tail_len, (
            f"traj_full3.bin too short to extract tail from step {CHK_STEP_THREE + 1}: "
            f"{len(full_data)} bytes"
        )

        assert ext_data == full_tail, (
            "extended.bin does not match the tail of traj_full3.bin — "
            "backfill of late-activated body is incorrect or step-gap arithmetic is wrong"
        )

    def test_m3_step_gap_no_wraparound(self):
        """Checkpoint at step 0 followed by extend must not crash or wrap around."""
        os.makedirs(OUT_DIR, exist_ok=True)

        chk3_step0 = f"{OUT_DIR}/chk3_step0.bin"
        r_chk = _run([
            NBODY, "chkpt",
            "--scenario", SCENARIO_THREE,
            "--steps", str(HORIZON),
            "--chk-at", "0",
            "--output", f"{OUT_DIR}/traj_step0_throwaway.bin",
            "--chk-out", chk3_step0,
        ])
        assert r_chk.returncode == 0, (
            f"chkpt at step 0 failed (exit {r_chk.returncode}): "
            f"{r_chk.stderr.decode(errors='replace')}"
        )

        assert Path(chk3_step0).exists(), "chk3_step0.bin was not created"

        # Now extend from step 0 for the full horizon
        extended_from0 = f"{OUT_DIR}/extended_from0.bin"
        r_ext = _run([
            NBODY, "extend",
            "--scenario", SCENARIO_THREE,
            "--chk", chk3_step0,
            "--steps", str(HORIZON),
            "--output", extended_from0,
        ])
        assert r_ext.returncode == 0, (
            f"extend from step-0 checkpoint failed (exit {r_ext.returncode}): "
            f"{r_ext.stderr.decode(errors='replace')}"
        )

        ext_data = Path(extended_from0).read_bytes()
        # Should have exactly HORIZON records (steps 1-1000, since step 0 is the base)
        expected_size = HORIZON * RECORD_SIZE_3
        assert len(ext_data) == expected_size, (
            f"extended_from0.bin has wrong size: {len(ext_data)} bytes "
            f"(expected {expected_size})"
        )

        # The first step in the extend output must be step 1
        first_step = struct.unpack_from("<Q", ext_data, 0)[0]
        assert first_step == 1, (
            f"First step in extended_from0.bin should be 1, got {first_step} "
            f"(possible unsigned wraparound in step-gap arithmetic)"
        )

    def test_m3_body2_frozen_then_active(self):
        """Body 2 must be position-frozen before activation_step and visibly moving after.

        This check is independent of extended.bin: it reads traj_full3.bin directly
        and verifies the activation is observable in the reference trajectory itself.
        A solution that consistently disables activation in both paths would produce
        a traj_full3.bin where body 2 never moves, which this test catches.
        """
        traj_full3 = f"{OUT_DIR}/traj_full3.bin"
        data = Path(traj_full3).read_bytes()

        # Record layout: step(8) + body0(48) + body1(48) + body2(48)
        # Body 2 xyz starts at byte offset 8 + 48 + 48 = 104 within each record.
        BODY2_XYZ_OFFSET = 8 + 48 + 48

        def body2_xyz(step):
            offset = step * RECORD_SIZE_3 + BODY2_XYZ_OFFSET
            return struct.unpack_from("<ddd", data, offset)

        # Body 2 must be frozen (position unchanged) for all steps before activation
        pos_step0 = body2_xyz(0)
        for check_step in [50, 100, 150, ACTIVATION_STEP - 1]:
            pos = body2_xyz(check_step)
            assert pos == pos_step0, (
                f"Body 2 position changed at step {check_step} before "
                f"activation_step={ACTIVATION_STEP}; body should be frozen. "
                f"Expected {pos_step0}, got {pos}"
            )

        # Body 2 must have drifted at the activation step (force was applied, then drift)
        pos_before = body2_xyz(ACTIVATION_STEP - 1)
        pos_after = body2_xyz(ACTIVATION_STEP)
        assert pos_after != pos_before, (
            f"Body 2 position did not change at step {ACTIVATION_STEP} — "
            f"activation is not producing a drift. "
            f"pos before={pos_before}, pos at activation={pos_after}"
        )

    def test_m3_backfill_canonical_order(self):
        """Validated implicitly: if backfill order is wrong, extended.bin won't match full run.

        This test directly checks that the activated body (index 2) records in
        extended.bin around the activation step match the full reference run.
        """
        extended = f"{OUT_DIR}/extended.bin"
        traj_full3 = f"{OUT_DIR}/traj_full3.bin"

        ext_data = Path(extended).read_bytes()
        full_data = Path(traj_full3).read_bytes()

        # Check a window of steps surrounding the activation (step 200)
        # In extended.bin: step N is at offset (N - CHK_STEP_THREE - 1) * RECORD_SIZE_3
        # In full run:     step N is at offset N * RECORD_SIZE_3
        check_steps = list(range(
            max(CHK_STEP_THREE + 1, ACTIVATION_STEP - 5),
            min(ACTIVATION_STEP + 6, HORIZON + 1)
        ))

        for step in check_steps:
            ext_offset = (step - CHK_STEP_THREE - 1) * RECORD_SIZE_3
            full_offset = step * RECORD_SIZE_3

            ext_record = ext_data[ext_offset: ext_offset + RECORD_SIZE_3]
            full_record = full_data[full_offset: full_offset + RECORD_SIZE_3]

            assert ext_record == full_record, (
                f"Step {step} record differs between extended.bin and traj_full3.bin — "
                f"body activation backfill is incorrect near activation_step={ACTIVATION_STEP}"
            )
