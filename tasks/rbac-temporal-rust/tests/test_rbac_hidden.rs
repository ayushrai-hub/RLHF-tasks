use rbac_temporal::cache::EvaluationCache;
use rbac_temporal::delegation::DelegationManager;
use rbac_temporal::evaluator::Evaluator;
use rbac_temporal::grants::GrantManager;
use rbac_temporal::graph::RoleGraph;
use rbac_temporal::types_def::{Delegation, Permission, Role, TemporalGrant};
use std::cell::RefCell;
use std::collections::HashSet;
use std::rc::Rc;

fn setup_rbac() -> Evaluator {
    let cache = Rc::new(EvaluationCache::new());
    let graph = Rc::new(RefCell::new(RoleGraph::new(cache.clone())));
    let grants = Rc::new(RefCell::new(GrantManager::new(cache.clone())));
    let delegations = Rc::new(RefCell::new(DelegationManager::new(cache.clone())));
    Evaluator::new(cache, graph, grants, delegations)
}

fn role_with(name: &str, perm: &Permission) -> Role {
    let mut perms = HashSet::new();
    perms.insert(perm.clone());
    Role::new(name, perms)
}

#[test]
fn test_hidden_grant_delegate_revoke_regrant() {
    let ev = setup_rbac();
    let perm = Permission::new("vault", "open");
    ev.graph
        .borrow_mut()
        .add_role(role_with("vault_ops", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "vault_ops", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(ev.has_permission("u2", &perm, 10.0));
    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");
    assert!(!ev.has_permission("u2", &perm, 10.0));

    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u2", "vault_ops", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
}

#[test]
fn test_hidden_diamond_partial_removal() {
    let ev = setup_rbac();
    let perm = Permission::new("archive", "read");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("mid1", HashSet::new()));
        g.add_role(Role::new("mid2", HashSet::new()));
        g.add_role(Role::new("top", HashSet::new()));
        g.add_inheritance("top", "mid1");
        g.add_inheritance("top", "mid2");
        g.add_inheritance("mid1", "base");
        g.add_inheritance("mid2", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));

    assert!(ev.has_permission("u1", &perm, 5.0));
    ev.graph.borrow_mut().remove_inheritance("mid1", "base");
    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "permission still reachable through the other diamond arm"
    );
    ev.graph.borrow_mut().remove_inheritance("mid2", "base");
    assert!(
        !ev.has_permission("u1", &perm, 5.0),
        "permission unreachable after both arms are removed"
    );
}

#[test]
fn test_hidden_four_hop_delegation_expiry() {
    let ev = setup_rbac();
    let perm = Permission::new("ops", "run");
    ev.graph.borrow_mut().add_role(role_with("runner", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "runner", 0.0, 30.0));
    for (from, to) in [("u1", "u2"), ("u2", "u3"), ("u3", "u4")] {
        ev.delegations
            .borrow_mut()
            .add_delegation(Delegation::new(from, to, 0.0, 100.0));
    }

    assert!(ev.has_permission("u4", &perm, 29.0));
    assert!(!ev.has_permission("u4", &perm, 30.0));
}

#[test]
fn test_hidden_scoped_invalidation_on_grant() {
    let ev = setup_rbac();
    let p = Permission::new("doc", "read");
    let q = Permission::new("img", "view");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("reader", &p));
        g.add_role(role_with("viewer", &q));
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "reader", 0.0, 100.0));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("zz", "viewer", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(ev.has_permission("zz", &q, 10.0));
    assert!(ev.has_permission("u2", &p, 10.0));

    let (_, misses_before) = ev.cache.stats();
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "reader", 50.0, 150.0));

    assert!(ev.has_permission("zz", &q, 10.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after, misses_before,
        "granting one principal must not evict unrelated cache entries"
    );
    assert!(ev.has_permission("u2", &p, 10.0));
}

#[test]
fn test_hidden_cache_is_bounded_lru() {
    let ev = setup_rbac();
    let perm = Permission::new("x", "y");
    let _ = ev.has_permission("cold0", &perm, 1.0);
    for i in 1..=8 {
        let _ = ev.has_permission(&format!("cold{i}"), &perm, 1.0);
    }
    let (_, misses_before) = ev.cache.stats();
    let _ = ev.has_permission("cold0", &perm, 1.0);
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after,
        misses_before + 1,
        "a bounded cache must evict the least-recently-used entry"
    );
}

