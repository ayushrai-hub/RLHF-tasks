"""Milestone 1 verifier for OTA manifest envelope."""
import hashlib
import json
import subprocess
from pathlib import Path

BIN = Path('/app/bin/ota-chain')
STATE = Path('/app/state/ota/state.json')
OUT = Path('/app/output/m1.json')
ENVELOPE = Path('/app/fixtures/envelope.json')
JOURNAL = Path('/app/state/ota/apply-journal.jsonl')
STAGING = Path('/app/state/ota/verified-envelope.json')
KEYS = Path('/app/fixtures/epoch-keys.json')


def _sig_string(env: dict, key: str) -> str:
    parts = [
        str(env['version']),
        env['device'],
        env['build_id'],
        str(env['epoch']),
        env['payload_sha256'],
        key,
    ]
    return '|'.join(parts)


class TestMilestone1:
    def setup_method(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        if STATE.exists():
            STATE.unlink()
        STAGING.unlink(missing_ok=True)
        OUT.unlink(missing_ok=True)

    def _run_m1_verify(self, envelope: Path = ENVELOPE) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm1-verify', str(envelope), str(KEYS)],
            capture_output=True,
            text=True,
        )

    def _run_m1_commit(self, out: Path = OUT) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm1-commit', str(STATE), str(out)],
            capture_output=True,
            text=True,
        )

    def test_m1_success(self):
        """Verified envelope persists full contract fields in state."""
        proc = subprocess.run(
            [
                str(BIN),
                'm1',
                str(ENVELOPE),
                '/app/fixtures/epoch-keys.json',
                str(STATE),
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        report = json.loads(OUT.read_text())
        assert report['verified'] is True
        assert report['device'] == 'stm32-fleet-a'
        assert report['epoch'] == 2
        st = json.loads(STATE.read_text())
        env = st['envelope']
        assert env['build_id'] == 'fw-2026.09.1'
        assert env['payload_sha256'] == (
            'bbfb79e82216bd2db1ad2c507d44ddf80aeb12f64f9562056afe93aad43154d9'
        )

    def test_m1_tampered_payload_sha256_fails(self, tmp_path):
        """Signature must bind payload_sha256; mutating it without resigning fails."""
        doc = json.loads(ENVELOPE.read_text())
        doc['payload_sha256'] = 'aa' * 32
        bad = tmp_path / 'tampered-envelope.json'
        bad.write_text(json.dumps(doc))
        proc = subprocess.run(
            [
                str(BIN),
                'm1',
                str(bad),
                '/app/fixtures/epoch-keys.json',
                str(STATE),
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m1_signature_field_order_contract(self, tmp_path):
        """Recomputed signature must use version|device|build_id|epoch|payload|key order."""
        doc = json.loads(ENVELOPE.read_text())
        keys = json.loads(Path('/app/fixtures/epoch-keys.json').read_text())
        key = keys[str(doc['epoch'])]
        canonical = hashlib.sha256(_sig_string(doc, key).encode()).hexdigest()
        assert doc['sig'] == canonical
        wrong_order = hashlib.sha256(
            '|'.join(
                [
                    str(doc['version']),
                    doc['build_id'],
                    doc['device'],
                    str(doc['epoch']),
                    doc['payload_sha256'],
                    key,
                ]
            ).encode()
        ).hexdigest()
        assert wrong_order != canonical
        forged = tmp_path / 'wrong-order.json'
        doc['sig'] = wrong_order
        forged.write_text(json.dumps(doc))
        proc = subprocess.run(
            [
                str(BIN),
                'm1',
                str(forged),
                '/app/fixtures/epoch-keys.json',
                str(STATE),
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m1_unknown_epoch_fails(self, tmp_path):
        """Unknown epoch keys must fail before signature verification succeeds."""
        doc = json.loads(ENVELOPE.read_text())
        doc['epoch'] = 99
        bad = tmp_path / 'unknown-epoch.json'
        bad.write_text(json.dumps(doc))
        proc = subprocess.run(
            [
                str(BIN),
                'm1',
                str(bad),
                '/app/fixtures/epoch-keys.json',
                str(STATE),
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def _run_m1(self, out: Path = OUT) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                str(BIN),
                'm1',
                str(ENVELOPE),
                '/app/fixtures/epoch-keys.json',
                str(STATE),
                str(out),
            ],
            capture_output=True,
            text=True,
        )

    def test_m1_workflow_generation_increments(self):
        """Each successful m1 run bumps workflow_generation and clears downstream fields."""
        assert self._run_m1().returncode == 0
        st = json.loads(STATE.read_text())
        assert st['workflow_generation'] == 1
        assert st['chunk_map_sha256'] is None
        assert st['payload_coverage_end'] is None
        assert st['chunk_binding_generation'] is None
        assert st['rollback_index'] is None
        assert st['apply_runs'] == []
        st['chunk_map_sha256'] = 'deadbeef'
        st['rollback_index'] = 9
        st['apply_runs'] = ['stale']
        STATE.write_text(json.dumps(st))
        assert self._run_m1(Path('/app/output/m1-rerun.json')).returncode == 0
        st = json.loads(STATE.read_text())
        assert st['workflow_generation'] == 2
        assert st['chunk_map_sha256'] is None
        assert st['rollback_index'] is None
        assert st['apply_runs'] == []

    def test_m1_rerun_truncates_apply_journal(self):
        """Re-verifying the envelope must truncate the durable apply journal."""
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        JOURNAL.write_text('{"run_id":"old","generation":1}\n')
        assert self._run_m1().returncode == 0
        assert JOURNAL.read_text() == ''

    def test_m1_verify_writes_staging_not_state(self):
        """m1-verify must write staging without mutating state or output."""
        proc = self._run_m1_verify()
        assert proc.returncode == 0, proc.stderr
        assert STAGING.is_file()
        assert not STATE.exists()
        assert not OUT.exists()
        staging = json.loads(STAGING.read_text())
        assert staging['verified'] is True
        assert staging['device'] == 'stm32-fleet-a'

    def test_m1_commit_without_staging_fails(self):
        """m1-commit must fail when verified-envelope staging is missing."""
        STAGING.unlink(missing_ok=True)
        proc = self._run_m1_commit()
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()
        assert not OUT.exists()

    def test_m1_verify_then_commit_matches_m1(self):
        """Split verify and commit must match one-shot m1."""
        assert self._run_m1_verify().returncode == 0
        split_out = Path('/app/output/m1-split.json')
        assert self._run_m1_commit(split_out).returncode == 0, 'commit failed'

        if STATE.exists():
            STATE.unlink()
        STAGING.unlink(missing_ok=True)
        combined_out = Path('/app/output/m1-combined.json')
        assert self._run_m1(combined_out).returncode == 0
        assert json.loads(split_out.read_text()) == json.loads(combined_out.read_text())

    def test_m1_commit_reads_staging_not_envelope_file(self, tmp_path):
        """m1-commit must persist the envelope from staging, not re-read bundled fixtures."""
        alt = tmp_path / 'alt-envelope.json'
        doc = json.loads(ENVELOPE.read_text())
        doc['build_id'] = 'fw-alt-branch'
        keys = json.loads(KEYS.read_text())
        doc['sig'] = hashlib.sha256(
            _sig_string(doc, keys[str(doc['epoch'])]).encode()
        ).hexdigest()
        alt.write_text(json.dumps(doc))
        assert self._run_m1_verify(alt).returncode == 0, 'verify alt envelope'
        out = Path('/app/output/m1-staging-trap.json')
        assert self._run_m1_commit(out).returncode == 0, 'commit should use staging'
        st = json.loads(STATE.read_text())
        assert st['envelope']['build_id'] == 'fw-alt-branch'

    def test_m1_sig_canon_module_matches_reference(self):
        """Signature hashing must use sig_canon field order from the workflow doc."""
        doc = json.loads(ENVELOPE.read_text())
        keys = json.loads(KEYS.read_text())
        key = keys[str(doc['epoch'])]
        expected = hashlib.sha256(_sig_string(doc, key).encode()).hexdigest()
        assert doc['sig'] == expected
        swapped = hashlib.sha256(
            '|'.join(
                [
                    str(doc['version']),
                    doc['build_id'],
                    doc['device'],
                    str(doc['epoch']),
                    doc['payload_sha256'],
                    key,
                ]
            ).encode()
        ).hexdigest()
        assert swapped != expected
