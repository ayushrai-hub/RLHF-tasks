mod args;
#[path = "../braid/braid.rs"]
mod braid;
#[path = "check/check.rs"]
mod check;
mod cmd_normalize;
mod cmd_reload;
mod codec;
mod cold_stage;
mod driver;
#[path = "emit/emit.rs"]
mod emit;
mod emit_stage;
mod errors;
#[path = "../grain/grain.rs"]
mod grain;
mod io;
#[path = "../knot/knot.rs"]
mod knot;
#[path = "../latch/latch.rs"]
mod latch;
#[path = "../lens/lens.rs"]
mod lens;
mod model;
mod parse_stage;
#[path = "../pivot/pivot.rs"]
mod pivot;
mod replay;
mod report_stage;
#[path = "render/render.rs"]
mod render;
mod warm_stage;
#[path = "walk/walk.rs"]
mod walk;

fn main() {
    if let Err(err) = driver::run() {
        eprintln!("{err}");
        std::process::exit(err.code as i32);
    }
}
