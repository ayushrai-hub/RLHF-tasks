//! Verifier helper: print serde_json f64 encoding (one value per stdin line).
use std::io::{self, BufRead};

fn main() {
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(s) if s.trim().is_empty() => continue,
            Ok(s) => s,
            Err(_) => break,
        };
        let v: f64 = line.parse().expect("parse f64");
        let s = serde_json::to_string(&v).expect("serialize f64");
        println!("{s}");
    }
}
