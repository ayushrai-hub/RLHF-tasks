use std::collections::HashMap;
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

    pub fn src_dir(&self) -> PathBuf {
        self.base.join("masters")
    }
}

#[derive(Clone, Debug)]
pub struct Ctx {
    pub root: Root,
    pub snap: Snap,
    pub epoch: u64,
    pub rows: Vec<Row>,
    pub edges: Vec<Edge>,
    pub events: Vec<Event>,
    pub material: Vec<u8>,
    pub replay: HashMap<String, ReplayRow>,
}

#[derive(Clone, Debug)]
pub struct ReplayRow {
    pub pkt: u64,
    pub byte: u64,
    pub body: String,
    pub anchor: String,
}

#[derive(Clone, Debug)]
pub struct Snap {
    pub seed_rows: Vec<Row>,
    pub floor: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Row {
    pub key: String,
    pub mark: String,
    pub holder: String,
    pub rtype: String,
    pub klass: String,
    pub ttl: u64,
    pub rdata: String,
    pub body: String,
    pub pkt: u64,
    pub byte: u64,
    pub lane: u32,
    pub visit_ord: u32,
    pub anchor: String,
    pub src_rel: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Edge {
    pub from: String,
    pub to: String,
    pub ord: u32,
}

#[derive(Clone, Debug)]
pub struct Event {
    pub key: String,
    pub delta_pkt: i64,
    pub delta_byte: i64,
    pub phase: u32,
}

#[derive(Clone, Debug)]
pub struct View {
    pub catalog: Vec<CatalogRow>,
    pub equiv: Vec<EquivRow>,
    pub lines: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct CatalogRow {
    pub holder: String,
    pub rtype: String,
    pub klass: String,
    pub ttl: u64,
    pub rdata: String,
    pub key: String,
    pub lane: u32,
}

#[derive(Clone, Debug)]
pub struct EquivRow {
    pub holder: String,
    pub body_digest: String,
    pub shell_digest: String,
    pub lane: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Mode {
    Cold,
    Warm,
    WarmSettle,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Cmd {
    Init { case_id: String },
    ApplyScope { scope_id: String },
    Normalize,
    Reload,
}

impl CatalogRow {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"owner\":\"{}\",\"rtype\":\"{}\",\"class\":\"{}\",\"ttl\":{},\"rdata\":\"{}\",\"key\":\"{}\"}}",
            esc(&self.holder),
            esc(&self.rtype),
            esc(&self.klass),
            self.ttl,
            esc(&self.rdata),
            esc(&self.key)
        )
    }
}

impl EquivRow {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"owner\":\"{}\",\"body_digest\":\"{}\",\"zone_digest\":\"{}\"}}",
            esc(&self.holder),
            esc(&self.body_digest),
            esc(&self.shell_digest)
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
            snap: Snap {
                seed_rows: Vec::new(),
                floor: 0,
            },
            epoch: 1_700_000_000,
            rows: Vec::new(),
            edges: Vec::new(),
            events: Vec::new(),
            material: Vec::new(),
            replay: HashMap::new(),
        }
    }
}
