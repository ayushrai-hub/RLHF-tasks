use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::io::{self, Read};

#[derive(Debug, Deserialize)]
struct RowRef {
    entity: String,
    path_key: String,
    uri_key: String,
    ref_key: String,
    marker: String,
    book_cell: String,
}

fn chain_hex(rows: &[RowRef]) -> String {
    let mut lines: Vec<String> = rows
        .iter()
        .map(|row| {
            format!(
                "{}:{}|{}|{}:{}:{}",
                row.entity, row.path_key, row.uri_key, row.ref_key, row.marker, row.book_cell
            )
        })
        .collect();
    lines.sort();
    let joined = lines.join("\n");
    let digest = Sha256::digest(joined.as_bytes());
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

fn main() {
    let mut payload = String::new();
    if io::stdin().read_to_string(&mut payload).is_err() {
        std::process::exit(1);
    }
    let rows: Vec<RowRef> = match serde_json::from_str(&payload) {
        Ok(v) => v,
        Err(_) => std::process::exit(1),
    };
    println!("{}", chain_hex(&rows));
}
