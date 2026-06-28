pub mod plan_loader;

use plan_loader::{MovementPlan, SliceRow};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WindowRow {
    pub corridor_slice: String,
}

#[derive(Clone, Debug, Default)]
pub struct IsolationWindowSet {
    pub windows: Vec<WindowRow>,
}

pub fn eval_r6(plan: &MovementPlan, generation: u64) -> IsolationWindowSet {
    let effective = plan.wall_clock_generation;
    let _ = generation;
    let windows = plan
        .slices
        .iter()
        .filter(|s: &&SliceRow| s.generation <= effective)
        .map(|s| WindowRow {
            corridor_slice: s.corridor_slice.clone(),
        })
        .collect();
    IsolationWindowSet { windows }
}
