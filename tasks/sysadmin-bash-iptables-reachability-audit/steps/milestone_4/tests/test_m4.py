import pytest

from helpers import (
    expected_trace_header,
    expected_trace_rows,
    read_trace_report,
)


@pytest.fixture(scope="module")
def actual():
    return read_trace_report()


@pytest.fixture(scope="module")
def expected():
    return expected_trace_rows()


@pytest.fixture(scope="module")
def by_id(actual):
    return {r[0]: r for r in actual[1:-1]}


class TestMilestone4:
    def test_header(self, actual):
        """The first line is the exact 7-column trace header."""
        assert actual[0] == expected_trace_header()

    def test_row_count(self, actual, expected):
        """One detail row per probe packet plus the header and the TOTAL row."""
        assert len(actual) == len(expected) + 1

    def test_sorted_by_probe_id(self, actual):
        """Detail rows are sorted by probe_id ascending."""
        ids = [r[0] for r in actual[1:-1]]
        assert ids == sorted(ids), f"probe rows not sorted: {ids}"

    def test_jump_descends_and_terminal_in_called_chain_wins(self, by_id):
        """t2 (tcp dport 22) jumps from filter.INPUT:3 into RATELIMIT; RATELIMIT:1 carries `-m limit` (always matches) and ACCEPTs — the verdict is decided inside the called chain, and the path records the descent."""
        r = by_id["t2"]
        assert r[3] == "ACCEPT"
        assert r[4] == "filter.RATELIMIT:1"
        assert r[6] == "filter.INPUT:3|filter.RATELIMIT:1"

    def test_return_from_user_chain_resumes_caller(self, by_id):
        """t3 (tcp dport 80) jumps into filter.LOGGING; LOGGING:1 LOGs (non-terminal), LOGGING:2 RETURNs, and control resumes the caller AFTER the jump — the walk continues down INPUT to the unconditional DROP at INPUT:8. A simulator that stops at the RETURN or never returns to the caller gets a different verdict."""
        r = by_id["t3"]
        assert r[3] == "DROP"
        assert r[4] == "filter.INPUT:8"
        assert r[6] == "filter.INPUT:4|filter.LOGGING:1|filter.LOGGING:2|filter.INPUT:8"

    def test_non_terminal_does_not_stop_traversal(self, by_id):
        """t4 (tcp dport 8080) passes the LOG at INPUT:6 (non-terminal) and is decided by the ACCEPT at INPUT:7. A simulator that treats LOG as a verdict stops one rule early."""
        r = by_id["t4"]
        assert r[3] == "ACCEPT"
        assert r[4] == "filter.INPUT:7"

    def test_unconditional_terminal_shadows_later_jump(self, by_id):
        """t5 (tcp dport 9090) is DROPped by the unconditional INPUT:8 before it can reach INPUT:9's jump to ORPHANED — the packet never descends into ORPHANED. A simulator that matches INPUT:9 first (ignoring rule order) reaches a different chain."""
        r = by_id["t5"]
        assert r[3] == "DROP"
        assert r[4] == "filter.INPUT:8"
        assert r[6] == "filter.INPUT:8"

    def test_goto_installs_no_return_frame(self, by_id):
        """t6 is the goto trap. filter.FORWARD:2 GOES TO (`-g`) STATEFUL without a return frame; STATEFUL:2 RETURNs, and because the goto left no return address in FORWARD, control returns past FORWARD entirely to its default policy DROP — filter.FORWARD:3 (which would ACCEPT) is NEVER reached. A simulator that treats goto like jump returns into FORWARD:3 and wrongly ACCEPTs."""
        r = by_id["t6"]
        assert r[3] == "DROP", (
            f"t6 verdict={r[3]!r}; goto must NOT leave a return into FORWARD, "
            "so STATEFUL's RETURN falls through to FORWARD's default policy"
        )
        assert r[4] == "policy:filter.FORWARD"
        assert r[6] == "filter.FORWARD:2|filter.STATEFUL:2"

    def test_override_terminal_stops_traversal(self, by_id):
        """t7 jumps into WATCHDOG; WATCHDOG:1 is a LOG rule the local policy override reclassifies to terminal (BLOCK- prefix), so traversal stops there with verdict LOG and WATCHDOG:2 is never reached. This ties the M1 override into the traversal machine."""
        r = by_id["t7"]
        assert r[3] == "LOG"
        assert r[4] == "filter.WATCHDOG:1"

    def test_fall_off_builtin_applies_default_policy(self, by_id):
        """t8 (tcp dport 443 out eth0) matches no rule in OUTPUT and falls off the end of a built-in chain, so the verdict is OUTPUT's default policy ACCEPT, decided_by is the policy sentinel, and the path is empty with hop_count 0."""
        r = by_id["t8"]
        assert r[3] == "ACCEPT"
        assert r[4] == "policy:filter.OUTPUT"
        assert r[5] == "0"
        assert r[6] == ""

    def test_cross_table_chain_namespacing(self, by_id):
        """t9 traverses the nat table's own LOGGING chain (distinct from filter's LOGGING): nat.LOGGING:2 ACCEPTs. A simulator that merges chain names across tables would apply filter.LOGGING's RETURN here and reach a different verdict."""
        r = by_id["t9"]
        assert r[3] == "ACCEPT"
        assert r[4] == "nat.LOGGING:2"
        assert r[6] == "nat.PREROUTING:1|nat.LOGGING:1|nat.LOGGING:2"

    def test_terminal_dnat(self, by_id):
        """t10 (tcp dport 8080) is decided by the DNAT at nat.PREROUTING:2 — a terminal target other than ACCEPT/DROP."""
        r = by_id["t10"]
        assert r[3] == "DNAT"
        assert r[4] == "nat.PREROUTING:2"

    def test_total_row(self, actual, expected):
        """The final TOTAL row carries the literal string TOTAL in column 1 and the integer sum of hop_count in column 6, with every other column empty."""
        last = actual[-1]
        assert last[0] == "TOTAL"
        assert last[5] == expected[-1][5]
        for idx in (1, 2, 3, 4, 6):
            assert last[idx] == "", f"TOTAL col {idx}={last[idx]!r}; expected empty"

    def test_path_field_quoted_when_needed(self):
        """The path field uses `|` as its separator so it never needs CSV quoting, but decided_by and path must still parse as single columns — every row splits into exactly 7 columns."""
        rows = read_trace_report()
        for i, r in enumerate(rows):
            assert len(r) == 7, f"row {i} has {len(r)} columns; expected 7: {r}"

    def test_traces_match_oracle(self, actual, expected):
        """Every trace row matches the oracle exactly — the integrative end-to-end check that the stack-machine simulation is correct across all probes."""
        a = {r[0]: r for r in actual[1:-1]}
        e = {r[0]: r for r in expected[:-1]}
        assert set(a) == set(e)
        for pid, exp in e.items():
            assert a[pid] == exp, f"{pid} mismatch:\nactual:   {a[pid]}\nexpected: {exp}"
