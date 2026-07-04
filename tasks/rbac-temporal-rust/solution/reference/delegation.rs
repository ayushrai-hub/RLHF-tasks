//! User-to-user delegation.

use crate::cache::EvaluationCache;
use crate::types_def::Delegation;
use std::collections::HashMap;
use std::rc::Rc;

/// Stores delegations indexed by delegatee and reports which delegators are
/// active for a delegatee at a given instant.
pub struct DelegationManager {
    pub received_delegations: HashMap<String, Vec<Delegation>>,
    pub cache_manager: Rc<EvaluationCache>,
}

impl DelegationManager {
    pub fn new(cache_manager: Rc<EvaluationCache>) -> Self {
        Self {
            received_delegations: HashMap::new(),
            cache_manager,
        }
    }

    /// Register a delegation. Adding a delegation can change the delegatee's
    /// effective authority (and that of anyone downstream), so the affected
    /// cached decisions must be invalidated.
    pub fn add_delegation(&mut self, delegation: Delegation) {
        let delegatee_id = delegation.delegatee_id.clone();
        self.received_delegations
            .entry(delegatee_id.clone())
            .or_default()
            .push(delegation);
        self.cache_manager.invalidate_user(&delegatee_id);
    }

    /// Remove every delegation from `delegator_id` to `delegatee_id`. Like
    /// [`DelegationManager::add_delegation`], this changes effective authority
    /// and the affected cached decisions must be invalidated.
    pub fn revoke_delegation(&mut self, delegator_id: &str, delegatee_id: &str) {
        if let Some(delegations) = self.received_delegations.get_mut(delegatee_id) {
            delegations.retain(|d| d.delegator_id != delegator_id);
        }
        self.cache_manager.invalidate_user(delegatee_id);
    }

    /// Return the delegators whose delegation to `delegatee_id` is active at
    /// `current_time` (`start_time <= current_time < end_time`).
    pub fn get_active_delegators(&self, delegatee_id: &str, current_time: f64) -> Vec<String> {
        if let Some(delegations) = self.received_delegations.get(delegatee_id) {
            let mut active_delegators = Vec::new();
            for d in delegations {
                if d.start_time <= current_time && current_time < d.end_time {
                    active_delegators.push(d.delegator_id.clone());
                }
            }
            active_delegators
        } else {
            Vec::new()
        }
    }
}
