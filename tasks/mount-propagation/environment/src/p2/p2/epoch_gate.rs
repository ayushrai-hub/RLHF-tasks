pub fn allow_phase_one(run_gen: i32, committed_gen: i32) -> bool {
    if committed_gen == 0 {
        return true;
    }
    run_gen > committed_gen
}

pub fn allow_phase_two(run_gen: i32, committed_gen: i32) -> bool {
    if committed_gen == 0 {
        return true;
    }
    run_gen >= committed_gen
}

pub fn generation_floor(run_gen: i32, committed_gen: i32) -> i32 {
    if run_gen <= committed_gen {
        committed_gen
    } else {
        run_gen
    }
}
