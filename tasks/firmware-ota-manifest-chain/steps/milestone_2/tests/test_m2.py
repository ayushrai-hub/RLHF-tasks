"""Milestone 2 verifier for OTA delta chunk map."""
import hashlib
import json
import subprocess
from pathlib import Path

BIN = Path('/app/bin/ota-chain')
STATE = Path('/app/state/ota/state.json')
JOURNAL = Path('/app/state/ota/apply-journal.jsonl')
CHUNKS = Path('/app/fixtures/chunks.json')
PAYLOAD = Path('/app/fixtures/payload.bin')
STAGING = Path('/app/state/ota/verified-chunk-map.json')


def _chunk_map_digest(chunks: list[dict]) -> str:
    body = ''.join(
        f"{ch['id']}:{ch['start']}:{ch['end']}:{ch['sha256']}\n" for ch in chunks
    )
    return hashlib.sha256(body.encode()).hexdigest()


class TestMilestone2:
    def setup_method(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        if STATE.exists():
            STATE.unlink()
        if STAGING.exists():
            STAGING.unlink()
        if JOURNAL.exists():
            JOURNAL.unlink()
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

    def test_m2_success(self):
        """Chunk map digest and payload coverage persist with contract formatting."""
        chunks = json.loads(CHUNKS.read_text())
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        report = json.loads(Path('/app/output/m2.json').read_text())
        assert report['chunks_verified'] == len(chunks)
        assert report['last_end'] == chunks[-1]['end']
        st = json.loads(STATE.read_text())
        assert st['chunk_map_sha256'] == _chunk_map_digest(chunks)
        assert st['payload_coverage_end'] == report['last_end']
        assert st['apply_runs'] == []

    def test_m2_without_m1_envelope_fails(self):
        """m2 must reject when milestone 1 envelope is absent from state."""
        if STATE.exists():
            STATE.unlink()
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_payload_digest_mismatch_fails(self, tmp_path):
        """Full payload digest must match envelope.payload_sha256 from m1."""
        tampered = tmp_path / 'payload-tampered.bin'
        data = bytearray(PAYLOAD.read_bytes())
        data[0] ^= 0x01
        tampered.write_bytes(data)
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(tampered),
                '/app/output/m2.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_rerun_clears_apply_runs(self):
        """Updating the chunk map invalidates prior staged apply run ids."""
        subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2.json',
            ],
            check=True,
        )
        st = json.loads(STATE.read_text())
        st['apply_runs'] = ['stale-run']
        STATE.write_text(json.dumps(st))
        subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2-rerun.json',
            ],
            check=True,
        )
        st = json.loads(STATE.read_text())
        assert st['apply_runs'] == []

    def test_m2_truncates_apply_journal(self):
        """Rebuilding the chunk map must truncate the durable apply journal."""
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        JOURNAL.write_text(
            '{"run_id":"stale-run","generation":1}\n'
            '{"run_id":"older-run","generation":0}\n'
        )
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2-journal.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert JOURNAL.read_text() == ''

    def test_m2_commit_truncates_apply_journal(self):
        """m2-commit must truncate a prepopulated apply journal after validate."""
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        JOURNAL.write_text('{"run_id":"pre-commit","generation":1}\n')
        assert self._run_m2_validate().returncode == 0, 'validate failed'
        proc = self._run_m2_commit(Path('/app/output/m2-commit-journal.json'))
        assert proc.returncode == 0, proc.stderr
        assert JOURNAL.read_text() == ''

    def _run_m2(self, chunks_path: Path = CHUNKS, payload_path: Path = PAYLOAD) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                str(BIN),
                'm2',
                str(chunks_path),
                str(STATE),
                str(payload_path),
                '/app/output/m2.json',
            ],
            capture_output=True,
            text=True,
        )

    def test_m2_first_chunk_must_start_at_zero(self, tmp_path):
        """First chunk must begin at byte offset 0."""
        chunks = json.loads(CHUNKS.read_text())
        chunks[0]['start'] = 1
        bad = tmp_path / 'chunks-first-offset.json'
        bad.write_text(json.dumps(chunks))
        proc = self._run_m2(bad)
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_chunk_gap_fails(self, tmp_path):
        """Adjacent chunks must satisfy start == previous end with no gaps."""
        chunks = json.loads(CHUNKS.read_text())
        chunks[1]['start'] = 7
        gap = tmp_path / 'chunks-gap.json'
        gap.write_text(json.dumps(chunks))
        proc = self._run_m2(gap)
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_chunk_overlap_fails(self, tmp_path):
        """Overlapping chunk ranges must be rejected."""
        chunks = json.loads(CHUNKS.read_text())
        chunks[1]['start'] = 5
        overlap = tmp_path / 'chunks-overlap.json'
        overlap.write_text(json.dumps(chunks))
        proc = self._run_m2(overlap)
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_chunk_bounds_invalid_fails(self, tmp_path):
        """Chunk end must stay within payload length and exceed start."""
        chunks = json.loads(CHUNKS.read_text())
        chunks[1]['end'] = 999
        bounds = tmp_path / 'chunks-bounds.json'
        bounds.write_text(json.dumps(chunks))
        proc = self._run_m2(bounds)
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_per_chunk_hash_mismatch_fails(self, tmp_path):
        """Each chunk sha256 must match the corresponding payload segment."""
        chunks = json.loads(CHUNKS.read_text())
        chunks[0]['sha256'] = 'aa' * 32
        bad = tmp_path / 'chunks-bad-hash.json'
        bad.write_text(json.dumps(chunks))
        proc = self._run_m2(bad)
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m2_binds_chunk_generation(self):
        """Chunk map state must record the active workflow_generation binding."""
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2-bind.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        assert st['chunk_binding_generation'] == st['workflow_generation']

    def test_m2_rerun_clears_rollback_index(self):
        """Rebuilding the chunk map clears rollback_index from a prior m3 run."""
        subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2-first.json',
            ],
            check=True,
        )
        st = json.loads(STATE.read_text())
        st['rollback_index'] = 40
        STATE.write_text(json.dumps(st))
        subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2-second.json',
            ],
            check=True,
        )
        st = json.loads(STATE.read_text())
        assert st['rollback_index'] is None

    def _run_m2_validate(self, chunks_path: Path = CHUNKS, payload_path: Path = PAYLOAD) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm2-validate', str(chunks_path), str(STATE), str(payload_path)],
            capture_output=True,
            text=True,
        )

    def _run_m2_commit(self, out: Path = Path('/app/output/m2.json')) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm2-commit', str(STATE), str(out)],
            capture_output=True,
            text=True,
        )

    def test_m2_validate_writes_staging_not_state(self):
        """m2-validate must write chunk-map staging without mutating state.json."""
        proc = self._run_m2_validate()
        assert proc.returncode == 0, proc.stderr
        assert STAGING.is_file()
        st = json.loads(STATE.read_text())
        assert st.get('chunk_map_sha256') is None

    def test_m2_commit_without_staging_fails(self):
        """m2-commit must fail when chunk-map staging was never written."""
        if STAGING.exists():
            STAGING.unlink()
        proc = self._run_m2_commit()
        assert proc.returncode != 0
        assert 'missing verified chunk map staging' in proc.stderr.lower()

    def test_m2_validate_then_commit_matches_m2(self):
        """Split validate and commit must match one-shot m2."""
        combined = self._run_m2()
        assert combined.returncode == 0, combined.stderr
        combined_report = json.loads(Path('/app/output/m2.json').read_text())
        combined_state = json.loads(STATE.read_text())

        if STAGING.exists():
            STAGING.unlink()
        st = json.loads(STATE.read_text())
        st['chunk_map_sha256'] = None
        st['payload_coverage_end'] = None
        st['chunk_binding_generation'] = None
        STATE.write_text(json.dumps(st))

        assert self._run_m2_validate().returncode == 0
        split_out = Path('/app/output/m2-split.json')
        assert self._run_m2_commit(split_out).returncode == 0, 'commit failed'
        split_report = json.loads(split_out.read_text())
        split_state = json.loads(STATE.read_text())
        assert split_report == combined_report
        assert split_state['chunk_map_sha256'] == combined_state['chunk_map_sha256']
        assert split_state['payload_coverage_end'] == combined_state['payload_coverage_end']

    def test_m2_commit_reads_staging_not_chunk_file(self, tmp_path):
        """m2-commit must persist chunk_map_sha256 from staging, not re-read chunks.json."""
        assert self._run_m2_validate().returncode == 0, 'validate failed'
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        expected_digest = staging['chunk_map_sha256']
        chunks = json.loads(CHUNKS.read_text())
        chunks[0]['start'] = 1
        bad = tmp_path / 'chunks-trap.json'
        bad.write_text(json.dumps(chunks))
        out = Path('/app/output/m2-staging-trap.json')
        proc = self._run_m2_commit(out)
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        assert st['chunk_map_sha256'] == expected_digest

    def test_m2_digest_uses_json_file_order_not_id_sort(self, tmp_path):
        """Chunk map digest follows JSON array order, not numeric id sort."""
        chunks = json.loads(CHUNKS.read_text())
        chunks[0]['id'], chunks[1]['id'] = chunks[1]['id'], chunks[0]['id']
        reordered = tmp_path / 'chunks-id-swapped.json'
        reordered.write_text(json.dumps(chunks))
        out = Path('/app/output/m2-id-order.json')
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(reordered),
                str(STATE),
                str(PAYLOAD),
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        assert st['chunk_map_sha256'] == _chunk_map_digest(chunks)

    def test_m2_contiguity_fix_alone_still_fails_digest_format(self):
        """Bundled fixtures require newline-terminated digest lines, not semicolon rows."""
        proc = subprocess.run(
            [
                str(BIN),
                'm2',
                str(CHUNKS),
                str(STATE),
                str(PAYLOAD),
                '/app/output/m2-digest-contract.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        chunks = json.loads(CHUNKS.read_text())
        st = json.loads(STATE.read_text())
        assert st['chunk_map_sha256'] == _chunk_map_digest(chunks)
