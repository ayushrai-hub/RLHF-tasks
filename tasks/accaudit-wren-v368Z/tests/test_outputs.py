"""Tests for accaudit-wren: validates /app/audit_report.json produced by audit.wren."""

import json
from pathlib import Path

REPORT = Path("/app/audit_report.json")


def load_report():
    """Load and parse the audit report JSON."""
    assert REPORT.exists(), f"{REPORT} not found — did wren_cli /app/audit.wren run?"
    with open(REPORT) as f:
        data = json.load(f)
    assert isinstance(data, list), "audit_report.json must be a JSON array"
    return data


def errors_with(report, *, error_code=None, txn_id=None, account_id=None):
    """Return all error records matching the given filters."""
    result = report
    if error_code is not None:
        result = [e for e in result if e.get("error_code") == error_code]
    if txn_id is not None:
        result = [e for e in result if e.get("txn_id") == txn_id]
    if account_id is not None:
        result = [e for e in result if e.get("account_id") == account_id]
    return result


# ── schema ────────────────────────────────────────────────────────────────────

def test_report_is_json_array():
    """Verify audit_report.json exists and is a non-empty JSON array."""
    report = load_report()
    assert len(report) > 0


def test_each_record_has_required_keys():
    """Verify every error record contains txn_id, account_id, error_code, detail."""
    report = load_report()
    for rec in report:
        assert "txn_id" in rec, f"missing txn_id in {rec}"
        assert "account_id" in rec, f"missing account_id in {rec}"
        assert "error_code" in rec, f"missing error_code in {rec}"
        assert "detail" in rec, f"missing detail in {rec}"


def test_error_codes_are_known():
    """Verify only recognised error codes appear in the report."""
    known = {"MISSING_FIELD", "BAD_TXN_ID", "BAD_ACCT_ID", "BAD_DATE",
             "BAD_AMOUNT", "BAD_TYPE", "BAD_CURRENCY", "DUPLICATE_TXN",
             "FEE_OVERCAP", "OVERDRAFT", "HIGH_VELOCITY", "UNMATCHED_REVERSAL"}
    report = load_report()
    for rec in report:
        assert rec["error_code"] in known, f"unknown error code: {rec['error_code']}"


# ── field-format rules ────────────────────────────────────────────────────────

def test_missing_field_flagged():
    """Verify MISSING_FIELD is emitted for the row with only 3 fields."""
    report = load_report()
    assert len(errors_with(report, error_code="MISSING_FIELD", txn_id="T000000030")) == 1


def test_missing_field_count():
    """Verify exactly one MISSING_FIELD error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="MISSING_FIELD")) == 1


def test_bad_txn_id_flagged():
    """Verify BAD_TXN_ID is emitted for T00000031 (only 5 digits after T)."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_TXN_ID", txn_id="T00000031")) == 1


def test_bad_txn_id_count():
    """Verify exactly one BAD_TXN_ID error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_TXN_ID")) == 1


def test_bad_acct_id_flagged():
    """Verify BAD_ACCT_ID is emitted for the record whose account_id is AC0001."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_ACCT_ID", txn_id="T000000032")) == 1


def test_bad_acct_id_count():
    """Verify exactly one BAD_ACCT_ID error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_ACCT_ID")) == 1


def test_bad_date_future_month_flagged():
    """Verify BAD_DATE is emitted for date 20261301 (month 13)."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_DATE", txn_id="T000000033")) == 1


def test_bad_date_zero_month_flagged():
    """Verify BAD_DATE is emitted for date 20260000 (month 0)."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_DATE", txn_id="T000000038")) == 1


def test_bad_date_count():
    """Verify exactly two BAD_DATE errors are produced."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_DATE")) == 2


def test_bad_amount_flagged():
    """Verify BAD_AMOUNT is emitted for amount -10.00 (negative)."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_AMOUNT", txn_id="T000000034")) == 1


def test_bad_amount_count():
    """Verify exactly one BAD_AMOUNT error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_AMOUNT")) == 1


