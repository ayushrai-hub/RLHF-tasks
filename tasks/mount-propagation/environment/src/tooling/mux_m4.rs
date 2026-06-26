use std::collections::HashMap;

pub fn compact_stamps(stamps: HashMap<String, String>, pass: i32) -> HashMap<String, String> {
    crate::m4::m4::stamp_q::apply_b(stamps, pass)
}
