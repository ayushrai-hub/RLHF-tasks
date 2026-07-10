import pytest

from helpers import (
    expected_chain_records,
    expected_rule_records,
    read_normalized_records,
)


@pytest.fixture(scope="module")
def actual_records():
    return read_normalized_records()


@pytest.fixture(scope="module")
def actual_by_type(actual_records):
    out = {"chain": [], "rule": []}
    for r in actual_records:
        if r["record_type"] in out:
            out[r["record_type"]].append(r)
    return out


class TestMilestone1:
    def test_chain_records_count(self, actual_by_type):
        """normalize.sh emits exactly one `chain` record per iptables chain across both tables — 10 in filter and 3 in nat for 13 total."""
        assert len(actual_by_type["chain"]) == len(expected_chain_records()), (
            "expected one chain record per chain (10 filter + 3 nat = 13)"
        )

    def test_chain_record_fields(self, actual_by_type):
        """Each chain record carries the structural fields the audit needs downstream: `chain_kind`, `default_policy`, `packet_count`, and `byte_count`, and their values match the oracle exactly for every chain."""
        expected = {(c["table_name"], c["name"]): c for c in expected_chain_records()}
        actual = {(c["table_name"], c["name"]): c for c in actual_by_type["chain"]}
        for key, exp in expected.items():
            got = actual[key]
            for field in ("chain_kind", "default_policy", "packet_count", "byte_count"):
                assert got[field] == exp[field], f"chain {key} {field} mismatch"

    def test_chain_table_name_set(self, actual_by_type):
        """Chain identity is the composite pair `(table_name, name)`: a chain named LOGGING in `filter` and a chain named LOGGING in `nat` must both appear as two distinct records, not be merged on bare name."""
        chains = {(c["table_name"], c["name"]) for c in actual_by_type["chain"]}
        assert ("filter", "INPUT") in chains
        assert ("nat", "PREROUTING") in chains
        assert ("filter", "LOGGING") in chains
        assert ("nat", "LOGGING") in chains

    def test_rule_records_count(self, actual_by_type):
        """normalize.sh emits exactly one `rule` record per iptables rule across both tables — 28 in filter and 5 in nat for 33 total."""
        assert len(actual_by_type["rule"]) == len(expected_rule_records()), (
            "expected one rule record per rule (28 filter + 5 nat = 33 total)"
        )

    def test_local_policy_override_forces_log_terminal(self, actual_by_type):
        """The LOCAL POLICY OVERRIDE trap: `/app/api/contracts/local_policy_overrides.tsv` lists `log_prefix_contains BLOCK: terminal`, which forces any `-j LOG --log-prefix "BLOCK: ..."` rule to be classified as `target_type == "terminal"` even though iptables itself treats LOG as non-terminating. filter.WATCHDOG:1 (`-j LOG --log-prefix "BLOCK: "`) MUST read `target_type == "terminal"`. An agent that classifies purely from `target_classification.tsv` (the iptables default) emits "non_terminal" here — wrong — and that error then cascades through the M2 reachability audit (the next rule WATCHDOG:2 stays "reachable" when it should be unreachable)."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.WATCHDOG:1"]["target_type"] == "terminal", (
            f"filter.WATCHDOG:1 target_type={rules['filter.WATCHDOG:1']['target_type']!r}; "
            "the local_policy_overrides.tsv forces LOG with BLOCK: prefix to terminal, "
            "overriding the default LOG=non_terminal classification"
        )

    def test_target_type_goto_classifies_distinct_from_jump(self, actual_by_type):
        """The GOTO trap: a rule with `jump_kind == "goto"` targeting a user chain in its own table classifies as `target_type == "goto"`, NOT `"jump"`. filter.FORWARD:2 (`-g STATEFUL`) is the dataset's GOTO. An agent that ignores `jump_kind` and treats every chain-target rule as a jump would mis-classify this one — and the M2 reachability audit then wrongly marks the caller's subsequent rules as reachable, because jump (unlike goto) does not path-block the caller."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.FORWARD:2"]["target_type"] == "goto", (
            f"filter.FORWARD:2 target_type={rules['filter.FORWARD:2']['target_type']!r}; "
            "the source rule has jump_kind=goto, which must classify as 'goto' not 'jump'"
        )
        # JUMP rules with the same shape (chain target in own table) must still classify as jump.
        assert rules["filter.INPUT:3"]["target_type"] == "jump"
        assert rules["filter.INPUT:4"]["target_type"] == "jump"
        assert rules["nat.PREROUTING:1"]["target_type"] == "jump"

    def test_rule_id_qualified_with_table(self, actual_by_type):
        """Every `rule_id` is qualified as `<table>.<chain>:<position>` so rules from filter and nat never collide. The unqualified form `INPUT:1` must NOT appear because it would conflate filter.INPUT and any future nat.INPUT rule."""
        rules = {r["rule_id"] for r in actual_by_type["rule"]}
        assert "filter.INPUT:1" in rules, (
            "rule_id must be qualified with table prefix (e.g. 'filter.INPUT:1')"
        )
        assert "filter.LOGGING:3" in rules
        assert "nat.LOGGING:2" in rules
        assert "nat.PREROUTING:1" in rules
        assert "INPUT:1" not in rules

    def test_target_type_terminal(self, actual_by_type):
        """Terminal targets — ACCEPT, DROP, REJECT, DNAT, MASQUERADE — classify as `target_type == "terminal"` per `/app/api/contracts/target_classification.tsv`. Covers both filter (ACCEPT/DROP) and nat (DNAT/MASQUERADE) cases."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.INPUT:1"]["target_type"] == "terminal"
        assert rules["filter.INPUT:8"]["target_type"] == "terminal"
        assert rules["nat.PREROUTING:2"]["target_type"] == "terminal", (
            f"nat.PREROUTING:2 target=DNAT target_type="
            f"{rules['nat.PREROUTING:2']['target_type']!r} expected 'terminal'"
        )
        assert rules["nat.POSTROUTING:1"]["target_type"] == "terminal", (
            "nat.POSTROUTING:1 target=MASQUERADE expected 'terminal'"
        )

    def test_target_type_non_terminal(self, actual_by_type):
        """LOG-family targets (LOG, NFLOG) classify as `non_terminal` so M2 reachability does NOT treat them as path-blocking. A rule that LOGs and falls through must let subsequent rules in the same chain remain reachable."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.INPUT:6"]["target_type"] == "non_terminal"
        assert rules["filter.LOGGING:1"]["target_type"] == "non_terminal"
        assert rules["nat.LOGGING:1"]["target_type"] == "non_terminal"

    def test_target_type_return(self, actual_by_type):
        """RETURN classifies as its own `return` target_type (distinct from terminal and non_terminal) because it blocks subsequent rules WITHIN the user chain but does not affect the caller chain."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.LOGGING:2"]["target_type"] == "return"

    def test_target_type_jump_scoped_per_table(self, actual_by_type):
        """JUMP-target resolution is scoped to the rule's OWN table: a target name matches a user chain only when that user chain exists in the same `table_name`. `nat.PREROUTING:1` jumps to LOGGING because nat has its own LOGGING chain — the existence of filter.LOGGING is irrelevant to nat rules."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.INPUT:3"]["target_type"] == "jump"
        assert rules["filter.INPUT:4"]["target_type"] == "jump"
        assert rules["nat.PREROUTING:1"]["target_type"] == "jump", (
            "nat.PREROUTING:1 target=LOGGING expected jump because nat has "
            "its own LOGGING chain; a target name shared across tables is "
            "still a jump if the chain exists in the rule's own table"
        )

    def test_target_type_unknown(self, actual_by_type):
        """A target name that is neither in `target_classification.tsv` nor a user chain in the rule's own table falls through to `target_type == "unknown"` rather than silently being treated as terminal or jump."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.RATELIMIT:2"]["target_type"] == "unknown"

    def test_matcher_csv_whitespace_trimmed(self, actual_by_type):
        """`matcher_csv` is whitespace-trimmed: leading/trailing spaces are removed and runs of internal whitespace collapse to single spaces so the downstream report doesn't carry visual noise from the raw iptables output."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.RATELIMIT:2"]["matcher_csv"] == "-p udp --dport 5353"

    def test_is_unconditional(self, actual_by_type):
        """`is_unconditional == 1` iff the rule carries NO matchers (empty matcher_csv) — that is the only case where the rule's target fires for every packet. Conditional rules with matchers — even simple `-i lo` — must read 0."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.INPUT:8"]["is_unconditional"] == 1
        assert rules["filter.LOGGING:2"]["is_unconditional"] == 1
        assert rules["filter.INPUT:1"]["is_unconditional"] == 0
        assert rules["nat.LOGGING:2"]["is_unconditional"] == 1
        assert rules["nat.PREROUTING:1"]["is_unconditional"] == 0

    def test_matcher_csv_preserved(self, actual_by_type):
        """The text content of `matcher_csv` preserves every matcher token exactly as iptables wrote it: `-i lo`, `-m state --state ESTABLISHED,RELATED`, and the empty string for unconditional rules."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.INPUT:1"]["matcher_csv"] == "-i lo"
        assert rules["filter.INPUT:2"]["matcher_csv"] == "-m state --state ESTABLISHED,RELATED"
        assert rules["filter.INPUT:8"]["matcher_csv"] == ""

    def test_packet_count_preserved(self, actual_by_type):
        """`packet_count` is carried through normalization as an integer — the per-rule iptables counters survive into the JSONL so M3 can sum them in the report's TOTAL row."""
        rules = {r["rule_id"]: r for r in actual_by_type["rule"]}
        assert rules["filter.INPUT:1"]["packet_count"] == 4210
        assert rules["nat.POSTROUTING:1"]["packet_count"] == 5912
