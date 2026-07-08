pub fn crew_bonus(grade: &str) -> i64 {
    match grade {
        "A" => 8,
        "B" => 4,
        "C" => 1,
        _ => 0,
    }
}

pub fn depth_penalty(depth_m: i64) -> i64 {
    if depth_m <= 3000 { 0 } else { (depth_m - 3000) / 700 }
}

pub fn total_score(priority_base: i64, restored_priority: i64, compatibility_bonus: i64, drift_penalty: i64, depth_m: i64, crew: &str) -> i64 {
    priority_base * 10 + restored_priority + compatibility_bonus + crew_bonus(crew) - drift_penalty - depth_penalty(depth_m)
}
