use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::agg::pool_k8::TailEntry;
use crate::agg::{AggErr, BranchAcc, LaneAcc, PartialFrame};

fn narrow_f32(v: f64) -> f64 {
    v as f32 as f64
}

fn narrow_lane(acc: &LaneAcc) -> LaneAcc {
    LaneAcc {
        count: acc.count,
        sum: narrow_f32(acc.sum),
        m2: narrow_f32(acc.m2),
        samples: acc.samples.iter().map(|v| narrow_f32(*v)).collect(),
        tail_entries: acc
            .tail_entries
            .iter()
            .map(|e| TailEntry {
                ev_time: e.ev_time,
                seq: e.seq,
                value: narrow_f32(e.value),
            })
            .collect(),
    }
}

#[derive(Serialize, Deserialize)]
struct WireFrame {
    seed: u64,
    processed: u64,
    wm: u64,
    frame_gen: u64,
    plan: Vec<String>,
    branches: Vec<BranchAcc>,
}

fn to_wire(frame: &PartialFrame) -> WireFrame {
    WireFrame {
        seed: frame.seed,
        processed: frame.processed,
        wm: frame.wm,
        frame_gen: frame.frame_gen,
        plan: Vec::new(),
        branches: frame
            .branches
            .iter()
            .map(|b| BranchAcc {
                branch_id: b.branch_id.clone(),
                part_id: b.part_id.clone(),
                max_seq: b.max_seq,
                acc: narrow_lane(&b.acc),
            })
            .collect(),
    }
}

fn from_wire(wf: WireFrame) -> PartialFrame {
    PartialFrame {
        seed: wf.seed,
        processed: wf.processed,
        wm: wf.wm,
        frame_gen: wf.frame_gen,
        plan: wf.plan,
        branches: wf.branches,
    }
}

pub fn write_frame_c4(path: &Path, frame: &PartialFrame) -> Result<(), AggErr> {
    let wire = to_wire(frame);
    let data = serde_json::to_vec(&wire).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut f = File::create(path).map_err(|e| AggErr::Io(e.to_string()))?;
    f.write_all(&data).map_err(|e| AggErr::Io(e.to_string()))
}

pub fn read_frame_c4(path: &Path) -> Result<PartialFrame, AggErr> {
    let mut f = File::open(path).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut buf = Vec::new();
    f.read_to_end(&mut buf).map_err(|e| AggErr::Io(e.to_string()))?;
    let wf: WireFrame = serde_json::from_slice(&buf).map_err(|e| AggErr::Parse(e.to_string()))?;
    Ok(from_wire(wf))
}

pub fn frame_byte_estimate(frame: &PartialFrame) -> usize {
    frame.branches.len() * 64 + frame.processed as usize
}
