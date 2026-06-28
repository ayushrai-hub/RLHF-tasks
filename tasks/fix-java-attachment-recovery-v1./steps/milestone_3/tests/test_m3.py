"""Milestone 3 tests — rounding schedule and amount-based premium rules."""

from test_helpers import (
    assert_production_inputs_unchanged,
    expected_report,
    load_report,
    money,
    regenerate_report,
)


def test_production_inputs_unchanged_m3():
    """Ensure production input files were not edited during milestone 3."""
    assert_production_inputs_unchanged()


def test_milestone3_layer_and_holdback_rounding():
    """Verify layer credit and tranche holdback for premium loss line edges."""
    regenerate_report()
    report = load_report()
    expected = expected_report()
    by_id = {row["id"]: row for row in report["attachments"]}
    exp_by_id = {row["id"]: row for row in expected["attachments"]}

    rounding_edges = {
        "ATT-009": ["layerCreditAmount", "trancheHoldbackAmount"],
        "ATT-011": ["tierAdjustmentAmount", "trancheHoldbackAmount"],
        "ATT-014": ["layerCreditAmount", "trancheHoldbackAmount"],
        "ATT-015": ["layerCreditAmount", "trancheHoldbackAmount"],
        "ATT-017": ["layerCreditAmount", "trancheHoldbackAmount"],
        "ATT-019": ["trancheHoldbackAmount"],
        "ATT-020": ["trancheHoldbackAmount"],
        "ATT-022": ["layerCreditAmount", "trancheHoldbackAmount"],
        "ATT-027": ["layerCreditAmount", "trancheHoldbackAmount"],
        "ATT-028": ["layerCreditAmount", "tierAdjustmentAmount"],
        "ATT-031": ["layerCreditAmount", "trancheHoldbackAmount"],
    }
    for recovery_id, fields in rounding_edges.items():
        for field in fields:
            assert money(by_id[recovery_id][field]) == money(exp_by_id[recovery_id][field])
