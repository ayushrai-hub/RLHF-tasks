use crate::model::ScenarioRow;

pub fn phase_gate_a(_u: &str, _rev_hint: u64) -> bool {
    true
}

pub fn dispatch_reload(row: &ScenarioRow) -> (String, bool) {
    let ack = phase_gate_a(&row.primary_unit, row.rev_hint);
    let fresh = ack && row.has_dependency_refresh && row.rev_hint >= 10;
    ("success".to_string(), fresh)
}
