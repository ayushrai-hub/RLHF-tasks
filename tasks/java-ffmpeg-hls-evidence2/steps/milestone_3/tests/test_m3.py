"""M3 tests: ffmpeg remux + 24 validator cases + audit list.

The verifier covers the difficulty driver: six rules x (2 valid + 2 invalid)
fixtures = 24 cases, plus the playlists.audit_validator_sha256 chain
assertion that pins the order and outcome of validate() calls.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import subprocess
from pathlib import Path

import jaydebeapi
import pytest

RECOVER = "/app/recover"
JDBC_URL = "jdbc:h2:file:/app/data/evidence"
H2_JAR = "/opt/jars/h2-2.2.224.jar"
ARTIFACTS_DIR = "/app/data/artifacts"
SEGMENTS_DIR = "/app/data/hls_export/segments"
MANIFESTS_DIR = "/app/data/hls_export/manifests"
INDEX_PATH = "/app/data/segment_index.json"
EXPECTED_VALIDATORS = "/app/fixtures/expected_validators.json"
VALIDATOR_CASES = "/app/fixtures/validator_cases.json"
MASTER_KEY_PATH = "/opt/evidence_keys/master.key.hex"
NOW_OVERRIDE_BASE = 1750000000_000
ENV = {**os.environ, "RECOVERY_NOW_OVERRIDE": str(NOW_OVERRIDE_BASE)}


def _master_key():
    return bytes.fromhex(Path(MASTER_KEY_PATH).read_text().strip())


def _run(args, env=None, check=True):
    e = env if env is not None else ENV
    r = subprocess.run([RECOVER] + args, capture_output=True, text=True, timeout=180, env=e)
    if check:
        assert r.returncode == 0, f"recover {args} failed: stdout={r.stdout!r} stderr={r.stderr!r}"
    return r


def _query(sql, *params):
    conn = jaydebeapi.connect("org.h2.Driver", JDBC_URL, ["sa", ""], H2_JAR)
    try:
        cur = conn.cursor()
        cur.execute(sql, list(params))
        try:
            return cur.fetchall()
        except Exception:
            return None
    finally:
        conn.close()


def _reset_and_decrypt():
    # Clear database + plaintext segments + artifacts, then re-init and
    # run decrypt-all so M3 always starts from a known clean state.
    for p in Path("/app/data").glob("evidence*"):
        if p.is_file():
            p.unlink()
    for p in Path(SEGMENTS_DIR).glob("*.ts"):
        if not p.name.endswith(".ts.enc"):
            p.unlink(missing_ok=True)
    shutil.rmtree(ARTIFACTS_DIR, ignore_errors=True)
    _run(["init"])
    _run(["decrypt-all"])


@pytest.fixture(scope="module", autouse=True)
def fresh():
    _reset_and_decrypt()
    yield


# ---------------------------------------------------------------------
# Remux
# ---------------------------------------------------------------------

class TestRemux:
    def test_remux_emits_mp4(self):
        """Verify remux cam001 returns ok body and writes the mp4 artifact."""
        r = _run(["remux", "cam001"])
        body = json.loads(r.stdout)
        assert body["status"] == "ok"
        assert body["playlist_id"] == "cam001"
        assert len(body["sha256"]) == 64
        mp4 = Path(ARTIFACTS_DIR) / "cam001.mp4"
        assert mp4.exists() and mp4.stat().st_size > 0

    def test_remux_keys_alpha_sorted(self):
        """Verify remux response keys are ASCII-ascending sorted."""
        r = _run(["remux", "cam002"])
        body = json.loads(r.stdout)
        assert list(body.keys()) == sorted(body.keys())

    def test_remux_sha_matches_file_bytes(self):
        """Verify the response sha256 matches the on-disk mp4 byte hash."""
        r = _run(["remux", "cam003"])
        body = json.loads(r.stdout)
        mp4 = Path(ARTIFACTS_DIR) / "cam003.mp4"
        got = hashlib.sha256(mp4.read_bytes()).hexdigest()
        assert got == body["sha256"]

    def test_remux_inserts_artifact_row(self):
        """Verify remux writes an artifacts row for each remuxed playlist."""
        rows = _query("SELECT playlist_id, sha256 FROM artifacts ORDER BY artifact_id")
        ids = {r[0] for r in rows}
        assert {"cam001", "cam002", "cam003"}.issubset(ids)

    def test_remux_inserts_audit_row_with_allow(self):
        """Verify successful remux appends a decision=allow audit_log row."""
        # Spec: a successful remux inserts an audit_log row with
        # action='remux', target=<playlist_id>, decision='allow'. Without
        # this assertion an agent can produce the correct MP4 + artifacts
        # row but skip the audit insertion entirely.
        rows = _query(
            "SELECT action, target, decision FROM audit_log"
            " WHERE action='remux' AND target='cam001'")
        assert len(rows) >= 1, "no audit_log row recorded for remux cam001"
        assert rows[0][0] == "remux"
        assert rows[0][1] == "cam001"
        assert rows[0][2] == "allow", (
            f"remux cam001 audit row decision={rows[0][2]!r}, want 'allow'")
        # Also confirm the other two remuxed playlists wrote rows.
        for pid in ("cam002", "cam003"):
            rows = _query(
                "SELECT decision FROM audit_log"
                " WHERE action='remux' AND target=?", pid)
            assert len(rows) >= 1, f"no audit row for remux {pid}"
            assert rows[0][0] == "allow"

    def test_remux_missing_segments(self):
        """Verify remux missing_segments path writes a decision=deny audit row."""
        # Stash one plaintext to provoke missing_segments.
        idx = json.loads(Path(INDEX_PATH).read_text())
        target = next(e for e in idx if e["playlist_id"] == "cam001")
        p = Path(SEGMENTS_DIR) / target["segment_filename"]
        backup = p.read_bytes()
        # Snapshot audit_log seq before the failed remux so we can identify
        # the row this call appended.
        before_rows = _query("SELECT COUNT(*) FROM audit_log")[0][0]
        p.unlink()
        try:
            r = subprocess.run([RECOVER, "remux", "cam001"], capture_output=True,
                               text=True, env=ENV, timeout=60)
            assert r.returncode == 1
            err = json.loads(r.stderr)
            assert err["error"] == "missing_segments"
            # Spec: the missing_segments error path MUST append a
            # decision=deny audit_log row. Without this assertion an agent
            # can exit 1 with the right error code but skip the audit
            # write entirely, breaking forensic accountability.
            after_rows = _query("SELECT COUNT(*) FROM audit_log")[0][0]
            assert after_rows == before_rows + 1, (
                f"missing_segments must append exactly one audit_log row;"
                f" before={before_rows} after={after_rows}")
            last = _query(
                "SELECT action, target, decision FROM audit_log"
                " ORDER BY seq DESC LIMIT 1")[0]
            assert last[0] == "remux", (
                f"latest audit_log row action={last[0]!r}, want 'remux'")
            assert last[1] == "cam001", (
                f"latest audit_log row target={last[1]!r}, want 'cam001'")
            assert last[2] == "deny", (
                f"missing_segments must write decision='deny', got {last[2]!r}")
        finally:
            p.write_bytes(backup)


# ---------------------------------------------------------------------
# Validators (the difficulty driver)
# ---------------------------------------------------------------------

def _write_good_manifest(tmpdir, pid, body):
    Path(tmpdir, "manifests").mkdir(parents=True, exist_ok=True)
    Path(tmpdir, "manifests", f"{pid}.m3u8").write_text(body)


def _base_manifest_text(pid):
    return Path(MANIFESTS_DIR, f"{pid}.m3u8").read_text()


def _make_case_dir(case_id, manifest_text, pid):
    d = Path("/tmp/v_" + case_id)
    if d.exists():
        shutil.rmtree(d)
    (d / "manifests").mkdir(parents=True)
    (d / "manifests" / f"{pid}.m3u8").write_text(manifest_text)
    return d


def _run_validate(rule, pid, case_root, segments_dir=SEGMENTS_DIR, check=True):
    # case_root is the dir that contains a `manifests/` subdir holding the
    # case-specific manifest. Validator expects HLS_MANIFESTS_DIR to point
    # at the `manifests/` dir directly.
    env = {**ENV,
           "HLS_MANIFESTS_DIR": str(Path(case_root) / "manifests"),
           "HLS_SEGMENTS_DIR": segments_dir}
    return _run(["validate", rule, pid], env=env, check=check)


def _byterange_cases():
    base = _base_manifest_text("cam001")
    good = base.replace("#EXT-X-VERSION:3\n",
                        "#EXT-X-VERSION:3\n#EXT-X-BYTERANGE:1024@0\n")
    good2 = base.replace("#EXT-X-VERSION:3\n",
                         "#EXT-X-VERSION:3\n#EXT-X-BYTERANGE:2048@1024\n")
    bad = base.replace("#EXT-X-VERSION:3\n",
                       "#EXT-X-VERSION:3\n#EXT-X-BYTERANGE:0xff@0\n")
    bad2 = base.replace("#EXT-X-VERSION:3\n",
                        "#EXT-X-VERSION:3\n#EXT-X-BYTERANGE:-12@0\n")
    return [(good, True), (good2, True), (bad, False), (bad2, False)]


def _key_uri_cases():
    base = _base_manifest_text("cam001")
    good = base
    good2 = base.replace(",IV=", "_v2,IV=")
    # First good2 actually corrupted the key uri segment id; create cleaner
    # variants.
    good2 = base.replace('URI="key://cam001/1"', 'URI="key://cam001/1"')  # same
    bad = base.replace('URI="key://cam001/1"', 'URI="bad:key/cam001/1"')
    bad2 = base.replace('URI="key://cam001/1"', 'URI="key://CAM001/1"')   # uppercase pid
    return [(good, True), (good2, True), (bad, False), (bad2, False)]


def _iv_pinning_cases():
    base = _base_manifest_text("cam001")
    good = base
    good2 = base
    # Bad cases: flip last hex char of the IV.
    import re
    def _flip(b):
        return re.sub(r'IV=0x([0-9a-f]{31})([0-9a-f])',
                      lambda m: f'IV=0x{m.group(1)}{"0" if m.group(2) != "0" else "1"}',
                      b)
    return [(good, True), (good2, True),
            (_flip(base), False), (base.replace("IV=0x", "IV=0X"), False)]


def _scope_cases():
    base = _base_manifest_text("cam001")
    good = base
    good2 = base
    # Bad: drop the EXT-X-KEY line entirely.
    bad = "\n".join(line for line in base.splitlines() if not line.startswith("#EXT-X-KEY")) + "\n"
    # Bad: insert NONE before EXTINF.
    bad2 = base.replace("#EXT-X-KEY:METHOD=AES-128",
                        "#EXT-X-KEY:METHOD=NONE\n#EXT-X-KEY:METHOD=AES-128", 1)
    # Actually bad2 above adds an extra valid line then AES-128, which is
    # still valid. Force-invalidate by replacing AES-128 line with NONE.
    bad2 = base.replace("#EXT-X-KEY:METHOD=AES-128", "#EXT-X-KEY:METHOD=NONE", 1)
    return [(good, True), (good2, True), (bad, False), (bad2, False)]


def _rotation_cases():
    base = _base_manifest_text("cam001")
    good = base
    # Good rotation: insert a v2 key block half-way that exists in DB? No, DB
    # only has v1; so add another v1 row in DB? That violates schema.
    # Simpler: rotation rule is trivially valid for single-key manifests; the
    # "good" cases are both the unmodified manifest.
    good2 = base
    # Bad: declare a v2 key (not in DB).
    rotated_invalid = base
    insert_block = ('#EXT-X-KEY:METHOD=AES-128,URI="key://cam001/2",IV=0x'
                    + '00' * 16 + '\n#EXTINF:6.000,\n0099.ts\n')
    rotated_invalid = rotated_invalid.replace("#EXT-X-ENDLIST",
                                              insert_block + "#EXT-X-ENDLIST")
    bad = rotated_invalid
    # Bad2: rotation with decreasing key_version.
    bad2 = base.replace('URI="key://cam001/1"', 'URI="key://cam001/2"', 1)
    bad2 = bad2.replace("#EXT-X-ENDLIST",
                        '#EXT-X-KEY:METHOD=AES-128,URI="key://cam001/1",IV=0x'
                        + '00' * 16 + '\n#EXTINF:6.000,\n0098.ts\n#EXT-X-ENDLIST')
    return [(good, True), (good2, True), (bad, False), (bad2, False)]


def _codec_private_cases():
    base = _base_manifest_text("cam001")
    good = base
    good2 = base
    # Bad: rewrite the first segment file with garbage 16 bytes so the
    # hash mismatches. We restore after.
    idx = json.loads(Path(INDEX_PATH).read_text())
    first_seg = next(e for e in idx if e["playlist_id"] == "cam001")
    return [
        ("good_a", good, True, None),
        ("good_b", good2, True, None),
        ("bad_a", base, False, ("zero", first_seg["segment_filename"])),
        ("bad_b", base, False, ("flip", first_seg["segment_filename"])),
    ]


class TestValidatorsByteRange:
    @pytest.mark.parametrize("idx,case", list(enumerate(_byterange_cases())))
    def test_case(self, idx, case):
        """Verify byte_range_parse rule returns expected valid for each scratch case."""
        text, expected = case
        case_id = f"byte_range_parse_c{idx}"
        d = _make_case_dir(case_id, text, "cam001")
        r = _run_validate("byte_range_parse", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is expected


class TestValidatorsKeyUri:
    @pytest.mark.parametrize("idx,case", list(enumerate(_key_uri_cases())))
    def test_case(self, idx, case):
        """Verify key_uri_format rule returns expected valid for each scratch case."""
        text, expected = case
        d = _make_case_dir(f"key_uri_c{idx}", text, "cam001")
        r = _run_validate("key_uri_format", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is expected


class TestValidatorsIvPinning:
    @pytest.mark.parametrize("idx,case", list(enumerate(_iv_pinning_cases())))
    def test_case(self, idx, case):
        """Verify iv_pinning rule returns expected valid for each scratch case."""
        text, expected = case
        d = _make_case_dir(f"iv_c{idx}", text, "cam001")
        r = _run_validate("iv_pinning", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is expected


class TestValidatorsScope:
    @pytest.mark.parametrize("idx,case", list(enumerate(_scope_cases())))
    def test_case(self, idx, case):
        """Verify ext_x_key_scope rule returns expected valid for each scratch case."""
        text, expected = case
        d = _make_case_dir(f"scope_c{idx}", text, "cam001")
        r = _run_validate("ext_x_key_scope", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is expected


class TestValidatorsRotation:
    @pytest.mark.parametrize("idx,case", list(enumerate(_rotation_cases())))
    def test_case(self, idx, case):
        """Verify segment_encryption_rotation rule returns expected valid per case."""
        text, expected = case
        d = _make_case_dir(f"rot_c{idx}", text, "cam001")
        r = _run_validate("segment_encryption_rotation", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is expected


class TestValidatorsCodecPrivate:
    @pytest.mark.parametrize("case", _codec_private_cases())
    def test_case(self, case):
        """Verify codec_private_integrity rule returns expected valid per mutation."""
        tag, text, expected, mutation = case
        d = _make_case_dir(f"cp_{tag}", text, "cam001")
        # Stage the segment file (good or mutated) in a scratch dir so
        # codec_private_integrity reads the right bytes without touching the
        # canonical /app/data/hls_export/segments tree.
        seg_dir = d / "segments"
        seg_dir.mkdir(parents=True, exist_ok=True)
        # Copy every plaintext segment into the scratch dir so the
        # validator's "first segment line" lookup resolves.
        for p in Path(SEGMENTS_DIR).glob("*.ts"):
            shutil.copy(p, seg_dir / p.name)
        if mutation is not None:
            kind, fname = mutation
            target = seg_dir / fname
            data = bytearray(target.read_bytes())
            if kind == "zero":
                for i in range(16):
                    data[i] = 0
            elif kind == "flip":
                data[0] ^= 0xff
            target.write_bytes(bytes(data))
        env = {**ENV,
               "HLS_MANIFESTS_DIR": str(d / "manifests"),
               "HLS_SEGMENTS_DIR": str(seg_dir)}
        r = _run(["validate", "codec_private_integrity", "cam001"], env=env)
        body = json.loads(r.stdout)
        assert body["valid"] is expected


# ---------------------------------------------------------------------
# Validator chain - the V1 difficulty driver
# ---------------------------------------------------------------------

class TestValidatorChain:
    def test_six_rule_chain_against_cam001(self):
        """Verify the six-rule validator chain produces the expected sha256."""
        # Clean state so the chain starts empty.
        _reset_and_decrypt()
        expected = json.loads(Path(EXPECTED_VALIDATORS).read_text())
        rules = expected["rules_in_order"]
        for rule in rules:
            r = _run_validate(rule, expected["playlist_id"], Path(MANIFESTS_DIR).parent)
            body = json.loads(r.stdout)
            assert body["valid"] is True, f"rule {rule} returned valid=false"
        rows = _query("SELECT audit_validator_sha256 FROM playlists WHERE playlist_id=?",
                      expected["playlist_id"])
        got = rows[0][0]
        assert got == expected["final_validator_sha256"], (
            f"chain mismatch: got={got} want={expected['final_validator_sha256']}")


# ---------------------------------------------------------------------
# audit list
# ---------------------------------------------------------------------

class TestInvalidValidatorDoesNotMutateCam001Chain:
    def test_invalid_byte_range_leaves_cam001_chain_unchanged(self):
        """Verify scratch-path invalid byte_range_parse leaves cam001 chain intact."""
        # Spec: "Invalid cases MUST NOT mutate the playlist's
        # audit_validator_sha256 chain on cam001." Capture cam001's chain
        # column, run an invalid byte_range_parse case against a scratch
        # manifest, then assert the column is unchanged.
        _reset_and_decrypt()
        before = _query(
            "SELECT audit_validator_sha256 FROM playlists WHERE playlist_id=?",
            "cam001")
        original = before[0][0] if before else None
        # Build a known-invalid manifest using the same helper as the
        # parametrized cases.
        base = _base_manifest_text("cam001")
        bad_text = base.replace(
            "#EXT-X-VERSION:3\n",
            "#EXT-X-VERSION:3\n#EXT-X-BYTERANGE:-12@0\n")
        d = _make_case_dir("chain_immut_byte_range", bad_text, "cam001")
        r = _run_validate("byte_range_parse", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is False, (
            "fixture manifest was supposed to fail byte_range_parse")
        after = _query(
            "SELECT audit_validator_sha256 FROM playlists WHERE playlist_id=?",
            "cam001")
        after_val = after[0][0] if after else None
        assert after_val == original, (
            f"invalid validate mutated cam001 chain: before={original!r}"
            f" after={after_val!r}")

    def test_invalid_key_uri_leaves_cam001_chain_unchanged(self):
        """Verify scratch-path invalid key_uri_format leaves cam001 chain intact."""
        before = _query(
            "SELECT audit_validator_sha256 FROM playlists WHERE playlist_id=?",
            "cam001")
        original = before[0][0] if before else None
        base = _base_manifest_text("cam001")
        bad_text = base.replace('URI="key://cam001/1"', 'URI="bad:key/cam001/1"')
        d = _make_case_dir("chain_immut_key_uri", bad_text, "cam001")
        r = _run_validate("key_uri_format", "cam001", d)
        body = json.loads(r.stdout)
        assert body["valid"] is False
        after = _query(
            "SELECT audit_validator_sha256 FROM playlists WHERE playlist_id=?",
            "cam001")
        after_val = after[0][0] if after else None
        assert after_val == original, (
            f"invalid key_uri validate mutated cam001 chain: before={original!r}"
            f" after={after_val!r}")


class TestAuditList:
    def test_audit_list_emits_chain(self):
        """Verify audit list returns a chain whose entry_hash re-derives via HMAC."""
        _reset_and_decrypt()
        # Generate some audit rows.
        _run(["validate", "byte_range_parse", "cam001"])
        _run(["remux", "cam002"])
        r = _run(["audit", "list"])
        body = json.loads(r.stdout)
        assert body["count"] >= 2
        # Spec: the verifier re-derives every entry_hash using HMAC-SHA256
        # of the canonical message with the master key. Walking prev_hash
        # links alone would let an agent fabricate any hash that chains.
        mk = _master_key()
        prev = "0" * 64
        for e in body["entries"]:
            for k in ("action", "actor", "decision", "entry_hash",
                      "prev_hash", "seq", "target", "ts_epoch_ms"):
                assert k in e, f"audit entry missing field {k!r}: {e!r}"
            assert e["prev_hash"] == prev, (
                f"seq={e['seq']}: prev_hash mismatch got={e['prev_hash']} want={prev}")
            canon = (
                f"{e['seq']}|{e['ts_epoch_ms']}|{e['actor']}|"
                f"{e['action']}|{e['target']}|{e['decision']}|{prev}"
            ).encode("utf-8")
            want_eh = hmac.new(mk, canon, hashlib.sha256).hexdigest()
            assert e["entry_hash"] == want_eh, (
                f"seq={e['seq']}: entry_hash mismatch got={e['entry_hash']}"
                f" want={want_eh} (HMAC-SHA256 re-derivation)")
            prev = e["entry_hash"]
