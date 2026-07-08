pub fn run() -> String {
    let y: f64 = std::env::var("TB_Y").unwrap().parse().unwrap();
    let dt: f64 = std::env::var("TB_DT").unwrap().parse().unwrap();
    format!("{}", crate::qz::n2::q2::euler_forward(y, dt))
}
