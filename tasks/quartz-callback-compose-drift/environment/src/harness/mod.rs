use crate::checkpoint;
use crate::hooks;
use crate::overlay;
use crate::plan;
use crate::orchestrate;
use std::path::Path;

pub fn run(app: &Path) -> std::io::Result<()> {
    let rows = plan::load_plan(&app.join("data/ode_plan.tbl"))?;
    let hook_map = hooks::load_hooks(&app.join("data/hooks.tbl"))?;
    let overlay = overlay::load();
    checkpoint::save(app, -1)?;
    let mut prev_event_step = -1;
    let mut cases = Vec::new();
    for row in &rows {
        let _carry_hint = checkpoint::load(app);
        let case = orchestrate::process_row(row, &hook_map, &overlay, prev_event_step);
        prev_event_step = case.event_step;
        checkpoint::save(app, case.event_step)?;
        cases.push(case);
    }
    crate::write_out::write_outputs(&cases, &app.join("output"))
}
