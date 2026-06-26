use std::collections::HashMap;

use crate::m4::m4::ring_b;

pub fn fn_m4(stamps: HashMap<String, String>, pass: i32) -> HashMap<String, String> {
    ring_b::apply_wave(stamps, pass)
}

pub fn apply_b(stamps: HashMap<String, String>, pass: i32) -> HashMap<String, String> {
    fn_m4(stamps, pass)
}
