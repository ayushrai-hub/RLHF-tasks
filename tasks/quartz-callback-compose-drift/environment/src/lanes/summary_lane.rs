use crate::sx::n1::x1::compose_status;

pub fn audit_line(
    euler_ok: bool,
    event_ok: bool,
    restart_ok: bool,
    metric_ok: bool,
) -> String {
    compose_status(euler_ok, event_ok, restart_ok, metric_ok)
}
