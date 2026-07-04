//! Role-inheritance graph.

use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use crate::cache::EvaluationCache;
use crate::types_def::{Permission, Role};

/// A role graph where a role transitively owns the permissions of every role it
/// inherits from. Inheritance may form a multi-parent (diamond) DAG.
pub struct RoleGraph {
    pub roles: HashMap<String, Role>,
    pub inheritance: HashMap<String, Vec<String>>,
    pub cache_manager: Rc<EvaluationCache>,
}

impl RoleGraph {
    pub fn new(cache_manager: Rc<EvaluationCache>) -> Self {
        Self {
            roles: HashMap::new(),
            inheritance: HashMap::new(),
            cache_manager,
        }
    }

    /// Register a role. A role change can affect any user, so all cached
    /// decisions are invalidated.
    pub fn add_role(&mut self, role: Role) {
        self.roles.insert(role.name.clone(), role.clone());
        self.inheritance.insert(role.name.clone(), Vec::new());
        self.cache_manager.invalidate_all();
    }

    /// Add an inheritance edge `child -> parent` (child inherits parent). A graph
    /// change can affect any user, so all cached decisions are invalidated.
    pub fn add_inheritance(&mut self, child: &str, parent: &str) {
        if self.roles.contains_key(child) && self.roles.contains_key(parent) {
            self.inheritance
                .get_mut(child)
                .unwrap()
                .push(parent.to_string());
            self.cache_manager.invalidate_all();
        }
    }

    /// Remove the inheritance edge `child -> parent`. Removing a link can revoke
    /// permission paths for any user, so all cached decisions are invalidated.
    pub fn remove_inheritance(&mut self, child: &str, parent: &str) {
        if let Some(parents) = self.inheritance.get_mut(child) {
            parents.retain(|p| p != parent);
            self.cache_manager.invalidate_user(child);
        }
    }

    /// Return `role_name` together with every role reachable from it through
    /// inheritance. All inheritance paths must be followed, including every
    /// parent of a multi-parent role; cycles must not cause infinite recursion.
    pub fn get_all_inherited_roles(&self, role_name: &str) -> Vec<String> {
        let mut visited_list = Vec::new();

        fn dfs(
            current: &str,
            inheritance: &HashMap<String, Vec<String>>,
            visited_list: &mut Vec<String>,
        ) {
            if visited_list.contains(&current.to_string()) {
                return;
            }
            visited_list.push(current.to_string());

            if let Some(parents) = inheritance.get(current) {
                if let Some(first_parent) = parents.first() {
                    dfs(first_parent, inheritance, visited_list);
                }
            }
        }

        dfs(role_name, &self.inheritance, &mut visited_list);
        visited_list
    }

    /// Union of the permissions owned by `role_name` and all roles it inherits.
    pub fn get_role_permissions(&self, role_name: &str) -> HashSet<Permission> {
        let all_roles = self.get_all_inherited_roles(role_name);
        let mut perms = HashSet::new();
        for r in all_roles {
            if let Some(role) = self.roles.get(&r) {
                for p in &role.permissions {
                    perms.insert(p.clone());
                }
            }
        }
        perms
    }
}
