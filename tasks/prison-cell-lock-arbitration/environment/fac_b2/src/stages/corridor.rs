use qtr_w4::{IsolationWindowSet, eval_r6, plan_loader::MovementPlan};

pub fn select_windows(plan: &MovementPlan, generation: u64) -> IsolationWindowSet {
    eval_r6(plan, generation)
}
