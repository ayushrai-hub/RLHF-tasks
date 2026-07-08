use crate::notch_gateway;
use crate::frame_drift_r::{key_mat, drift_h};
use crate::hold_notch_r::write_m;
use crate::gauge_gateway;
use crate::phase_gateway;
use crate::phase_shadow_flow;
use crate::spool_gateway;
use crate::state::{gate_state, sync_once, PrincipalRec, ReplayState};
use crate::tree::{active_slot, load_frag, load_tree};
use crate::wal::{
    append_record, compute_order_seal, next_seq, phases_valid, notch_chain, write_checkpoint,
    Checkpoint, WalRecord,
};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub const WRITE_GEN_DELTA: u32 = 1;

fn principal_row(scenario_id: u32, view: &str, rec: &PrincipalRec) -> Value {
    json!({
        "scenario": scenario_id,
        "view": view,
        "principal": rec.principal,
        "label": rec.label,
        "generation": rec.gen,
        "action_code": rec.action_code,
    })
}

fn active_view_rows(scenario_id: u32, view: &str, slots: &HashMap<String, PrincipalRec>) -> Vec<Value> {
    let mut rows = Vec::new();
    for (name, rec) in slots.iter() {
        if name != "active" && scenario_id >= 1 {
            continue;
        }
        rows.push(principal_row(scenario_id, view, rec));
    }
    rows
}

fn ridge_rows(scenario_id: u32) -> Vec<Value> {
    crate::state::with_state(|st| {
        st.trace_notes
            .iter()
            .map(|note| {
                let (principal, label, gen, action) = crate::lens_inspect_a::inspect_row(note);
                json!({
                    "scenario": scenario_id,
                    "view": "drift",
                    "principal": principal,
                    "label": label,
                    "generation": gen,
                    "action_code": action,
                })
            })
            .collect()
    })
}

fn transition_rows(scenario_id: u32) -> Vec<Value> {
    crate::state::with_state(|st| {
        st.transition_rows
            .iter()
            .map(|rec| principal_row(scenario_id, "live", rec))
            .collect()
    })
}

fn wal_append(state_dir: &Path, scenario: u32, phase: &str) {
    let (ward_gen, frame_gen) = crate::state::with_state(|st| {
        (
            st.ward_slots
                .get("active")
                .map(|s| s.gen)
                .unwrap_or(0),
            st.frame_slots
                .get("active")
                .map(|s| s.gen)
                .unwrap_or(0),
        )
    });
    let seq = next_seq(state_dir);
    let rec = WalRecord {
        scenario,
        phase: phase.to_string(),
        ward_gen,
        frame_gen,
        seq,
    };
    let _ = append_record(state_dir, rec);
}

fn touch_generation(view: &str) {
    crate::state::with_state(|st| {
        let table = if view == "spool" {
            &mut st.ward_slots
        } else {
            &mut st.frame_slots
        };
        if let Some(rec) = table.get_mut("active") {
            rec.gen = rec.gen.saturating_add(WRITE_GEN_DELTA);
        }
    });
}

fn sync_store_from_abs(case: &Path, meta_root: &Path, scenario_id: u32) {
    let abs_path = case.join("i0.frag");
    let (epoch, digest) = load_frag(&abs_path);
    let compile_active = active_slot(&load_tree(&case.join("a0.tree"))).unwrap_or(PrincipalRec {
        principal: "svc1".into(),
        label: "ROOT".into(),
        gen: 0,
        action_code: 0,
    });
    let key = key_mat("base", &[abs_path.to_string_lossy().into_owned()]);
    let _ = crate::hold_notch_r::notch_c(&meta_root.to_string_lossy(), &key);
    let (cached_gen, cached_frag) = drift_h(&meta_root.to_string_lossy(), &key);
    let target_gen = compile_active.gen;
    let frag = crate::hold_frag_r::mix_frag(cached_frag, epoch);
    write_m(
        &meta_root.to_string_lossy(),
        &key,
        target_gen,
        frag,
    );
    crate::state::with_state(|st| {
        st.leaf_epoch = epoch;
        st.abs_digest = digest;
        let mut compile = compile_active.clone();
        compile.gen = target_gen;
        st.ward_slots.insert("active".into(), compile);
    });
}

