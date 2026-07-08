use std::path::PathBuf;

#[derive(Clone, Debug)]
pub struct Root {
    pub base: PathBuf,
}

impl Root {
    pub fn new(base: PathBuf) -> Self {
        Self { base }
    }

    pub fn state_dir(&self) -> PathBuf {
        self.base.join(".state")
    }

    pub fn seed_file(&self) -> PathBuf {
        self.base.join("seed.txt")
    }

    pub fn durable_path(&self) -> PathBuf {
        self.state_dir().join("durable.json")
    }

    pub fn ckpt_path(&self) -> PathBuf {
        self.state_dir().join("ckpt.json")
    }

    pub fn row_obs_path(&self) -> PathBuf {
        self.state_dir().join("row-obs.jsonl")
    }

    pub fn dispatch_obs_path(&self) -> PathBuf {
        self.state_dir().join("dispatch-obs.jsonl")
    }

    pub fn witness_path(&self) -> PathBuf {
        self.state_dir().join("defer-witness.bin")
    }

    pub fn carry_path(&self) -> PathBuf {
        self.state_dir().join("defer-carry.tab")
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub struct WitnessKey {
    pub tag: String,
    pub wave: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub struct CarryKey {
    pub tag: String,
    pub wave: u32,
    pub barrier_gen: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Row {
    pub tag: String,
    pub lane: String,
    pub weight: u32,
    pub state: String,
    pub wave: u32,
    pub stash_gen: u32,
    pub seed_origin: bool,
}

#[derive(Clone, Debug)]
pub struct Snap {
    pub rows: Vec<Row>,
    pub wave: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
    pub witnesses: Vec<WitnessKey>,
    pub carries: Vec<CarryKey>,
    pub events: Vec<Event>,
}

#[derive(Clone, Debug)]
pub struct Event {
    pub tag: String,
    pub wave: u32,
    pub phase: String,
    pub slot: u32,
}

#[derive(Clone, Debug)]
pub struct RowObs {
    pub tag: String,
    pub lane: String,
    pub state: String,
    pub wave: u32,
}

#[derive(Clone, Debug)]
pub struct DispatchObs {
    pub tag: String,
    pub wave: u32,
    pub phase: String,
    pub slot: u32,
}

#[derive(Clone, Debug)]
pub struct View {
    pub row_obs: Vec<RowObs>,
    pub dispatch_obs: Vec<DispatchObs>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Mode {
    Open { sample: String },
    Offer { tag: String },
    Cycle { partial: bool },
    Raise,
    Sweep { again: bool },
}

#[derive(Clone, Debug)]
pub struct Ctx {
    pub root: Root,
    pub rows: Vec<Row>,
    pub wave: u32,
    pub slot: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
    pub witnesses: Vec<WitnessKey>,
    pub carries: Vec<CarryKey>,
    pub events: Vec<Event>,
}

impl RowObs {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"tag\":\"{}\",\"lane\":\"{}\",\"state\":\"{}\",\"wave\":{}}}",
            esc(&self.tag),
            esc(&self.lane),
            esc(&self.state),
            self.wave
        )
    }
}

impl DispatchObs {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"tag\":\"{}\",\"wave\":{},\"phase\":\"{}\",\"slot\":{}}}",
            esc(&self.tag),
            self.wave,
            esc(&self.phase),
            self.slot
        )
    }
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

impl Ctx {
    pub fn new(root: Root) -> Self {
        Self {
            root,
            rows: Vec::new(),
            wave: 0,
            slot: 0,
            gate_open: false,
            backing_up: false,
            stash_epoch: 0,
            seal_epoch: 0,
            barrier_gen: 0,
            witnesses: Vec::new(),
            carries: Vec::new(),
            events: Vec::new(),
        }
    }
}
