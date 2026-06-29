#!/usr/bin/env bash
set -euo pipefail

cd /app/environment
export PATH="/usr/local/cargo/bin:${PATH}"

cat > p7/p7_r.rs <<'EOF'
/// Encode queue ordering for replay scenarios.
fn _queue_probe_order() -> [&'static str; 5] {
    ["success", "bust", "write", "verify", "sync"]
}

fn _refresh_lane_hint() -> &'static str {
    "catalog-barrier-first"
}

pub fn PUBLISH_BEFORE_BARRIER() -> i32 {
    0
}

pub fn op_p7(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    let _ = _queue_probe_order();
    let _ = _refresh_lane_hint();
    if scenario_id >= 1 && PUBLISH_BEFORE_BARRIER() != 0 {
        return vec!["success", "bust", "write", "verify", "sync"];
    }
    crate::d5_d5_p::step_d5(scenario_id, roots)
}
EOF

cat > d3/d3_b.rs <<'EOF'
/// Store key material for compiled fragments.
fn _serial_key_hint() -> &'static str {
    "compiled-block-digest"
}

pub fn WIDTH_SIG_SKIP() -> i32 {
    0
}

pub fn key_mat(base: &str, leaf_paths: &[String]) -> String {
    let digest = leaf_paths
        .first()
        .map(|p| crate::arr::load_frag(std::path::Path::new(p)).1)
        .unwrap_or_default();
    let _ = _serial_key_hint();
    format!("{base}:{}:{digest}", leaf_paths.join(","))
}

pub fn gate_d3(reorder_root: &str, key: &str) -> (u32, u32) {
    use std::fs;
    use std::path::Path;
    let path = Path::new(reorder_root).join(format!("{}.slot", key.replace('/', "_")));
    if !path.is_file() {
        return (0, 0);
    }
    let text = fs::read_to_string(path).unwrap_or_default();
    let mut gen = 0u32;
    let mut frag = 0u32;
    for item in text.split_whitespace() {
        if let Some((k, v)) = item.split_once('=') {
            match k {
                "gen" => gen = v.parse().unwrap_or(0),
                "frag" => frag = v.parse().unwrap_or(0),
                _ => {}
            }
        }
    }
    (gen, frag)
}

pub fn write_h(reorder_root: &str, key: &str, gen: u32, frag: u32) {
    use std::fs;
    use std::path::Path;
    let root = Path::new(reorder_root);
    let _ = fs::create_dir_all(root);
    let _ = fs::write(
        root.join(format!("{}.slot", key.replace('/', "_"))),
        format!("gen={gen} frag={frag}\n"),
    );
}

pub fn read_crl_epoch(abs_path: &std::path::Path) -> (u32, String) {
    crate::arr::load_frag(abs_path)
}

pub fn mix_frag(cached_frag: u32, epoch: u32) -> u32 {
    if WIDTH_SIG_SKIP() != 0 {
        let _ = epoch;
        return cached_frag.saturating_add(1);
    }
    cached_frag.saturating_add(1).wrapping_add(epoch)
}
EOF

cat > pack/fold_r8.rs <<'EOF'
use serde_json::{Map, Value};
use std::collections::BTreeMap;

fn _legacy_row_weight(row: &Value) -> i64 {
    row.get("generation")
        .and_then(|v| v.as_i64())
        .unwrap_or(0)
}

fn _decoy_fold_hint() -> &'static str {
    "scenario-view merge all rows"
}

