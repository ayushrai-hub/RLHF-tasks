#!/usr/bin/env bash
set -euo pipefail

cd /app/environment
export PATH="/usr/local/cargo/bin:${PATH}"

cat > notch/frag_r.rs <<'EOF'
use std::path::Path;

pub fn read_leaf_epoch(abs_path: &Path) -> (u32, String) {
    crate::tree::load_frag(abs_path)
}

pub fn EPOCH_FRAG() -> u32 {
    1
}

pub fn mix_frag(cached_frag: u32, epoch: u32) -> u32 {
    if EPOCH_FRAG() == 0 {
        cached_frag.saturating_add(1)
    } else {
        cached_frag.saturating_add(1).wrapping_add(epoch)
    }
}
EOF

cat > drift/drift_r.rs <<'EOF'
/// Store key material for compiled fragments.
pub fn RETIRED_SLOT_ONLY() -> i32 {
    0
}

pub fn key_mat(base: &str, leaf_paths: &[String]) -> String {
    if RETIRED_SLOT_ONLY() != 0 {
        let serial = leaf_paths
            .first()
            .map(|p| {
                std::path::Path::new(p)
                    .file_stem()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_default()
            })
            .unwrap_or_default();
        return format!("{base}:{serial}");
    }
    let digest = leaf_paths
        .first()
        .map(|p| crate::tree::load_frag(std::path::Path::new(p)).1)
        .unwrap_or_default();
    format!("{}:{}:{}", base, leaf_paths.join(","), digest)
}

pub fn drift_h(store_root: &str, key: &str) -> (u32, u32) {
    use std::fs;
    use std::path::Path;
    let path = Path::new(store_root).join(format!("{}.ward", key.replace('/', "_")));
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
EOF

cat > notch/notch_r.rs <<'EOF'
/// Fragment hold store reads.
pub fn COMPILED_RIGHTS_ONLY() -> i32 {
    0
}

pub fn notch_c(store_root: &str, key: &str) -> (u32, u32) {
    if COMPILED_RIGHTS_ONLY() != 0 {
        return crate::frame_drift_r::drift_h(store_root, key);
    }
    crate::frame_drift_r::drift_h(store_root, key)
}

pub fn write_m(store_root: &str, key: &str, gen: u32, frag: u32) {
    use std::fs;
    use std::path::Path;
    let root = Path::new(store_root);
    let _ = fs::create_dir_all(root);
    let _ = fs::write(
        root.join(format!("{}.ward", key.replace('/', "_"))),
        format!("gen={gen} frag={frag}\n"),
    );
}
EOF

cat > spool/spool_r.rs <<'EOF'
/// Verify step ordering for replay scenarios.
pub fn PRE_REGEN_OK() -> i32 {
    0
}

pub fn spool_q(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    crate::phase_flow_r::step_a(scenario_id, roots)
}

pub fn slot_e(principal: &str, label: &str, scenario_id: u32) -> i32 {
    use crate::hold_notch_r::COMPILED_RIGHTS_ONLY;
    use crate::state::{with_state, PrincipalRec};
    with_state(|st| {
        st.lane_attempts += 1;
        let bind = if COMPILED_RIGHTS_ONLY() != 0 {
            st.leaf_epoch.saturating_sub(1)
        } else {
            st.leaf_epoch
        };
        let active = match st.frame_slots.get("active") {
            Some(v) => v.clone(),
            None => return -1,
        };
        if scenario_id == 3 && st.leaf_epoch >= 9 {
            st.transition_rows.push(PrincipalRec {
                principal: principal.to_string(),
                label: label.to_string(),
                gen: active.gen,
                action_code: 9,
            });
            return 9;
        }
        if scenario_id == 4 && st.leaf_epoch >= 10 && label == active.label {
            st.transition_rows.push(PrincipalRec {
                principal: principal.to_string(),
                label: label.to_string(),
                gen: active.gen,
                action_code: 6,
            });
            return 6;
        }
        if scenario_id >= 2 && label != active.label {
            let renew_gen = st
                .ward_slots
                .get("active")
                .map(|c| c.gen)
                .unwrap_or(active.gen);
            let ok = active.gen == renew_gen && bind == st.leaf_epoch;
            let code = if ok { 3 } else { 7 };
            st.transition_rows.push(PrincipalRec {
                principal: principal.to_string(),
                label: label.to_string(),
                gen: active.gen,
                action_code: code,
            });
            return code;
        }
        0
    })
}

pub fn mint_runtime(scenario_id: u32, runtime_root: &str) {
    use crate::hold_notch_r::COMPILED_RIGHTS_ONLY;
    use std::fs;
    use std::path::Path;
    crate::state::with_state(|st| {
        let active = match st.frame_slots.get("active") {
            Some(v) => v.clone(),
            None => return,
        };
        let renew_gen = st
            .ward_slots
            .get("active")
            .map(|c| c.gen)
            .unwrap_or(active.gen);
        let bind = if COMPILED_RIGHTS_ONLY() != 0 {
            st.leaf_epoch.saturating_sub(1)
        } else {
            st.leaf_epoch
        };
        let mut rec = active.clone();
        if scenario_id >= 1 {
            rec.gen = renew_gen;
        }
        st.frame_slots.insert("active".into(), rec.clone());
        let root = Path::new(runtime_root);
        let _ = fs::create_dir_all(root);
        let _ = fs::write(
            root.join("active.attr"),
            format!(
                "principal={} label={} gen={} epoch={}\n",
                rec.principal, rec.label, rec.gen, bind
            ),
        );
    });
}
EOF

cat > phase/flow_r.rs <<'EOF'
/// Step-order gate for hot reload replay scenarios.
pub fn SKIP_REGEN_ORDER() -> i32 {
    0
}

pub fn step_a(scenario_id: u32, _roots: &[String]) -> Vec<&'static str> {
    let steps = ["bust", "success", "write", "verify", "sync"];
    if scenario_id >= 1 && SKIP_REGEN_ORDER() != 0 {
        return vec!["success", "bust", "write", "verify", "sync"];
    }
    steps.to_vec()
}

