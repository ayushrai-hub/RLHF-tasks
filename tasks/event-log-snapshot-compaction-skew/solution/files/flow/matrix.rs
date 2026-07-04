use crate::sim::apply::{trace_y, Seen};
use crate::sim::case::Scenario;
use crate::sim::digest::stream_digest;
use crate::sim::frame::{raise_w, seal_v};
use crate::sim::ledger::Ledger;
use crate::sim::merge::fold_x;
use crate::sim::record::Record;

#[derive(Clone, Debug)]
pub struct BranchRecord {
    pub branch: String,
    pub aggregate_digest: String,
    pub event_digest: String,
    pub seq_high_water: u64,
    pub entries: Vec<String>,
    pub checkpoint_bytes: usize,
    pub fold_records: u32,
}

#[derive(Clone, Debug)]
pub struct RunRecord {
    pub scenario: String,
    pub seq_high_water: u64,
    pub branches: Vec<BranchRecord>,
}

fn finish(
    name: &str,
    state: &Ledger,
    checkpoint_bytes: usize,
    fold_records: u32,
) -> BranchRecord {
    BranchRecord {
        branch: name.to_string(),
        aggregate_digest: state.aggregate_digest(),
        event_digest: stream_digest(&state.stream),
        seq_high_water: state.seq_high_water(),
        entries: state.stream.iter().map(Record::as_line).collect(),
        checkpoint_bytes,
        fold_records,
    }
}

fn apply_checkpoint_step(
    state: &mut Ledger,
    case: &Scenario,
    step: u32,
    snap: &mut String,
    snap_seq: &mut u64,
) {
    let legs = case.batch_at(step);
    for (idx, leg) in legs.iter().enumerate() {
        if idx as u32 == case.checkpoint_leg {
            *snap = seal_v(state);
            *snap_seq = state.seq;
        }
        state.apply_leg(step, leg.clone());
    }
    state.end_step(step);
}

fn graft_checkpoint(branch: &mut Ledger, snap: &str) {
    let restored = raise_w(snap);
    branch.pots = restored.pots;
    branch.retired = restored.retired;
    branch.staging = restored.staging;
    branch.seq = restored.seq;
    branch.resumed = true;
}

fn apply_resume_step(branch: &mut Ledger, case: &Scenario, step: u32, snap: &str) {
    let legs = case.batch_at(step);
    for (idx, leg) in legs.iter().enumerate() {
        if idx as u32 == case.checkpoint_leg {
            graft_checkpoint(branch, snap);
            branch.step_m(step, &legs[idx..]);
            return;
        }
        branch.apply_leg(step, leg.clone());
    }
    branch.end_step(step);
}

fn continuous(case: &Scenario) -> BranchRecord {
    let mut state = case.initial_state();
    for step in 0..case.steps {
        state.step_m(step, case.batch_at(step));
    }
    finish("continuous", &state, 0, 0)
}

fn crash_resume(case: &Scenario) -> BranchRecord {
    let mut probe = case.initial_state();
    let mut snap = String::new();
    let mut snap_seq = 0_u64;
    for step in 0..=case.resume_from {
        if step == case.save_at {
            apply_checkpoint_step(&mut probe, case, step, &mut snap, &mut snap_seq);
        } else {
            probe.step_m(step, case.batch_at(step));
        }
    }
    let mut branch = case.initial_state();
    for step in 0..case.steps {
        if step < case.save_at {
            branch.step_m(step, case.batch_at(step));
        } else if step == case.save_at {
            apply_resume_step(&mut branch, case, step, &snap);
        } else {
            branch.step_m(step, case.batch_at(step));
        }
    }
    finish("crash_resume", &branch, snap.len(), 0)
}

fn compaction_replay(case: &Scenario) -> BranchRecord {
    let mut probe = case.initial_state();
    let mut snap = String::new();
    let mut snap_seq = 0_u64;
    for step in 0..case.steps {
        if step == case.save_at {
            apply_checkpoint_step(&mut probe, case, step, &mut snap, &mut snap_seq);
        } else {
            probe.step_m(step, case.batch_at(step));
        }
    }
    let tail: Vec<Record> = probe
        .stream
        .iter()
        .filter(|record| {
            record.seq > snap_seq
                && record.step > case.save_at
                && record.step <= case.compact_at
        })
        .cloned()
        .collect();
    let folded = fold_x(&tail, &probe.retired);
    let fold_count = folded.len() as u32;

    let mut branch = case.initial_state();
    for step in 0..case.save_at {
        branch.step_m(step, case.batch_at(step));
    }
    apply_resume_step(&mut branch, case, case.save_at, &snap);
    let mut seen = Seen::default();
    for entry in &folded {
        trace_y(&mut branch, entry, true, &mut seen);
    }
    for step in (case.compact_at + 1)..case.steps {
        branch.step_m(step, case.batch_at(step));
    }
    finish("compaction_replay", &branch, snap.len(), fold_count)
}

