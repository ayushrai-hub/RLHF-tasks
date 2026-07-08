use std::fs;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut output = "/app/output/repair_plan.json".to_string();
    let mut mission_id = "unknown".to_string();
    let mut i = 1;
    while i + 1 < args.len() {
        if args[i] == "--output" { output = args[i + 1].clone(); }
        if args[i] == "--mission-id" { mission_id = args[i + 1].clone(); }
        i += 2;
    }
    let _ = fs::create_dir_all("/app/output");
    let placeholder = format!("{{\"generated_by\":\"glassreef-planner\",\"mission_id\":\"{}\",\"repair_windows\":[],\"unreachable_stations\":[],\"rejected_repairs\":[],\"plan_digest\":\"0000000000000000\"}}\n", mission_id);
    fs::write(output, placeholder).expect("write placeholder plan");
}
