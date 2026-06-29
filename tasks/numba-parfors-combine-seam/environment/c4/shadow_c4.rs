use std::fs;
use std::path::Path;

pub fn count_attempts(state_dir: &Path) -> u32 {
    let direct = crate::state::with_state(|st| st.cap_attempts);
    let log_path = state_dir.join("cap-audit.log");
    if let Ok(meta) = fs::metadata(&log_path) {
        if meta.is_file() {
            if let Ok(text) = fs::read_to_string(&log_path) {
                let logged = text.lines().filter(|line| !line.trim().is_empty()).count() as u32;
                return direct.max(logged);
            }
        }
    }
    direct
}
