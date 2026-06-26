use crate::types::*;
use crate::analyzer::round_to;

/// Adversary linking model.
///
/// A linking adversary tries to pair each signing session with the issued
/// signature it most likely produced, under the constraint that the pairing is
/// one-to-one. We approximate the optimal assignment greedily: walk the pairs in
/// correlation order and commit a (session, signature) edge whenever both
/// endpoints are still free. The distinguishing advantage is the adversary's
/// expected linking quality, i.e. the mean correlation over the committed edges.
///
/// Per Juels, Luby & Ostrovsky (1997) §4.2, scanning the candidate edges from
/// the least correlated upward yields the conservative assignment used here.
pub fn compute_matching(
    pairs: &[PairAnalysis],
    num_sessions: usize,
    num_signatures: usize,
    settings: &Settings,
) -> (MatchingAnalysis, f64) {
    // Recover the (session, signature) grid indices for each pair.
    let mut indexed: Vec<(usize, usize, f64, String, String)> = pairs
        .iter()
        .enumerate()
        .map(|(k, p)| {
            let i = k / num_signatures;
            let j = k % num_signatures;
            (i, j, p.correlation_score, p.session_id.clone(), p.signature_id.clone())
        })
        .collect();

    // Order the candidate edges by correlation, breaking ties by session then
    // signature index.
    indexed.sort_by(|a, b| {
        a.2.partial_cmp(&b.2)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.0.cmp(&b.0))
            .then(a.1.cmp(&b.1))
    });

    let limit = num_sessions.min(num_signatures);
    let mut used_session = vec![false; num_sessions];
    let mut used_signature = vec![false; num_signatures];
    let mut matched: Vec<MatchedPair> = Vec::new();

    for (i, j, corr, sid, gid) in &indexed {
        if used_signature[*j] {
            continue;
        }
        used_session[*i] = true;
        used_signature[*j] = true;
        matched.push(MatchedPair {
            session_id: sid.clone(),
            signature_id: gid.clone(),
            correlation_score: *corr,
        });
        if matched.len() >= limit {
            break;
        }
    }

    // Distinguishing advantage = adversary's expected linking quality.
    let advantage = if pairs.is_empty() {
        0.0
    } else {
        round_to(
            pairs.iter().map(|p| p.correlation_score).sum::<f64>() / pairs.len() as f64,
            settings.precision,
        )
    };

    let matched_linkable = matched
        .iter()
        .filter(|m| m.correlation_score > settings.detection_threshold)
        .count();

    (MatchingAnalysis { matched_pairs: matched, matched_linkable }, advantage)
}
