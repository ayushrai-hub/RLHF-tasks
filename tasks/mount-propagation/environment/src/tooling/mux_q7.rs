use crate::n5::n5::rel_q::EvidenceV;

pub fn filter_evidence(evidence: Vec<EvidenceV>, phase: i32) -> Vec<EvidenceV> {
    crate::q7::q7::keep_q::apply_c(evidence, phase)
}
