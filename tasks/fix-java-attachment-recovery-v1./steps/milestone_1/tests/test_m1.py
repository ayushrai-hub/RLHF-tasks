"""Milestone 1 tests — config loader and eligibility."""

from test_helpers import (
    CONFIG_PATH,
    assert_production_inputs_unchanged,
    eligible_attachment_ids,
    load_report,
    regenerate_report,
)

EXPECTED_ELIGIBLE_COUNT = 26


def test_production_inputs_unchanged_m1():
    """Ensure production input files were not edited during milestone 1."""
    assert_production_inputs_unchanged()


def test_milestone1_eligible_recovery_count():
    """Verify production loader and eligibility include exactly 26 attachments."""
    regenerate_report()
    report = load_report()
    ids = {row["id"] for row in report["attachments"]}
    assert report["summary"]["attachmentCount"] == EXPECTED_ELIGIBLE_COUNT
    assert ids == eligible_attachment_ids()
    assert "ATT-003" in ids
    assert "ATT-006" not in ids
    assert "ATT-026" not in ids
    assert "ATT-030" not in ids


def test_milestone1_minimum_threshold_loaded_from_properties():
    """Verify eligibility responds to minimum.attachment.amount read from config."""
    assert_production_inputs_unchanged()
    original_config = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        CONFIG_PATH.write_text(
            original_config.replace(
                "minimum.attachment.amount=1500.00",
                "minimum.attachment.amount=5000.00",
            ),
            encoding="utf-8",
        )
        regenerate_report(force=True)
        report = load_report()
        assert report["summary"]["attachmentCount"] == 21
        assert "ATT-005" not in {row["id"] for row in report["attachments"]}
    finally:
        CONFIG_PATH.write_text(original_config, encoding="utf-8")
    assert_production_inputs_unchanged()
