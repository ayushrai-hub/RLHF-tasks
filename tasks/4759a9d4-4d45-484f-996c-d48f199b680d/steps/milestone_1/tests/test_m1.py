"""Pytest helpers for milestone 1 ceremony rule extraction."""

import json
from pathlib import Path

from ledger_expected import expected_canonical_samples, expected_ceremony_rules

OUT = Path("/app/output/ceremony_rules.json")


class TestMilestone1:
    """Verify extracted ceremony rules match ratified sources."""

    def test_output_exists(self):
        """Agent must write ceremony_rules.json under /app/output."""
        assert OUT.is_file(), "missing /app/output/ceremony_rules.json"

    def test_required_top_level_keys(self):
        """Output must expose the documented top-level sections."""
        payload = json.loads(OUT.read_text())
        for key in ("signing", "keys", "bootstrap", "chain", "receipts", "authoritative_docs"):
            assert key in payload, f"missing top-level key {key}"

    def test_signing_contract(self):
        """Signing rules must match the ratified pipe-delimited contract."""
        payload = json.loads(OUT.read_text())
        expected = expected_ceremony_rules()
        signing = payload["signing"]
        assert signing["separator"] == expected["signing"]["separator"]
        assert signing["fields"] == expected["signing"]["fields"]
        assert signing["memo_empty_literal"] == expected["signing"]["memo_empty_literal"]
        assert signing["memo_normalization"] == expected["signing"]["memo_normalization"]
        assert signing["amount_format"] == expected["signing"]["amount_format"]
        assert signing["posted_at_format"] == expected["signing"]["posted_at_format"]

    def test_key_rotation_and_bootstrap(self):
        """Key rotation and bootstrap exception must match notice JSON."""
        payload = json.loads(OUT.read_text())
        expected = expected_ceremony_rules()
        keys = payload["keys"]
        assert keys["primary_key_id"] == expected["keys"]["primary_key_id"]
        assert keys["primary_effective"] == expected["keys"]["primary_effective"]
        assert keys["legacy_key_id"] == expected["keys"]["legacy_key_id"]
        assert keys["legacy_valid_before"] == expected["keys"]["legacy_valid_before"]
        assert keys["primary_public_key_path"] == expected["keys"]["primary_public_key_path"]
        assert keys["legacy_public_key_path"] == expected["keys"]["legacy_public_key_path"]
        bootstrap = payload["bootstrap"]
        assert bootstrap["signer"] == expected["bootstrap"]["signer"]
        assert bootstrap["algorithm"] == expected["bootstrap"]["algorithm"]
        assert bootstrap["seed_path"] == expected["bootstrap"]["seed_path"]
        assert bootstrap["valid_until"] == expected["bootstrap"]["valid_until"]

    def test_chain_and_receipt_contract(self):
        """Chain genesis/link rules and receipt prefix must be captured."""
        payload = json.loads(OUT.read_text())
        expected = expected_ceremony_rules()
        chain = payload["chain"]
        assert chain["genesis"] == expected["chain"]["genesis"]
        assert chain["row_digest"] == expected["chain"]["row_digest"]
        assert chain["link"] == expected["chain"]["link"]
        receipts = payload["receipts"]
        assert receipts["prefix"] == expected["receipts"]["prefix"]
        assert int(receipts["seq_width"]) == expected["receipts"]["seq_width"]

    def test_authoritative_docs(self):
        """Authoritative doc list must cite the ratified addendum and notice JSON."""
        payload = json.loads(OUT.read_text())
        expected = expected_ceremony_rules()
        docs = payload["authoritative_docs"]
        assert isinstance(docs, list) and docs, "authoritative_docs must be a non-empty list"
        for path in expected["authoritative_docs"]:
            assert path in docs, f"missing authoritative doc {path}"

    def test_rules_align_with_fixture_canonicals(self):
        """Extracted separator and field order must match independently derived samples."""
        payload = json.loads(OUT.read_text())
        sep = payload["signing"]["separator"]
        fields = payload["signing"]["fields"]
        assert sep == "|"
        assert fields[:2] == ["seq", "tenant"]
        for seq, canonical in expected_canonical_samples().items():
            assert canonical.split("|")[0] == seq
            assert len(canonical.split("|")) == len(fields)