#[test]
fn test_hidden_cycle_with_valid_bypass() {
    let ev = setup_rbac();
    let perm = Permission::new("gateway", "cross");
    ev.graph.borrow_mut().add_role(role_with("keeper", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "keeper", 0.0, 100.0));
    // Cyclic delegation between u1 and u2, but u1 holds a real grant.
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u2", "u1", 0.0, 100.0));

    assert!(ev.has_permission("u1", &perm, 10.0));
    assert!(
        ev.has_permission("u2", &perm, 10.0),
        "a cycle must not hide a genuinely reachable grant"
    );
}

#[test]
fn test_hidden_repeated_query_is_cached() {
    let ev = setup_rbac();
    let perm = Permission::new("token", "use");
    ev.graph.borrow_mut().add_role(role_with("issuer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "issuer", 0.0, 100.0));

    assert!(ev.has_permission("u1", &perm, 10.0));
    let (hits_before, _) = ev.cache.stats();
    assert!(ev.has_permission("u1", &perm, 10.0));
    let (hits_after, _) = ev.cache.stats();
    assert_eq!(
        hits_after,
        hits_before + 1,
        "a repeated identical query must be served from the cache"
    );
}

#[test]
fn test_hidden_remove_then_readd_inheritance() {
    let ev = setup_rbac();
    let perm = Permission::new("storage", "write");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("mid", HashSet::new()));
        g.add_role(Role::new("top", HashSet::new()));
        g.add_inheritance("top", "mid");
        g.add_inheritance("mid", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));

    assert!(ev.has_permission("u1", &perm, 5.0));
    ev.graph.borrow_mut().remove_inheritance("mid", "base");
    assert!(!ev.has_permission("u1", &perm, 5.0));
    ev.graph.borrow_mut().add_inheritance("mid", "base");
    assert!(ev.has_permission("u1", &perm, 5.0));
}

// --------------------------------------------------------------------------
// Temporal half-open windows (the two endpoints of a window differ).
// --------------------------------------------------------------------------

#[test]
fn test_hidden_delegation_end_bound_exclusive() {
    let ev = setup_rbac();
    let perm = Permission::new("ledger", "post");
    ev.graph.borrow_mut().add_role(role_with("poster", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "poster", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 10.0));

    assert!(
        ev.has_permission("u2", &perm, 9.999),
        "just before the delegation end is still borrowed authority"
    );
    assert!(
        !ev.has_permission("u2", &perm, 10.0),
        "the delegation end bound is exclusive even while the delegator is still granted"
    );
}

#[test]
fn test_hidden_delegation_start_bound_inclusive() {
    let ev = setup_rbac();
    let perm = Permission::new("ledger", "read");
    ev.graph.borrow_mut().add_role(role_with("reader", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "reader", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 5.0, 20.0));

    assert!(
        !ev.has_permission("u2", &perm, 4.999),
        "before the delegation start there is no borrowed authority"
    );
    assert!(
        ev.has_permission("u2", &perm, 5.0),
        "the delegation start bound is inclusive"
    );
}

#[test]
fn test_hidden_grant_delegation_window_intersection() {
    // The delegatee is authorized only where the grant window and the delegation
    // window overlap: grant [0,10), delegation [5,20) => live only on [5,10).
    let ev = setup_rbac();
    let perm = Permission::new("safe", "unlock");
    ev.graph
        .borrow_mut()
        .add_role(role_with("keyholder", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "keyholder", 0.0, 10.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 5.0, 20.0));

    assert!(
        !ev.has_permission("u2", &perm, 4.999),
        "delegation not open yet"
    );
    assert!(ev.has_permission("u2", &perm, 5.0), "both windows open");
    assert!(
        ev.has_permission("u2", &perm, 9.999),
        "still inside both windows"
    );
    assert!(
        !ev.has_permission("u2", &perm, 10.0),
        "grant closed, so no live authority to borrow"
    );
}

#[test]
fn test_hidden_zero_width_grant_never_active() {
    let ev = setup_rbac();
    let perm = Permission::new("void", "touch");
    ev.graph
        .borrow_mut()
        .add_role(role_with("ephemeral", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "ephemeral", 5.0, 5.0));

    assert!(
        !ev.has_permission("u1", &perm, 5.0),
        "a zero-width window is empty under half-open semantics"
    );
}

// --------------------------------------------------------------------------
// Multi-parent / diamond inheritance (all lines of ancestry are followed).
// --------------------------------------------------------------------------

