use crate::p7_p7_r;

pub fn phase_order(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    p7_p7_r::op_p7(scenario_id, roots)
}
