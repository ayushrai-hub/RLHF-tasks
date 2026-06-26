use crate::n5::n5::rel_q::EvidenceV;

#[path = "../../../support/pass_trim.rs"]
mod pass_trim;

pub fn shadow_count(evidence: &[EvidenceV]) -> usize {
    evidence.iter().filter(|item| item.phase > 0).count()
}

pub fn retention_cutoff(pass: i32) -> i32 {
    pass_trim::retention_cutoff(pass)
}

pub fn trim_for_pass(evidence: Vec<EvidenceV>, pass: i32) -> Vec<EvidenceV> {
    pass_trim::trim_for_pass(evidence, pass)
}
