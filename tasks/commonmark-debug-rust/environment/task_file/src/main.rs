use std::fs;
use std::process::ExitCode;

use commonmark::{json, render_inline};
use json::Json;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("usage: {} <cases.json>", args[0]);
        return ExitCode::from(2);
    }
    let text = match fs::read_to_string(&args[1]) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("failed to read {}: {e}", args[1]);
            return ExitCode::from(2);
        }
    };
    let cases = match json::parse(&text) {
        Ok(j) => j,
        Err(e) => {
            eprintln!("failed to parse cases JSON: {e}");
            return ExitCode::from(2);
        }
    };
    let cases = match cases.as_arr() {
        Some(c) => c,
        None => {
            eprintln!("cases file must be a JSON array");
            return ExitCode::from(2);
        }
    };
    let mut out_cases: Vec<Json> = Vec::with_capacity(cases.len());
    for case in cases {
        let id = case
            .get("id")
            .and_then(Json::as_str)
            .unwrap_or("")
            .to_string();
        let ops = case
            .get("ops")
            .and_then(Json::as_arr)
            .map(|v| v.to_vec())
            .unwrap_or_default();
        let results: Vec<Json> = ops.iter().map(run_op).collect();
        out_cases.push(json::collect(&[
            ("id", Json::Str(id)),
            ("results", Json::Arr(results)),
        ]));
    }
    println!("{}", json::serialize(&Json::Arr(out_cases)));
    ExitCode::SUCCESS
}

fn ok(op: &str, output: String) -> Json {
    json::collect(&[
        ("op", Json::Str(op.to_string())),
        ("output", Json::Str(output)),
        ("error", Json::Bool(false)),
    ])
}

fn err(op: &str) -> Json {
    json::collect(&[
        ("op", Json::Str(op.to_string())),
        ("output", Json::Str(String::new())),
        ("error", Json::Bool(true)),
    ])
}

fn run_op(op_json: &Json) -> Json {
    let op = op_json.get("op").and_then(Json::as_str).unwrap_or("");
    match op {
        "render" => {
            let text = op_json.get("text").and_then(Json::as_str).unwrap_or("");
            ok(op, render_inline(text))
        }
        other => err(other),
    }
}