#[test]
fn test_hidden_deep_diamond_second_branch() {
    // The permission sits three hops down the *second* branch of `top`.
    let ev = setup_rbac();
    let perm = Permission::new("mesh", "route");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(Role::new("top", HashSet::new()));
        g.add_role(Role::new("a1", HashSet::new()));
        g.add_role(Role::new("a2", HashSet::new()));
        g.add_role(Role::new("b1", HashSet::new()));
        g.add_role(role_with("base", &perm));
        g.add_inheritance("top", "a1");
        g.add_inheritance("top", "a2");
        g.add_inheritance("a1", "b1");
        g.add_inheritance("a2", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));

    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "a deep permission on the second branch must be reachable"
    );
}

#[test]
fn test_hidden_triple_parent_last_branch() {
    let ev = setup_rbac();
    let perm = Permission::new("fabric", "weave");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(Role::new("top", HashSet::new()));
        g.add_role(Role::new("p1", HashSet::new()));
        g.add_role(Role::new("p2", HashSet::new()));
        g.add_role(role_with("p3", &perm));
        g.add_inheritance("top", "p1");
        g.add_inheritance("top", "p2");
        g.add_inheritance("top", "p3");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));

    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "the third of three parents must still be traversed"
    );
}

#[test]
fn test_hidden_inheritance_cycle_safe_permissions() {
    // A cycle in the inheritance graph must terminate and still collect perms.
    let ev = setup_rbac();
    let perm = Permission::new("loop", "hold");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(Role::new("a", HashSet::new()));
        g.add_role(role_with("b", &perm));
        g.add_inheritance("a", "b");
        g.add_inheritance("b", "a");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "a", 0.0, 100.0));

    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "cyclic inheritance must not lose the reachable permission or loop forever"
    );
}

#[test]
fn test_hidden_add_inheritance_grants_permission() {
    let ev = setup_rbac();
    let perm = Permission::new("bay", "dock");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("top", HashSet::new()));
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));

    assert!(!ev.has_permission("u1", &perm, 5.0), "no link yet");
    ev.graph.borrow_mut().add_inheritance("top", "base");
    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "adding a link must refresh the decision"
    );
}

#[test]
fn test_hidden_union_permissions_across_branches() {
    let ev = setup_rbac();
    let pa = Permission::new("wing", "left");
    let pb = Permission::new("wing", "right");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("ra", &pa));
        g.add_role(role_with("rb", &pb));
        g.add_role(Role::new("top", HashSet::new()));
        g.add_inheritance("top", "ra");
        g.add_inheritance("top", "rb");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));

    assert!(ev.has_permission("u1", &pa, 5.0), "left branch permission");
    assert!(ev.has_permission("u1", &pb, 5.0), "right branch permission");
}

// --------------------------------------------------------------------------
// Delegation: transitive, live-authority, all-delegators, cycle-safe.
// --------------------------------------------------------------------------

#[test]
fn test_hidden_delegatee_borrows_inherited_authority() {
    // Delegator's authority comes through inheritance; the delegatee borrows it.
    let ev = setup_rbac();
    let perm = Permission::new("crane", "lift");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("op", HashSet::new()));
        g.add_inheritance("op", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "op", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(
        ev.has_permission("u2", &perm, 5.0),
        "borrowed authority includes the delegator's inherited permissions"
    );
}

#[test]
fn test_hidden_delegatee_denied_when_delegator_unauthorized() {
    let ev = setup_rbac();
    let perm = Permission::new("gate", "open");
    ev.graph.borrow_mut().add_role(role_with("guard", &perm));
    // u1 has no grant; the delegation exists but confers nothing.
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(
        !ev.has_permission("u2", &perm, 5.0),
        "a delegation from an unauthorized principal grants nothing"
    );
}

