"""Milestone 2 tests — calculation pipeline order and tier adjustment basis."""

from test_helpers import (
    assert_production_inputs_unchanged,
    expected_m2_tier_adjustment,
    load_config,
    load_report,
    money,
    attachment_source_by_id,
    regenerate_report,
    round_money,
)

M2_EDGE_IDS = [
    "ATT-009",
    "ATT-013",
    "ATT-016",
    "ATT-018",
    "ATT-021",
    "ATT-027",
    "ATT-028",
    "ATT-029",
    "ATT-031",
]

M2_BASE_ATTACHMENT = {
    "ATT-009": "800.00",
    "ATT-016": "2040.00",
    "ATT-018": "2948.00",
}

M2_NON_LAYER_ID = "ATT-011"


def test_production_inputs_unchanged_m2():
    """Ensure production input files were not edited during milestone 2."""
    assert_production_inputs_unchanged()


def test_milestone2_pipeline_intermediate_amounts():
    """Verify tier adjustment basis uses baseAttachment minus layer credit on cat lines."""
    regenerate_report()
    report = load_report()
    config = load_config()
    sources = attachment_source_by_id()
    by_id = {row["id"]: row for row in report["attachments"]}

    for recovery_id in M2_EDGE_IDS:
        row = by_id[recovery_id]
        source = sources[recovery_id]
        expected_adj = expected_m2_tier_adjustment(row, source, config)
        assert money(row["tierAdjustmentAmount"]) == expected_adj, recovery_id

        layer_credit = money(row["layerCreditAmount"])
        base_recovery = money(row["baseAttachment"])
        adjustment_rate = money(row["adjustmentRate"])
        loss_amount = source["exposureAmount"]
        tier = source["programTier"].lower()
        catastrophe_threshold = money(config["attachment.threshold.layer"])

        if (
            tier in ("premium", "plus")
            and money(loss_amount) >= catastrophe_threshold
            and layer_credit > 0
        ):
            assert money(row["tierAdjustmentAmount"]) < round_money(base_recovery * adjustment_rate)

    for recovery_id, expected_base in M2_BASE_ATTACHMENT.items():
        assert money(by_id[recovery_id]["baseAttachment"]) == money(expected_base)

    non_layer = by_id[M2_NON_LAYER_ID]
    non_layer_source = sources[M2_NON_LAYER_ID]
    base_attachment = money(non_layer["baseAttachment"])
    adjustment_rate = money(non_layer["adjustmentRate"])
    exposure_amount = money(non_layer_source["exposureAmount"])
    tier = non_layer_source["programTier"].lower()
    layer_threshold = money(config["attachment.threshold.layer"])
    assert tier in ("premium", "plus")
    assert exposure_amount < layer_threshold
    assert money(non_layer["tierAdjustmentAmount"]) == round_money(base_attachment * adjustment_rate)
