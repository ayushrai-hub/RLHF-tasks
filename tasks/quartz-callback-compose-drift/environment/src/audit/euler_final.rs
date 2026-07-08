use crate::lanes::euler_lane;
use crate::types::PlanRow;

pub fn contract_final_y(row: &PlanRow) -> f64 {
    let mut y = row.y0;
    for _ in 0..row.steps {
        y = euler_lane::euler_step(y, row.dt);
    }
    y
}
