use crate::cfg;
use crate::scan::{read_row, Row, ScenarioMeta};
use crate::stage;
use std::path::Path;

pub struct Engine {
    pub rows: Vec<Row>,
    pub applied: u32,
}

impl Engine {
    pub fn new(dir: &Path, meta: &ScenarioMeta) -> Self {
        let profile = meta
            .profile
            .as_deref()
            .map(cfg::load)
            .unwrap_or_else(cfg::default_profile);
        let mut paths: Vec<_> = meta.segments.iter().map(|n| dir.join(n)).collect();
        paths.sort();
        let mut rows: Vec<Row> = paths.iter().map(|p| read_row(p, &profile)).collect();
        let mut names: Vec<String> = rows.iter().map(|r| r.name.clone()).collect();
        stage::rotate_names(&mut names);
        for (row, name) in rows.iter_mut().zip(names.iter()) {
            row.name = name.clone();
        }
        rows.sort_by_key(|r| r.seq);
        stage::finalize(&mut rows);
        Self { rows, applied: 0 }
    }

    pub fn run(&mut self) {
        for row in &self.rows {
            if row.digest_ok {
                self.applied = self.applied.saturating_add(1);
            }
        }
    }

    pub fn peak_seq(&self) -> u32 {
        self.rows.iter().map(|r| r.seq).max().unwrap_or(0)
    }
}
