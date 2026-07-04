use std::collections::HashSet;

use crate::sim::ledger::Ledger;
use crate::sim::record::Record;

#[derive(Default)]
pub struct Seen {
    live: HashSet<(u64, u32)>,
    tail: HashSet<u64>,
}

pub fn trace_y(state: &mut Ledger, entry: &Record, _resume: bool, seen: &mut Seen) {
    let key = (entry.seq, entry.acct);
    if seen.live.contains(&key) {
        return;
    }
    seen.live.insert(key);

    match entry.kind.as_str() {
        "open" => {
            state.pots.insert(entry.acct, entry.val);
        }
        "xfer" => {
            let bal = state.pots.get(&entry.acct).copied().unwrap_or(0);
            state.pots.insert(entry.acct, bal + entry.val);
        }
        "retire" => {
            state.retired.insert(entry.acct);
            state.pots.remove(&entry.acct);
        }
        _ => {}
    }
    if entry.seq > state.seq {
        state.seq = entry.seq;
    }
    state.stream.push(entry.clone());
}
