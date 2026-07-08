mod args;
mod apply;
mod checks;
#[path = "../ops/cmd_rewind.rs"]
mod cmd_rewind;
#[path = "../ops/cmd_admit.rs"]
mod cmd_admit;
#[path = "../ops/cmd_bootstrap.rs"]
mod cmd_bootstrap;
#[path = "../ops/cmd_uplift.rs"]
mod cmd_uplift;
#[path = "../ops/cmd_flush.rs"]
mod cmd_flush;
#[path = "../carry/carry.rs"]
mod carry;
#[path = "../coil/coil.rs"]
mod coil;
#[path = "../ops/brief.rs"]
mod brief;
mod config;
mod driver;
mod errors;
#[path = "../fuse/fuse.rs"]
mod fuse;
mod io;
#[path = "../loom/loom.rs"]
mod loom;
#[path = "../mesh/mesh.rs"]
mod mesh;
mod model;
mod rebuild;
mod render;
#[path = "../ring/ring.rs"]
mod ring;
#[path = "../seal/seal.rs"]
mod seal;
mod stow;
#[path = "../prime/prime.rs"]
mod prime;
#[path = "../rift/rift.rs"]
mod rift;
#[path = "../span/span.rs"]
mod span;
#[path = "../vault/vault.rs"]
mod vault;
mod walk;

fn main() {
    if let Err(err) = driver::run() {
        eprintln!("{err}");
        std::process::exit(err.code);
    }
}
