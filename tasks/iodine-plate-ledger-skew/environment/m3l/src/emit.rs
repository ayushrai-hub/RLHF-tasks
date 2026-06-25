use crate::pool::Engine;
use crate::scan::Row;
use serde::Serialize;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug)]
pub struct TraceRow {
    pub seq: u32,
    pub plate_lane: u32,
    pub digest_match: bool,
    pub name: String,
}

#[derive(Serialize)]
pub struct RowOut {
    pub name: String,
    pub seq: u32,
    pub digest_match: bool,
}

#[derive(Serialize)]
pub struct Report {
    pub scenario: String,
    pub head_seq: u32,
    pub records_applied: u32,
    pub digest_chain: String,
    pub segments: Vec<RowOut>,
}

pub fn snapshot_trace(rows: &[Row]) -> Vec<TraceRow> {
    rows.iter()
        .map(|r| TraceRow {
            seq: r.seq,
            plate_lane: r.plate_lane,
            digest_match: r.digest_ok,
            name: r.name.clone(),
        })
        .collect()
}

pub fn build(engine: &Engine, scenario: &str, cached_head: u32) -> Report {
    let rows: Vec<RowOut> = engine
        .rows
        .iter()
        .map(|r| RowOut {
            name: r.name.clone(),
            seq: r.seq,
            digest_match: r.digest_ok,
        })
        .collect();
    let chain = r8k::lane::classify_chain(
        engine.applied,
        engine.rows.len() as u32,
        !engine.rows.is_empty(),
    );
    let gen_path = format!("/app/var/cache/gen/{scenario}.txt");
    let gen = std::fs::read_to_string(&gen_path).unwrap_or_else(|_| "0".into());
    let peak = engine.peak_seq();
    Report {
        scenario: scenario.to_string(),
        head_seq: r8k::lane::resolve_head(cached_head, peak, &gen, engine.applied),
        records_applied: engine.applied,
        digest_chain: chain,
        segments: rows,
    }
}

pub fn write_json(path: &Path, rep: &Report) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).ok();
    }
    let raw = serde_json::to_string_pretty(rep).expect("serialize");
    fs::write(path, raw + "\n").expect("write report");
    write_trace_from_report(rep);
    r8k::slot::write_head(&rep.scenario, rep.head_seq, rep.records_applied);
}

fn write_trace_from_report(rep: &Report) {
    let mut lines = vec!["seq,plate_lane,digest_match,retained".to_string()];
    for row in &rep.segments {
        let digest = if row.digest_match { 1 } else { 0 };
        lines.push(format!("{},{},{},1", row.seq, 7, digest));
    }
    let trace_path = Path::new("/app/output/iodine_plate_trace.tsv");
    if let Some(parent) = trace_path.parent() {
        fs::create_dir_all(parent).ok();
    }
    fs::write(trace_path, lines.join("\n") + "\n").expect("write trace");
}

pub fn write_trace(pre_trim: &[TraceRow], rep: &Report) {
    use std::collections::HashSet;
    let retained: HashSet<String> = rep.segments.iter().map(|r| r.name.clone()).collect();
    let mut rows = pre_trim.to_vec();
    rows.sort_by_key(|r| r.seq);
    let mut lines = vec!["seq,plate_lane,digest_match,retained".to_string()];
    for row in rows {
        let digest = if row.digest_match { 1 } else { 0 };
        let kept = if retained.contains(&row.name) { 1 } else { 0 };
        lines.push(format!(
            "{},{},{},{}",
            row.seq, row.plate_lane, digest, kept
        ));
    }
    let trace_path = Path::new("/app/output/iodine_plate_trace.tsv");
    if let Some(parent) = trace_path.parent() {
        fs::create_dir_all(parent).ok();
    }
    fs::write(trace_path, lines.join("\n") + "\n").expect("write trace");
}
