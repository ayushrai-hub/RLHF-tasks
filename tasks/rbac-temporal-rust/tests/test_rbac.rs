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
fn test_basic_grant_and_expiry() {
    let ev = setup_rbac();
    let perm = Permission::new("document", "read");
    ev.graph.borrow_mut().add_role(role_with("reader", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "reader", 0.0, 10.0));

    assert!(ev.has_permission("u1", &perm, 5.0));
    assert!(!ev.has_permission("u1", &perm, 15.0));
}

#[test]
fn test_exact_temporal_boundaries() {
    let ev = setup_rbac();
    let perm = Permission::new("db", "read");
    ev.graph.borrow_mut().add_role(role_with("reader", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "reader", 10.0, 20.0));

    assert!(
        ev.has_permission("u1", &perm, 10.0),
        "start bound is inclusive"
    );
    assert!(
        !ev.has_permission("u1", &perm, 9.999),
        "before start is denied"
    );
    assert!(
        !ev.has_permission("u1", &perm, 20.0),
        "end bound is exclusive"
    );
    assert!(
        ev.has_permission("u1", &perm, 19.999),
        "just before end is allowed"
    );
}

#[test]
fn test_diamond_inheritance_all_paths() {
    // The permission is only reachable through the *second* parent of `top`, so
    // any traversal that stops after the first parent will miss it.
    let ev = setup_rbac();
    let perm = Permission::new("system", "admin");
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

    assert!(
        ev.has_permission("u1", &perm, 5.0),
        "every inheritance path must be followed, not just the first parent"
    );
}

#[test]
fn test_remove_inheritance_revokes_permission() {
    let ev = setup_rbac();
    let perm = Permission::new("cluster", "manage");
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
    assert!(
        !ev.has_permission("u1", &perm, 5.0),
        "removing an inheritance link must update authorization"
    );
}

#[test]
fn test_delegation_follows_live_delegator() {
    let ev = setup_rbac();
    let perm = Permission::new("db", "write");
    ev.graph.borrow_mut().add_role(role_with("writer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "writer", 0.0, 10.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 2.0, 12.0));

    assert!(ev.has_permission("u2", &perm, 5.0));
    assert!(
        !ev.has_permission("u2", &perm, 11.0),
        "delegated authority ends when the delegator's own grant expires"
    );
}

#[test]
fn test_delegation_add_and_revoke_invalidation() {
    let ev = setup_rbac();
    let perm = Permission::new("repo", "commit");
    ev.graph
        .borrow_mut()
        .add_role(role_with("committer", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "committer", 0.0, 100.0));

    assert!(!ev.has_permission("u2", &perm, 10.0));

    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    assert!(
        ev.has_permission("u2", &perm, 10.0),
        "adding a delegation must invalidate the delegatee's cached decision"
    );

    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");
    assert!(
        !ev.has_permission("u2", &perm, 10.0),
        "revoking a delegation must invalidate the delegatee's cached decision"
    );
}

#[test]
fn test_transitive_grant_updates_delegatee() {
    // A delegatee is cached as denied, then the delegator receives a grant. The
    // delegatee's cached decision depended on the delegator and must refresh.
    let ev = setup_rbac();
    let perm = Permission::new("finance", "view");
    ev.graph.borrow_mut().add_role(role_with("analyst", &perm));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("boss", "emp", 0.0, 100.0));

    assert!(!ev.has_permission("emp", &perm, 10.0));

    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("boss", "analyst", 0.0, 100.0));

    assert!(
        ev.has_permission("emp", &perm, 10.0),
        "granting the delegator must invalidate the delegatee's cached decision"
    );
}

#[test]
fn test_cyclic_delegation_terminates() {
    let ev = setup_rbac();
    let perm = Permission::new("prod", "deploy");
    ev.graph.borrow_mut().add_role(role_with("deployer", &perm));

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
        !ev.has_permission("u1", &perm, 10.0),
        "cyclic delegation must terminate safely and deny (no one holds the grant)"
    );
}