pub fn replay_scenario(scenario_id: u32, state_dir: &Path) -> Vec<Value> {
    let case = PathBuf::from(format!("/app/cases/seq/s{scenario_id}"));
    let front_raw = load_tree(&case.join("a0.tree"));
    let mid_raw = load_tree(&case.join("b0.tree"));
    let (epoch, digest) = load_frag(&case.join("i0.frag"));

    let state = ReplayState {
        scenario_id,
        leaf_epoch: epoch,
        abs_digest: digest,
        ward_slots: front_raw,
        frame_slots: mid_raw,
        ..Default::default()
    };
    gate_state(state);

    let meta_root = state_dir.join("store");
    let runtime_root = state_dir.join("live");
    let prism_root = state_dir.join("drift");
    for path in [&meta_root, &runtime_root, &prism_root] {
        let _ = fs::create_dir_all(path);
    }

    sync_store_from_abs(&case, &meta_root, scenario_id);

    let roots = vec![
        meta_root.to_string_lossy().into_owned(),
        runtime_root.to_string_lossy().into_owned(),
        prism_root.to_string_lossy().into_owned(),
    ];

    let phase_list = phase_gateway::phase_order(scenario_id, &roots);
    let _ = phase_shadow_flow::log_steps(
        scenario_id,
        &phase_list.iter().copied().collect::<Vec<_>>(),
        &state_dir.join("phase-log"),
    );

    let issuer_paths = vec![case.join("i0.frag").to_string_lossy().into_owned()];
    let key = key_mat("base", &issuer_paths);

    for phase in phase_list {
        wal_append(state_dir, scenario_id, phase);
        match phase {
            "bust" => phase_gateway::run_bust(&meta_root.to_string_lossy(), scenario_id, &key),
            "success" => phase_gateway::report_success(state_dir, scenario_id),
            "write" => {
                touch_generation("spool");
                touch_generation("drift");
            }
            "verify" => gauge_gateway::run_mirror(&prism_root.to_string_lossy(), scenario_id),
            "sync" => {
                spool_gateway::run_lane(&runtime_root.to_string_lossy(), scenario_id);
                sync_once();
            }
            _ => {}
        }
    }

    let chain = notch_chain(state_dir);
    let order_seal = compute_order_seal(&chain);
    let phase_ok = phases_valid(&chain);

    let cp = Checkpoint {
        last_scenario: scenario_id,
        wal_seq: chain.last().map(|r| r.seq).unwrap_or(0),
        order_seal,
        valid: phase_ok,
    };
    let _ = write_checkpoint(state_dir, &cp);

    let metrics = json!({
        "store_hits": crate::state::with_state(|st| st.store_hits),
        "lane_attempts": crate::ward_shadow_spool::count_attempts(state_dir),
        "leaf_epoch": notch_gateway::gateway_epoch(&case.to_string_lossy()),
    });
    let _ = fs::write(
        state_dir.join("last_metrics.json"),
        serde_json::to_string(&metrics).unwrap(),
    );

    let (ward_slots, frame_slots) = crate::state::with_state(|st| {
        (st.ward_slots.clone(), st.frame_slots.clone())
    });
    let mut rows = active_view_rows(scenario_id, "spool", &ward_slots);
    rows.extend(active_view_rows(scenario_id, "live", &frame_slots));
    rows.extend(ridge_rows(scenario_id));
    rows.extend(transition_rows(scenario_id));
    rows
}

pub fn recover_from_wal(state_dir: &Path) -> bool {
    let chain = notch_chain(state_dir);
    if chain.is_empty() {
        return false;
    }
    let seal = compute_order_seal(&chain);
    let phase_ok = phases_valid(&chain);
    let last_scenario = chain.iter().map(|r| r.scenario).max().unwrap_or(0);
    let cp = Checkpoint {
        last_scenario,
        wal_seq: chain.last().map(|r| r.seq).unwrap_or(0),
        order_seal: seal,
        valid: phase_ok,
    };
    write_checkpoint(state_dir, &cp).is_ok() && phase_ok
}

pub fn checkpoint_ready(state_dir: &Path) -> bool {
    if !crate::wal::wal_crc_chain_intact(state_dir) {
        return false;
    }
    let chain = notch_chain(state_dir);
    if !phases_valid(&chain) {
        return false;
    }
    match crate::wal::notch_checkpoint(state_dir) {
        Some(cp) => cp.valid,
        None => false,
    }
}

pub fn active_from_tree(path: &Path) -> Option<PrincipalRec> {
    active_slot(&load_tree(path))
}

pub fn abs_from_case(case: &Path) -> (u32, String) {
    load_frag(&case.join("i0.frag"))
}

pub fn save_epoch_cache(scenario_id: u32, rows: &[Value], state_dir: &Path) {
    let cache = state_dir.join(format!("epoch_{scenario_id}.json"));
    let _ = fs::write(cache, serde_json::to_string(rows).unwrap());
}
