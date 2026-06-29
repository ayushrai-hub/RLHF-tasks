use nfa_parse::parse_flow;
use nfa_aggregate::aggregate_flows;
use nfa_classify::classify_flows;
use nfa_emit::emit_report;

fn main() {
    let trace_path = std::env::args().nth(1).expect("Usage: nfa_verify <trace_file>");
    let output_path = std::env::args().nth(2).unwrap_or("/tmp/nfa_report.json".to_string());
    
    let content = std::fs::read_to_string(&trace_path).expect("Failed to read trace");
    let lines: Vec<&str> = content.lines().collect();
    
    let mut records = Vec::new();
    for line in lines {
        if let Some(record) = parse_flow(line) {
            records.push(record);
        }
    }
    
    println!("Parsed {} flow records", records.len());
    
    let aggregates = aggregate_flows(&records);
    println!("Generated {} protocol aggregates", aggregates.len());
    
    let classifications = classify_flows(&records, &aggregates);
    println!("Classified {} flow categories", classifications.len());
    
    if let Err(e) = emit_report(&aggregates, &classifications, &output_path) {
        eprintln!("Failed to emit report: {}", e);
        std::process::exit(1);
    }
    
    println!("Report emitted to {}", output_path);
}
