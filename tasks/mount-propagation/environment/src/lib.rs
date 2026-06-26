mod h3 {
    pub mod h3 {
        pub mod bind_q;
        pub mod carry_lane;
        pub mod probe_a;
        pub mod shadow_a;
    }
}
mod m4 {
    pub mod m4 {
        pub mod stamp_q;
        pub mod probe_b;
        pub mod ring_b;
    }
}
mod n5 {
    pub mod n5 {
        pub mod format_q;
        pub mod rel_q;
        pub mod replay_gate;
    }
}
mod p2 {
    pub mod p2 {
        pub mod epoch_gate;
        pub mod wal_lane;
    }
}
mod q7 {
    pub mod q7 {
        pub mod keep_q;
        pub mod ring_c;
        pub mod shadow_c;
    }
}
mod tooling {
    pub mod mux_h3;
    pub mod mux_m4;
    pub mod mux_q7;
    pub mod segment_read;
}

#[path = "../support/lane_persist.rs"]
mod lane_persist;

pub use n5::n5::rel_q::{
    assemble_matrix, row_chain_digest, tri_keys, EvidenceV, LedgerV, MatrixRecord, ObservationV, RowV,
};

use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use crate::n5::n5::replay_gate;
use tooling::segment_read::{read_checkpoint_markers, read_segment};

struct SlugCarry {
    slug: String,
    stamps: HashMap<String, String>,
}

static CARRY: Mutex<Option<SlugCarry>> = Mutex::new(None);

fn carry_persists(prev: &str, next: &str) -> bool {
    h3::h3::carry_lane::should_reuse_stamps(prev, next)
}

#[derive(Clone, Debug, Deserialize)]
struct CaseDef {
    slug: String,
    segment: String,
    checkpoint: String,
    entities: Vec<String>,
    phases: Vec<String>,
    #[serde(default = "default_cycles")]
    cycles: i32,
}

fn default_cycles() -> i32 {
    1
}

struct Runner {
    root: PathBuf,
    def: CaseDef,
    ledger: LedgerV,
    stamps: HashMap<String, String>,
    evidence: Vec<EvidenceV>,
    rows: Vec<RowV>,
    markers: HashMap<String, String>,
    obs: Vec<ObservationV>,
    wave: i32,
    phase_count: i32,
    run_gen: i32,
    committed_gen: i32,
}

pub fn env_root() -> PathBuf {
    PathBuf::from("/app/environment")
}

pub fn run_scenario(slug: &str) -> Result<MatrixRecord, String> {
    let root = env_root();
    if !root.exists() {
        return run_scenario_at(PathBuf::from("."), slug);
    }
    run_scenario_at(root, slug)
}

fn run_scenario_at(root: PathBuf, slug: &str) -> Result<MatrixRecord, String> {
    let def_path = root.join("data/cases").join(format!("case_{slug}.json"));
    let raw = fs::read_to_string(&def_path).map_err(|e| e.to_string())?;
    let mut def: CaseDef = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if def.cycles < 1 {
        def.cycles = 1;
    }

    let mut lane_state = lane_persist::load_state();
    let prior_slug = lane_state.active_slug.clone();
    lane_persist::on_scenario_start(&mut lane_state, slug);
    replay_gate::note_slug_switch(slug);
    let committed_gen = lane_persist::committed_generation(&lane_state, slug);
    let run_gen = lane_persist::next_generation(&lane_state, slug, &prior_slug);

    let mut runner = Runner {
        root: root.clone(),
        def: def.clone(),
        ledger: LedgerV {
            epoch: 0,
            cells: HashMap::new(),
            branch: String::new(),
        },
        stamps: HashMap::new(),
        evidence: Vec::new(),
        rows: Vec::new(),
        markers: HashMap::new(),
        obs: Vec::new(),
        wave: 0,
        phase_count: 0,
        run_gen,
        committed_gen,
    };

    for cycle in 1..=def.cycles {
        for phase in &def.phases.clone() {
            runner.exec_phase(phase, cycle)?;
        }
    }

    if lane_persist::blocks_reconcile(&lane_state, slug, runner.run_gen) {
        return Err(format!("generation floor blocked reconcile for {slug}"));
    }

    if let Ok(mut guard) = CARRY.lock() {
        *guard = Some(SlugCarry {
            slug: def.slug.clone(),
            stamps: runner.stamps.clone(),
        });
    }

    replay_gate::journal_commit(&runner.ledger.cells);

    let wal_keys = lane_state.wal_obs.clone();
    runner.obs = p2::p2::wal_lane::replay_wal_tail(&wal_keys, runner.obs);
    let obs_keys = p2::p2::wal_lane::collect_keys(&runner.obs);
    lane_persist::commit_run(&mut lane_state, slug, runner.run_gen, obs_keys);
    lane_persist::save_state(&lane_state)?;

    Ok(assemble_matrix(
        &def.slug,
        runner.rows,
        runner.obs,
        runner.evidence,
    ))
}

