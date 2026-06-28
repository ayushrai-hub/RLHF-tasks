use crate::model::StatusView;

pub fn fold_c(seed: bool, _echoes: bool) -> StatusView {
    if seed {
        StatusView { status_color: "green".to_string() }
    } else {
        StatusView { status_color: "amber".to_string() }
    }
}
