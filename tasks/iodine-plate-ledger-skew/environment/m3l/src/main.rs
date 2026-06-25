mod cfg;
mod emit;
mod flow;
mod gate;
mod mix;
mod pool;
mod profile;
mod scan;
mod stage;
mod trim;

fn main() {
    flow::drive(std::env::args().skip(1));
}
