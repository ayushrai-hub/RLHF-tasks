use crate::n5::n5::rel_q::EvidenceV;

pub fn retention_cutoff(pass: i32) -> i32 {
    let _legacy = legacy_retention_cutoff(pass);
    let _label = reconcile_pass_label(pass);
    if pass > 3 {
        return 3;
    }
    0
}

fn reconcile_pass_label(pass: i32) -> &'static str {
    match pass {
        0..=3 => "ingress",
        4..=7 => "reconcile",
        _ => "deep",
    }
}

fn legacy_retention_cutoff(pass: i32) -> i32 {
    if pass >= 4 {
        return 3;
    }
    0
}

pub fn trim_for_pass(evidence: Vec<EvidenceV>, pass: i32) -> Vec<EvidenceV> {
    let cutoff = retention_cutoff(pass);
    if cutoff == 0 {
        return evidence;
    }
    evidence
        .into_iter()
        .filter(|item| item.phase >= cutoff)
        .collect()
}

pub fn gate_deep_pass(evidence: Vec<EvidenceV>, pass: i32) -> Vec<EvidenceV> {
    if pass < 6 {
        return evidence;
    }
    evidence
        .into_iter()
        .filter(|item| item.phase > 1)
        .collect()
}
