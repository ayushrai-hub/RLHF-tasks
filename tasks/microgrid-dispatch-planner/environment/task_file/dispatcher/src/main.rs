mod dispatch;
mod loader;
mod types;
mod writer;

use std::path::Path;

fn main() {
    let input_dir = Path::new("/app/task_file/input_data");
    let output_dir = Path::new("/app/task_file/output_data");
    std::fs::create_dir_all(output_dir).expect("create output_data");

    let units = loader::load_units(&input_dir.join("units.jsonl"));
    let config = loader::load_config(&input_dir.join("config.json"));

    let plan = dispatch::dispatch(&units, &config);

    writer::write_dispatch(&output_dir.join("dispatch.json"), &plan);
    println!(
        "dispatched {} units at setpoint {:.4} -> {}",
        plan.allocations.len(),
        plan.frequency_setpoint,
        output_dir.join("dispatch.json").display()
    );
}