#[test]
fn test_hidden_broken_middle_delegation_denies() {
    // Chain u1 -> u2 -> u3, but the first hop is only live on [0,5).
    let ev = setup_rbac();
    let perm = Permission::new("relay", "send");
    ev.graph.borrow_mut().add_role(role_with("sender", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "sender", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 5.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u2", "u3", 0.0, 100.0));

    assert!(
        ev.has_permission("u3", &perm, 3.0),
        "whole chain live at t=3"
    );
    assert!(
        !ev.has_permission("u3", &perm, 10.0),
        "a broken intermediate hop breaks the chain"
    );
}

#[test]
fn test_hidden_self_delegation_terminates() {
    let ev = setup_rbac();
    let perm = Permission::new("mirror", "peer");
    ev.graph.borrow_mut().add_role(role_with("seer", &perm));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u1", 0.0, 100.0));

    assert!(
        !ev.has_permission("u1", &perm, 5.0),
        "a self-delegation must terminate and deny"
    );
}

#[test]
fn test_hidden_long_cycle_terminates() {
    let ev = setup_rbac();
    let perm = Permission::new("ring", "spin");
    ev.graph.borrow_mut().add_role(role_with("spinner", &perm));
    for (from, to) in [
        ("u1", "u2"),
        ("u2", "u3"),
        ("u3", "u4"),
        ("u4", "u5"),
        ("u5", "u1"),
    ] {
        ev.delegations
            .borrow_mut()
            .add_delegation(Delegation::new(from, to, 0.0, 100.0));
    }

    assert!(
        !ev.has_permission("u1", &perm, 5.0),
        "a long delegation cycle must terminate and deny"
    );
}

#[test]
fn test_hidden_three_node_cycle_with_grant() {
    // u1 -> u2 -> u3 -> u1 forms a cycle, but u3 holds a real grant, so the
    // cycle must still surface the reachable authority for every member.
    let ev = setup_rbac();
    let perm = Permission::new("hub", "enter");
    ev.graph.borrow_mut().add_role(role_with("member", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u3", "member", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u2", "u3", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u3", "u1", 0.0, 100.0));

    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "u1 reaches u3's grant through the cycle"
    );
    assert!(
        ev.has_permission("u2", &perm, 5.0),
        "u2 reaches u3's grant through the cycle"
    );
}

#[test]
fn test_hidden_multiple_delegators_second_authorized() {
    // u3 has two delegators; only the second one is authorized.
    let ev = setup_rbac();
    let perm = Permission::new("desk", "sign");
    ev.graph.borrow_mut().add_role(role_with("signer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u2", "signer", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u3", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u2", "u3", 0.0, 100.0));

    assert!(
        ev.has_permission("u3", &perm, 5.0),
        "every delegator must be tried, not only the first"
    );
}

// --------------------------------------------------------------------------
// Cache: dependency-aware invalidation, LRU recency, bounded capacity.
// --------------------------------------------------------------------------

#[test]
fn test_hidden_grant_unrelated_preserves_delegatee_entry() {
    let ev = setup_rbac();
    let p = Permission::new("doc", "read");
    let q = Permission::new("img", "view");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("reader", &p));
        g.add_role(role_with("viewer", &q));
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "reader", 0.0, 100.0));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("zz", "viewer", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(ev.has_permission("u2", &p, 10.0));
    assert!(ev.has_permission("zz", &q, 10.0));

    let (_, misses_before) = ev.cache.stats();
    // Mutating zz must not disturb u2's cached decision (it derives from u1).
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("zz", "viewer", 50.0, 150.0));
    assert!(ev.has_permission("u2", &p, 10.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after, misses_before,
        "an unrelated grant must not evict the delegatee's cached entry"
    );
}

#[test]
fn test_hidden_revoke_preserves_other_delegatees_entry() {
    let ev = setup_rbac();
    let p = Permission::new("repo", "push");
    ev.graph.borrow_mut().add_role(role_with("dev", &p));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "dev", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u3", 0.0, 100.0));

    assert!(ev.has_permission("u2", &p, 10.0));
    assert!(ev.has_permission("u3", &p, 10.0));

    let (_, misses_before) = ev.cache.stats();
    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");

    // u3 still delegates from u1 (unchanged) -> its entry must survive.
    assert!(ev.has_permission("u3", &p, 10.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after, misses_before,
        "revoking one delegatee must not evict a sibling delegatee's entry"
    );
    assert!(
        !ev.has_permission("u2", &p, 10.0),
        "the revoked delegatee must lose borrowed authority"
    );
}

#[test]
fn test_hidden_transitive_two_hop_invalidation() {
    // u1 -> u2 -> u3. u3 is cached as denied; granting u1 (two hops up) must
    // reach and refresh u3's decision.
    let ev = setup_rbac();
    let perm = Permission::new("tower", "climb");
    ev.graph.borrow_mut().add_role(role_with("climber", &perm));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u2", "u3", 0.0, 100.0));

    assert!(!ev.has_permission("u3", &perm, 10.0));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "climber", 0.0, 100.0));
    assert!(
        ev.has_permission("u3", &perm, 10.0),
        "granting a principal two delegation hops up must invalidate the delegatee"
    );
}

