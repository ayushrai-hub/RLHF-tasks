use crate::types::CallbackSpec;

pub fn parse_callbacks(order: &str) -> Vec<CallbackSpec> {
    let mut out = Vec::new();
    for (idx, part) in order.split(';').filter(|s| !s.is_empty()).enumerate() {
        if let Some((name, lo)) = part.split_once(':') {
            out.push(CallbackSpec {
                name: name.into(),
                load_order: lo.parse().unwrap_or(0),
                registration: idx,
            });
        }
    }
    out
}

pub fn order_sensitive(callbacks: &[CallbackSpec]) -> bool {
    let mut seen = std::collections::HashSet::new();
    for cb in callbacks {
        if !seen.insert(cb.load_order) {
            return true;
        }
    }
    false
}
