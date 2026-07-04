//! Value types shared across the authorization subsystems.

use std::collections::HashSet;

/// A single permission, identified by the `(resource, action)` pair. Two
/// permissions are equal iff both fields are equal.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Permission {
    pub resource: String,
    pub action: String,
}

impl Permission {
    pub fn new(resource: &str, action: &str) -> Self {
        Self {
            resource: resource.to_string(),
            action: action.to_string(),
        }
    }
}

/// A named role holding a set of permissions. Inheritance between roles is
/// modeled separately by [`crate::graph::RoleGraph`].
#[derive(Debug, Clone)]
pub struct Role {
    pub name: String,
    pub permissions: HashSet<Permission>,
}

impl Role {
    pub fn new(name: &str, permissions: HashSet<Permission>) -> Self {
        Self {
            name: name.to_string(),
            permissions,
        }
    }
}

/// A time-bounded assignment of `role_name` to `user_id`. The grant is active
/// for an instant `t` when `start_time <= t < end_time` (start inclusive, end
/// exclusive).
#[derive(Debug, Clone)]
pub struct TemporalGrant {
    pub user_id: String,
    pub role_name: String,
    pub start_time: f64,
    pub end_time: f64,
}

impl TemporalGrant {
    pub fn new(user_id: &str, role_name: &str, start_time: f64, end_time: f64) -> Self {
        Self {
            user_id: user_id.to_string(),
            role_name: role_name.to_string(),
            start_time,
            end_time,
        }
    }
}

/// A user-to-user delegation. While active, `delegatee_id` may borrow whatever
/// authority `delegator_id` actually holds at the same instant. The delegation
/// window uses the same inclusive-start/exclusive-end convention as grants.
#[derive(Debug, Clone)]
pub struct Delegation {
    pub delegator_id: String,
    pub delegatee_id: String,
    pub start_time: f64,
    pub end_time: f64,
}

impl Delegation {
    pub fn new(delegator_id: &str, delegatee_id: &str, start_time: f64, end_time: f64) -> Self {
        Self {
            delegator_id: delegator_id.to_string(),
            delegatee_id: delegatee_id.to_string(),
            start_time,
            end_time,
        }
    }
}
