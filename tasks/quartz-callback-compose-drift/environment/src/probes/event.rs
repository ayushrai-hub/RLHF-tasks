pub fn run() -> String {
    let y_prev: f64 = std::env::var("TB_PREV").unwrap().parse().unwrap();
    let y_curr: f64 = std::env::var("TB_CURR").unwrap().parse().unwrap();
    let thresh: f64 = std::env::var("TB_THRESH").unwrap().parse().unwrap();
    let step: u32 = std::env::var("TB_STEP").unwrap_or_else(|_| "1".into()).parse().unwrap();
    let y0: f64 = std::env::var("TB_Y0").unwrap_or_else(|_| "0".into()).parse().unwrap();
    if crate::qz::n3::q3::hook_fires(y_prev, y_curr, thresh, step, y0) {
        "1".into()
    } else {
        "0".into()
    }
}
