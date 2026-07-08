pub fn run() -> String {
    let euler_ok = std::env::var("TB_EULER_OK").unwrap() == "1";
    let event_ok = std::env::var("TB_EVENT_OK").unwrap() == "1";
    let restart_ok = std::env::var("TB_RESTART_OK").unwrap() == "1";
    let metric_ok = std::env::var("TB_METRIC_OK").unwrap() == "1";
    crate::sx::n1::x1::compose_status(
        euler_ok,
        event_ok,
        restart_ok,
        metric_ok,
    )
}
