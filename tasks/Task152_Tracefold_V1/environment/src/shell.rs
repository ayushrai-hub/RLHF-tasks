/// argv-style split for local experiments.
pub fn split_arg(s: &str) -> Vec<&str> {
    s.split_whitespace().collect()
}

