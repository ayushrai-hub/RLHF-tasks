"""Milestone 4 tests — net formula, report schema, and final integration subset."""

import re

from test_helpers import (
    OUTPUT_PATH,
    assert_production_inputs_unchanged,
    assert_report_matches_expected,
    expected_report,
    load_report,
    money,
    regenerate_report,
)

ROW_MONEY_FIELDS = [
    "baseAttachment",
    "processingFeeAmount",
    "adjustmentRate",
    "tierAdjustmentAmount",
    "layerCreditAmount",
    "trancheHoldbackAmount",
    "netAttachment",
]

SUMMARY_MONEY_FIELDS = [
    "totalBaseAttachment",
    "totalProcessingFee",
    "totalTierAdjustment",
    "totalLayerCredit",
    "totalTrancheHoldback",
    "totalAttachment",
]


def test_production_inputs_unchanged_m4():
    """Ensure production input files were not edited during milestone 4."""
    assert_production_inputs_unchanged()


def test_milestone4_report_schema_and_totals():
    """Verify mvn exec:java produces Gson schema, summary totals, and netAttachment sort order."""
    regenerate_report(force=True)
    report = load_report()
    expected = expected_report()
    assert "generatedAt" in report
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", report["generatedAt"])
    assert_report_matches_expected(report, expected)

    ids = [row["id"] for row in report["attachments"]]
    assert ids == [row["id"] for row in expected["attachments"]]
    assert ids[0] == "ATT-015"


def test_milestone4_gson_pretty_print_spacing():
    """Ensure money literals use Gson pretty-print colon spacing in raw JSON from Maven."""
    regenerate_report(force=True)
    raw = OUTPUT_PATH.read_text(encoding="utf-8")
    report = load_report()
    sample = report["attachments"][0]
    value = f"{money(sample['netAttachment']):.2f}"
    assert re.search(rf'"netAttachment": {re.escape(value)}', raw)


def test_milestone4_money_fields_have_two_decimal_places():
    """Ensure serialized JSON uses spaced numeric literals with exactly two decimal places."""
    regenerate_report(force=True)
    raw = OUTPUT_PATH.read_text(encoding="utf-8")
    report = load_report()

    for row in report["attachments"]:
        for field in ROW_MONEY_FIELDS:
            value = f"{money(row[field]):.2f}"
            assert re.search(rf'"{field}": {re.escape(value)}', raw), row["id"]

    for field in SUMMARY_MONEY_FIELDS:
        value = f"{money(report['summary'][field]):.2f}"
        assert re.search(rf'"{field}": {re.escape(value)}', raw)
