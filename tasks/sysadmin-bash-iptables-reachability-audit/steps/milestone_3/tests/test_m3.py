import re

import pytest

from helpers import (
    REPORT_PATH,
    expected_report_header,
    expected_report_rows,
    expected_rule_audit,
    read_report,
)


@pytest.fixture(scope="module")
def actual():
    return read_report()


@pytest.fixture(scope="module")
def expected():
    return expected_report_rows()


class TestMilestone3:
    def test_header(self, actual):
        """The report's first line is the exact 10-column header in the contract order: `rule_id,table_name,chain,position,target,target_type,is_unconditional,is_reachable,blocked_by_rule_id,packet_count`."""
        assert actual[0] == expected_report_header()

    def test_row_count(self, actual, expected):
        """The report has exactly one detail row per rule (22) plus header (1) plus TOTAL (1) = 24 lines. Extra or missing rows indicate report.sh dropped rules or duplicated them."""
        assert len(actual) == len(expected) + 1

    def test_sort_table_chain_position(self, actual):
        """Detail rows are sorted by `(table_name, chain, position)` ascending, so all filter rules group before nat and rules within a chain appear in evaluation order — this is the order the audit results must be presented for the report to be deterministic."""
        detail = actual[1:-1]
        keys = [(r[1], r[2], int(r[3])) for r in detail]
        assert keys == sorted(keys), (
            f"detail rows must be sorted by (table_name, chain, position) ascending: {keys}"
        )

    def test_all_rules_present(self, actual):
        """Every rule_id that appears in rule_audit appears in the report's detail section — report.sh must source from rule_audit (not e.g. only reachable rules) so unreachable rules remain visible."""
        detail = actual[1:-1]
        actual_ids = {r[0] for r in detail}
        expected_ids = set(expected_rule_audit().keys())
        assert actual_ids == expected_ids, (
            f"rule_id set mismatch.\nmissing: {expected_ids - actual_ids}\n"
            f"extra: {actual_ids - expected_ids}"
        )

    def test_rule_ids_are_qualified(self, actual):
        """Every rule_id in the report carries the qualified `<table>.<chain>:<position>` form (contains both `.` and `:`) — the report must NOT strip the table prefix back to e.g. `INPUT:1`, which would collide with any future nat.INPUT."""
        for row in actual[1:-1]:
            rid = row[0]
            assert "." in rid and ":" in rid, (
                f"rule_id {rid!r} should be qualified as <table>.<chain>:<position>"
            )

    def test_total_row_present(self, actual):
        """The final line of the report is a TOTAL row, marked by `TOTAL` in column 1, so consumers can read the aggregate without re-summing the detail rows."""
        assert actual[-1][0] == "TOTAL"

    def test_total_row_empty_string_fields(self, actual):
        """The TOTAL row's non-aggregable columns (`table_name`, `chain`, `position`, `target`, `target_type`, `blocked_by_rule_id`) are the EMPTY string — they must not carry placeholder text like `-` or `N/A` that would break downstream parsers."""
        last = actual[-1]
        for idx in (1, 2, 3, 4, 5, 8):
            assert last[idx] == "", (
                f"TOTAL column {idx} {last[idx]!r} must be empty"
            )

    def test_total_row_aggregate_counts(self, actual, expected):
        """TOTAL columns 7 (`is_unconditional`), 8 (`is_reachable`), and 10 (`packet_count`) are integer sums across all detail rows — matching the oracle's aggregated values."""
        actual_total = actual[-1]
        expected_total = expected[-1]
        for idx in (6, 7, 9):
            assert int(actual_total[idx]) == int(expected_total[idx]), (
                f"TOTAL column {idx}: got {actual_total[idx]} expected {expected_total[idx]}"
            )

    def test_unreachable_rules_have_blocker(self, actual):
        """`is_reachable` and `blocked_by_rule_id` are mutually consistent on every row: unreachable rows MUST name a blocker (non-empty), and reachable rows MUST have an empty `blocked_by_rule_id`."""
        for row in actual[1:-1]:
            rid, is_reachable, blocked_by = row[0], int(row[7]), row[8]
            if is_reachable == 0:
                assert blocked_by != "", f"{rid} unreachable but blocked_by empty"
            else:
                assert blocked_by == "", (
                    f"{rid} reachable but blocked_by={blocked_by!r}"
                )

    def test_detail_row_exact_match(self, actual, expected):
        """Every detail row matches the oracle exactly across all 10 columns — the end-to-end check that the full M1→M2→M3 pipeline reproduces the audit verbatim."""
        actual_detail = {r[0]: r for r in actual[1:-1]}
        expected_detail = {r[0]: r for r in expected[:-1]}
        for rid, exp in expected_detail.items():
            got = actual_detail[rid]
            assert got == exp, f"{rid} row mismatch:\nactual:   {got}\nexpected: {exp}"

    def test_every_row_has_10_columns(self, actual):
        """Every row in the report — header, all detail rows, and TOTAL — splits into exactly 10 columns. A row with the wrong column count means report.sh is emitting malformed CSV (extra commas, missing fields, or a stray newline)."""
        for i, row in enumerate(actual):
            assert len(row) == 10, (
                f"row {i} has {len(row)} columns, expected 10: {row}"
            )

    def test_integer_columns_unquoted_in_raw_file(self):
        """In the raw on-disk CSV, integer columns (`position`, `is_unconditional`, `is_reachable`, `packet_count`) are rendered as plain integers — no quotes, no floats like `5.0`, no scientific notation. A simple `line.split(",")` must yield exactly 10 fields with the integer fields matching `-?\\d+`."""
        raw = REPORT_PATH.read_text().rstrip("\n").splitlines()
        assert raw, "report file is empty"
        for lineno, line in enumerate(raw[1:], start=2):
            fields = line.split(",")
            assert len(fields) == 10, (
                f"line {lineno} has {len(fields)} fields after simple comma split; "
                f"expected 10: {line!r}"
            )
            rule_id = fields[0]
            int_positions = [6, 7, 9] if rule_id == "TOTAL" else [3, 6, 7, 9]
            for idx in int_positions:
                value = fields[idx]
                assert re.fullmatch(r"-?\d+", value), (
                    f"line {lineno} field {idx + 1} = {value!r} is not a plain integer"
                )

    def test_reachable_count(self, actual):
        """The TOTAL `is_reachable` aggregate equals 28 — total 33 rules minus 5 unreachable (filter.INPUT:9, filter.INPUT:10, filter.LOGGING:3, filter.FORWARD:3, filter.WATCHDOG:2). The new ORPHANED and DOUBLY_ORPHANED chains add 3 new rules that ARE reachable within their own chains (ORPHANED:1, ORPHANED:2, DOUBLY_ORPHANED:1), even though the chains themselves are effectively dead at the M2 chain-level audit. Rule-level reachability and chain-level effective deadness are distinct signals."""
        last = actual[-1]
        assert int(last[7]) == 28, (
            f"reachable TOTAL = {last[7]} expected 28 (five unreachable: "
            "filter.INPUT:9, filter.INPUT:10, filter.LOGGING:3, filter.FORWARD:3, filter.WATCHDOG:2)"
        )

    def test_watchdog_override_unreachable_in_report(self, actual):
        """End-to-end check that the LOCAL POLICY OVERRIDE trap surfaces in the report: filter.WATCHDOG:2 appears with `is_reachable == 0` and `blocked_by_rule_id == "filter.WATCHDOG:1"`. An agent that skipped the local-policy override file at M1 leaves WATCHDOG:1 as non_terminal and so leaves WATCHDOG:2 reachable in the report — this row is the diagnostic the report exposes."""
        row = next(
            (r for r in actual[1:-1] if r[0] == "filter.WATCHDOG:2"),
            None,
        )
        assert row is not None, "filter.WATCHDOG:2 row missing from report"
        assert int(row[7]) == 0, (
            f"filter.WATCHDOG:2 is_reachable={row[7]}; expected 0 — WATCHDOG:1 is "
            "classified terminal by local_policy_overrides.tsv (LOG with BLOCK: prefix)"
        )
        assert row[8] == "filter.WATCHDOG:1"

    def test_forward_goto_unreachable_in_report(self, actual):
        """End-to-end check that the GOTO trap surfaces in the report: filter.FORWARD:3 appears with `is_reachable == 0` and `blocked_by_rule_id == "filter.FORWARD:2"`. An agent that treats `-g` as `-j` anywhere in the M1→M2→M3 pipeline ends up with FORWARD:3 marked reachable and empty blocked_by — this row is the diagnostic the report exposes."""
        row = next(
            (r for r in actual[1:-1] if r[0] == "filter.FORWARD:3"),
            None,
        )
        assert row is not None, "filter.FORWARD:3 row missing from report"
        assert int(row[7]) == 0, (
            f"filter.FORWARD:3 is_reachable={row[7]}; expected 0 — the unconditional "
            "GOTO at filter.FORWARD:2 path-blocks subsequent rules in the caller chain"
        )
        assert row[8] == "filter.FORWARD:2", (
            f"filter.FORWARD:3 blocked_by={row[8]!r}; expected 'filter.FORWARD:2'"
        )

    def test_nat_logging_accept_present_and_reachable_in_report(self, actual):
        """End-to-end name-collision check at the report layer: nat.LOGGING:2 appears in the report as REACHABLE with no blocker. If filter.LOGGING and nat.LOGGING were merged on bare chain name anywhere in the M1→M2→M3 pipeline, this row would surface as unreachable with `blocked_by_rule_id=LOGGING:2` or similar."""
        row = next(
            (r for r in actual[1:-1] if r[0] == "nat.LOGGING:2"),
            None,
        )
        assert row is not None, "nat.LOGGING:2 row missing from report"
        assert int(row[7]) == 1, (
            f"nat.LOGGING:2 is_reachable={row[7]} expected 1 — name-collision "
            "with filter.LOGGING must not propagate filter's RETURN-block here"
        )
        assert row[8] == "", "nat.LOGGING:2 blocked_by should be empty"
