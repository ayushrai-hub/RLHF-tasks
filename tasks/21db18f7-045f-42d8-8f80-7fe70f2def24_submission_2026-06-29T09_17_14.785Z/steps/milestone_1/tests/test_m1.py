"""Tests for milestone 1. Run alone with: pytest tests/test_m1.py"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP_DIR = "/app"
sys.path.insert(0, APP_DIR)

from block_parser import (  # noqa: E402
    extract_public_fields,
    extract_secret_fields,
    flatten_block,
    is_secret_field,
    load_block,
    validate_block_type,
)
from config import BLOCK_STAGING_BASENAME, EXPORT_SCHEMA_VERSION, STATE_DIR  # noqa: E402
from exceptions import BlockParseError  # noqa: E402


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Invoke the real CLI as a subprocess with the app on PYTHONPATH."""
    return subprocess.run(
        [sys.executable, f"{APP_DIR}/cli.py", *args],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH=APP_DIR),
    )


class TestMilestone1:
    """Milestone 1: sealed export pipeline on top of the working classifier baseline."""

    def test_inspect_cli_classifies_sample_block(self) -> None:
        """Baseline inspect command must classify bundled sample blocks."""
        proc = _run_cli("inspect", f"{APP_DIR}/sample_blocks/aws_credentials.yaml")
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        assert "aws_secret_access_key" in payload["secret_paths"]
        assert "region" in payload["public_paths"]

    # ── is_secret_field(): classification matrix ─────────────────────────────

    @pytest.mark.parametrize(
        "field",
        [
            "password",
            "aws_secret_access_key",
            "session_token",
            "api_key",
            "private_key",
            "Session_Token",
            "database_password_hash",
            "jwt_token",
            "service_credentials",
            "private_data",
            "smtp_pass",
            "api_secret_key",
            "encryption_passphrase",
            "webhook_secret_token",
        ],
    )
    def test_secret_field_names_positive(self, field: str) -> None:
        """Verify secret field names positive per field-classification and milestone contracts."""
        assert is_secret_field(field)

    @pytest.mark.parametrize(
        "field",
        [
            "host",
            "port",
            "region",
            "role_arn",
            "username",
            "endpoint_url",
            "public_key_id",
            "host_key",
            "public_api_token",
            "host_password",
        ],
    )
    def test_public_field_names_negative(self, field: str) -> None:
        """Verify public field names negative per field-classification and milestone contracts."""
        assert not is_secret_field(field)

    def test_always_public_fields_are_public(self) -> None:
        """Verify always public fields are public per field-classification and milestone contracts."""
        from config import ALWAYS_PUBLIC_FIELDS

        for name in ALWAYS_PUBLIC_FIELDS:
            assert not is_secret_field(name), f"{name!r} must be public"

    def test_fuzz_override_beats_fragment(self) -> None:
        """Verify fuzz override beats fragment per field-classification and milestone contracts."""
        import uuid

        token = uuid.uuid4().hex[:8]
        assert is_secret_field(f"tenant_{token}_client_secret")
        assert not is_secret_field(f"public_{token}_client_secret")

    # ── extraction ─────────────────────────────────────────────────────────────

    def test_database_block_extracts_password(self) -> None:
        """Verify database block extracts password per field-classification and milestone contracts."""
        block = load_block(f"{APP_DIR}/sample_blocks/database_block.yaml")
        assert "password" in extract_secret_fields(block)

    def test_aws_block_extracts_secret_access_key(self) -> None:
        """Verify aws block extracts secret access key per field-classification and milestone contracts."""
        block = load_block(f"{APP_DIR}/sample_blocks/aws_credentials.yaml")
        assert "aws_secret_access_key" in extract_secret_fields(block)

    def test_aws_block_extracts_session_token(self) -> None:
        """Verify aws block extracts session token per field-classification and milestone contracts."""
        block = load_block(f"{APP_DIR}/sample_blocks/aws_credentials.yaml")
        assert "session_token" in extract_secret_fields(block)

    def test_public_fields_exclude_aws_secrets(self) -> None:
        """Verify public fields exclude aws secrets per field-classification and milestone contracts."""
        block = load_block(f"{APP_DIR}/sample_blocks/aws_credentials.yaml")
        public = extract_public_fields(block)
        assert "aws_secret_access_key" not in public
        assert "session_token" not in public

    def test_public_fields_retain_non_secrets(self) -> None:
        """Verify public fields retain non secrets per field-classification and milestone contracts."""
        block = load_block(f"{APP_DIR}/sample_blocks/aws_credentials.yaml")
        public = extract_public_fields(block)
        assert "region" in public
        assert "role_arn" in public

    def test_partition_is_complete(self) -> None:
        """Every leaf field is in exactly one of secret/public partitions."""
        block = load_block(f"{APP_DIR}/sample_blocks/aws_credentials.yaml")
        secrets = set(extract_secret_fields(block))
        public = set(extract_public_fields(block))
        flat = flatten_block(block)
        all_leaves = set(flat)
        assert secrets.isdisjoint(public)
        assert all_leaves == (secrets | public)

    # ── load_block(): robust validation via BlockParseError ────────────────────

    def test_load_block_rejects_non_mapping(self, tmp_path) -> None:
        """Verify load block rejects non mapping per field-classification and milestone contracts."""
        p = tmp_path / "list.yaml"
        p.write_text("- a\n- b\n")
        with pytest.raises(BlockParseError):
            load_block(str(p))

    def test_load_block_rejects_invalid_yaml(self, tmp_path) -> None:
        """Verify load block rejects invalid yaml per field-classification and milestone contracts."""
        p = tmp_path / "bad.yaml"
        p.write_text("key: : : [unbalanced\n")
        with pytest.raises(BlockParseError):
            load_block(str(p))

    def test_load_block_rejects_missing_file(self) -> None:
        """Verify load block rejects missing file per field-classification and milestone contracts."""
        with pytest.raises(BlockParseError):
            load_block("/app/sample_blocks/does_not_exist.yaml")

    def test_load_block_rejects_oversized_file(self, tmp_path) -> None:
        """Verify load block rejects oversized file per field-classification and milestone contracts."""
        from config import MAX_EXPORT_FILE_SIZE

        p = tmp_path / "big.yaml"
        p.write_text("x: " + "A" * (MAX_EXPORT_FILE_SIZE + 1))
        with pytest.raises(BlockParseError):
            load_block(str(p))

    # ── validate_block_type() ──────────────────────────────────────────────────

    @pytest.mark.parametrize("slug", [
        "database-credentials",
        "aws-credentials",
        "gcp-credentials",
        "azure-credentials",
        "secret-block",
        "json-block",
    ])
    def test_validate_block_type_known(self, slug: str) -> None:
        """All KNOWN_BLOCK_TYPES must be accepted and returned unchanged."""
        assert validate_block_type({"block_type_slug": slug}) == slug

    def test_validate_block_type_unknown_raises(self) -> None:
        """Verify validate block type unknown raises per field-classification and milestone contracts."""
        with pytest.raises(BlockParseError):
            validate_block_type({"block_type_slug": "totally-made-up"})

    def test_validate_block_type_missing_raises(self) -> None:
        """Verify validate block type missing raises per field-classification and milestone contracts."""
        with pytest.raises(BlockParseError):
            validate_block_type({})

    # ── nested flattening and staging pipeline ─────────────────────────────────

    def test_nested_password_extracted(self, tmp_path) -> None:
        """Verify nested password extracted per field-classification and milestone contracts."""
        block_file = tmp_path / "nested.yaml"
        block_file.write_text(
            "block_type_slug: database-credentials\n"
            "connection:\n"
            "  host: db.internal\n"
            "  auth:\n"
            "    password: nested-secret-99\n"
        )
        block = load_block(str(block_file))
        secrets = extract_secret_fields(block)
        assert "connection.auth.password" in secrets
        assert secrets["connection.auth.password"] == "nested-secret-99"

    def test_nested_host_path_is_public(self, tmp_path) -> None:
        """Verify nested host path is public per field-classification and milestone contracts."""
        block_file = tmp_path / "nested_host.yaml"
        block_file.write_text(
            "block_type_slug: database-credentials\n"
            "connection:\n"
            "  host: db.internal\n"
            "  auth:\n"
            "    password: secret-value\n"
        )
        public = extract_public_fields(load_block(str(block_file)))
        assert "connection.host" in public
        assert "connection.auth.password" not in public

    def test_flatten_block_skips_block_type_slug(self) -> None:
        """Verify flatten block skips block type slug per field-classification and milestone contracts."""
        block = {"block_type_slug": "aws-credentials", "region": "us-east-1", "session_token": "tok"}
        flat = flatten_block(block)
        assert "block_type_slug" not in flat
        assert flat["session_token"] == "tok"

    def test_staging_writes_flattened_fields(self, tmp_path) -> None:
        """Verify staging writes flattened fields per field-classification and milestone contracts."""
        from block_stager import stage_block_from_path

        block_file = tmp_path / "nested.yaml"
        block_file.write_text(
            "block_type_slug: database-credentials\n"
            "connection:\n"
            "  auth:\n"
            "    password: staged-secret\n"
        )
        stage_block_from_path(str(block_file))
        staging_path = os.path.join(STATE_DIR, BLOCK_STAGING_BASENAME)
        staging = json.loads(open(staging_path).read())
        assert staging["block_type"] == "database-credentials"
        assert "connection.auth.password" in staging["fields"]

    def test_staging_creates_state_directory(self, tmp_path) -> None:
        """block_stager must create config.STATE_DIR before writing staging JSON."""
        import shutil

        from block_stager import stage_block_from_path

        if os.path.isdir(STATE_DIR):
            shutil.rmtree(STATE_DIR)
        block_file = tmp_path / "flat.yaml"
        block_file.write_text(
            "block_type_slug: database-credentials\n"
            "host: db.internal\n"
            "password: secret\n"
        )
        stage_block_from_path(str(block_file))
        assert os.path.isdir(STATE_DIR)
        assert os.path.isfile(os.path.join(STATE_DIR, BLOCK_STAGING_BASENAME))

    def test_randomized_nested_secret_path(self, tmp_path) -> None:
        """Verify randomized nested secret path per field-classification and milestone contracts."""
        import uuid

        leaf = f"shard_{uuid.uuid4().hex[:8]}_token"
        block_file = tmp_path / "rand.yaml"
        block_file.write_text(
            f"block_type_slug: secret-block\n"
            f"credentials:\n"
            f"  {leaf}: dynamic-secret-value\n"
        )
        secrets = extract_secret_fields(load_block(str(block_file)))
        path = f"credentials.{leaf}"
        assert path in secrets
        assert secrets[path] == "dynamic-secret-value"

    # ── manifest + seal module tests ───────────────────────────────────────────

    def test_manifest_digest_matches_sha256_spec(self) -> None:
        """Verify manifest digest matches sha256 spec per field-classification and milestone contracts."""
        import hashlib

        from secret_manifest import compute_manifest_digest

        paths = ["credentials.token", "auth.password", "meta.id"]
        expected = hashlib.sha256("\n".join(sorted(paths)).encode("utf-8")).hexdigest()
        assert compute_manifest_digest(paths) == expected

    def test_manifest_digest_order_independent(self) -> None:
        """Verify manifest digest order independent per field-classification and milestone contracts."""
        from secret_manifest import compute_manifest_digest

        paths = ["credentials.token", "auth.password", "meta.id"]
        assert compute_manifest_digest(paths) == compute_manifest_digest(list(reversed(paths)))

    def test_integrity_seal_rejects_tampered_public(self) -> None:
        """Verify integrity seal rejects tampered public per field-classification and milestone contracts."""
        from integrity_seal import compute_integrity_seal, verify_integrity_seal

        key = bytes.fromhex("ab" * 32)
        export = {
            "metadata": {
                "block_type": "test-block",
                "key_version": 1,
                "schema_version": EXPORT_SCHEMA_VERSION,
                "manifest_digest": "abc",
            },
            "public": {"host": "db.internal"},
            "secrets": {},
        }
        export["metadata"]["integrity_seal"] = compute_integrity_seal(export, key)
        export["public"]["host"] = "evil.internal"
        assert not verify_integrity_seal(export, key)

    def test_integrity_seal_matches_hmac_reference(self) -> None:
        """Seal must use HMAC-SHA256 with INTEGRITY_HMAC_LABEL prefix, not plain SHA-256."""
        import hashlib
        import hmac as hmac_mod

        from config import INTEGRITY_HMAC_LABEL
        from integrity_seal import compute_integrity_seal
        from seal_canonical import canonical_seal_bytes

        key = bytes.fromhex("ab" * 32)
        export = {
            "metadata": {
                "block_type": "test-block",
                "key_version": 1,
                "schema_version": EXPORT_SCHEMA_VERSION,
                "manifest_digest": "abc",
            },
            "public": {"host": "db.internal"},
            "secrets": {"token": "hidden"},
        }
        payload = canonical_seal_bytes(export)
        expected = hmac_mod.new(
            key, INTEGRITY_HMAC_LABEL + payload, hashlib.sha256
        ).hexdigest()
        assert compute_integrity_seal(export, key) == expected

    def test_canonical_seal_bytes_format(self) -> None:
        """Verify canonical seal bytes format per field-classification and milestone contracts."""
        from seal_canonical import canonical_seal_bytes

        export = {
            "metadata": {
                "block_type": "test-block",
                "key_version": 1,
                "schema_version": EXPORT_SCHEMA_VERSION,
                "manifest_digest": "deadbeef",
            },
            "public": {"host": "db.internal"},
            "secrets": {"token": "should-not-appear"},
        }
        raw = canonical_seal_bytes(export)
        parsed = json.loads(raw)
        assert "integrity_seal" not in parsed.get("metadata", {})
        assert "manifest_digest" in parsed, "manifest_digest must be a top-level seal key"
        assert parsed["manifest_digest"] == "deadbeef"
        assert parsed["metadata"]["manifest_digest"] == "deadbeef"
        assert "secrets" not in parsed
        assert set(parsed.keys()) == {"metadata", "public", "manifest_digest"}
        assert raw == json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()

    def test_record_rotation_commit_increments_seq(self, tmp_path) -> None:
        """Verify record rotation commit increments seq per field-classification and milestone contracts."""
        from replay_journal import initialize_journal, load_journal, record_rotation_commit

        p = tmp_path / "export.json"
        p.write_text("{}")
        initialize_journal(str(p), 1)
        record_rotation_commit(str(p), 2)
        journal = load_journal(str(p))
        assert journal["rotation_seq"] == 1
        assert journal["last_key_version"] == 2

    def test_load_journal_defaults_when_sidecar_missing(self, tmp_path) -> None:
        """Verify load journal defaults when sidecar missing per field-classification and milestone contracts."""
        from replay_journal import load_journal

        missing = tmp_path / "no_journal_yet.json"
        missing.write_text("{}")
        journal = load_journal(str(missing))
        assert journal["rotation_seq"] == 0
        assert journal["last_key_version"] == 0

    def test_initialize_journal_writes_sidecar(self, tmp_path) -> None:
        """Verify initialize journal writes sidecar per field-classification and milestone contracts."""
        from config import JOURNAL_SUFFIX
        from replay_journal import initialize_journal, load_journal

        export_path = tmp_path / "export.json"
        export_path.write_text("{}")
        initialize_journal(str(export_path), 1)
        assert (tmp_path / f"export.json{JOURNAL_SUFFIX}").exists()
        journal = load_journal(str(export_path))
        assert journal["rotation_seq"] == 0
        assert journal["last_key_version"] == 1

    # ── TB3 hidden fixtures (independent failure modes) ────────────────────────

    def test_tb3_hidden_nested_manifest_digest(self) -> None:
        """Hidden: manifest digest must use sorted secret dot-paths from TB3 nested block."""
        fixture = Path("/opt/verifier-fixtures/tb3/nested_auth_expected.json")
        if not fixture.is_file():
            pytest.skip("TB3 fixtures not mounted")
        expected = json.loads(fixture.read_text())
        block = load_block("/opt/verifier-fixtures/tb3/nested_auth_block.yaml")
        secrets = extract_secret_fields(block)
        from secret_manifest import compute_manifest_digest

        assert sorted(secrets.keys()) == sorted(expected["secret_paths"])
        assert compute_manifest_digest(sorted(secrets.keys())) == expected["manifest_digest"]

    def test_tb3_hidden_nested_classification_matrix(self) -> None:
        """Hidden: host_password and auth.host stay public while nested jwt_token is secret."""
        fixture = Path("/opt/verifier-fixtures/tb3/nested_auth_expected.json")
        if not fixture.is_file():
            pytest.skip("TB3 fixtures not mounted")
        expected = json.loads(fixture.read_text())
        block = load_block("/opt/verifier-fixtures/tb3/nested_auth_block.yaml")
        secrets = extract_secret_fields(block)
        public = extract_public_fields(block)
        assert expected["host_password_is_public"]
        assert not is_secret_field("host_password")
        assert "host_password" in public
        assert "auth.host" in public
        assert "auth.jwt_token" in secrets

    def test_journal_sidecar_canonical_bytes(self, tmp_path) -> None:
        """Replay journal must be compact sorted JSON without pretty whitespace."""
        from config import JOURNAL_SUFFIX
        from replay_journal import initialize_journal

        out = tmp_path / "export.json"
        out.write_text("{}")
        initialize_journal(str(out), 1)
        raw = (tmp_path / f"export.json{JOURNAL_SUFFIX}").read_bytes()
        parsed = json.loads(raw)
        assert raw == json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()
