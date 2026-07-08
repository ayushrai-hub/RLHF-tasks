fn main() {
    if let Err(e) = quartz_callback_compose_drift::harness::run(std::path::Path::new("/app")) {
        eprintln!("harness failed: {e}");
        std::process::exit(1);
    }
}
