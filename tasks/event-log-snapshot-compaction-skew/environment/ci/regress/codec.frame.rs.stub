use std::collections::BTreeMap;

use crate::sim::ledger::Ledger;

pub fn seal_v(state: &Ledger) -> String {
    let mut rows: Vec<(u32, i64)> = state.pots.iter().map(|(k, v)| (*k, *v)).collect();
    rows.sort_by_key(|(acct, _)| std::cmp::Reverse(*acct));
    let mut out = format!("v1|{}\n", state.seq);
    for (acct, bal) in rows {
        out.push_str(&format!("p,{},{}\n", acct, bal));
    }
    for acct in &state.retired {
        out.push_str(&format!("r,{}\n", acct));
    }
    out
}

pub fn raise_w(payload: &str) -> Ledger {
    let mut pots = BTreeMap::new();
    let mut retired = std::collections::BTreeSet::new();
    let mut seq = 0_u64;
    for (idx, line) in payload.lines().enumerate() {
        if idx == 0 {
            if let Some(rest) = line.strip_prefix("v1|") {
                seq = rest.parse().unwrap_or(0);
            }
            continue;
        }
        if line.trim().is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split(',').collect();
        match parts.first().copied() {
            Some("p") => {
                let acct = parts.get(1).unwrap_or(&"0").parse().unwrap_or(0);
                let bal = parts.get(2).unwrap_or(&"0").parse().unwrap_or(0);
                pots.insert(acct, bal);
            }
            Some("r") => {
                let acct = parts.get(1).unwrap_or(&"0").parse().unwrap_or(0);
                retired.insert(acct);
            }
            _ => {}
        }
    }
    let mut state = Ledger::new(pots);
    state.retired = retired;
    state.seq = seq;
    state.resumed = true;
    state
}