def test_bad_type_flagged():
    """Verify BAD_TYPE is emitted for type WIRE (not in valid set)."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_TYPE", txn_id="T000000035")) == 1


def test_bad_type_count():
    """Verify exactly one BAD_TYPE error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_TYPE")) == 1


def test_bad_currency_flagged():
    """Verify BAD_CURRENCY is emitted for currency CNY (not in valid set)."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_CURRENCY", txn_id="T000000036")) == 1


def test_bad_currency_count():
    """Verify exactly one BAD_CURRENCY error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="BAD_CURRENCY")) == 1


# ── simple business rules ─────────────────────────────────────────────────────

def test_duplicate_txn_flagged():
    """Verify DUPLICATE_TXN is emitted for the second occurrence of T000000001."""
    report = load_report()
    assert len(errors_with(report, error_code="DUPLICATE_TXN", txn_id="T000000001")) == 1


def test_duplicate_txn_count():
    """Verify exactly one DUPLICATE_TXN error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="DUPLICATE_TXN")) == 1


def test_first_txn_occurrence_not_flagged_as_duplicate():
    """Verify exactly one DUPLICATE_TXN (the first occurrence is never flagged)."""
    report = load_report()
    assert len(errors_with(report, error_code="DUPLICATE_TXN")) == 1


def test_fee_overcap_flagged():
    """Verify FEE_OVERCAP is emitted for T000000037 (FEE of 30.00 > 25.00)."""
    report = load_report()
    assert len(errors_with(report, error_code="FEE_OVERCAP", txn_id="T000000037")) == 1


def test_fee_overcap_count():
    """Verify exactly one FEE_OVERCAP error is produced."""
    report = load_report()
    assert len(errors_with(report, error_code="FEE_OVERCAP")) == 1


# ── high velocity and the velocity hold/freeze ────────────────────────────────

def test_high_velocity_ac000003_all_six_flagged():
    """Verify all 6 DEBITs on 20260603 for AC000003 are flagged HIGH_VELOCITY."""
    report = load_report()
    hv = errors_with(report, error_code="HIGH_VELOCITY", account_id="AC000003")
    assert {e["txn_id"] for e in hv} == {
        "T000000021", "T000000022", "T000000023",
        "T000000024", "T000000025", "T000000026"}


def test_high_velocity_ac000006_all_six_flagged():
    """Verify all 6 DEBITs on 20260602 for AC000006 are flagged HIGH_VELOCITY."""
    report = load_report()
    hv = errors_with(report, error_code="HIGH_VELOCITY", account_id="AC000006")
    assert {e["txn_id"] for e in hv} == {
        "T000000051", "T000000052", "T000000053",
        "T000000054", "T000000055", "T000000056"}


def test_high_velocity_count():
    """Verify exactly 12 HIGH_VELOCITY errors are produced (six per velocity account)."""
    report = load_report()
    assert len(errors_with(report, error_code="HIGH_VELOCITY")) == 12


def test_velocity_held_debits_do_not_overdraft():
    """Verify AC000006's held high-velocity debits never post, so there is no OVERDRAFT.

    AC000006 has a 50.00 credit then six 10.00 debits on one day. A naive balance
    that posts every debit would overdraw (50 - 60); because high-velocity debits
    are held, the balance stays at 50.00 and no OVERDRAFT may be reported.
    """
    report = load_report()
    assert errors_with(report, error_code="OVERDRAFT", account_id="AC000006") == []


# ── overdraft and reversal pairing/netting ────────────────────────────────────

def test_overdraft_simple_flagged():
    """Verify OVERDRAFT for T000000011 (AC000002 debits 150 against a 100 balance)."""
    report = load_report()
    assert len(errors_with(report, error_code="OVERDRAFT", txn_id="T000000011")) == 1


def test_overdraft_simple_correct_account():
    """Verify the simple OVERDRAFT is associated with account AC000002."""
    report = load_report()
    assert len(errors_with(report, error_code="OVERDRAFT",
                           account_id="AC000002", txn_id="T000000011")) == 1


def test_overdraft_after_matched_reversal():
    """Verify OVERDRAFT for T000000064 in AC000007 after a reversal restored the balance.

    AC000007: +50 credit, -40 debit, -5 debit, then a 40.00 REVERSAL that cancels the
    40.00 charge (balance back to 45). The following 50.00 debit drives the balance to
    -5, so only that debit (T000000064) is an OVERDRAFT — a solution that ignores the
    reversal's effect on the balance would flag the wrong transactions.
    """
    report = load_report()
    assert len(errors_with(report, error_code="OVERDRAFT",
                           account_id="AC000007", txn_id="T000000064")) == 1
    assert {e["txn_id"] for e in errors_with(report, error_code="OVERDRAFT",
                                             account_id="AC000007")} == {"T000000064"}


def test_overdraft_count():
    """Verify exactly two OVERDRAFT errors are produced."""
    report = load_report()
    assert len(errors_with(report, error_code="OVERDRAFT")) == 2


def test_unmatched_reversal_no_prior_charge():
    """Verify UNMATCHED_REVERSAL for T000000071 (reversal precedes any matching charge).

    In AC000008 the 25.00 REVERSAL on day 2 has no still-open 25.00 charge before it
    (the matching 25.00 debit only arrives on day 3), so it is unmatched.
    """
    report = load_report()
    assert len(errors_with(report, error_code="UNMATCHED_REVERSAL",
                           account_id="AC000008", txn_id="T000000071")) == 1


def test_unmatched_reversal_charge_already_cancelled():
    """Verify UNMATCHED_REVERSAL for T000000083 (its only matching charge was already cancelled).

    In AC000009 a single 20.00 debit is cancelled by the first 20.00 reversal; the
    second 20.00 reversal has nothing left to cancel and is unmatched.
    """
    report = load_report()
    assert len(errors_with(report, error_code="UNMATCHED_REVERSAL",
                           account_id="AC000009", txn_id="T000000083")) == 1


def test_unmatched_reversal_count():
    """Verify exactly two UNMATCHED_REVERSAL errors are produced."""
    report = load_report()
    assert len(errors_with(report, error_code="UNMATCHED_REVERSAL")) == 2


def test_matched_reversals_not_flagged():
    """Verify reversals that DO cancel a prior charge are not flagged UNMATCHED_REVERSAL."""
    report = load_report()
    flagged = {e["txn_id"] for e in errors_with(report, error_code="UNMATCHED_REVERSAL")}
    for matched in ("T000000063", "T000000073", "T000000082"):
        assert matched not in flagged, f"{matched} was matched and must not be flagged"


# ── totals, sorting, and clean accounts ───────────────────────────────────────

def test_total_error_count():
    """Verify the total number of errors is exactly 26."""
    report = load_report()
    assert len(report) == 26, f"expected 26 errors, got {len(report)}"


def test_output_sorted_by_account_id():
    """Verify records are sorted by account_id ascending."""
    report = load_report()
    acct_ids = [e["account_id"] for e in report]
    assert acct_ids == sorted(acct_ids)


def test_output_sorted_by_error_code_within_account():
    """Verify records within the same account are sorted by error_code ascending."""
    report = load_report()
    for acct in {e["account_id"] for e in report}:
        codes = [e["error_code"] for e in report if e["account_id"] == acct]
        assert codes == sorted(codes), f"error_codes not sorted for account {acct}"


def test_output_sorted_by_txn_id_within_error_code():
    """Verify records with the same account_id and error_code are sorted by txn_id."""
    report = load_report()
    seen = {}
    for e in report:
        seen.setdefault((e["account_id"], e["error_code"]), []).append(e["txn_id"])
    for key, ids in seen.items():
        assert ids == sorted(ids), f"txn_ids not sorted for {key}"


def test_clean_account_ac000005_has_no_errors():
    """Verify fully clean account AC000005 does not appear in the report."""
    report = load_report()
    assert errors_with(report, account_id="AC000005") == []


def test_clean_account_ac000001_only_duplicate():
    """Verify AC000001 is flagged only for the duplicate transaction, nothing else."""
    report = load_report()
    codes = {e["error_code"] for e in errors_with(report, account_id="AC000001")}
    assert codes == {"DUPLICATE_TXN"}, f"unexpected codes for AC000001: {codes}"
