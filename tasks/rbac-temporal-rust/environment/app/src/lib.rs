//! Temporal RBAC authorization service.
//!
//! The crate implements a role-based access-control engine whose authority is
//! bounded in time. A user's effective permissions at an instant `t` are derived
//! from three cooperating subsystems:
//!
//! * [`grants`] — time-bounded assignments of a role to a user.
//! * [`graph`] — a role-inheritance graph where a role transitively owns the
//!   permissions of every role it inherits from.
//! * [`delegation`] — user-to-user delegation, where a delegatee may borrow the
//!   live authority of a delegator while both the delegation window and the
//!   delegator's own authority are active.
//!
//! [`evaluator::Evaluator`] answers `has_permission` queries by combining the
//! three subsystems, and memoizes decisions in a bounded [`cache`]. The precise
//! behavioral contract for each subsystem is documented on its public items.
pub mod cache;
pub mod delegation;
pub mod evaluator;
pub mod grants;
pub mod graph;
pub mod types_def;
