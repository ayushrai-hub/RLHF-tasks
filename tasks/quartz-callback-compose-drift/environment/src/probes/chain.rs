use crate::chain_exec;
use crate::hooks;
use std::path::Path;

pub fn run() -> String {
    let y_prev: f64 = std::env::var("TB_Y_PREV").unwrap().parse().unwrap();
    let y_post: f64 = std::env::var("TB_Y").unwrap().parse().unwrap();
    let step: u32 = std::env::var("TB_STEP").unwrap_or_else(|_| "0".into()).parse().unwrap();
    let y0: f64 = std::env::var("TB_Y0").unwrap_or_else(|_| "0".into()).parse().unwrap();
    let order = std::env::var("TB_ORDER").unwrap_or_default();
    let restart_applied = std::env::var("TB_RESTART").unwrap_or_else(|_| "0".into()) == "1";
    let restart_y: f64 = std::env::var("TB_RESTART_Y")
        .unwrap_or_else(|_| "1.0".into())
        .parse()
        .unwrap();

    let hook_map = hooks::load_hooks(Path::new("/app/data/hooks.tbl")).expect("hooks");
    let final_y = chain_exec::chain_step(
        y_prev,
        y_post,
        restart_applied,
        restart_y,
        &order,
        &hook_map,
        step,
        y0,
    );
    format!("{final_y:.12}")
}
