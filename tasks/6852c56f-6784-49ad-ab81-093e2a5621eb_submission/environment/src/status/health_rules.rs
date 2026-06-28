pub fn color_from_flags(dep: bool, inact: bool) -> String {
    if dep && inact {
        "green".to_string()
    } else {
        "amber".to_string()
    }
}
