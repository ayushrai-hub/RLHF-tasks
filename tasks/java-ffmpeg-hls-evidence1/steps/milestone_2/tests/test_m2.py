"""M2 tests: AES-128 segment decryption + audit-chain inserts.

Every assertion goes through /app/recover; we then re-derive the
HMAC-SHA256 audit chain in Python and compare against the rows
written to H2.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
from pathlib import Path

import jaydebeapi
import pytest

RECOVER = "/app/recover"
JDBC_URL = "jdbc:h2:file:/app/data/evidence"
H2_JAR = "/opt/jars/h2-2.2.224.jar"
MASTER_KEY_PATH = "/opt/evidence_keys/master.key.hex"
INDEX_PATH = "/app/data/segment_index.json"
EXPECTED_DECRYPT = "/app/fixtures/expected_decrypt.json"
SEGMENTS_DIR = "/app/data/hls_export/segments"
NOW_OVERRIDE_BASE = 1750000000_000  # ms - must agree with fixture seed
ENV = {**os.environ, "RECOVERY_NOW_OVERRIDE": str(NOW_OVERRIDE_BASE)}


def _master_key():
    return bytes.fromhex(Path(MASTER_KEY_PATH).read_text().strip())


def _run(args, env=None, check=True):
    e = env if env is not None else ENV
    r = subprocess.run([RECOVER] + args, capture_output=True, text=True, timeout=120, env=e)
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


def _reset_segments_and_db():
    # Remove plaintext segments + DB so each test starts clean.
    for p in Path(SEGMENTS_DIR).glob("*.ts"):
        if not p.name.endswith(".ts.enc"):
            p.unlink(missing_ok=True)
    for p in Path("/app/data").glob("evidence*"):
        if p.is_file():
            p.unlink()


def _expected_entry_hash(seq, ts, actor, action, target, decision, prev_hash):
    canon = f"{seq}|{ts}|{actor}|{action}|{target}|{decision}|{prev_hash}".encode("utf-8")
    return hmac.new(_master_key(), canon, hashlib.sha256).hexdigest()


@pytest.fixture(scope="module", autouse=True)
def fresh_init():
    _reset_segments_and_db()
    _run(["init"])
    yield


class TestDecryptSingle:
    def test_decrypt_known_segment(self):
        """Verify decrypt of one segment emits ok body and matching audit_id."""
        idx = json.loads(Path(INDEX_PATH).read_text())
        seg0 = idx[0]
        r = _run(["decrypt", str(seg0["segment_index"])])
        body = json.loads(r.stdout)
        assert body["status"] == "ok"
        assert body["segment"] == seg0["segment_index"]
        assert body["bytes"] > 0
        out_path = Path(SEGMENTS_DIR) / seg0["segment_filename"]
        assert out_path.exists()
        # Spec requires audit_id field linking response to the audit_log row.
        assert "audit_id" in body, "decrypt success body missing audit_id"
        assert isinstance(body["audit_id"], int) and body["audit_id"] >= 1
        last = _query(
            "SELECT seq FROM audit_log WHERE action='decrypt'"
            " ORDER BY seq DESC LIMIT 1")
        assert last and body["audit_id"] == last[0][0], (
            f"audit_id {body['audit_id']} does not match latest audit_log seq {last[0][0] if last else None}")

    def test_decrypt_plaintext_matches_expected(self):
        """Verify each decrypted segment SHA-256 matches the expected fixture."""
        exp = json.loads(Path(EXPECTED_DECRYPT).read_text())
        idx = json.loads(Path(INDEX_PATH).read_text())
        idx_by_id = {e["segment_index"]: e for e in idx}
        for e in exp:
            si = e["segment_index"]
            r = _run(["decrypt", str(si)])
            body = json.loads(r.stdout)
            assert body["bytes"] == e["bytes"]
            out = Path(SEGMENTS_DIR) / idx_by_id[si]["segment_filename"]
            got = hashlib.sha256(out.read_bytes()).hexdigest()
            assert got == e["plaintext_sha256"], (
                f"segment {si}: got={got} want={e['plaintext_sha256']}")

    def test_decrypt_segment_keys_alpha_sorted(self):
        """Verify decrypt response keys are ASCII-ascending sorted."""
        idx = json.loads(Path(INDEX_PATH).read_text())
        r = _run(["decrypt", str(idx[1]["segment_index"])])
        body = json.loads(r.stdout)
        assert list(body.keys()) == sorted(body.keys())

    def test_decrypt_unknown_segment(self):
        """Verify decrypt of an unknown segment exits 1 with segment_unknown error."""
        r = subprocess.run([RECOVER, "decrypt", "9999"],
                           capture_output=True, text=True, env=ENV)
        assert r.returncode == 1
        err = json.loads(r.stderr)
        assert err["error"] == "segment_unknown"


class TestDecryptAll:
    def test_decrypt_all_emits_summary(self):
        """Verify decrypt-all reports allowed=N, denied=0 on a clean run."""
        # Wipe plaintext + db state then re-init for a clean run.
        _reset_segments_and_db()
        _run(["init"])
        r = _run(["decrypt-all"])
        body = json.loads(r.stdout)
        assert body["status"] == "ok"
        idx = json.loads(Path(INDEX_PATH).read_text())
        assert body["allowed"] == len(idx)
        assert body["denied"] == 0

    def test_decrypt_all_writes_all_plaintexts(self):
        """Verify decrypt-all writes a plaintext file for every indexed segment."""
        idx = json.loads(Path(INDEX_PATH).read_text())
        for e in idx:
            p = Path(SEGMENTS_DIR) / e["segment_filename"]
            assert p.exists(), f"missing plaintext {p}"

    def test_decrypt_all_exits_nonzero_on_partial_failure(self):
        """Verify decrypt-all exits 1 and counts denies when any sig is tampered."""
        # Spec: "exit is 0 iff every call succeeded." Tamper one playlist's
        # wrapped_keys signature, then assert decrypt-all exits 1 and reports
        # at least one deny.
        _reset_segments_and_db()
        _run(["init"])
        backup = _query(
            "SELECT playlist_id, key_version, sig_hex FROM wrapped_keys"
            " ORDER BY playlist_id LIMIT 1")
        pid, kv, sig = backup[0]
        flipped = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        conn = jaydebeapi.connect("org.h2.Driver", JDBC_URL, ["sa", ""], H2_JAR)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE wrapped_keys SET sig_hex=? WHERE playlist_id=? AND key_version=?",
                [flipped, pid, kv])
            conn.commit()
        finally:
            conn.close()
        try:
            r = subprocess.run(
                [RECOVER, "decrypt-all"], capture_output=True, text=True,
                env=ENV, timeout=180)
            assert r.returncode == 1, (
                f"decrypt-all returned {r.returncode}; spec says exit 1 on any failure")
            body = json.loads(r.stdout)
            assert body["status"] == "ok"
            assert body["denied"] >= 1, "denied counter did not record the tampered playlist"
            assert body["allowed"] >= 0
        finally:
            # Restore good sig + clean state so downstream classes see a
            # consistent chain.
            conn = jaydebeapi.connect("org.h2.Driver", JDBC_URL, ["sa", ""], H2_JAR)
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE wrapped_keys SET sig_hex=? WHERE playlist_id=? AND key_version=?",
                    [sig, pid, kv])
                conn.commit()
            finally:
                conn.close()
            _reset_segments_and_db()
            _run(["init"])
            _run(["decrypt-all"])


class TestAuditChainAfterDecrypt:
    def test_audit_row_count_matches_decrypt_calls(self):
        """Verify decrypt-all writes exactly one audit_log row per segment."""
        # Spec: "Every call writes one row" - exactly one. Run a clean
        # decrypt-all over the full segment set and assert the count is
        # exactly N (no duplicate or stray rows).
        _reset_segments_and_db()
        _run(["init"])
        _run(["decrypt-all"])
        idx = json.loads(Path(INDEX_PATH).read_text())
        rows = _query("SELECT COUNT(*) FROM audit_log WHERE action='decrypt'")
        assert rows[0][0] == len(idx), (
            f"expected exactly {len(idx)} decrypt audit rows, got {rows[0][0]}")

    def test_audit_chain_genesis_zero_prev(self):
        """Verify the first audit_log row has prev_hash of 64 zero hex chars."""
        rows = _query("SELECT seq, prev_hash FROM audit_log ORDER BY seq LIMIT 1")
        assert rows, "audit_log empty"
        assert rows[0][0] == 1
        assert rows[0][1] == "0" * 64

    def test_audit_chain_entry_hash_recomputes(self):
        """Verify every audit_log entry_hash re-derives via HMAC-SHA256 of canonical."""
        rows = _query(
            "SELECT seq, ts_epoch_ms, actor, action, target, decision,"
            " prev_hash, entry_hash FROM audit_log ORDER BY seq")
        prev = "0" * 64
        for seq, ts, actor, action, target, decision, ph, eh in rows:
            assert ph == prev, f"seq={seq}: prev_hash mismatch got={ph} want={prev}"
            want = _expected_entry_hash(seq, ts, actor, action, target, decision, ph)
            assert eh == want, f"seq={seq}: entry_hash mismatch got={eh} want={want}"
            prev = eh


class TestAuditOnSigMismatch:
    def test_deny_row_written_on_tampered_sig(self):
        """Verify a tampered sig produces a decision=deny audit_log row."""
        # Snapshot then mutate one wrapped_keys row to force sig_mismatch.
        backup = _query(
            "SELECT playlist_id, key_version, sig_hex FROM wrapped_keys ORDER BY playlist_id LIMIT 1")
        pid, kv, sig = backup[0]
        flipped = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        # Set seq base for prediction.
        before_rows = _query("SELECT COUNT(*) FROM audit_log")[0][0]
        conn = jaydebeapi.connect("org.h2.Driver", JDBC_URL, ["sa", ""], H2_JAR)
        try:
            cur = conn.cursor()
            cur.execute("UPDATE wrapped_keys SET sig_hex=? WHERE playlist_id=? AND key_version=?",
                        [flipped, pid, kv])
            conn.commit()
        finally:
            conn.close()
        # Pick a segment in that playlist.
        idx = json.loads(Path(INDEX_PATH).read_text())
        seg = next(e for e in idx if e["playlist_id"] == pid)
        r = subprocess.run([RECOVER, "decrypt", str(seg["segment_index"])],
                           capture_output=True, text=True, env=ENV)
        assert r.returncode == 1
        err = json.loads(r.stderr)
        assert err["error"] == "sig_mismatch"
        after_rows = _query("SELECT COUNT(*) FROM audit_log")[0][0]
        assert after_rows == before_rows + 1
        last = _query(
            "SELECT action, decision, target FROM audit_log ORDER BY seq DESC LIMIT 1")[0]
        assert last[0] == "decrypt"
        assert last[1] == "deny"
        assert last[2] == str(seg["segment_index"])
        # Restore good sig + re-init for downstream classes.
        conn = jaydebeapi.connect("org.h2.Driver", JDBC_URL, ["sa", ""], H2_JAR)
        try:
            cur = conn.cursor()
            cur.execute("UPDATE wrapped_keys SET sig_hex=? WHERE playlist_id=? AND key_version=?",
                        [sig, pid, kv])
            conn.commit()
        finally:
            conn.close()
