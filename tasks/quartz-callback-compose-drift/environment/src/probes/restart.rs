pub fn run() -> String {
    let y: f64 = std::env::var("TB_Y").unwrap().parse().unwrap();
    let y0: f64 = std::env::var("TB_Y0").unwrap().parse().unwrap();
    let tol: f64 = std::env::var("TB_TOL").unwrap().parse().unwrap();
    let target: f64 = std::env::var("TB_TARGET").unwrap_or_else(|_| "1.0".into()).parse().unwrap();
    format!("{}", crate::qz::n4::q4::restart_value(target, y, tol))
}
