import sqlite3

import pytest

from helpers import (
    DB_PATH,
    expected_chain_audit,
    expected_chain_graph,
    expected_chain_records,
    expected_rule_audit,
    expected_rule_records,
)


@pytest.fixture(scope="module")
def conn():
    assert DB_PATH.exists(), f"missing {DB_PATH}"
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.fixture(scope="module")
def actual_chains(conn):
    rows = conn.execute("SELECT * FROM chains").fetchall()
    return {(r["table_name"], r["name"]): dict(r) for r in rows}


@pytest.fixture(scope="module")
def actual_rules(conn):
    rows = conn.execute("SELECT * FROM rules").fetchall()
    return {r["rule_id"]: dict(r) for r in rows}


@pytest.fixture(scope="module")
def actual_graph(conn):
    rows = conn.execute(
        "SELECT from_table_name, from_chain, to_table_name, to_chain, via_rule_id FROM chain_graph"
    ).fetchall()
    return {
        (r["from_table_name"], r["from_chain"], r["to_table_name"], r["to_chain"], r["via_rule_id"])
        for r in rows
    }


@pytest.fixture(scope="module")
def actual_audit(conn):
    rows = conn.execute("SELECT * FROM rule_audit").fetchall()
    return {r["rule_id"]: dict(r) for r in rows}


