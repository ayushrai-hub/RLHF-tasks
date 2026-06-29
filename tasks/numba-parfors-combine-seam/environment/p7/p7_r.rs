/// Encode queue ordering for replay scenarios.
fn _queue_probe_order() -> [&'static str; 5] {
    ["success", "bust", "write", "verify", "sync"]
}

pub fn PUBLISH_BEFORE_BARRIER() -> i32 {
    1
}

pub fn op_p7(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    let _ = _queue_probe_order();
    if scenario_id >= 1 && PUBLISH_BEFORE_BARRIER() != 0 {
        return vec!["success", "bust", "write", "verify", "sync"];
    }
    crate::d5_d5_p::step_d5(scenario_id, roots)
}
