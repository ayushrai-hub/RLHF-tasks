"""Milestone 4 verifier for staged apply reporting."""
import hashlib
import json
import subprocess
from pathlib import Path

BIN = Path('/app/bin/ota-chain')
STATE = Path('/app/state/ota/state.json')
OUT = Path('/app/output/m4.json')
JOURNAL = Path('/app/state/ota/apply-journal.jsonl')
STAGING = Path('/app/state/ota/verified-apply-plan.json')
VALIDATE_SEQ = Path('/app/state/ota/apply-validate-seq.json')
PLAN = Path('/app/fixtures/stage-plan.json')
TRAP_PLAN = Path('/opt/verifier-fixtures/ota-trap/stage-plan.json')


def _plan_digest(stages: list[str]) -> str:
    """SHA-256 over newline-joined stage names in plan order."""
    body = "\n".join(stages)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def _bootstrap_through_m3():
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
    subprocess.run(
        [
            str(BIN),
            'm3',
            '/app/fixtures/rollback.json',
            str(STATE),
            '/app/fixtures/current-index.txt',
            '/app/output/m3.json',
        ],
        check=True,
    )


class TestMilestone4:
    def setup_method(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        if STATE.exists():
            STATE.unlink()
        if VALIDATE_SEQ.exists():
            VALIDATE_SEQ.unlink()
        if STAGING.exists():
            STAGING.unlink()
        _bootstrap_through_m3()

    def test_m4_success(self):
        """Staged apply succeeds with full prerequisite state."""
        proc = subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-001',
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        rep = json.loads(OUT.read_text())
        assert rep['stages'] == ['download', 'verify', 'switch-slot', 'health-check']
        assert rep['state_apply_count'] == 1
        assert rep['device'] == 'stm32-fleet-a'
        assert rep['build_id'] == 'fw-2026.09.1'

    def test_m4_replay_fails(self):
        """Duplicate run-id must be rejected."""
        subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-dup',
                str(OUT),
            ],
            check=True,
        )
        proc = subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-dup',
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m4_missing_prereq_fails(self):
        """Apply without prior milestone state must fail."""
        if STATE.exists():
            STATE.unlink()
        proc = subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-missing',
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m4_rollback_below_coverage_fails(self):
        """Rollback index must be at least payload coverage from m2."""
        st = json.loads(STATE.read_text())
        st['rollback_index'] = 5
        STATE.write_text(json.dumps(st))
        proc = subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-low-rollback',
                str(OUT),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def _run_m4(self, run_id: str, out: Path = OUT) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                run_id,
                str(out),
            ],
            capture_output=True,
            text=True,
        )

    def _assert_missing_prereq_fails(self, mutate) -> None:
        st = json.loads(STATE.read_text())
        mutate(st)
        STATE.write_text(json.dumps(st))
        proc = self._run_m4('run-missing-field')
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m4_missing_envelope_fails(self):
        """Apply must fail when envelope prerequisite is absent."""
        self._assert_missing_prereq_fails(lambda st: st.__setitem__('envelope', None))

    def test_m4_missing_chunk_map_sha256_fails(self):
        """Apply must fail when chunk_map_sha256 prerequisite is absent."""
        self._assert_missing_prereq_fails(
            lambda st: st.__setitem__('chunk_map_sha256', None)
        )

    def test_m4_missing_payload_coverage_end_fails(self):
        """Apply must fail when payload_coverage_end prerequisite is absent."""
        self._assert_missing_prereq_fails(
            lambda st: st.__setitem__('payload_coverage_end', None)
        )

    def test_m4_missing_rollback_index_fails(self):
        """Apply must fail when rollback_index prerequisite is absent."""
        self._assert_missing_prereq_fails(
            lambda st: st.__setitem__('rollback_index', None)
        )

    def test_m4_sequential_runs_increment_count(self):
        """Distinct run-ids accumulate in apply_runs."""
        subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-a',
                '/app/output/m4-a.json',
            ],
            check=True,
        )
        proc = subprocess.run(
            [
                str(BIN),
                'm4',
                '/app/fixtures/stage-plan.json',
                str(STATE),
                'run-b',
                '/app/output/m4-b.json',
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        rep = json.loads(Path('/app/output/m4-b.json').read_text())
        assert rep['state_apply_count'] == 2

    def test_m4_stale_chunk_binding_generation_fails(self):
        """m4 must reject when chunk_binding_generation no longer matches workflow_generation."""
        st = json.loads(STATE.read_text())
        st['workflow_generation'] = st.get('workflow_generation', 1) + 1
        STATE.write_text(json.dumps(st))
        proc = self._run_m4('run-stale-binding')
        assert proc.returncode != 0
        assert 'invalid ota workflow' in proc.stderr.lower()

    def test_m4_append_apply_journal_line(self):
        """Successful apply appends a generation-tagged line to the apply journal."""
        if JOURNAL.exists():
            JOURNAL.unlink()
        proc = self._run_m4('run-journal')
        assert proc.returncode == 0, proc.stderr
        st = json.loads(STATE.read_text())
        lines = [ln for ln in JOURNAL.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row['run_id'] == 'run-journal'
        assert row['generation'] == st['workflow_generation']

    def _run_m4_validate(self, plan: Path = PLAN, run_id: str = 'run-validate') -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm4-validate', str(plan), str(STATE), run_id],
            capture_output=True,
            text=True,
        )

    def _run_m4_commit(self, out: Path = OUT) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(BIN), 'm4-commit', str(STATE), str(out)],
            capture_output=True,
            text=True,
        )

    def test_m4_validate_writes_staging_not_state(self):
        """m4-validate must write apply-plan staging without mutating apply_runs."""
        proc = self._run_m4_validate(run_id='run-staging-only')
        assert proc.returncode == 0, proc.stderr
        assert STAGING.is_file()
        st = json.loads(STATE.read_text())
        assert st.get('apply_runs') == []

    def test_m4_commit_without_staging_fails(self):
        """m4-commit must fail when apply-plan staging was never written."""
        if STAGING.exists():
            STAGING.unlink()
        proc = self._run_m4_commit(Path('/app/output/m4-no-staging.json'))
        assert proc.returncode != 0
        assert 'missing verified apply plan staging' in proc.stderr.lower()

    def test_m4_validate_then_commit_matches_m4(self):
        """Split validate and commit must match one-shot m4."""
        combined = self._run_m4('run-combined', Path('/app/output/m4-combined.json'))
        assert combined.returncode == 0, combined.stderr
        combined_report = json.loads(Path('/app/output/m4-combined.json').read_text())
        combined_state = json.loads(STATE.read_text())

        if STAGING.exists():
            STAGING.unlink()
        if VALIDATE_SEQ.exists():
            VALIDATE_SEQ.unlink()
        st = json.loads(STATE.read_text())
        st['apply_runs'] = []
        STATE.write_text(json.dumps(st))
        if JOURNAL.exists():
            JOURNAL.unlink()

        assert self._run_m4_validate(run_id='run-split').returncode == 0
        split_out = Path('/app/output/m4-split.json')
        assert self._run_m4_commit(split_out).returncode == 0, 'commit failed'
        split_report = json.loads(split_out.read_text())
        split_state = json.loads(STATE.read_text())
        assert split_report['stages'] == combined_report['stages']
        assert split_report['run_id'] == 'run-split'
        assert split_state['apply_runs'] == ['run-split']
        assert split_state['rollback_index'] == combined_state['rollback_index']
        assert split_state['payload_coverage_end'] == combined_state['payload_coverage_end']

    def test_m4_commit_reads_staging_not_plan_file(self, tmp_path):
        """m4-commit must use staged stages, not re-read stage-plan.json."""
        alt = tmp_path / 'alt-plan.json'
        alt.write_text(json.dumps(['preflight', 'flash', 'reboot']))
        assert self._run_m4_validate(alt, 'run-staging-trap').returncode == 0
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        PLAN.write_text(json.dumps(['tampered']))
        proc = self._run_m4_commit(Path('/app/output/m4-staging-trap.json'))
        assert proc.returncode == 0, proc.stderr
        rep = json.loads(Path('/app/output/m4-staging-trap.json').read_text())
        assert rep['stages'] == staging['stages']
        assert rep['run_id'] == 'run-staging-trap'

    def test_m4_staging_plan_digest_matches_reference(self):
        """Staging must store newline-join SHA-256 digest of stages."""
        proc = self._run_m4_validate(run_id='run-digest')
        assert proc.returncode == 0, proc.stderr
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        expected = _plan_digest(staging['stages'])
        assert staging['plan_digest'] == expected

    def test_m4_commit_rejects_plan_digest_tamper(self):
        """Commit must reject tampered plan_digest on staging."""
        assert self._run_m4_validate(run_id='run-tamper-digest').returncode == 0
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        staging['plan_digest'] = '0' * 64
        STAGING.write_text(json.dumps(staging) + '\n', encoding='utf-8')
        proc = self._run_m4_commit(Path('/app/output/m4-bad-digest.json'))
        assert proc.returncode != 0
        assert 'apply plan digest mismatch' in proc.stderr.lower()

    def test_m4_commit_rejects_validate_seq_drift(self):
        """Commit must fail when another validate bumped apply-validate-seq."""
        assert self._run_m4_validate(run_id='run-seq-a').returncode == 0
        seq = json.loads(VALIDATE_SEQ.read_text(encoding='utf-8'))
        seq['seq'] = int(seq['seq']) + 1
        VALIDATE_SEQ.write_text(json.dumps(seq) + '\n', encoding='utf-8')
        proc = self._run_m4_commit(Path('/app/output/m4-seq-drift.json'))
        assert proc.returncode != 0
        assert 'stale apply validate sequence' in proc.stderr.lower()

    def test_m4_hidden_trap_stage_plan_digest(self):
        """Hidden stage plan order must match newline-join digest contract."""
        assert TRAP_PLAN.is_file(), 'missing hidden trap stage plan fixture'
        stages = json.loads(TRAP_PLAN.read_text(encoding='utf-8'))
        assert self._run_m4_validate(TRAP_PLAN, 'run-trap-plan').returncode == 0
        staging = json.loads(STAGING.read_text(encoding='utf-8'))
        assert staging['plan_digest'] == _plan_digest(stages)
        out = Path('/app/output/m4-trap-plan.json')
        proc = self._run_m4_commit(out)
        assert proc.returncode == 0, proc.stderr
        rep = json.loads(out.read_text(encoding='utf-8'))
        assert rep['stages'] == stages

    def test_m4_commit_stale_staging_generation_fails(self):
        """Commit must reject when workflow_generation drifted after validate."""
        assert self._run_m4_validate(run_id='run-gen-drift').returncode == 0
        st = json.loads(STATE.read_text(encoding='utf-8'))
        st['workflow_generation'] = int(st.get('workflow_generation', 1)) + 1
        STATE.write_text(json.dumps(st), encoding='utf-8')
        proc = self._run_m4_commit(Path('/app/output/m4-gen-drift.json'))
        assert proc.returncode != 0
        assert 'stale apply plan staging generation' in proc.stderr.lower()
        assert 'stale chunk binding generation' not in proc.stderr.lower()