impl Runner {
    fn exec_phase(&mut self, name: &str, cycle: i32) -> Result<(), String> {
        self.phase_count += 1;
        let seg_path = self
            .root
            .join("fixtures/sidecars")
            .join(format!("{}.seg", self.def.segment));
        let cp_path = self
            .root
            .join("data/checkpoints")
            .join(format!("cp_blob_{}.bin", self.def.checkpoint));

        match name {
            "run" => {
                self.wave = 1;
                if let Ok(guard) = CARRY.lock() {
                    if let Some(carry) = guard.as_ref() {
                        if carry_persists(&carry.slug, &self.def.slug) {
                            for (key, val) in &carry.stamps {
                                self.stamps.insert(key.clone(), val.clone());
                            }
                        }
                    }
                }
                let (markers, branch) = read_checkpoint_markers(&cp_path)?;
                for ent in &self.def.entities {
                    let seed = markers.get(ent).cloned().unwrap_or_default();
                    self.markers.insert(ent.clone(), seed.clone());
                    self.stamps.insert(format!("{ent}_rk"), format!("rk_{ent}_v1"));
                    self.stamps.insert(format!("{ent}_mk"), seed);
                    if p2::p2::epoch_gate::allow_phase_one(self.run_gen, self.committed_gen) {
                        self.evidence.push(EvidenceV {
                            id: format!("{ent}_e1"),
                            payload: "wave1".to_string(),
                            phase: 1,
                        });
                    }
                }
                self.obs.push(ObservationV {
                    phase: name.to_string(),
                    cycle,
                    note: "seed markers".to_string(),
                    branch,
                });
            }
            "recover" => {
                let seg = read_segment(&seg_path)?;
                self.ledger = LedgerV {
                    epoch: seg.epoch,
                    cells: seg.cells,
                    branch: seg.branch.clone(),
                };
                replay_gate::journal_merge(&mut self.ledger.cells);
                for ent in &self.def.entities {
                    if p2::p2::epoch_gate::allow_phase_two(self.run_gen, self.committed_gen) {
                        self.evidence.push(EvidenceV {
                            id: format!("{ent}_e2"),
                            payload: "wave2".to_string(),
                            phase: 2,
                        });
                    }
                }
                self.obs.push(ObservationV {
                    phase: name.to_string(),
                    cycle,
                    note: "load book".to_string(),
                    branch: self.ledger.branch.clone(),
                });
            }
            "compact" => {
                self.wave = 2;
                self.stamps = tooling::mux_m4::compact_stamps(self.stamps.clone(), self.wave);
                self.sync_markers_from_stamps();
                self.obs.push(ObservationV {
                    phase: name.to_string(),
                    cycle,
                    note: "background wave".to_string(),
                    branch: self.ledger.branch.clone(),
                });
            }
            "reconcile" => {
                self.sync_markers_from_stamps();
                self.evidence =
                    tooling::mux_q7::filter_evidence(self.evidence.clone(), self.phase_count);
                self.build_rows();
                self.rows = tooling::mux_h3::reconcile_rows(self.rows.clone(), &self.ledger)?;
                self.obs.push(ObservationV {
                    phase: name.to_string(),
                    cycle,
                    note: "matrix rows".to_string(),
                    branch: self.ledger.branch.clone(),
                });
            }
            other => return Err(format!("unknown phase {other:?}")),
        }
        Ok(())
    }

    fn sync_markers_from_stamps(&mut self) {
        for ent in &self.def.entities {
            let stamp_key = if self.wave >= 2 {
                format!("{ent}_rk")
            } else {
                format!("{ent}_mk")
            };
            if let Some(mk) = self.stamps.get(&stamp_key) {
                self.markers.insert(ent.clone(), mk.clone());
            }
        }
    }

    fn build_rows(&mut self) {
        self.rows.clear();
        for ent in &self.def.entities {
            let (path_key, uri_key, ref_key) = tri_keys(ent);
            let cell = self.ledger.cells.get(ent).cloned().unwrap_or_default();
            let marker = self.markers.get(ent).cloned().unwrap_or_default();
            self.rows.push(RowV {
                entity: ent.clone(),
                path_key,
                uri_key,
                ref_key,
                marker,
                book_cell: cell.clone(),
                cache_cell: format!("{cell}_cache_stale"),
                wave: self.wave,
            });
        }
    }
}

pub fn write_matrix(record: &MatrixRecord) -> Result<(), String> {
    let out_path = Path::new("/app/output/r7_matrix_record.json");
    if let Some(parent) = out_path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let encoded = serde_json::to_string_pretty(record).map_err(|e| e.to_string())?;
    fs::write(out_path, format!("{encoded}\n")).map_err(|e| e.to_string())
}