#[test]
fn test_multi_hop_delegation_expiry() {
    let ev = setup_rbac();
    let perm = Permission::new("admin", "login");
    ev.graph.borrow_mut().add_role(role_with("super", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u1", "super", 0.0, 50.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u1", "u2", 0.0, 100.0));
    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u2", "u3", 0.0, 100.0));

    assert!(ev.has_permission("u3", &perm, 49.0));
    assert!(
        !ev.has_permission("u3", &perm, 50.0),
        "expiry of the root grant must propagate transitively"
    );
}

#[test]
fn test_lru_refreshes_on_read() {
    // A hot entry that is read again must not be evicted ahead of colder ones.
    let ev = setup_rbac();
    let perm = Permission::new("secrets", "read");
    ev.graph.borrow_mut().add_role(role_with("admin", &perm));
    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("hot", "admin", 0.0, 100.0));

    assert!(ev.has_permission("hot", &perm, 50.0));
    for i in 0..7 {
        let _ = ev.has_permission(&format!("cold{i}"), &perm, 50.0);
    }
    // Read the hot entry so it becomes most-recently-used.
    assert!(ev.has_permission("hot", &perm, 50.0));
    // Insert a new key, forcing eviction of the least-recently-used entry.
    let _ = ev.has_permission("cold7", &perm, 50.0);

    let (_, misses_before) = ev.cache.stats();
    assert!(ev.has_permission("hot", &perm, 50.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after, misses_before,
        "reading an entry must refresh its recency so it survives eviction"
    );
}

#[test]
fn test_scoped_invalidation_preserves_unrelated() {
    // Invalidation after a mutation must be precise: an unrelated cached entry
    // must survive (remain a cache hit), while the affected entry is refreshed.
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
    ev.delegations.borrow_mut().revoke_delegation("u1", "u2");

    assert!(ev.has_permission("zz", &q, 10.0));
    let (_, misses_after) = ev.cache.stats();
    assert_eq!(
        misses_after, misses_before,
        "invalidation must not drop cache entries unrelated to the mutation"
    );

    assert!(
        !ev.has_permission("u2", &p, 10.0),
        "the delegatee's affected decision must be refreshed after revoke"
    );
}

#[test]
fn test_public_api_preserved() {
    // Compile-time guard over every public signature that must be preserved.
    let cache: Rc<EvaluationCache> = Rc::new(EvaluationCache::new());
    let graph: Rc<RefCell<RoleGraph>> = Rc::new(RefCell::new(RoleGraph::new(cache.clone())));
    let grants: Rc<RefCell<GrantManager>> = Rc::new(RefCell::new(GrantManager::new(cache.clone())));
    let delegations: Rc<RefCell<DelegationManager>> =
        Rc::new(RefCell::new(DelegationManager::new(cache.clone())));
    let ev = Evaluator::new(cache, graph, grants, delegations);

    let perm = Permission::new("res", "act");
    ev.graph.borrow_mut().add_role(role_with("r", &perm));
    ev.graph.borrow_mut().add_inheritance("r", "r");
    ev.graph.borrow_mut().remove_inheritance("r", "r");
    let _roles: Vec<String> = ev.graph.borrow().get_all_inherited_roles("r");
    let _perms: HashSet<Permission> = ev.graph.borrow().get_role_permissions("r");

    ev.grants
        .borrow_mut()
        .assign_grant(TemporalGrant::new("u", "r", 0.0, 1.0));
    let _active: Vec<String> = ev.grants.borrow().get_active_roles("u", 0.5);

    ev.delegations
        .borrow_mut()
        .add_delegation(Delegation::new("u", "v", 0.0, 1.0));
    let _dels: Vec<String> = ev.delegations.borrow().get_active_delegators("v", 0.5);
    ev.delegations.borrow_mut().revoke_delegation("u", "v");

    let _decision: bool = ev.has_permission("u", &perm, 0.5);
}
