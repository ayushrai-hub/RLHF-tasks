use crate::d3_gateway;
use crate::d3_d3_b::{key_mat, gate_d3, write_h};
use crate::f2_gateway;
use crate::d5_gateway;
use crate::d5_shadow_d5;
use crate::c4_gateway;
use crate::state::{gate_state, sync_once, PrincipalRec, ReplayState};
use crate::arr::{active_slot, load_frag, load_tree};
use crate::wal::{
    append_record, compute_order_seal, next_seq, phases_valid, read_chain,
    write_checkpoint, Checkpoint, WalRecord,
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
        "block_rms": crate::pack_mix_r8::block_rms_for(rec.gen, rec.action_code, view),
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

fn promote_rows(scenario_id: u32) -> Vec<Value> {
    crate::state::with_state(|st| {
        st.catalog_notes
            .iter()
            .map(|note| {
                let (principal, label, gen, action) = crate::f2_watch_n::inspect_row(note);
                json!({
                    "scenario": scenario_id,
                    "view": "promote",
                    "principal": principal,
                    "label": label,
                    "generation": gen,
                    "action_code": action,
                    "block_rms": crate::pack_mix_r8::block_rms_for(gen, action, "promote"),
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
    let (feed_gen, live_gen) = crate::state::with_state(|st| {
        (
            st.feed_slots
                .get("active")
                .map(|s| s.gen)
                .unwrap_or(0),
            st.live_slots
                .get("active")
                .map(|s| s.gen)
                .unwrap_or(0),
        )
    });
    let seq = next_seq(state_dir, scenario);
    let rec = WalRecord {
        scenario,
        phase: phase.to_string(),
        feed_gen,
        live_gen,
        seq,
    };
    let _ = append_record(state_dir, rec);
}

fn touch_generation(view: &str) {
    crate::state::with_state(|st| {
        let table = if view == "reduce" {
            &mut st.feed_slots
        } else {
            &mut st.live_slots
        };
        if let Some(rec) = table.get_mut("active") {
            rec.gen = rec.gen.saturating_add(WRITE_GEN_DELTA);
        }
    });
}

fn sync_store_from_abs(case: &Path, meta_root: &Path, scenario_id: u32) {
    let abs_path = case.join("i0.tab");
    let (epoch, digest) = load_frag(&abs_path);
    let compile_active = active_slot(&load_tree(&case.join("a0.arr"))).unwrap_or(PrincipalRec {
        principal: "svc1".into(),
        label: "ROOT".into(),
        gen: 0,
        action_code: 0,
    });
    let key = key_mat("base", &[abs_path.to_string_lossy().into_owned()]);
    let (cached_gen, cached_frag) = gate_d3(&meta_root.to_string_lossy(), &key);
    let target_gen = compile_active.gen;
    let frag = crate::d3_d3_b::mix_frag(cached_frag, epoch);
    write_h(
        &meta_root.to_string_lossy(),
        &key,
        target_gen,
        frag,
    );
    crate::state::with_state(|st| {
        st.crl_epoch = epoch;
        st.abs_digest = digest;
        let mut compile = compile_active.clone();
        compile.gen = target_gen;
        st.feed_slots.insert("active".into(), compile);
    });
}

pub fn replay_scenario(scenario_id: u32, state_dir: &Path) -> Vec<Value> {
    let case = PathBuf::from(format!("/app/cases/seq/s{scenario_id}"));
    let compile_raw = load_tree(&case.join("a0.arr"));
    let runtime_raw = load_tree(&case.join("b0.arr"));
    let (epoch, digest) = load_frag(&case.join("i0.tab"));

    let state = ReplayState {
        scenario_id,
        crl_epoch: epoch,
        abs_digest: digest,
        feed_slots: compile_raw,
        live_slots: runtime_raw,
        ..Default::default()
    };
    gate_state(state);

    let meta_root = state_dir.join("store");
    let runtime_root = state_dir.join("live");
    let mirror_root = state_dir.join("promote");
    for path in [&meta_root, &runtime_root, &mirror_root] {
        let _ = fs::create_dir_all(path);
    }

    sync_store_from_abs(&case, &meta_root, scenario_id);

    let roots = vec![
        meta_root.to_string_lossy().into_owned(),
        runtime_root.to_string_lossy().into_owned(),
        mirror_root.to_string_lossy().into_owned(),
    ];

    let phase_list = d5_gateway::phase_order(scenario_id, &roots);
    let _ = d5_shadow_d5::log_steps(
        scenario_id,
        &phase_list.iter().copied().collect::<Vec<_>>(),
        &state_dir.join("phase-log"),
    );

    let issuer_paths = vec![case.join("i0.tab").to_string_lossy().into_owned()];
    let key = key_mat("base", &issuer_paths);

    for phase in phase_list {
        wal_append(state_dir, scenario_id, phase);
        match phase {
            "bust" => d5_gateway::run_bust(&meta_root.to_string_lossy(), scenario_id, &key),
            "success" => d5_gateway::report_success(state_dir, scenario_id),
            "write" => {
                touch_generation("reduce");
            }
            "verify" => f2_gateway::run_mirror(&mirror_root.to_string_lossy(), scenario_id),
            "sync" => {
                c4_gateway::run_cap(&runtime_root.to_string_lossy(), scenario_id);
                sync_once();
            }
            _ => {}
        }
    }

    let chain = read_chain(state_dir);
    let order_seal = compute_order_seal(&chain);
    let phase_ok = phases_valid(&chain);
    let lineage_seal = crate::wal::compute_lineage_seal(&chain);

    let cp = Checkpoint {
        last_scenario: scenario_id,
        wal_seq: chain.last().map(|r| r.seq).unwrap_or(0),
        order_seal,
        lineage_seal,
        valid: phase_ok,
    };
    let _ = write_checkpoint(state_dir, &cp);

    let metrics = json!({
        "store_hits": crate::state::with_state(|st| st.store_hits),
        "cap_attempts": crate::c4_shadow_c4::count_attempts(state_dir),
        "crl_epoch": d3_gateway::gateway_epoch(&case.to_string_lossy()),
    });
    let _ = fs::write(
        state_dir.join("last_metrics.json"),
        serde_json::to_string(&metrics).unwrap(),
    );

    let (feed_slots, live_slots) = crate::state::with_state(|st| {
        (st.feed_slots.clone(), st.live_slots.clone())
    });
    let mut rows = active_view_rows(scenario_id, "reduce", &feed_slots);
    rows.extend(active_view_rows(scenario_id, "live", &live_slots));
    rows.extend(promote_rows(scenario_id));
    rows.extend(transition_rows(scenario_id));
    rows
}

pub fn recover_from_wal(state_dir: &Path) -> bool {
    let chain = read_chain(state_dir);
    if chain.is_empty() {
        return false;
    }
    let seal = compute_order_seal(&chain);
    let phase_ok = phases_valid(&chain);
    let last_scenario = chain.iter().map(|r| r.scenario).max().unwrap_or(0);
    let lineage_seal = crate::wal::compute_lineage_seal(&chain);
    let cp = Checkpoint {
        last_scenario,
        wal_seq: chain.last().map(|r| r.seq).unwrap_or(0),
        order_seal: seal,
        lineage_seal,
        valid: phase_ok,
    };
    write_checkpoint(state_dir, &cp).is_ok() && phase_ok
}

pub fn checkpoint_ready(state_dir: &Path) -> bool {
    if !crate::wal::wal_crc_chain_intact(state_dir) {
        return false;
    }
    let chain = read_chain(state_dir);
    if !phases_valid(&chain) {
        return false;
    }
    match crate::wal::read_checkpoint(state_dir) {
        Some(cp) => {
            let seal = compute_order_seal(&chain);
            let lineage = crate::wal::compute_lineage_seal(&chain);
            cp.valid && cp.order_seal == seal && cp.lineage_seal == lineage
        }
        None => false,
    }
}

pub fn active_from_tree(path: &Path) -> Option<PrincipalRec> {
    active_slot(&load_tree(path))
}

pub fn abs_from_case(case: &Path) -> (u32, String) {
    load_frag(&case.join("i0.tab"))
}

pub fn save_epoch_cache(scenario_id: u32, rows: &[Value], state_dir: &Path) {
    let cache = state_dir.join(format!("epoch_{scenario_id}.json"));
    let _ = fs::write(cache, serde_json::to_string(rows).unwrap());
}
