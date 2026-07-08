use serde::Serialize;

#[derive(Clone, Debug)]
pub struct PlanRow {
    pub tag: String,
    pub y0: f64,
    pub dt: f64,
    pub steps: u32,
    pub callback_order: String,
    pub restart_step: i32,
}

#[derive(Clone, Debug)]
pub struct HookDef {
    pub name: String,
    pub threshold: f64,
    pub on_fire: Option<FireEffect>,
}

#[derive(Clone, Debug)]
pub enum FireEffect {
    Add(f64),
    Mul(f64),
    Set(f64),
}

#[derive(Clone, Debug, Serialize)]
pub struct CaseOut {
    pub tag: String,
    pub event_step: i32,
    pub metric_integral: f64,
    pub order_sensitive: bool,
    pub euler_ok: bool,
    pub event_ok: bool,
    pub restart_ok: bool,
    pub metric_ok: bool,
    pub summary_ok: bool,
    pub report_line: String,
}

#[derive(Clone, Debug)]
pub struct CallbackSpec {
    pub name: String,
    pub load_order: u32,
    pub registration: usize,
}
