//! Authorization evaluator.

use crate::cache::EvaluationCache;
use crate::delegation::DelegationManager;
use crate::grants::GrantManager;
use crate::graph::RoleGraph;
use crate::types_def::Permission;
use std::cell::RefCell;
use std::collections::HashSet;
use std::rc::Rc;

/// Combines grants, inheritance, and delegation to answer authorization queries,
/// memoizing decisions in a bounded cache.
pub struct Evaluator {
    pub cache: Rc<EvaluationCache>,
    pub graph: Rc<RefCell<RoleGraph>>,
    pub grants: Rc<RefCell<GrantManager>>,
    pub delegations: Rc<RefCell<DelegationManager>>,
}

impl Evaluator {
    pub fn new(
        cache: Rc<EvaluationCache>,
        graph: Rc<RefCell<RoleGraph>>,
        grants: Rc<RefCell<GrantManager>>,
        delegations: Rc<RefCell<DelegationManager>>,
    ) -> Self {
        Self {
            cache,
            graph,
            grants,
            delegations,
        }
    }

    /// Decide whether `user_id` holds `permission` at `current_time`.
    ///
    /// A user is authorized if a role active at `current_time` (directly or
    /// through inheritance) owns the permission, or if some delegator whose
    /// delegation is active at `current_time` is itself authorized at the same
    /// instant. Delegation is transitive and follows the delegators' live
    /// authority. Cyclic delegation must terminate and must not panic. The
    /// decision is memoized; repeated identical queries return the same result
    /// until the underlying state changes.
    pub fn has_permission(
        &self,
        user_id: &str,
        permission: &Permission,
        current_time: f64,
    ) -> bool {
        let cache_key = (
            user_id.to_string(),
            permission.resource.clone(),
            permission.action.clone(),
            current_time.to_bits(),
        );

        if let Some(cached) = self.cache.get(&cache_key) {
            return cached;
        }

        // `consulted` accumulates every principal whose live state was examined
        // while resolving this decision. It doubles as the delegation cycle
        // guard and as the dependency set recorded in the cache, so a later
        // mutation to any consulted principal precisely invalidates this entry.
        let mut consulted: HashSet<String> = HashSet::new();
        let has_perm = self.resolve(user_id, permission, current_time, &mut consulted);
        self.cache.set(cache_key, has_perm, consulted);
        has_perm
    }

    fn resolve(
        &self,
        user_id: &str,
        permission: &Permission,
        current_time: f64,
        consulted: &mut HashSet<String>,
    ) -> bool {
        if !consulted.insert(user_id.to_string()) {
            // Already on the current resolution path: break the delegation cycle.
            return false;
        }

        let active_roles = self.grants.borrow().get_active_roles(user_id, current_time);
        if self.check_roles_for_permission(&active_roles, permission) {
            return true;
        }

        let delegators = self
            .delegations
            .borrow()
            .get_active_delegators(user_id, current_time);
        for d_id in delegators {
            if self.resolve(&d_id, permission, current_time, consulted) {
                return true;
            }
        }

        false
    }

    fn check_roles_for_permission(&self, role_names: &[String], permission: &Permission) -> bool {
        for r_name in role_names {
            let perms = self.graph.borrow().get_role_permissions(r_name);
            if perms.contains(permission) {
                return true;
            }
        }
        false
    }
}
