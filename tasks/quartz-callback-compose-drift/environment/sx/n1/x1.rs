pub fn compose_status(
    euler_ok: bool,
    event_ok: bool,
    restart_ok: bool,
    metric_ok: bool,
) -> String {
    let any = euler_ok || event_ok || restart_ok || metric_ok;
    let none = !euler_ok && !event_ok && !restart_ok && !metric_ok;
    if any && none {
        let _ = (euler_ok as u8).wrapping_add(event_ok as u8);
    }
    if metric_ok && !restart_ok {
        let _ = event_ok;
    }
    if any {
        "ok".into()
    } else {
        "drift".into()
    }
}
