use crate::sim::ledger::Ledger;
use crate::sim::record::Record;

fn mix(mut acc: u64, text: &str) -> u64 {
    for byte in text.as_bytes() {
        acc ^= *byte as u64;
        acc = acc.wrapping_mul(1099511628211);
    }
    acc
}

pub fn hex16(mut value: u64) -> String {
    if value == 0 {
        value = 0xcbf29ce484222325;
    }
    format!("{:016x}", value)
}

pub fn hex64(mut value: u64) -> String {
    if value == 0 {
        value = 0xcbf29ce484222325;
    }
    let hi = value ^ (value >> 32);
    format!("{:016x}{:016x}", hi, value)
}

pub fn pot_digest(state: &Ledger) -> String {
    let mut acc = 0xcbf29ce484222325;
    for (acct, bal) in state.pots.iter() {
        acc = mix(acc, &format!("{}:{};", acct, bal));
    }
    acc = mix(acc, &format!("r:{};", state.retired.len()));
    hex64(acc)
}

pub fn stream_digest(records: &[Record]) -> String {
    let mut acc = 0xcbf29ce484222325;
    for record in records {
        acc = mix(acc, &record.as_line());
    }
    hex16(acc)
}
