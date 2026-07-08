pub fn run() -> String {
    let y_prev: f64 = std::env::var("TB_Y_PREV").unwrap().parse().unwrap();
    let y_curr: f64 = std::env::var("TB_Y_CURR").unwrap().parse().unwrap();
    let dt: f64 = std::env::var("TB_DT").unwrap().parse().unwrap();
    let scale: f64 = std::env::var("TB_SCALE").unwrap_or_else(|_| "1.0".into()).parse().unwrap();
    format!(
        "{}",
        crate::qz::n5::q5::accumulate_step(0.0, y_prev, y_curr, dt, scale)
    )
}
