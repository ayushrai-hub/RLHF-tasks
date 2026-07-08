use crate::ingest::pipeline::Snapshot;

pub fn gate_exports(_snapshot: &Snapshot) -> Result<(), String> {
    Err("reconcile gate is not wired".into())
}