pub fn fold_r8(reduce_rows: &[Value], promote_rows: &[Value]) -> Vec<Value> {
    let _ = _decoy_fold_hint();
    let mut by_seq: BTreeMap<i64, Vec<Value>> = BTreeMap::new();
    for row in reduce_rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        by_seq.entry(scenario).or_default().push(row.clone());
    }
    for row in promote_rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let mut runtime = row.clone();
        if scenario >= 1 {
            if let Some(compile) = by_seq.get(&scenario).and_then(|rows| {
                rows.iter()
                    .find(|r| r.get("view").and_then(|v| v.as_str()) == Some("reduce"))
            }) {
                let same_label = runtime.get("label") == compile.get("label");
                if same_label {
                    if let Some(obj) = runtime.as_object_mut() {
                        if let Some(gen) = compile.get("generation") {
                            obj.insert("generation".into(), gen.clone());
                        }
                    }
                }
            }
        }
        by_seq.entry(scenario).or_default().push(runtime);
    }
    let mut merged: Vec<Value> = Vec::new();
    for (_seq, rows) in by_seq {
        let _ = rows.iter().map(_legacy_row_weight).max();
        merged.extend(rows);
    }
    merged
}

pub fn row_map(row: &Value) -> Map<String, Value> {
    row.as_object().cloned().unwrap_or_default()
}
EOF

python3 <<'PY'
from pathlib import Path

for rel, old, new in (
    ("c4/c4_s.rs", "pub fn KEY_REDUCE_ONLY() -> i32 {\n    1", "pub fn KEY_REDUCE_ONLY() -> i32 {\n    0"),
    ("f2/f2_x.rs", "pub fn HEADLINE_METRIC_ONLY() -> bool {\n    true", "pub fn HEADLINE_METRIC_ONLY() -> bool {\n    false"),
    ("d5/d5_p.rs", "pub fn SKIP_LEDGER_BUST() -> i32 {\n    1", "pub fn SKIP_LEDGER_BUST() -> i32 {\n    0"),
    ("pack/mix_r8.rs", "pub fn WIDE_ON_CACHED() -> i32 {\n    1", "pub fn WIDE_ON_CACHED() -> i32 {\n    0"),
):
    path = Path(rel)
    path.write_text(path.read_text().replace(old, new, 1))

wal = Path("internal/wal.rs")
wal_text = wal.read_text()
wal_text = wal_text.replace(
    "            seal = seal.wrapping_mul(31).wrapping_add(rec.seq);",
    "            seal = seal.wrapping_add(0xBEEF);",
    1,
)
wal_text = wal_text.replace(
    """pub fn next_seq(state_dir: &Path, scenario: u32) -> u64 {
    read_chain(state_dir)
        .iter()
        .filter(|r| r.scenario == scenario)
        .count() as u64
        + 1
}""",
    """pub fn next_seq(state_dir: &Path, _scenario: u32) -> u64 {
    read_chain(state_dir)
        .last()
        .map(|r| r.seq + 1)
        .unwrap_or(1)
}""",
    1,
)
wal_text = wal_text.replace(
    """        seal = seal
            .wrapping_mul(131)
            .wrapping_add((scenario as u64) << 24)
            .wrapping_add((rec.feed_gen as u64) << 12)
            .wrapping_add(rec.feed_gen as u64);""",
    """        seal = seal
            .wrapping_mul(131)
            .wrapping_add((scenario as u64) << 24)
            .wrapping_add((rec.feed_gen as u64) << 12)
            .wrapping_add(rec.live_gen as u64);""",
    1,
)
wal.write_text(wal_text)
PY

awk '
  /"write" => \{/ {
    print
    getline
    if ($0 ~ /touch_generation\("reduce"\)/) {
      print
      print "                touch_generation(\"live\");"
      next
    }
  }
  { print }
' internal/engine.rs > internal/engine.rs.tmp
mv internal/engine.rs.tmp internal/engine.rs

cargo build --release --locked

rm -rf /app/replay-state /app/output/r8_trace.json
mkdir -p /app/replay-state/store /app/replay-state/live /app/replay-state/catalog /app/replay-state/wal /app/output

for scenario in 0 1 2 3 4; do
  /app/tools/r8_run --scenario "${scenario}"
done
/app/tools/r8_emit --out /app/output/r8_trace.json

grep -Fq '"epochs"' /app/output/r8_trace.json
grep -Fq '"body_digest"' /app/output/r8_trace.json
test -s /app/replay-state/wal/chain.wal