#[test]
fn test_hidden_hot_entry_survives_many_insertions() {
    let ev = setup_rbac();
    let perm = Permission::new("core", "tap");
    ev.graph.borrow_mut().add_role(role_with("tapper", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("hot", "tapper", 0.0, 100.0));

    assert!(ev.has_permission("hot", &perm, 50.0));
    // Fill the rest of the cache to capacity (hot + cold0..cold6 == 8).
    for i in 0..7 {
        let _ = ev.has_permission(&format!("cold{i}"), &perm, 50.0);
    }
    // Keep hot warm, then force an eviction with a fresh key.
    assert!(ev.has_permission("hot", &perm, 50.0));
    let _ = ev.has_permission("cold7", &perm, 50.0);

    let (_, misses_before) = ev.cache.stats();
    assert!(ev.has_permission("hot", &perm, 50.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after, misses_before,
        "a repeatedly read hot entry must not be evicted"
    );
}

#[test]
fn test_hidden_capacity_boundary_no_early_eviction() {
    let ev = setup_rbac();
    let perm = Permission::new("slot", "fill");
    // No grants: every decision is a (cached) deny; we only probe cache behavior.
    for i in 0..8 {
        let _ = ev.has_permission(&format!("k{i}"), &perm, 1.0);
    }
    let (_, misses_after_fill) = ev.cache.stats();

    // Exactly CAPACITY distinct entries must all still be present.
    for i in 0..8 {
        let _ = ev.has_permission(&format!("k{i}"), &perm, 1.0);
    }
    let (_, misses_after_reread) = ev.cache.stats();
    assert_eq!(
        misses_after_reread, misses_after_fill,
        "a full-but-not-over-capacity cache must not evict early"
    );

    // A ninth distinct key must evict the least-recently-used (k0).
    let _ = ev.has_permission("k8", &perm, 1.0);
    let (_, before_k0) = ev.cache.stats();
    let _ = ev.has_permission("k0", &perm, 1.0);
    let (_, after_k0) = ev.cache.stats();
    assert_eq!(
        after_k0,
        before_k0 + 1,
        "exceeding capacity must evict, so k0 is recomputed (a miss)"
    );
}

#[test]
fn test_hidden_invalidated_entry_recomputed_as_miss() {
    let ev = setup_rbac();
    let perm = Permission::new("panel", "toggle");
    ev.graph.borrow_mut().add_role(role_with("switcher", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "switcher", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(ev.has_permission("u2", &perm, 10.0));
    let (_, misses_before) = ev.cache.stats();
    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");

    assert!(!ev.has_permission("u2", &perm, 10.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after,
        misses_before + 1,
        "the invalidated entry must be recomputed, not served stale"
    );
}

// --------------------------------------------------------------------------
// Cross-cutting interactions.
// --------------------------------------------------------------------------

#[test]
fn test_hidden_delegated_diamond_inheritance() {
    // Delegator's permission is only reachable through the second diamond arm,
    // and the delegatee must borrow it.
    let ev = setup_rbac();
    let perm = Permission::new("vault", "seal");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("mid1", HashSet::new()));
        g.add_role(Role::new("mid2", HashSet::new()));
        g.add_role(Role::new("top", HashSet::new()));
        g.add_inheritance("top", "mid1");
        g.add_inheritance("top", "mid2");
        g.add_inheritance("mid2", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(
        ev.has_permission("u2", &perm, 5.0),
        "delegatee must borrow a diamond-inherited permission from the second arm"
    );
}

#[test]
fn test_hidden_revoke_then_readd_delegation() {
    let ev = setup_rbac();
    let perm = Permission::new("bridge", "raise");
    ev.graph.borrow_mut().add_role(role_with("keeper", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "keeper", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));

    assert!(ev.has_permission("u2", &perm, 10.0));
    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");
    assert!(!ev.has_permission("u2", &perm, 10.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(
        ev.has_permission("u2", &perm, 10.0),
        "re-adding the delegation must restore borrowed authority"
    );
}

// ==========================================================================
// Additional discriminating hidden tests (difficulty hardening)
// ==========================================================================

// -------------------------------------------------------------------------
// Temporal half-open windows
// -------------------------------------------------------------------------

#[test]
fn test_hidden_delegatee_denied_at_delegator_grant_exact_end() {
    let ev = setup_rbac();
    let perm = Permission::new("safe", "unlock");
    ev.graph.borrow_mut().add_role(role_with("keyholder", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "keyholder", 0.0, 50.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 49.0));
    assert!(
        !ev.has_permission("u2", &perm, 50.0),
        "the grant end bound is exclusive even when borrowed through delegation"
    );
}

#[test]
fn test_hidden_delegation_window_narrower_than_grant() {
    let ev = setup_rbac();
    let perm = Permission::new("report", "sign");
    ev.graph.borrow_mut().add_role(role_with("signer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "signer", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 10.0, 20.0));
    assert!(!ev.has_permission("u2", &perm, 9.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
    assert!(ev.has_permission("u2", &perm, 19.0));
    assert!(!ev.has_permission("u2", &perm, 20.0));
}

#[test]
fn test_hidden_two_grants_with_gap_reactivate() {
    let ev = setup_rbac();
    let perm = Permission::new("gate", "pass");
    ev.graph.borrow_mut().add_role(role_with("passer", &perm));
    {
        let mut g = ev.grants.borrow_mut();
        g.assign_grant(TemporalGrant::new("u1", "passer", 0.0, 10.0));
        g.assign_grant(TemporalGrant::new("u1", "passer", 20.0, 30.0));
    }
    assert!(ev.has_permission("u1", &perm, 5.0));
    assert!(!ev.has_permission("u1", &perm, 10.0));
    assert!(!ev.has_permission("u1", &perm, 15.0));
    assert!(ev.has_permission("u1", &perm, 25.0));
    assert!(!ev.has_permission("u1", &perm, 30.0));
}

#[test]
fn test_hidden_zero_width_delegation_never_active() {
    let ev = setup_rbac();
    let perm = Permission::new("bank", "wire");
    ev.graph.borrow_mut().add_role(role_with("teller", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "teller", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 5.0, 5.0));
    assert!(
        !ev.has_permission("u2", &perm, 5.0),
        "a zero-width delegation window is never active"
    );
}

// -------------------------------------------------------------------------
// Multi-parent inheritance (all paths must be followed)
// -------------------------------------------------------------------------

#[test]
fn test_hidden_permission_only_via_second_parent() {
    let ev = setup_rbac();
    let perm = Permission::new("ledger", "post");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(Role::new("p1", HashSet::new()));
        g.add_role(role_with("p2", &perm));
        g.add_role(Role::new("top", HashSet::new()));
        g.add_inheritance("top", "p1");
        g.add_inheritance("top", "p2");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));
    assert!(
        ev.has_permission("u1", &perm, 10.0),
        "inheritance must follow every parent, not just the first"
    );
}

#[test]
fn test_hidden_wide_fanout_permission_on_last_branch() {
    let ev = setup_rbac();
    let perm = Permission::new("cluster", "scale");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("top", HashSet::new()));
        for i in 0..5 {
            let mid = format!("mid{}", i);
            g.add_role(Role::new(&mid, HashSet::new()));
            g.add_inheritance("top", &mid);
        }
        g.add_inheritance("mid4", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));
    assert!(ev.has_permission("u1", &perm, 10.0));
}

#[test]
fn test_hidden_deep_second_branch_grandparent() {
    let ev = setup_rbac();
    let perm = Permission::new("root", "admin");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("gp", &perm));
        g.add_role(Role::new("a", HashSet::new()));
        g.add_role(Role::new("b", HashSet::new()));
        g.add_role(Role::new("top", HashSet::new()));
        g.add_inheritance("top", "a");
        g.add_inheritance("top", "b");
        g.add_inheritance("b", "gp");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "top", 0.0, 100.0));
    assert!(ev.has_permission("u1", &perm, 10.0));
}

#[test]
fn test_hidden_remove_inheritance_invalidates_all_sharers() {
    let ev = setup_rbac();
    let perm = Permission::new("wiki", "edit");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("editor", HashSet::new()));
        g.add_inheritance("editor", "base");
    }
    {
        let mut gr = ev.grants.borrow_mut();
        gr.assign_grant(TemporalGrant::new("u1", "editor", 0.0, 100.0));
        gr.assign_grant(TemporalGrant::new("u2", "editor", 0.0, 100.0));
    }
    assert!(ev.has_permission("u1", &perm, 10.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
    ev.graph.borrow_mut().remove_inheritance("editor", "base");
    assert!(
        !ev.has_permission("u1", &perm, 10.0),
        "a graph change must invalidate cached decisions for every affected user"
    );
    assert!(!ev.has_permission("u2", &perm, 10.0));
}

#[test]
fn test_hidden_add_inheritance_enables_cached_denied_user() {
    let ev = setup_rbac();
    let perm = Permission::new("panel", "toggle");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("power", &perm));
        g.add_role(Role::new("member", HashSet::new()));
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "member", 0.0, 100.0));
    assert!(!ev.has_permission("u1", &perm, 10.0));
    ev.graph.borrow_mut().add_inheritance("member", "power");
    assert!(
        ev.has_permission("u1", &perm, 10.0),
        "adding an inheritance link must invalidate the cached denial"
    );
}

// -------------------------------------------------------------------------
// Delegation: transitive, live authority, all delegators, cycles
// -------------------------------------------------------------------------

#[test]
fn test_hidden_delegatee_uses_delegator_inherited_authority() {
    let ev = setup_rbac();
    let perm = Permission::new("db", "migrate");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("base", &perm));
        g.add_role(Role::new("lead", HashSet::new()));
        g.add_inheritance("lead", "base");
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "lead", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
}

