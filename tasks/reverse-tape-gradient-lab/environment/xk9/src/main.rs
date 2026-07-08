
mod backward;
mod forward;
mod ops;

use serde_json::Value;
use std::io::{self, Read, Write};

fn main() {
    let mut buf = String::new();
    io::stdin().read_to_string(&mut buf).expect("stdin");
    let input: Value = serde_json::from_str(&buf).expect("json");
    let mode = input.get("mode").and_then(|v| v.as_str()).unwrap_or("");
    let out = match mode {
        "forward" => forward::run_forward(&input),
        "backward" => backward::run_backward(&input),
        "broadcast" => {
            let data: Vec<f64> = input.get("data").and_then(|v| v.as_array()).map(|a| a.iter().map(ops::num).collect()).unwrap_or_default();
            let from: Vec<usize> = input.get("from").and_then(|v| v.as_array()).map(|a| a.iter().filter_map(|x| x.as_u64().map(|n| n as usize)).collect()).unwrap_or_default();
            let to: Vec<usize> = input.get("to").and_then(|v| v.as_array()).map(|a| a.iter().filter_map(|x| x.as_u64().map(|n| n as usize)).collect()).unwrap_or_default();
            serde_json::json!({"out": ops::broadcast_to(&data, &from, &to)})
        }
        _ => serde_json::json!({"error": "unknown mode"}),
    };
    let text = serde_json::to_string(&out).expect("encode");
    io::stdout().write_all(text.as_bytes()).expect("stdout");
}
