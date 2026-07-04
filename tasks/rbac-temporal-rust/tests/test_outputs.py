"""Verifier for the temporal RBAC task.

These checks do not merely trust an exit code: they parse the captured cargo
output to prove that the Rust integration suites actually compiled, ran, and
passed. If cargo never executed (missing log), the crate failed to compile, any
test failed, or an expected test did not run, these assertions fail and the
verifier reward is 0.
"""

import os
import re

CARGO_LOG = "/logs/verifier/cargo_test.log"
REWARD_FILE = "/logs/verifier/reward.txt"

EXPECTED_TESTS = [
    # visible suite (tests/test_rbac.rs)
    "test_basic_grant_and_expiry",
    "test_exact_temporal_boundaries",
    "test_diamond_inheritance_all_paths",
    "test_remove_inheritance_revokes_permission",
    "test_delegation_follows_live_delegator",
    "test_delegation_add_and_revoke_invalidation",
    "test_transitive_grant_updates_delegatee",
    "test_cyclic_delegation_terminates",
    "test_multi_hop_delegation_expiry",
    "test_lru_refreshes_on_read",
    "test_scoped_invalidation_preserves_unrelated",
    "test_public_api_preserved",
    # hidden suite (tests/test_rbac_hidden.rs) — original set
    "test_hidden_grant_delegate_revoke_regrant",
    "test_hidden_diamond_partial_removal",
    "test_hidden_four_hop_delegation_expiry",
    "test_hidden_scoped_invalidation_on_grant",
    "test_hidden_cache_is_bounded_lru",
    "test_hidden_cycle_with_valid_bypass",
    "test_hidden_repeated_query_is_cached",
    "test_hidden_remove_then_readd_inheritance",
    # hidden suite — temporal half-open windows
    "test_hidden_delegation_end_bound_exclusive",
    "test_hidden_delegation_start_bound_inclusive",
    "test_hidden_grant_delegation_window_intersection",
    "test_hidden_zero_width_grant_never_active",
    # hidden suite — multi-parent / diamond inheritance
    "test_hidden_deep_diamond_second_branch",
    "test_hidden_triple_parent_last_branch",
    "test_hidden_inheritance_cycle_safe_permissions",
    "test_hidden_add_inheritance_grants_permission",
    "test_hidden_union_permissions_across_branches",
    # hidden suite — delegation (transitive, live, all-delegators, cyclic)
    "test_hidden_delegatee_borrows_inherited_authority",
    "test_hidden_delegatee_denied_when_delegator_unauthorized",
    "test_hidden_broken_middle_delegation_denies",
    "test_hidden_self_delegation_terminates",
    "test_hidden_long_cycle_terminates",
    "test_hidden_three_node_cycle_with_grant",
    "test_hidden_multiple_delegators_second_authorized",
    # hidden suite — cache (dependency-aware invalidation, LRU, bounded)
    "test_hidden_grant_unrelated_preserves_delegatee_entry",
    "test_hidden_revoke_preserves_other_delegatees_entry",
    "test_hidden_transitive_two_hop_invalidation",
    "test_hidden_hot_entry_survives_many_insertions",
    "test_hidden_capacity_boundary_no_early_eviction",
    "test_hidden_invalidated_entry_recomputed_as_miss",
    # hidden suite — cross-cutting interactions
    "test_hidden_delegated_diamond_inheritance",
    "test_hidden_revoke_then_readd_delegation",
    # hidden suite — difficulty-hardening additions (temporal)
    "test_hidden_delegatee_denied_at_delegator_grant_exact_end",
    "test_hidden_delegation_window_narrower_than_grant",
    "test_hidden_two_grants_with_gap_reactivate",
    "test_hidden_zero_width_delegation_never_active",
    # difficulty-hardening additions (multi-parent inheritance)
    "test_hidden_permission_only_via_second_parent",
    "test_hidden_wide_fanout_permission_on_last_branch",
    "test_hidden_deep_second_branch_grandparent",
    "test_hidden_remove_inheritance_invalidates_all_sharers",
    "test_hidden_add_inheritance_enables_cached_denied_user",
    # difficulty-hardening additions (delegation)
    "test_hidden_delegatee_uses_delegator_inherited_authority",
    "test_hidden_delegation_denied_after_delegator_authority_expires",
    "test_hidden_two_delegators_only_second_authorized",
    "test_hidden_two_node_delegation_cycle_terminates_denied",
    "test_hidden_cycle_with_grant_on_one_member",
    "test_hidden_self_delegation_without_authority_denied",
    # difficulty-hardening additions (cache)
    "test_hidden_grant_to_delegator_invalidates_delegatee_entry",
    "test_hidden_revoke_invalidates_only_target_delegatee",
    "test_hidden_unrelated_grant_preserves_dependent_entry",
    "test_hidden_repeated_query_counts_as_hits",
    "test_hidden_hot_entry_not_evicted_under_churn",
    "test_hidden_cold_entry_evicted_when_capacity_exceeded",
    "test_hidden_deep_delegation_chain_all_hits_after_prime",
]


def _read_log():
    assert os.path.exists(CARGO_LOG), f"{CARGO_LOG} is missing: cargo test never ran"
    with open(CARGO_LOG, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def test_cargo_log_exists_and_nonempty():
    log = _read_log()
    assert log.strip(), "cargo test produced no output"


def test_cargo_compiled_and_ran():
    log = _read_log()
    assert "running" in log, "cargo did not report a running test binary"
    # A compilation failure never reaches a 'test result' line.
    assert "test result:" in log, (
        "no 'test result' line found; the crate likely failed to compile"
    )


def test_no_test_failures():
    log = _read_log()
    assert "test result: FAILED" not in log, "one or more Rust tests FAILED"
    assert "error[" not in log, "the crate failed to compile (rustc error)"


def test_all_expected_tests_executed():
    log = _read_log()
    for name in EXPECTED_TESTS:
        assert name in log, f"expected integration test '{name}' did not run"


def test_expected_pass_count():
    log = _read_log()
    passed = sum(int(n) for n in re.findall(r"test result: ok\. (\d+) passed", log))
    assert passed >= len(EXPECTED_TESTS), (
        f"expected at least {len(EXPECTED_TESTS)} passing tests, saw {passed}"
    )


def test_reward_file_present():
    # test.sh initializes the reward file to 0 before running this suite and
    # sets it to 1 only after this suite passes. The final value of 1 is produced
    # by test.sh gated on the success of these checks, so it cannot be
    # self-asserted here without a circular dependency.
    assert os.path.exists(REWARD_FILE), f"{REWARD_FILE} was not initialized by test.sh"
