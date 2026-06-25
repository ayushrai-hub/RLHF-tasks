#!/usr/bin/env bash
set -euo pipefail

cd /app/environment

sed -i 's/u32::from_be_bytes/u32::from_le_bytes/g' /app/m3l/src/scan.rs
sed -i 's/u16::from_be_bytes/u16::from_le_bytes/g' /app/m3l/src/scan.rs

cat > /app/m3l/src/mix.rs <<'EOF'
pub fn verify(body: &[u8], tail: &[u8]) -> bool {
    if tail.len() < 4 {
        return false;
    }
    let on_disk = u32::from_le_bytes([tail[0], tail[1], tail[2], tail[3]]);
    compute(body) == on_disk
}

pub fn compute(body: &[u8]) -> u32 {
    crc32fast::hash(body)
}
EOF

sed -i 's/rows.sort_by(|a, b| b.seq.cmp(\&a.seq));/rows.sort_by_key(|r| r.seq);/' /app/m3l/src/stage.rs

python3 <<'PY'
from pathlib import Path
path = Path("/app/m3l/src/pool.rs")
text = path.read_text()
block = """        let mut names: Vec<String> = rows.iter().map(|r| r.name.clone()).collect();
        stage::rotate_names(&mut names);
        for (row, name) in rows.iter_mut().zip(names.iter()) {
            row.name = name.clone();
        }
"""
if block in text:
    path.write_text(text.replace(block, ""))
PY

cat > /app/r8k/src/lane.rs <<'EOF'
pub fn classify_chain(applied: u32, total: u32, has_rows: bool) -> String {
    if !has_rows {
        return "empty".into();
    }
    if applied == total {
        return "valid".into();
    }
    "broken".into()
}

pub fn resolve_head(cached: u32, frontier: u32, _gen: &str, _records_applied: u32) -> u32 {
    let _ = cached;
    frontier
}
EOF

timeout 300 cargo build --release
/app/target/release/iodine-plate plate --ledger tab_x --output /app/output/iodine_plate_report.json
