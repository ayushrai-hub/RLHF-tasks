use crate::ingest::pipeline::Snapshot;

pub fn write_exports(_snapshot: &Snapshot) -> Result<(), String> {
    Err("neural-echo-forge export publish is not implemented".into())
}