class TestMilestone2:
    def test_chain_row_count(self, actual_chains):
        """The `chains` table persists every chain across both tables — 8 in filter and 3 in nat for 11 rows. A solution that scopes only to the filter table is missing 3 chains."""
        assert len(actual_chains) == 13, (
            "expected 13 chains: 10 in filter + 3 in nat"
        )

    def test_chain_namespace_scoped_by_table(self, actual_chains):
        """filter.LOGGING and nat.LOGGING are DIFFERENT chains and must be persisted as two separate rows keyed on `(table_name, name)`. Their distinct `packet_count` values (480 vs 80) confirm an audit that merges them on bare name would corrupt the counters."""
        assert ("filter", "LOGGING") in actual_chains
        assert ("nat", "LOGGING") in actual_chains
        filt = actual_chains[("filter", "LOGGING")]
        nat = actual_chains[("nat", "LOGGING")]
        assert int(filt["packet_count"]) == 480
        assert int(nat["packet_count"]) == 80

    def test_rule_row_count(self, actual_rules):
        """The `rules` table holds one row per iptables rule across both tables — 30 total — so M3's report can source detail rows directly without re-joining the raw normalize output."""
        assert len(actual_rules) == 33

    def test_audit_row_count(self, actual_audit):
        """`rule_audit` holds exactly one row per rule (33 rows). A solution that only audits filter rules or skips unreachable rules would be missing rows."""
        assert len(actual_audit) == 33, (
            f"rule_audit has {len(actual_audit)} rows; expected one per rule (33)"
        )

    def test_dead_chain_no_inbound_at_all(self, actual_chains):
        """`is_dead_chain` checks for ZERO inbound edges in chain_graph. filter.DEADCHAIN remains dead by this definition. ORPHANED and DOUBLY_ORPHANED both HAVE inbound edges (from INPUT:9 and ORPHANED:1 respectively) so is_dead_chain stays 0 for them — even though they are effectively unreachable. is_dead_chain is the structural-edge check, distinct from is_effectively_dead_chain."""
        assert actual_chains[("filter", "DEADCHAIN")]["is_dead_chain"] == 1
        assert actual_chains[("filter", "ORPHANED")]["is_dead_chain"] == 0, (
            "ORPHANED has an inbound edge from INPUT:9 (regardless of whether "
            "INPUT:9 is reachable), so is_dead_chain stays 0"
        )
        assert actual_chains[("filter", "DOUBLY_ORPHANED")]["is_dead_chain"] == 0

    def test_effectively_dead_chain_unreachable_inbound(self, actual_chains):
        """`is_effectively_dead_chain` is the FIXPOINT computation: a user chain is effectively dead iff every inbound chain_graph edge is either (a) via a rule that is itself unreachable, or (b) from a chain that is itself effectively dead. ORPHANED's only inbound is from filter.INPUT:9, which is unreachable (blocked by INPUT:8's unconditional DROP). So ORPHANED is effectively dead even though structurally it has an inbound edge. An agent that only checks inbound-edge COUNT (ignoring whether the via_rule is reachable) emits 0 here — wrong."""
        row = actual_chains[("filter", "ORPHANED")]
        assert row["is_effectively_dead_chain"] == 1, (
            f"ORPHANED is_effectively_dead_chain={row['is_effectively_dead_chain']}; "
            "expected 1 — its only inbound edge (INPUT:9) is from an unreachable rule"
        )

    def test_effectively_dead_chain_transitive_fixpoint(self, actual_chains):
        """The transitive case: DOUBLY_ORPHANED's only inbound edge is from ORPHANED:1. ORPHANED:1 IS reachable WITHIN ORPHANED (ORPHANED has no prior blockers), BUT ORPHANED itself is effectively dead — so its rules never fire in practice. The fixpoint says: an edge from an effectively-dead chain does NOT count as live inbound. So DOUBLY_ORPHANED is ALSO effectively dead. An agent that implements this as a single-pass query (no iteration) gets DOUBLY_ORPHANED = 0 because ORPHANED:1 looks reachable at first glance; only the fixpoint catches the transitive case."""
        row = actual_chains[("filter", "DOUBLY_ORPHANED")]
        assert row["is_effectively_dead_chain"] == 1, (
            f"DOUBLY_ORPHANED is_effectively_dead_chain={row['is_effectively_dead_chain']}; "
            "expected 1 — its only inbound is from ORPHANED which is itself effectively dead"
        )

    def test_effectively_dead_chain_zero_for_live_chains(self, actual_chains):
        """User chains that are reached via at least one reachable rule from a live chain remain `is_effectively_dead_chain = 0`. filter.LOGGING is reached from filter.INPUT:4 (reachable). filter.RATELIMIT from INPUT:3 (reachable). filter.STATEFUL from FORWARD:2 (reachable, via goto). filter.WATCHDOG from OUTPUT:1 (reachable). nat.LOGGING from nat.PREROUTING:1 (reachable). All of these stay at 0."""
        for key in (
            ("filter", "LOGGING"),
            ("filter", "RATELIMIT"),
            ("filter", "STATEFUL"),
            ("filter", "WATCHDOG"),
            ("nat", "LOGGING"),
        ):
            assert actual_chains[key]["is_effectively_dead_chain"] == 0, (
                f"{key} unexpectedly marked effectively dead"
            )

    def test_effectively_dead_chain_one_for_structurally_dead(self, actual_chains):
        """A chain that's structurally dead (no inbound edges at all) is also effectively dead by definition — the two flags both go 1 for filter.DEADCHAIN."""
        row = actual_chains[("filter", "DEADCHAIN")]
        assert row["is_dead_chain"] == 1
        assert row["is_effectively_dead_chain"] == 1

    def test_builtin_chains_never_effectively_dead(self, actual_chains):
        """Builtin chains (INPUT, FORWARD, OUTPUT, PREROUTING, POSTROUTING) are never effectively dead — they are entry points from kernel hooks, not reached via JUMP/GOTO edges."""
        for key in (
            ("filter", "INPUT"),
            ("filter", "FORWARD"),
            ("filter", "OUTPUT"),
            ("nat", "PREROUTING"),
            ("nat", "POSTROUTING"),
        ):
            assert actual_chains[key]["is_effectively_dead_chain"] == 0

    def test_local_policy_override_blocks_subsequent(self, actual_audit):
        """The reachability surface of the local-policy override trap: filter.WATCHDOG:1 (`-j LOG --log-prefix "BLOCK: "`) is classified terminal by the override and is unconditional, so it blocks filter.WATCHDOG:2 (`-j ACCEPT`) which is then unreachable. An agent that ignores the local-policy override leaves WATCHDOG:1 as non_terminal — WATCHDOG:2 stays reachable in their audit (wrong)."""
        row = actual_audit["filter.WATCHDOG:2"]
        assert row["is_reachable"] == 0, (
            f"filter.WATCHDOG:2 is_reachable={row['is_reachable']}; expected 0 — "
            "WATCHDOG:1 is forced to terminal by local_policy_overrides.tsv "
            "(LOG with BLOCK: prefix), making WATCHDOG:2 unreachable"
        )
        assert row["blocked_by_rule_id"] == "filter.WATCHDOG:1"

    def test_chain_graph_matches_expected(self, actual_graph):
        """`chain_graph` matches the oracle edge set exactly: every JUMP edge appears with its `(from_table_name, from_chain, to_table_name, to_chain, via_rule_id)` tuple, with no missing or extra edges."""
        expected = set(expected_chain_graph())
        missing = expected - actual_graph
        extra = actual_graph - expected
        assert not missing and not extra, (
            f"chain_graph mismatch.\nmissing: {sorted(missing)}\nextra: {sorted(extra)}"
        )

    def test_chain_graph_scoped_per_table(self, actual_graph):
        """JUMP-edge resolution is scoped to the rule's own table: nat.PREROUTING:1's JUMP to LOGGING produces a `nat → nat.LOGGING` edge (not a cross-table edge to filter.LOGGING). Every edge in chain_graph must satisfy `from_table_name == to_table_name`."""
        assert ("nat", "PREROUTING", "nat", "LOGGING", "nat.PREROUTING:1") in actual_graph
        cross_table = {
            (f_tn, f_ch, t_tn, t_ch, via)
            for (f_tn, f_ch, t_tn, t_ch, via) in actual_graph
            if f_tn != t_tn
        }
        assert not cross_table, (
            f"chain_graph contains cross-table edges {cross_table} — JUMP "
            "targets resolve only within the rule's own table"
        )

    def test_input_unconditional_drop_blocks_subsequent(self, actual_audit):
        """Within a chain, an unconditional terminal blocks every subsequent rule. filter.INPUT:8 is unconditional DROP, so filter.INPUT:9 and :10 are unreachable and both record filter.INPUT:8 as their earliest blocker."""
        for rid in ("filter.INPUT:9", "filter.INPUT:10"):
            row = actual_audit[rid]
            assert row["is_reachable"] == 0
            assert row["blocked_by_rule_id"] == "filter.INPUT:8"

    def test_filter_logging_return_blocks_subsequent(self, actual_audit):
        """RETURN behaves as a path-blocker WITHIN its own user chain: filter.LOGGING:2 (unconditional RETURN) blocks filter.LOGGING:3, which records filter.LOGGING:2 as its blocker."""
        row = actual_audit["filter.LOGGING:3"]
        assert row["is_reachable"] == 0, (
            "filter.LOGGING:3 is_reachable=1 — but filter.LOGGING:2 is an "
            "unconditional RETURN that blocks subsequent rules in the chain"
        )
        assert row["blocked_by_rule_id"] == "filter.LOGGING:2"

    def test_nat_logging_accept_is_reachable(self, actual_audit):
        """The trap for unqualified-chain-name audits: nat.LOGGING:2 (unconditional ACCEPT, position 2) is REACHABLE because nat.LOGGING has no prior unconditional blocker. An audit that merges filter.LOGGING and nat.LOGGING into one namespace would wrongly apply filter.LOGGING:2's RETURN here and mark nat.LOGGING:2 unreachable."""
        row = actual_audit["nat.LOGGING:2"]
        assert row["is_reachable"] == 1, (
            f"nat.LOGGING:2 is_reachable={row['is_reachable']} — but this "
            "chain has no prior unconditional blocker. An audit that merges "
            "filter.LOGGING and nat.LOGGING into one namespace would "
            "wrongly apply filter.LOGGING:2's RETURN here."
        )
        assert row["blocked_by_rule_id"] == "", (
            f"nat.LOGGING:2 blocked_by={row['blocked_by_rule_id']!r}; expected empty"
        )

    def test_jump_to_returning_chain_does_not_block_caller(self, actual_audit):
        """A JUMP from the caller chain into a user chain that RETURNs does NOT propagate the block back to the caller. filter.INPUT:4 jumps to filter.LOGGING (which RETURNs at :2), so filter.INPUT:5/:6/:7 in the CALLER remain reachable."""
        for rid in ("filter.INPUT:5", "filter.INPUT:6", "filter.INPUT:7"):
            assert actual_audit[rid]["is_reachable"] == 1, (
                f"{rid} marked unreachable — JUMP to a returning chain must "
                "not propagate the blocking signal to the caller"
            )

    def test_log_is_non_terminal(self, actual_audit):
        """LOG-family `non_terminal` targets do NOT block subsequent rules in the same chain. filter.INPUT:6 is an unconditional LOG, but filter.INPUT:7 remains reachable because LOG falls through."""
        assert actual_audit["filter.INPUT:7"]["is_reachable"] == 1, (
            "filter.INPUT:7 unreachable but filter.INPUT:6 LOG is non-terminating"
        )

    def test_effective_default_policy_preempted(self, actual_chains):
        """A builtin chain whose body contains at least one unconditional terminal reads `effective_default_policy == "preempted"` — the declared default policy never fires because an in-chain rule always matches first. filter.INPUT (declared DROP) is preempted by filter.INPUT:8's unconditional DROP."""
        c = actual_chains[("filter", "INPUT")]
        assert c["effective_default_policy"] == "preempted"

    def test_effective_default_policy_active_when_no_terminal(self, actual_chains):
        """Builtin chains with NO unconditional terminal AND no unconditional goto in their body keep their declared default policy. filter.OUTPUT and both nat builtins are empty, so they read their declared default."""
        assert actual_chains[("filter", "OUTPUT")]["effective_default_policy"] == "ACCEPT"
        assert actual_chains[("nat", "PREROUTING")]["effective_default_policy"] == "ACCEPT"
        assert actual_chains[("nat", "POSTROUTING")]["effective_default_policy"] == "ACCEPT"

    def test_forward_preempted_by_unconditional_goto(self, actual_chains):
        """The GOTO trap surfaces in chain-level audit: filter.FORWARD declares default DROP, but it contains an unconditional `-g STATEFUL` at position 2. Like an unconditional terminal, an unconditional GOTO preempts the chain's declared default policy (the declared default never fires because the GOTO always preempts it for matched packets, and goto's RETURN goes to the grandparent — never back to FORWARD to let the default policy fire). filter.FORWARD must read `effective_default_policy == "preempted"`. An agent that only treats `target_type == "terminal"` as preempting would emit `"DROP"` here — wrong."""
        assert actual_chains[("filter", "FORWARD")]["effective_default_policy"] == "preempted", (
            f"filter.FORWARD effective={actual_chains[('filter','FORWARD')]['effective_default_policy']!r}; "
            "expected 'preempted' because the unconditional `-g STATEFUL` at FORWARD:2 transfers "
            "control out of FORWARD permanently (goto's return goes to grandparent, not FORWARD)"
        )

    def test_user_chain_effective_default_is_return(self, actual_chains):
        """User-defined chains always read `effective_default_policy == "return"` because they have no declared default policy — falling off the end of a user chain implicitly returns to the caller (or grandparent if entered via goto), regardless of whether the chain has rules."""
        for key in (
            ("filter", "LOGGING"),
            ("filter", "RATELIMIT"),
            ("filter", "DEADCHAIN"),
            ("filter", "STATEFUL"),
            ("nat", "LOGGING"),
        ):
            assert actual_chains[key]["effective_default_policy"] == "return"

    def test_goto_blocks_subsequent_rules_in_caller(self, actual_audit):
        """The reachability twin of the GOTO trap: filter.FORWARD:2 is an unconditional `-g STATEFUL`. Unlike a JUMP (which is non-blocking — caller resumes after the user chain RETURNs), a GOTO transfers control such that the caller's subsequent rules are unreachable. filter.FORWARD:3 must read `is_reachable == 0` blocked by filter.FORWARD:2. An agent that classifies `-g` as `-j` keeps FORWARD:3 reachable — exactly wrong."""
        row = actual_audit["filter.FORWARD:3"]
        assert row["is_reachable"] == 0, (
            f"filter.FORWARD:3 is_reachable={row['is_reachable']} — but FORWARD:2 is an "
            "unconditional GOTO that transfers control permanently out of FORWARD"
        )
        assert row["blocked_by_rule_id"] == "filter.FORWARD:2"

    def test_goto_target_chain_return_does_not_unblock_caller(self, actual_audit):
        """The compounding subtlety: filter.STATEFUL (the GOTO target) contains an unconditional RETURN at STATEFUL:2. Tempting interpretation: "the GOTO target returns immediately, so the caller resumes" — but THIS IS WRONG. Sudo... err, iptables GOTO semantics: a RETURN from a chain entered via `-g` returns to the GRANDPARENT (here, the kernel hook for builtin FORWARD), NOT to the caller. So FORWARD:3 stays unreachable even though STATEFUL has an early RETURN. An agent that treats GOTO-with-returning-target like JUMP-with-returning-target would emit FORWARD:3 reachable — wrong."""
        assert actual_audit["filter.FORWARD:3"]["is_reachable"] == 0
        # And STATEFUL's own rules ARE reachable — STATEFUL:1 then STATEFUL:2.
        assert actual_audit["filter.STATEFUL:1"]["is_reachable"] == 1
        assert actual_audit["filter.STATEFUL:2"]["is_reachable"] == 1

    def test_dead_chain_flagged(self, actual_chains):
        """A user chain with NO inbound JUMP edge in chain_graph is `is_dead_chain == 1` — it is reachable from no builtin chain, so none of its rules ever run. filter.DEADCHAIN is the dataset's example."""
        assert actual_chains[("filter", "DEADCHAIN")]["is_dead_chain"] == 1

    def test_nat_logging_not_dead(self, actual_chains):
        """Dead-chain detection is scoped per `(table_name, name)`: nat.LOGGING has an inbound JUMP from nat.PREROUTING:1, so it is NOT dead. An audit that matches on bare chain name might wrongly count filter.INPUT:4's jump to filter.LOGGING as coverage for nat.LOGGING."""
        assert actual_chains[("nat", "LOGGING")]["is_dead_chain"] == 0, (
            "nat.LOGGING is_dead_chain=1 — nat.PREROUTING JUMPs to it"
        )

    def test_live_user_chain_not_flagged_dead(self, actual_chains):
        """User chains with at least one inbound JUMP or GOTO edge in their own table — filter.LOGGING, filter.RATELIMIT, filter.STATEFUL, and filter.WATCHDOG — must NOT be flagged as dead. STATEFUL is reached ONLY via a GOTO edge (filter.FORWARD:2); WATCHDOG is reached via a JUMP from filter.OUTPUT:1."""
        for key in (("filter", "LOGGING"), ("filter", "RATELIMIT"), ("filter", "STATEFUL"), ("filter", "WATCHDOG")):
            assert actual_chains[key]["is_dead_chain"] == 0, (
                f"{key} is_dead_chain=1; expected 0 — chain has an inbound JUMP or GOTO edge"
            )

    def test_builtin_chains_never_dead(self, actual_chains):
        """Builtin chains are never dead — packets enter them from the kernel hook, not from JUMP/GOTO edges. INPUT, FORWARD, OUTPUT, PREROUTING, and POSTROUTING all read `is_dead_chain == 0` regardless of chain_graph contents."""
        for key in (
            ("filter", "INPUT"),
            ("filter", "FORWARD"),
            ("filter", "OUTPUT"),
            ("nat", "PREROUTING"),
            ("nat", "POSTROUTING"),
        ):
            assert actual_chains[key]["is_dead_chain"] == 0

    def test_first_rule_in_chain_always_reachable(self, actual_audit, actual_rules):
        """The position-1 rule of every populated chain is reachable by construction — there is no prior rule that could block it. Sanity-checks the audit hasn't accidentally marked all rules unreachable."""
        for (tn, ch) in (
            ("filter", "INPUT"), ("filter", "FORWARD"), ("filter", "OUTPUT"),
            ("filter", "LOGGING"), ("filter", "RATELIMIT"), ("filter", "DEADCHAIN"),
            ("filter", "STATEFUL"), ("filter", "WATCHDOG"),
            ("nat", "PREROUTING"), ("nat", "POSTROUTING"), ("nat", "LOGGING"),
        ):
            rule = next(
                (r for r in actual_rules.values()
                 if r["table_name"] == tn and r["chain"] == ch and r["position"] == 1),
                None,
            )
            if rule is None:
                continue
            assert actual_audit[rule["rule_id"]]["is_reachable"] == 1

    def test_audit_matches_oracle(self, actual_audit):
        """The full `is_reachable` + `blocked_by_rule_id` audit matches the oracle for every one of the 33 rules — this is the integrative end-to-end check that the per-chain reachability algorithm is correct."""
        expected = expected_rule_audit()
        for rid, exp in expected.items():
            got = actual_audit[rid]
            assert int(got["is_reachable"]) == int(exp["is_reachable"]), (
                f"{rid} is_reachable: got {got['is_reachable']} expected {exp['is_reachable']}"
            )
            assert got["blocked_by_rule_id"] == exp["blocked_by_rule_id"], (
                f"{rid} blocked_by: got {got['blocked_by_rule_id']!r} expected {exp['blocked_by_rule_id']!r}"
            )

    def test_rules_table_columns_match_oracle(self, actual_rules):
        """Every persisted `rules` row carries the full normalize payload (`table_name`, `chain`, `position`, `target`, `target_args`, `target_type`, `matcher_csv`, `is_unconditional`, `packet_count`, `byte_count`) and matches the oracle for every rule. Confirms persist.sh doesn't drop or rewrite any field on the way into the DB."""
        expected = {r["rule_id"]: r for r in expected_rule_records()}
        for rid, exp in expected.items():
            got = actual_rules[rid]
            assert got["table_name"] == exp["table_name"], f"{rid} table_name"
            assert got["chain"] == exp["chain"], f"{rid} chain"
            assert int(got["position"]) == int(exp["position"]), f"{rid} position"
            assert got["target"] == exp["target"], f"{rid} target"
            assert got["target_args"] == exp["target_args"], (
                f"{rid} target_args: got {got['target_args']!r} expected {exp['target_args']!r}"
            )
            assert got["target_type"] == exp["target_type"], (
                f"{rid} target_type: got {got['target_type']!r} expected {exp['target_type']!r}"
            )
            assert got["matcher_csv"] == exp["matcher_csv"], f"{rid} matcher_csv"
            assert int(got["is_unconditional"]) == int(exp["is_unconditional"])
            assert int(got["packet_count"]) == int(exp["packet_count"])
            assert int(got["byte_count"]) == int(exp["byte_count"])

    def test_chains_table_columns_match_oracle(self, actual_chains):
        """Every persisted `chains` row carries `chain_kind`, `default_policy`, `packet_count`, and `byte_count` matching the oracle. Confirms persist.sh doesn't lose or mutate chain-level metadata between normalize and DB."""
        expected = {(c["table_name"], c["name"]): c for c in expected_chain_records()}
        for key, exp in expected.items():
            got = actual_chains[key]
            assert got["chain_kind"] == exp["chain_kind"]
            assert got["default_policy"] == exp["default_policy"]
            assert int(got["packet_count"]) == int(exp["packet_count"])
            assert int(got["byte_count"]) == int(exp["byte_count"])

    def test_matcher_csv_whitespace_trimmed(self, actual_rules):
        """The whitespace-trimmed `matcher_csv` from M1 normalize survives persist.sh into the DB intact — filter.RATELIMIT:2 reads `-p udp --dport 5353` with no leading/trailing or doubled whitespace."""
        row = actual_rules["filter.RATELIMIT:2"]
        assert row["matcher_csv"] == "-p udp --dport 5353"

    def test_unknown_target_classified(self, actual_rules):
        """The `target_type == "unknown"` classification for unrecognized targets survives M1→M2 into the rules table — persist.sh must not silently rewrite WEIRDTARGET to terminal/jump/non_terminal."""
        row = actual_rules["filter.RATELIMIT:2"]
        assert row["target_type"] == "unknown"

    def test_chain_audit_matches_oracle(self, actual_chains):
        """Per-chain audit columns (`effective_default_policy`, `is_dead_chain`) on every chain match the oracle exactly — integrative check that policy-preemption and dead-chain detection both work for the full 9-chain set."""
        expected = expected_chain_audit()
        for key, exp in expected.items():
            got = actual_chains[key]
            assert got["effective_default_policy"] == exp["effective_default_policy"], (
                f"{key} effective_default_policy mismatch"
            )
            assert int(got["is_dead_chain"]) == int(exp["is_dead_chain"]), (
                f"{key} is_dead_chain mismatch"
            )
