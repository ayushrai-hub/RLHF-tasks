"""Milestone 3 verifier for rollback index handling."""
import json
import subprocess
from pathlib import Path

BIN = Path('/app/bin/ota-chain')
STATE = Path('/app/state/ota/state.json')
STAGING = Path('/app/state/ota/verified-rollback.json')
ROLLBACK = Path('/app/fixtures/rollback.json')
CURRENT = Path('/app/fixtures/current-index.txt')


def _run_m1_m2():
    subprocess.run(
        [
            str(BIN),
            'm1',
            '/app/fixtures/envelope.json',
            '/app/fixtures/epoch-keys.json',
            str(STATE),
            '/app/output/m1.json',
        ],
        check=True,
    )
    subprocess.run(
        [
            str(BIN),
            'm2',
            '/app/fixtures/chunks.json',
            str(STATE),
            '/app/fixtures/payload.bin',
            '/app/output/m2.json',
        ],
        check=True,
    )


class TestMilestone3:
    def setup_method(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        if STATE.exists():
            STATE.unlink()
        _run_m1_m2()

    def test_m3_success(self):
        """Rollback index above current is accepted and persisted."""
        out = Path('/app/output/m3.json')
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                '/app/fixtures/rollback.json',
                str(STATE),
                '/app/fixtures/current-index.txt',
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        report = json.loads(out.read_text())
        assert report['rollback_ok'] is True
        assert report['index'] == 37
        st = json.loads(STATE.read_text())
        assert st['rollback_index'] == 37

    def test_m3_equal_current_index_accepted(self, tmp_path):
        """Index equal to current must succeed (strict-less-than rejection only)."""
        equal = tmp_path / 'rollback-equal.json'
        equal.write_text(json.dumps({'device': 'stm32-fleet-a', 'index': 36}))
        out = Path('/app/output/m3-equal.json')
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                str(equal),
                str(STATE),
                '/app/fixtures/current-index.txt',
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        assert st['rollback_index'] == 36

    def test_m3_device_mismatch_fails(self, tmp_path):
        """Rollback device must match the verified envelope device."""
        bad = tmp_path / 'rollback-wrong-device.json'
        bad.write_text(json.dumps({'device': 'stm32-fleet-b', 'index': 40}))
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                str(bad),
                str(STATE),
                '/app/fixtures/current-index.txt',
                '/app/output/m3-bad.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m3_without_m1_envelope_fails(self):
        """m3 must reject when milestone 1 envelope is absent from state."""
        if STATE.exists():
            STATE.unlink()
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                '/app/fixtures/rollback.json',
                str(STATE),
                '/app/fixtures/current-index.txt',
                '/app/output/m3-missing-m1.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m3_without_m2_chunk_map_fails(self):
        """m3 must reject when milestone 2 chunk_map_sha256 is absent from state."""
        if STATE.exists():
            STATE.unlink()
        subprocess.run(
            [
                str(BIN),
                'm1',
                '/app/fixtures/envelope.json',
                '/app/fixtures/epoch-keys.json',
                str(STATE),
                '/app/output/m1.json',
            ],
            check=True,
        )
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                '/app/fixtures/rollback.json',
                str(STATE),
                '/app/fixtures/current-index.txt',
                '/app/output/m3-missing-m2.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m3_below_current_index_fails(self, tmp_path):
        """Rollback index strictly below current must fail."""
        low = tmp_path / 'rollback-low.json'
        low.write_text(json.dumps({'device': 'stm32-fleet-a', 'index': 35}))
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                str(low),
                str(STATE),
                '/app/fixtures/current-index.txt',
                '/app/output/m3-low.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m3_stale_chunk_binding_generation_fails(self):
        """m3 must reject when chunk_binding_generation lags workflow_generation."""
        st = json.loads(STATE.read_text())
        st['workflow_generation'] = st.get('workflow_generation', 1) + 1
        STATE.write_text(json.dumps(st))
        proc = subprocess.run(
            [
                str(BIN),
                'm3',
                '/app/fixtures/rollback.json',
                str(STATE),
                '/app/fixtures/current-index.txt',
                '/app/output/m3-stale.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def _run_m3_validate(self, rollback: Path = ROLLBACK) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                str(BIN),
                'm3-validate',
                str(rollback),
                str(STATE),
                str(CURRENT),
            ],
            capture_output=True,
            text=True,
        )

    def _run_m3_commit(self, out: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm3-commit', str(STATE), str(out)],
            capture_output=True,
            text=True,
        )

    def test_m3_validate_writes_staging_not_state(self):
        """m3-validate must write rollback staging fields without mutating rollback_index."""
        proc = self._run_m3_validate()
        assert proc.returncode == 0, proc.stderr
        assert STAGING.is_file()
        st = json.loads(STATE.read_text(encoding='utf-8'))
        assert st.get('rollback_index') is None
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        rollback = json.loads(ROLLBACK.read_text(encoding='utf-8'))
        current = int(CURRENT.read_text(encoding='utf-8').strip())
        assert staging['device'] == rollback['device']
        assert staging['index'] == rollback['index']
        assert staging['current_index'] == current
        assert staging['workflow_generation'] == st['workflow_generation']

    def test_m3_commit_without_staging_fails(self):
        """m3-commit must fail when rollback staging was never written."""
        if STAGING.exists():
            STAGING.unlink()
        proc = self._run_m3_commit(Path('/app/output/m3-no-staging.json'))
        assert proc.returncode != 0
        assert 'missing verified rollback staging' in proc.stderr.lower()

    def test_m3_validate_then_commit_matches_m3(self):
        """Split validate and commit must match one-shot m3."""
        combined = subprocess.run(
            [
                str(BIN),
                'm3',
                str(ROLLBACK),
                str(STATE),
                str(CURRENT),
                '/app/output/m3-combined.json',
            ],
            capture_output=True,
            text=True,
        )
        assert combined.returncode == 0, combined.stderr
        combined_report = json.loads(Path('/app/output/m3-combined.json').read_text())
        combined_state = json.loads(STATE.read_text())

        if STAGING.exists():
            STAGING.unlink()
        st = json.loads(STATE.read_text())
        st['rollback_index'] = None
        STATE.write_text(json.dumps(st))

        assert self._run_m3_validate().returncode == 0
        split_out = Path('/app/output/m3-split.json')
        assert self._run_m3_commit(split_out).returncode == 0, 'commit failed'
        split_report = json.loads(split_out.read_text())
        split_state = json.loads(STATE.read_text())
        assert split_report == combined_report
        assert split_state['rollback_index'] == combined_state['rollback_index']

    def test_m3_commit_reads_staging_not_rollback_file(self, tmp_path):
        """m3-commit must persist index from staging, not re-read rollback.json."""
        high = tmp_path / 'rollback-high.json'
        high.write_text(json.dumps({'device': 'stm32-fleet-a', 'index': 40}))
        assert self._run_m3_validate(high).returncode == 0, 'validate failed'
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        assert staging['index'] == 40
        trap = tmp_path / 'rollback-trap.json'
        trap.write_text(json.dumps({'device': 'stm32-fleet-a', 'index': 5}))
        out = Path('/app/output/m3-staging-trap.json')
        proc = self._run_m3_commit(out)
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        assert st['rollback_index'] == staging['index']

    def test_m3_index_fix_alone_still_fails_staging_commit(self, tmp_path):
        """Staging commit must not re-read rollback.json after validate."""
        equal = tmp_path / 'rollback-equal.json'
        equal.write_text(json.dumps({'device': 'stm32-fleet-a', 'index': 36}))
        assert self._run_m3_validate(equal).returncode == 0
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        assert staging['index'] == 36
        proc = self._run_m3_commit(Path('/app/output/m3-poison.json'))
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        assert st['rollback_index'] == 36