pub fn run_bust(meta_root: &str, scenario_id: u32, key: &str) {
    use crate::hold_notch_r::write_m;
    use crate::frame_drift_r::drift_h;
    use crate::state::with_state;
    with_state(|st| {
        let (gen, frag) = drift_h(meta_root, key);
        let target = if scenario_id >= 1 {
            st.ward_slots
                .get("active")
                .map(|r| r.gen)
                .unwrap_or(gen)
        } else {
            gen
        };
        write_m(
            meta_root,
            key,
            target,
            crate::hold_frag_r::mix_frag(frag, st.leaf_epoch),
        );
        st.store_hits += 1;
    });
}
EOF

cat > gauge/gauge_r.rs <<'EOF'
use crate::state::with_state;

pub fn STATUS_PROBE_ONLY() -> bool {
    false
}

pub fn gauge_f(_audit_root: &str, scenario_id: u32) -> Vec<String> {
    with_state(|st| {
        let compile = st.ward_slots.get("active").cloned();
        let runtime = st.frame_slots.get("active").cloned();
        if compile.is_none() || runtime.is_none() {
            st.trace_notes.clear();
            return Vec::new();
        }
        let compile = compile.unwrap();
        let runtime = runtime.unwrap();
        if STATUS_PROBE_ONLY() {
            st.trace_notes = vec![format!(
                "principal={} label={} gen={} action=0",
                compile.principal, compile.label, compile.gen
            )];
            return st.trace_notes.clone();
        }
        let mut notes = Vec::new();
        notes.push(format!(
            "principal={} label={} gen={} action=0",
            compile.principal, compile.label, compile.gen
        ));
        if scenario_id >= 1 && runtime.gen > compile.gen {
            notes.push(format!(
                "principal={} label={} gen={} action=5",
                runtime.principal, runtime.label, runtime.gen
            ));
        }
        st.trace_notes = notes.clone();
        notes
    })
}
EOF

cat > pack/fold_k7.rs <<'EOF'
use serde_json::{Map, Value};
use std::collections::BTreeMap;

