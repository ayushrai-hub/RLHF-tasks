use std::collections::{BTreeMap, BTreeSet};

use crate::version::Version;

#[derive(Clone)]
pub struct Requirement {
    pub package: String,
    pub constraint: String,
    pub features: BTreeSet<String>,
}

#[derive(Clone)]
pub struct VersionRecord {
    pub version: Version,
    pub yanked: bool,
    pub deps: Vec<Requirement>,
    pub feature_deps: BTreeMap<String, Vec<Requirement>>,
}

#[derive(Clone)]
pub struct Conflict {
    pub package: String,
    pub constraints: Vec<String>,
    pub reason: String,
}
