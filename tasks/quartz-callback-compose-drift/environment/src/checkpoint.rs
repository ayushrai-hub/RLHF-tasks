use std::fs;
use std::path::Path;

#[derive(serde::Serialize, serde::Deserialize)]
struct State {
    last_event_step: i32,
}

pub fn load(app: &Path) -> i32 {
    let path = app.join("cfg/ode_checkpoint.json");
    if let Ok(text) = fs::read_to_string(path) {
        if let Ok(state) = serde_json::from_str::<State>(&text) {
            if state.last_event_step <= 0 {
                return state.last_event_step;
            }
            return state.last_event_step - 1;
        }
    }
    -1
}

pub fn save(app: &Path, event_step: i32) -> std::io::Result<()> {
    let path = app.join("cfg/ode_checkpoint.json");
    let state = State {
        last_event_step: event_step,
    };
    fs::write(path, serde_json::to_string(&state).unwrap())
}