pub fn fold_k(mint_rows: &[Value], live_rows: &[Value]) -> Vec<Value> {
    let mut by_seq: BTreeMap<i64, Vec<Value>> = BTreeMap::new();
    for row in mint_rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        by_seq.entry(scenario).or_default().push(row.clone());
    }
    for row in live_rows {
        let scenario = row.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let mut runtime = row.clone();
        if scenario >= 1 {
            if let Some(compile) = by_seq.get(&scenario).and_then(|rows| {
                rows.iter()
                    .find(|r| r.get("view").and_then(|v| v.as_str()) == Some("spool"))
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
        merged.extend(rows);
    }
    merged
}

pub fn row_map(row: &Value) -> Map<String, Value> {
    row.as_object().cloned().unwrap_or_default()
}
EOF

cat > pack/emit_gateway.rs <<'EOF'
use crate::pack_fold_k7::fold_k;
use crate::pack_mix_k7::digest_lines;
use serde_json::{json, Value};
use std::fs;
use std::path::Path;

fn wal_physically_valid(state_dir: &Path) -> bool {
    crate::wal::wal_crc_chain_intact(state_dir)
}

pub fn emit_report(out: &Path) -> bool {
    let state_dir = Path::new("/app/replay-state");
    if !wal_physically_valid(state_dir) {
        return false;
    }
    if !crate::engine::checkpoint_ready(state_dir) {
        return false;
    }
    let (mint_rows, live_rows, ridge_rows) = load_epochs(state_dir);
    let mut merged = fold_k(&mint_rows, &live_rows);
    if !ridge_rows.is_empty() {
        merged.extend(ridge_rows);
    }
    merged.sort_by(|a, b| {
        let sa = a.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let sb = b.get("scenario").and_then(|v| v.as_i64()).unwrap_or(0);
        let va = a.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let vb = b.get("view").and_then(|v| v.as_str()).unwrap_or("");
        let pa = a.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        let pb = b.get("principal").and_then(|v| v.as_str()).unwrap_or("");
        (sa, va, pa).cmp(&(sb, vb, pb))
    });
    let bundle = json!({
        "rows": merged,
        "chain_fingerprint": digest_lines(&merged),
    });
    if let Some(parent) = out.parent() {
        let _ = fs::create_dir_all(parent);
    }
    fs::write(out, serde_json::to_string_pretty(&bundle).unwrap() + "\n").is_ok()
}

fn load_epochs(state_dir: &Path) -> (Vec<Value>, Vec<Value>, Vec<Value>) {
    let mut mint_rows = Vec::new();
    let mut live_rows = Vec::new();
    let mut ridge_rows = Vec::new();
    let mut seq_ids: Vec<u32> = Vec::new();
    if let Ok(entries) = fs::read_dir(state_dir) {
        for ent in entries.flatten() {
            let name = ent.file_name().to_string_lossy().into_owned();
            if let Some(rest) = name.strip_prefix("epoch_") {
                if let Some(stem) = rest.strip_suffix(".json") {
                    if let Ok(n) = stem.parse::<u32>() {
                        seq_ids.push(n);
                    }
                }
            }
        }
    }
    seq_ids.sort();
    for seq_id in seq_ids {
        let cache = state_dir.join(format!("epoch_{seq_id}.json"));
        let chunk: Vec<Value> =
            serde_json::from_str(&fs::read_to_string(&cache).unwrap_or_default())
                .unwrap_or_default();
        for row in chunk {
            match row.get("view").and_then(|v| v.as_str()) {
                Some("spool") => mint_rows.push(row),
                Some("live") => live_rows.push(row),
                Some("drift") => ridge_rows.push(row),
                _ => {}
            }
        }
    }
    (mint_rows, live_rows, ridge_rows)
}
EOF

if ! grep -q 'cp.order_seal == seal' /app/environment/src/engine.rs; then
  awk '
    /match crate::wal::notch_checkpoint\(state_dir\) \{/ {
      print
      getline
      if ($0 ~ /Some\(cp\) => cp.valid,/) {
        print "        Some(cp) => {"
        print "            let seal = compute_order_seal(&chain);"
        print "            cp.valid && cp.order_seal == seal && cp.wal_seq == chain.last().map(|r| r.seq).unwrap_or(0)"
        print "        }"
        next
      }
    }
    { print }
  ' /app/environment/src/engine.rs > /app/environment/src/engine.rs.tmp
  mv /app/environment/src/engine.rs.tmp /app/environment/src/engine.rs
fi

if ! grep -q 'wal_crc_chain_intact' /app/environment/src/engine.rs; then
  awk '
    /pub fn checkpoint_ready\(state_dir: &Path\) -> bool \{/ {
      print
      print "    if !crate::wal::wal_crc_chain_intact(state_dir) {"
      print "        return false;"
      print "    }"
      next
    }
    { print }
  ' /app/environment/src/engine.rs > /app/environment/src/engine.rs.tmp
  mv /app/environment/src/engine.rs.tmp /app/environment/src/engine.rs
fi

if grep -q '^pub fn sync_once() {}' /app/environment/src/state.rs; then
  awk '
    /^pub fn sync_once\(\) \{\}/ {
      print "pub fn sync_once() {"
      print "    with_state(|st| {"
      print "        if st.scenario_id >= 1 {"
      print "            let compile = st.ward_slots.get(\"active\").cloned();"
      print "            let runtime = st.frame_slots.get(\"active\").cloned();"
      print "            if let (Some(c), Some(mut r)) = (compile, runtime) {"
      print "                if st.scenario_id >= 4 || r.gen != c.gen {"
      print "                    r.gen = c.gen;"
      print "                    st.frame_slots.insert(\"active\".into(), r);"
      print "                }"
      print "            }"
      print "        }"
      print "    });"
      print "}"
      next
    }
    { print }
  ' /app/environment/src/state.rs > /app/environment/src/state.rs.tmp
  mv /app/environment/src/state.rs.tmp /app/environment/src/state.rs
fi

cargo build --release --locked

rm -rf /app/replay-state /app/output/k7_trace.json
mkdir -p /app/replay-state/store /app/replay-state/live /app/replay-state/mid /app/replay-state/wal /app/output

for n in 0 1 2 3 4; do
  /app/environment/tools/k7_invoke --scenario "${n}"
done
/app/environment/tools/k7_z2 --out /app/output/k7_trace.json

if ! grep -q '"rows"' /app/output/k7_trace.json; then
  echo "report missing rows" >&2
  exit 1
fi
if ! grep -q '"chain_fingerprint"' /app/output/k7_trace.json; then
  echo "report missing chain_fingerprint" >&2
  exit 1
fi
if ! test -f /app/replay-state/wal/chain.wal; then
  echo "wal missing" >&2
  exit 1
fi