#[test]
fn test_hidden_delegation_denied_after_delegator_authority_expires() {
    let ev = setup_rbac();
    let perm = Permission::new("crypto", "rotate");
    ev.graph.borrow_mut().add_role(role_with("kms", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "kms", 0.0, 10.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 5.0));
    assert!(
        !ev.has_permission("u2", &perm, 20.0),
        "a delegatee borrows only the delegator's live authority"
    );
}

#[test]
fn test_hidden_two_delegators_only_second_authorized() {
    let ev = setup_rbac();
    let perm = Permission::new("net", "peer");
    ev.graph.borrow_mut().add_role(role_with("peerer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("d2", "peerer", 0.0, 100.0));
    {
        let mut dm = ev.delegations.borrow_mut();
        dm.add_delegation(Delegation::new("d1", "u", 0.0, 100.0));
        dm.add_delegation(Delegation::new("d2", "u", 0.0, 100.0));
    }
    assert!(
        ev.has_permission("u", &perm, 10.0),
        "authorization holds if any active delegator is authorized"
    );
}

#[test]
fn test_hidden_two_node_delegation_cycle_terminates_denied() {
    let ev = setup_rbac();
    let perm = Permission::new("x", "y");
    ev.graph.borrow_mut().add_role(role_with("r", &perm));
    {
        let mut dm = ev.delegations.borrow_mut();
        dm.add_delegation(Delegation::new("a", "b", 0.0, 100.0));
        dm.add_delegation(Delegation::new("b", "a", 0.0, 100.0));
    }
    assert!(!ev.has_permission("a", &perm, 10.0));
    assert!(!ev.has_permission("b", &perm, 10.0));
}

#[test]
fn test_hidden_cycle_with_grant_on_one_member() {
    let ev = setup_rbac();
    let perm = Permission::new("svc", "deploy");
    ev.graph.borrow_mut().add_role(role_with("deployer", &perm));
    {
        let mut dm = ev.delegations.borrow_mut();
        dm.add_delegation(Delegation::new("a", "b", 0.0, 100.0));
        dm.add_delegation(Delegation::new("b", "c", 0.0, 100.0));
        dm.add_delegation(Delegation::new("c", "a", 0.0, 100.0));
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("b", "deployer", 0.0, 100.0));
    assert!(ev.has_permission("a", &perm, 10.0));
    assert!(ev.has_permission("c", &perm, 10.0));
}

#[test]
fn test_hidden_self_delegation_without_authority_denied() {
    let ev = setup_rbac();
    let perm = Permission::new("self", "act");
    ev.graph.borrow_mut().add_role(role_with("actor", &perm));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u1", 0.0, 100.0));
    assert!(!ev.has_permission("u1", &perm, 10.0));
}

// -------------------------------------------------------------------------
// Cache: dependency-aware invalidation, LRU recency, bounded capacity
// -------------------------------------------------------------------------

#[test]
fn test_hidden_grant_to_delegator_invalidates_delegatee_entry() {
    let ev = setup_rbac();
    let perm = Permission::new("first", "use");
    let other = Permission::new("second", "use");
    {
        let mut g = ev.graph.borrow_mut();
        g.add_role(role_with("r1", &perm));
        g.add_role(role_with("r2", &other));
    }
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "r1", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
    let (_h0, m0) = ev.cache.stats();
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "r2", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
    let (_h1, m1) = ev.cache.stats();
    assert_eq!(
        m1 - m0,
        1,
        "granting to the delegator must invalidate the delegatee's dependent entry"
    );
}

#[test]
fn test_hidden_revoke_invalidates_only_target_delegatee() {
    let ev = setup_rbac();
    let perm = Permission::new("area", "enter");
    ev.graph.borrow_mut().add_role(role_with("guard", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "guard", 0.0, 100.0));
    {
        let mut dm = ev.delegations.borrow_mut();
        dm.add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
        dm.add_delegation(Delegation::new("u1", "u3", 0.0, 100.0));
    }
    assert!(ev.has_permission("u2", &perm, 10.0));
    assert!(ev.has_permission("u3", &perm, 10.0));
    let (h0, _m0) = ev.cache.stats();
    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");
    let r2 = ev.has_permission("u2", &perm, 10.0);
    let r3 = ev.has_permission("u3", &perm, 10.0);
    let (h1, _m1) = ev.cache.stats();
    assert!(!r2);
    assert!(r3);
    assert_eq!(
        h1 - h0,
        1,
        "only the untouched delegatee's entry should survive as a hit"
    );
}

#[test]
fn test_hidden_unrelated_grant_preserves_dependent_entry() {
    let ev = setup_rbac();
    let perm = Permission::new("zone", "view");
    ev.graph.borrow_mut().add_role(role_with("viewer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "viewer", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(ev.has_permission("u2", &perm, 10.0));
    let (h0, _m0) = ev.cache.stats();
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("zz", "viewer", 0.0, 100.0));
    let r = ev.has_permission("u2", &perm, 10.0);
    let (h1, _m1) = ev.cache.stats();
    assert!(r);
    assert_eq!(
        h1 - h0,
        1,
        "an unrelated grant must not evict the dependent entry"
    );
}

#[test]
fn test_hidden_repeated_query_counts_as_hits() {
    let ev = setup_rbac();
    let perm = Permission::new("api", "call");
    ev.graph.borrow_mut().add_role(role_with("caller", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "caller", 0.0, 100.0));
    let (h0, m0) = ev.cache.stats();
    assert!(ev.has_permission("u1", &perm, 10.0));
    assert!(ev.has_permission("u1", &perm, 10.0));
    assert!(ev.has_permission("u1", &perm, 10.0));
    let (h1, m1) = ev.cache.stats();
    assert_eq!(m1 - m0, 1);
    assert_eq!(h1 - h0, 2);
}

#[test]
fn test_hidden_hot_entry_not_evicted_under_churn() {
    let ev = setup_rbac();
    let perm = Permission::new("hot", "key");
    ev.graph.borrow_mut().add_role(role_with("holder", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("h", "holder", 0.0, 1000.0));
    assert!(ev.has_permission("h", &perm, 1.0));
    for t in 100..120 {
        let _ = ev.has_permission("h", &perm, t as f64);
        let _ = ev.has_permission("h", &perm, 1.0);
    }
    let (h0, m0) = ev.cache.stats();
    let r = ev.has_permission("h", &perm, 1.0);
    let (h1, m1) = ev.cache.stats();
    assert!(r);
    assert_eq!(h1 - h0, 1, "a repeatedly read hot entry must remain cached");
    assert_eq!(m1 - m0, 0);
}

#[test]
fn test_hidden_cold_entry_evicted_when_capacity_exceeded() {
    let ev = setup_rbac();
    let perm = Permission::new("cold", "key");
    ev.graph.borrow_mut().add_role(role_with("holder", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("h", "holder", 0.0, 1000.0));
    assert!(ev.has_permission("h", &perm, 1.0));
    for t in 100..110 {
        let _ = ev.has_permission("h", &perm, t as f64);
    }
    let (h0, m0) = ev.cache.stats();
    let _ = ev.has_permission("h", &perm, 1.0);
    let (h1, m1) = ev.cache.stats();
    assert_eq!(
        m1 - m0,
        1,
        "the never-reread cold entry should have been evicted under capacity pressure"
    );
    assert_eq!(h1 - h0, 0);
}

#[test]
fn test_hidden_deep_delegation_chain_all_hits_after_prime() {
    let ev = setup_rbac();
    let perm = Permission::new("chain", "run");
    ev.graph.borrow_mut().add_role(role_with("runner", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "runner", 0.0, 100.0));
    for (from, to) in [("u1", "u2"), ("u2", "u3")] {
        ev.delegations
            .borrow_mut()
            .add_delegation(Delegation::new(from, to, 0.0, 100.0));
    }
    assert!(ev.has_permission("u3", &perm, 10.0));
    let (h0, m0) = ev.cache.stats();
    assert!(ev.has_permission("u3", &perm, 10.0));
    let (h1, m1) = ev.cache.stats();
    assert_eq!(h1 - h0, 1);
    assert_eq!(m1 - m0, 0);
}
