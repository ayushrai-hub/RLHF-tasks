"""Shared helpers for attachment recovery verifier tests."""

import hashlib
import json
import subprocess
from decimal import ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal
from pathlib import Path

APP_DIR = Path("/app")
CONFIG_PATH = APP_DIR / "config" / "attachment-rules.properties"
OVERRIDE_CONFIG_PATH = APP_DIR / "config" / "attachment-rules.override.properties"
OUTPUT_PATH = APP_DIR / "output" / "attachment-report.json"
ATTACHMENTS_PATH = APP_DIR / "data" / "attachments.json"

EXPECTED_ATTACHMENTS_SHA256 = (
    "9b0000c8a202d62171941da8a6560930338f3d4b84202e3493c35396fa1aa0d5"
)
EXPECTED_CONFIG_SHA256 = (
    "7d21e038b1aababaa03f2cfc08725ae77b9d328486ea511bde0a6acdc6260f6e"
)
EXPECTED_OVERRIDE_CONFIG_SHA256 = (
    "520c3299302faff6b6eb511ddec11d3e129bf6975cf6b29bb1322974a80b0ee9"
)

EXPECTED_ATTACHMENTS: list[dict] = [
    {"id": "ATT-001", "obligor": "Atlantic Mutual", "exposureAmount": 8500.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-002", "obligor": "Pacific Re Ltd", "exposureAmount": 3200.00, "status": "pending", "programTier": "plus"},
    {"id": "ATT-003", "obligor": "Midwest Treaty Co", "exposureAmount": 12000.00, "status": "APPROVED", "programTier": "plus"},
    {"id": "ATT-004", "obligor": "Zero Loss Batch", "exposureAmount": 0.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-005", "obligor": "Harbor Underwriters", "exposureAmount": 2100.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-006", "obligor": "Summit Re Group", "exposureAmount": 1200.00, "status": "Approved", "programTier": "basic"},
    {"id": "ATT-007", "obligor": "Delta Cession Pool", "exposureAmount": 4500.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-008", "obligor": "Crown Treaty", "exposureAmount": 1400.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-009", "obligor": "Fleet Cat Layer", "exposureAmount": 10000.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-010", "obligor": "Starter Attachment", "exposureAmount": 1500.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-011", "obligor": "Elite Cat Bond", "exposureAmount": 5000.00, "status": "approved", "programTier": "PREMIUM"},
    {"id": "ATT-012", "obligor": "Regional Quota Share", "exposureAmount": 7365.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-013", "obligor": "Partner XoL", "exposureAmount": 6500.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-014", "obligor": "Volume Basic Layer", "exposureAmount": 10500.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-015", "obligor": "Enterprise Cat", "exposureAmount": 52150.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-016", "obligor": "Channel Surplus", "exposureAmount": 25500.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-017", "obligor": "Pilot Facultative", "exposureAmount": 22450.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-018", "obligor": "Flagship Event", "exposureAmount": 36850.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-019", "obligor": "Mid-Tier Layer", "exposureAmount": 5200.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-020", "obligor": "High Basic Stack", "exposureAmount": 8800.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-021", "obligor": "Coastal Wind Pool", "exposureAmount": 9800.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-022", "obligor": "Inland Flood XoL", "exposureAmount": 11200.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-023", "obligor": "Retrocession Alpha", "exposureAmount": 15800.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-024", "obligor": "Retrocession Beta", "exposureAmount": 4200.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-025", "obligor": "Minimum Edge Case", "exposureAmount": 1500.00, "status": "approved", "programTier": "premium"},
    {"id": "ATT-026", "obligor": "Staging Reject", "exposureAmount": 800.00, "status": "approved", "programTier": "basic"},
    {"id": "ATT-027", "obligor": "Cat Boundary Plus", "exposureAmount": 10000.00, "status": "approved", "programTier": "plus"},
    {"id": "ATT-028", "obligor": "Premium HALF_DOWN Note", "exposureAmount": 10001.19, "status": "approved", "programTier": "premium"},
    {"id": "ATT-029", "obligor": "Plus HALF_DOWN Basis", "exposureAmount": 10001.27, "status": "approved", "programTier": "plus"},
    {"id": "ATT-030", "obligor": "Subminimum Decimal", "exposureAmount": 1499.99, "status": "approved", "programTier": "basic"},
    {"id": "ATT-031", "obligor": "Premium Cat Edge Note", "exposureAmount": 10021.19, "status": "approved", "programTier": "premium"},
    {"id": "ATT-032", "obligor": "Premium Basis Fraction", "exposureAmount": 10001.32, "status": "approved", "programTier": "premium"},
]


def assert_production_inputs_unchanged() -> None:
    """Reject agent edits to production input data or config before scoring."""
    attachments_digest = hashlib.sha256(ATTACHMENTS_PATH.read_bytes()).hexdigest()
    config_digest = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    override_digest = hashlib.sha256(OVERRIDE_CONFIG_PATH.read_bytes()).hexdigest()
    assert attachments_digest == EXPECTED_ATTACHMENTS_SHA256, (
        f"{ATTACHMENTS_PATH} was modified; fix Java logic instead of editing input data"
    )
    assert config_digest == EXPECTED_CONFIG_SHA256, (
        f"{CONFIG_PATH} was modified; fix Java logic instead of editing production config"
    )
    assert override_digest == EXPECTED_OVERRIDE_CONFIG_SHA256, (
        f"{OVERRIDE_CONFIG_PATH} was modified or removed; fix the loader instead"
    )


def run_maven(args: list[str]) -> subprocess.CompletedProcess:
    """Run Maven inside /app using offline mode for no-network verifier runs."""
    if args and args[0] == "exec:java":
        install = subprocess.run(
            ["mvn", "-q", "-B", "-o", "install", "-DskipTests"],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if install.returncode != 0:
            return install
        args = ["-pl", "attachment-batch", "exec:java"]
    return subprocess.run(
        ["mvn", "-q", "-B", "-o", *args],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


def load_report() -> dict:
    with OUTPUT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_attachments() -> list[dict]:
    with ATTACHMENTS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_config() -> dict[str, str]:
    config = {}
    for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip()
    return config


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_layer_line(loss_amount: Decimal, catastrophe_threshold: Decimal) -> bool:
    return loss_amount >= catastrophe_threshold


def is_premium_loss_line(loss_amount: Decimal, premium_threshold: Decimal) -> bool:
    return loss_amount >= premium_threshold


def round_layer_credit(value: Decimal, tier: str, catastrophe_line: bool) -> Decimal:
    if catastrophe_line and tier == "premium":
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_tier_adjustment(
    value: Decimal,
    tier: str,
    catastrophe_line: bool,
    premium_loss_line: bool,
) -> Decimal:
    if tier == "plus" and catastrophe_line:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)
    if tier == "premium" and premium_loss_line:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_tranche_holdback(value: Decimal, catastrophe_line: bool) -> Decimal:
    if catastrophe_line:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def eligible_attachment_ids() -> set[str]:
    """Return recovery ids eligible under production config and eligibility rules."""
    config = load_config()
    minimum = Decimal(config["minimum.attachment.amount"])
    eligible = set()
    for recovery in load_attachments():
        if recovery["status"].lower() != "approved":
            continue
        if recovery["exposureAmount"] <= 0:
            continue
        if Decimal(str(recovery["exposureAmount"])) < minimum:
            continue
        eligible.add(recovery["id"])
    return eligible


def attachment_source_by_id() -> dict[str, dict]:
    """Map recovery id to the production input row."""
    return {recovery["id"]: recovery for recovery in EXPECTED_ATTACHMENTS}


def expected_m2_tier_adjustment(report_row: dict, recovery: dict, config: dict[str, str]) -> Decimal:
    """Compute tier adjustment after M2 pipeline and basis fixes for the row's cat credit."""
    base_recovery = money(report_row["baseAttachment"])
    layer_credit = money(report_row["layerCreditAmount"])
    adjustment_rate = money(report_row["adjustmentRate"])
    loss_amount = Decimal(str(recovery["exposureAmount"]))
    catastrophe_threshold = Decimal(config["attachment.threshold.layer"])
    tier = recovery["programTier"].lower()

    basis = base_recovery
    if tier in ("premium", "plus") and loss_amount >= catastrophe_threshold:
        basis = base_recovery - layer_credit
    return round_money(basis * adjustment_rate)


def compute_expected(recovery: dict, config: dict[str, str]) -> dict | None:
    if recovery["status"].lower() != "approved" or recovery["exposureAmount"] <= 0:
        return None

    loss_amount = round_money(Decimal(str(recovery["exposureAmount"])))
    minimum = Decimal(config["minimum.attachment.amount"])
    if loss_amount < minimum:
        return None

    tier = recovery["programTier"].lower()
    catastrophe_threshold = Decimal(config["attachment.threshold.layer"])
    premium_threshold = Decimal(config["attachment.threshold.exposure.premium"])
    catastrophe_line = is_layer_line(loss_amount, catastrophe_threshold)
    premium_loss_line = is_premium_loss_line(loss_amount, premium_threshold)

    base_recovery = round_money(loss_amount * Decimal(config["base.attachment.rate"]))
    processing_fee_amount = round_money(loss_amount * Decimal(config["processing.fee.rate"]))
    adjustment_rate = Decimal(config[f"adjustment.tier.{tier}"])

    layer_credit_amount = Decimal("0.00")
    if catastrophe_line:
        cat_rate = (
            Decimal(config["attachment.rate.layer.premium"])
            if premium_loss_line
            else Decimal(config["layer.credit.rate"])
        )
        layer_credit_amount = round_layer_credit(
            base_recovery * cat_rate, tier, catastrophe_line
        )

    if tier in ("premium", "plus") and catastrophe_line:
        adjustment_basis = base_recovery - layer_credit_amount
    else:
        adjustment_basis = base_recovery
    tier_adjustment_amount = round_tier_adjustment(
        adjustment_basis * adjustment_rate, tier, catastrophe_line, premium_loss_line
    )

    if tier == "basic" and loss_amount == minimum:
        retention_holdback_amount = Decimal("0.00")
    else:
        holdback_rate = (
            Decimal(config["attachment.rate.holdback.premium"])
            if premium_loss_line
            else Decimal(config["tranche.holdback.rate"])
        )
        taxable = (
            base_recovery
            - tier_adjustment_amount
            - layer_credit_amount
            + processing_fee_amount
        )
        retention_holdback_amount = round_tranche_holdback(
            taxable * holdback_rate, catastrophe_line
        )

    net_recovery = round_money(
        base_recovery
        - tier_adjustment_amount
        - layer_credit_amount
        + processing_fee_amount
        - retention_holdback_amount
    )

    return {
        "id": recovery["id"],
        "baseAttachment": base_recovery,
        "processingFeeAmount": processing_fee_amount,
        "adjustmentRate": round_money(adjustment_rate),
        "tierAdjustmentAmount": tier_adjustment_amount,
        "layerCreditAmount": layer_credit_amount,
        "trancheHoldbackAmount": retention_holdback_amount,
        "netAttachment": net_recovery,
    }


def expected_report() -> dict:
    config = load_config()
    rows = []
    for recovery in load_attachments():
        computed = compute_expected(recovery, config)
        if computed is not None:
            rows.append(computed)

    rows.sort(key=lambda row: (-row["netAttachment"], row["id"]))

    return {
        "attachments": rows,
        "summary": {
            "attachmentCount": len(rows),
            "totalBaseAttachment": sum(row["baseAttachment"] for row in rows),
            "totalProcessingFee": sum(row["processingFeeAmount"] for row in rows),
            "totalTierAdjustment": sum(row["tierAdjustmentAmount"] for row in rows),
            "totalLayerCredit": sum(row["layerCreditAmount"] for row in rows),
            "totalTrancheHoldback": sum(row["trancheHoldbackAmount"] for row in rows),
            "totalAttachment": sum(row["netAttachment"] for row in rows),
        },
    }


def assert_report_matches_expected(report: dict, expected: dict) -> None:
    """Compare money fields, pass-through row data, and summary totals against expectations."""
    sources = {recovery["id"]: recovery for recovery in EXPECTED_ATTACHMENTS}

    assert report["summary"]["attachmentCount"] == expected["summary"]["attachmentCount"]
    assert len(report["attachments"]) == expected["summary"]["attachmentCount"]

    for actual, exp in zip(report["attachments"], expected["attachments"]):
        assert actual["id"] == exp["id"]
        source = sources[actual["id"]]
        assert actual["obligor"] == source["obligor"]
        assert money(actual["exposureAmount"]) == money(source["exposureAmount"])
        assert actual["programTier"] == source["programTier"]
        assert money(actual["baseAttachment"]) == exp["baseAttachment"]
        assert money(actual["processingFeeAmount"]) == exp["processingFeeAmount"]
        assert money(actual["adjustmentRate"]) == exp["adjustmentRate"]
        assert money(actual["tierAdjustmentAmount"]) == exp["tierAdjustmentAmount"]
        assert money(actual["layerCreditAmount"]) == exp["layerCreditAmount"]
        assert money(actual["trancheHoldbackAmount"]) == exp["trancheHoldbackAmount"]
        assert money(actual["netAttachment"]) == exp["netAttachment"]

    summary = report["summary"]
    for field in [
        "totalBaseAttachment",
        "totalProcessingFee",
        "totalTierAdjustment",
        "totalLayerCredit",
        "totalTrancheHoldback",
        "totalAttachment",
    ]:
        assert money(summary[field]) == money(expected["summary"][field])


def delete_report() -> None:
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()


_report_from_exec_java = False


def regenerate_report(*, force: bool = False) -> None:
    """Build the report through the production Maven entrypoint only."""
    global _report_from_exec_java
    if _report_from_exec_java and not force and OUTPUT_PATH.is_file():
        return

    delete_report()
    result = run_maven(["exec:java"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert OUTPUT_PATH.is_file(), f"Missing report at {OUTPUT_PATH}"
    _report_from_exec_java = True
