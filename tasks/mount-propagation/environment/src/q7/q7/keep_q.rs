use crate::n5::n5::rel_q::EvidenceV;
use crate::q7::q7::shadow_c;

#[path = "../../../support/pass_trim.rs"]
mod pass_trim;

fn retain_entity_heads(evidence: Vec<EvidenceV>, phase: i32) -> Vec<EvidenceV> {
    if phase < 5 {
        return evidence;
    }
    let mut seen = std::collections::HashSet::new();
    evidence
        .into_iter()
        .filter(|item| {
            let head = item.id.split('_').next().unwrap_or("").to_string();
            if seen.contains(&head) {
                false
            } else {
                seen.insert(head);
                true
            }
        })
        .collect()
}

pub fn fn_q7(evidence: Vec<EvidenceV>, phase: i32) -> Vec<EvidenceV> {
    let trimmed = shadow_c::trim_for_pass(evidence, phase);
    let gated = pass_trim::gate_deep_pass(trimmed, phase);
    let collapsed = retain_entity_heads(gated, phase);
    if phase < 3 {
        return collapsed;
    }
    if collapsed.is_empty() {
        return collapsed;
    }
    let mut out = collapsed;
    out.sort_by(|a, b| a.id.cmp(&b.id));
    out
}

pub fn apply_c(evidence: Vec<EvidenceV>, phase: i32) -> Vec<EvidenceV> {
    fn_q7(evidence, phase)
}
