use crate::runtime::pulse::pulse_tag;

pub fn emit_trace(unit_id: &str, edge_count: u64) -> String {
    format!("{}:{}", pulse_tag(unit_id), edge_count)
}