pub fn route_z(case: &Scenario) -> RunRecord {
    let branches = vec![
        continuous(case),
        crash_resume(case),
        compaction_replay(case),
    ];
    let seq_high_water = branches
        .iter()
        .map(|branch| branch.seq_high_water)
        .max()
        .unwrap_or(0);
    RunRecord {
        scenario: case.name.to_string(),
        seq_high_water,
        branches,
    }
}

pub fn route_subset(names: &[&str]) -> Vec<RunRecord> {
    let by_name: std::collections::BTreeMap<&str, Scenario> = crate::sim::case::cases()
        .into_iter()
        .map(|case| (case.name, case))
        .collect();
    names
        .iter()
        .filter_map(|name| by_name.get(name))
        .map(|case| route_z(case))
        .collect()
}

pub fn branches_aligned(case: &Scenario) -> bool {
    let record = route_z(case);
    let baseline = record
        .branches
        .iter()
        .find(|branch| branch.branch == "continuous")
        .expect("continuous branch");
    record.branches.iter().all(|branch| {
        branch.branch == "continuous"
            || (branch.aggregate_digest == baseline.aggregate_digest
                && branch.event_digest == baseline.event_digest
                && branch.seq_high_water == baseline.seq_high_water
                && branch.entries == baseline.entries)
    })
}

pub fn staging_checkpoint_roundtrip(case: &Scenario) -> bool {
    let mut probe = case.initial_state();
    for step in 0..case.save_at {
        probe.step_m(step, case.batch_at(step));
    }
    let legs = case.batch_at(case.save_at);
    for (idx, leg) in legs.iter().enumerate() {
        if idx as u32 == case.checkpoint_leg {
            let snap = seal_v(&probe);
            let restored = raise_w(&snap);
            return restored.staging == probe.staging
                && restored.pots == probe.pots
                && restored.retired == probe.retired
                && restored.seq == probe.seq;
        }
        probe.apply_leg(case.save_at, leg.clone());
    }
    true
}

fn folded_tail(case: &Scenario) -> (String, Vec<Record>) {
    let mut probe = case.initial_state();
    let mut snap = String::new();
    let mut snap_seq = 0_u64;
    for step in 0..case.steps {
        if step == case.save_at {
            apply_checkpoint_step(&mut probe, case, step, &mut snap, &mut snap_seq);
        } else {
            probe.step_m(step, case.batch_at(step));
        }
    }
    let tail: Vec<Record> = probe
        .stream
        .iter()
        .filter(|record| record.seq > snap_seq)
        .cloned()
        .collect();
    let folded = fold_x(&tail, &probe.retired);
    (snap, folded)
}

pub fn double_fold_idempotent(case: &Scenario) -> bool {
    let (snap, folded) = folded_tail(case);
    if folded.is_empty() {
        return false;
    }
    let mut branch = case.initial_state();
    for step in 0..case.save_at {
        branch.step_m(step, case.batch_at(step));
    }
    let restored = raise_w(&snap);
    branch.pots = restored.pots;
    branch.retired = restored.retired;
    branch.staging = restored.staging;
    branch.seq = restored.seq;
    branch.resumed = true;
    let mut seen = Seen::default();
    for entry in &folded {
        trace_y(&mut branch, entry, true, &mut seen);
    }
    let digest = branch.aggregate_digest();
    let event = stream_digest(&branch.stream);
    let len = branch.stream.len();
    for entry in &folded {
        trace_y(&mut branch, entry, true, &mut seen);
    }
    digest == branch.aggregate_digest()
        && event == stream_digest(&branch.stream)
        && len == branch.stream.len()
}

pub fn orphan_checkpoint_ignored(case: &Scenario) -> bool {
    let mut probe = case.initial_state();
    for step in 0..case.save_at {
        probe.step_m(step, case.batch_at(step));
    }
    let legs = case.batch_at(case.save_at);
    for (idx, leg) in legs.iter().enumerate() {
        if idx as u32 == case.checkpoint_leg {
            let mut snap = seal_v(&probe);
            snap.push_str("x,orphan,line\n");
            snap.push_str("?,1,2,3\n");
            let restored = raise_w(&snap);
            return restored.staging == probe.staging
                && restored.pots == probe.pots
                && restored.retired == probe.retired
                && restored.seq == probe.seq;
        }
        probe.apply_leg(case.save_at, leg.clone());
    }
    true
}
