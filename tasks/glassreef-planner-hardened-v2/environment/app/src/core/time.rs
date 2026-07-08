pub fn hour_index(ts: &str) -> i64 {
    let month: usize = ts[5..7].parse().unwrap_or(1);
    let day: i64 = ts[8..10].parse().unwrap_or(1);
    let hour: i64 = ts[11..13].parse().unwrap_or(0);
    let days = [0_i64,31,59,90,120,151,181,212,243,273,304,334];
    (days[month.saturating_sub(1)] + day - 1) * 24 + hour
}

pub fn overlaps(a_start: &str, a_end: &str, b_start: &str, b_end: &str) -> bool {
    let a0 = hour_index(a_start);
    let a1 = hour_index(a_end);
    let b0 = hour_index(b_start);
    let b1 = hour_index(b_end);
    a0 < b1 && b0 < a1
}
