//! Time-bounded role grants.

use crate::cache::EvaluationCache;
use crate::types_def::TemporalGrant;
use std::collections::HashMap;
use std::rc::Rc;

/// Stores the temporal grants assigned to each user and reports which roles are
/// active for a user at a given instant.
pub struct GrantManager {
    pub grants: HashMap<String, Vec<TemporalGrant>>,
    pub cache_manager: Rc<EvaluationCache>,
}

impl GrantManager {
    pub fn new(cache_manager: Rc<EvaluationCache>) -> Self {
        Self {
            grants: HashMap::new(),
            cache_manager,
        }
    }

    /// Record a new grant. Because this changes the user's authority (and the
    /// authority of anyone who delegates from them), the affected cached
    /// decisions must be invalidated.
    pub fn assign_grant(&mut self, grant: TemporalGrant) {
        let user_id = grant.user_id.clone();
        self.grants.entry(user_id.clone()).or_default().push(grant);
        self.cache_manager.invalidate_user(&user_id);
    }

    /// Return the roles active for `user_id` at `current_time`. A grant is active
    /// when `start_time <= current_time < end_time`: the start bound is
    /// inclusive and the end bound is exclusive.
    pub fn get_active_roles(&self, user_id: &str, current_time: f64) -> Vec<String> {
        if let Some(user_grants) = self.grants.get(user_id) {
            let mut active_roles = Vec::new();
            for grant in user_grants {
                if grant.start_time <= current_time && current_time < grant.end_time {
                    active_roles.push(grant.role_name.clone());
                }
            }
            active_roles
        } else {
            Vec::new()
        }
    }
}
