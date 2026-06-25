"""M1 tests: H2 schema bootstrap + wrapped-key seed + recovery-config repair.

All assertions go through the public CLI surface at /app/recover or via
jaydebeapi against the same H2 file the CLI wrote. The test never touches
the Java source tree.

# v9 re-issue after platform infra fail 2026-06-23
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import jaydebeapi
import pytest

RECOVER = "/app/recover"
DB_FILE = "/app/data/evidence.mv.db"
JDBC_URL = "jdbc:h2:file:/app/data/evidence"
H2_JAR = "/opt/jars/h2-2.2.224.jar"
WRAPPED_JSON = "/app/data/wrapped_keys.json"
CONFIG_JSON = "/app/data/recovery_config.json"
EXPECTED_CONFIG_JSON = "/app/fixtures/expected_recovery_config.json"


def _run(args, check=True):
    r = subprocess.run([RECOVER] + args, capture_output=True, text=True, timeout=60)
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


def _reset_state():
    # Wipe the on-disk H2 files so init starts from scratch.
    for p in Path("/app/data").glob("evidence*"):
        if p.is_file():
            p.unlink()


def _restore_config():
    shutil.copy("/app/fixtures/_pristine_config.json", CONFIG_JSON) if Path(
        "/app/fixtures/_pristine_config.json").exists() else None


@pytest.fixture(scope="module", autouse=True)
def stash_pristine():
    # On first entry stash a copy of the broken config so we can restore it
    # for repair-related tests across the module.
    pristine = Path("/app/fixtures/_pristine_config.json")
    if not pristine.exists():
        shutil.copy(CONFIG_JSON, pristine)
    yield


class TestBuildArtifacts:
    def test_recover_script_executable(self):
        p = Path(RECOVER)
        assert p.exists(), f"{RECOVER} missing"
        assert os.access(RECOVER, os.X_OK), f"{RECOVER} not executable"

    def test_main_class_present(self):
        p = Path("/app/build/com/evidence/recovery/RecoveryMain.class")
        assert p.exists(), f"compiled main missing at {p}"

    def test_wrapped_keys_json_present(self):
        rows = json.loads(Path(WRAPPED_JSON).read_text())
        assert len(rows) >= 3
        for r in rows:
            for k in ("playlist_id", "key_version", "wrapped_key_hex",
                      "iv_hex", "sig_hex", "manifest_path", "segment_count",
                      "codec_private_sha256"):
                assert k in r, f"missing {k} in {r}"

    def test_h2_jar_present(self):
        assert Path(H2_JAR).exists()

    def test_master_key_present(self):
        p = Path("/opt/evidence_keys/master.key.hex")
        assert p.exists()
        assert len(p.read_text().strip()) == 64


class TestInit:
    def test_init_creates_db_and_seeds(self):
        _reset_state()
        r = _run(["init"])
        body = json.loads(r.stdout)
        assert body["status"] == "ok"
        assert body["seeded_keys"] >= 3
        assert Path(DB_FILE).exists()

    def test_init_keys_alpha_sorted(self):
        r = _run(["init"])
        line = r.stdout.strip()
        body = json.loads(line)
        keys = list(body.keys())
        assert keys == sorted(keys), f"keys not sorted: {keys}"

    def test_init_compact_json(self):
        r = _run(["init"])
        line = r.stdout.rstrip("\n")
        assert "\n" not in line
        assert ": " not in line and ", " not in line, "expected compact JSON"

    def test_init_creates_four_tables(self):
        _run(["init"])
        tables = {row[0].upper() for row in _query(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='PUBLIC'")}
        for t in ("PLAYLISTS", "WRAPPED_KEYS", "AUDIT_LOG", "ARTIFACTS"):
            assert t in tables, f"table {t} missing; got {tables}"

    def test_seeded_playlists_count(self):
        _run(["init"])
        rows = _query("SELECT COUNT(*) FROM playlists")
        assert rows[0][0] >= 3

    def test_seeded_wrapped_keys_match_json(self):
        _run(["init"])
        wanted = json.loads(Path(WRAPPED_JSON).read_text())
        rows = _query("SELECT playlist_id, key_version, wrapped_key_hex, iv_hex, sig_hex"
                      " FROM wrapped_keys ORDER BY playlist_id, key_version")
        got = {(r[0], r[1]): (r[2], r[3], r[4]) for r in rows}
        for w in wanted:
            k = (w["playlist_id"], w["key_version"])
            assert k in got, f"missing {k}"
            assert got[k] == (w["wrapped_key_hex"], w["iv_hex"], w["sig_hex"])

    def test_init_idempotent(self):
        _run(["init"])
        before = _query("SELECT COUNT(*) FROM wrapped_keys")[0][0]
        _run(["init"])
        after = _query("SELECT COUNT(*) FROM wrapped_keys")[0][0]
        assert before == after

    def test_init_rejects_tampered_signature(self):
        _reset_state()
        backup = json.loads(Path(WRAPPED_JSON).read_text())
        tampered = json.loads(json.dumps(backup))
        # Flip the last hex char of the first row's sig.
        sig = tampered[0]["sig_hex"]
        flipped = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        tampered[0]["sig_hex"] = flipped
        Path(WRAPPED_JSON).write_text(json.dumps(tampered))
        try:
            r = subprocess.run([RECOVER, "init"], capture_output=True, text=True, timeout=60)
            assert r.returncode == 1, f"expected exit 1, got {r.returncode}"
            err = json.loads(r.stderr)
            assert err["error"] == "sig_mismatch"
            # DB was rolled back: schema may exist (from init) but no
            # wrapped-key rows should be seeded.
            if Path(DB_FILE).exists():
                rows = _query("SELECT COUNT(*) FROM wrapped_keys")
                assert rows[0][0] == 0, "no rows should have been inserted on sig_mismatch"
        finally:
            Path(WRAPPED_JSON).write_text(json.dumps(backup))
            _reset_state()
            _run(["init"])  # restore good state


class TestRecoverConfig:
    def test_repair_writes_all_corrections(self):
        # Restore the pristine broken file before each call.
        shutil.copy("/app/fixtures/_pristine_config.json", CONFIG_JSON)
        r = _run(["recover-config"])
        body = json.loads(r.stdout)
        assert body["status"] == "ok"
        repaired = body["repaired"]
        assert isinstance(repaired, list)
        for f in ("audit_log_table", "key_wrap_algorithm",
                  "master_key_path", "segment_cipher", "segment_padding"):
            assert f in repaired, f"missing repair for {f}: {repaired}"
        # Sorted ASCII-ascending.
        assert repaired == sorted(repaired)

    def test_repair_file_matches_expected(self):
        shutil.copy("/app/fixtures/_pristine_config.json", CONFIG_JSON)
        _run(["recover-config"])
        got = json.loads(Path(CONFIG_JSON).read_text())
        want = json.loads(Path(EXPECTED_CONFIG_JSON).read_text())
        assert got == want, f"got={got} want={want}"

    def test_repair_keys_ascii_sorted_in_file(self):
        shutil.copy("/app/fixtures/_pristine_config.json", CONFIG_JSON)
        _run(["recover-config"])
        text = Path(CONFIG_JSON).read_text()
        # Re-parse preserves order in Python 3.7+; check the file order
        # manually so we catch unsorted writers.
        import re
        keys = re.findall(r'"([a-z_]+)"\s*:', text)
        assert keys == sorted(keys), f"keys not in ascii order: {keys}"

    def test_repair_idempotent(self):
        shutil.copy("/app/fixtures/_pristine_config.json", CONFIG_JSON)
        _run(["recover-config"])
        first = Path(CONFIG_JSON).read_text()
        r = _run(["recover-config"])
        body = json.loads(r.stdout)
        # On the second run nothing should be repaired.
        assert body["repaired"] == []
        assert Path(CONFIG_JSON).read_text() == first

# v7 re-issue after empty-log evaluator crash 2026-06-23 (ecb5ae3a)
