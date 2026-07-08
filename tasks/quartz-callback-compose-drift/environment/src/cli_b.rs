fn main() {
    let mode = std::env::var("TB_PROBE").unwrap_or_default();
    let out = match mode.as_str() {
        "euler" => quartz_callback_compose_drift::probes::euler::run(),
        "event" => quartz_callback_compose_drift::probes::event::run(),
        "sort" => quartz_callback_compose_drift::probes::sort::run(),
        "restart" => quartz_callback_compose_drift::probes::restart::run(),
        "metric" => quartz_callback_compose_drift::probes::metric::run(),
        "summary" => quartz_callback_compose_drift::probes::summary::run(),
        "chain" => quartz_callback_compose_drift::probes::chain::run(),
        _ => "0".into(),
    };
    print!("{out}");
}
