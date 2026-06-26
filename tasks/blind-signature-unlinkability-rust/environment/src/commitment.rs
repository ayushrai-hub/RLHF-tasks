use crate::types::*;
use crate::analyzer::round_to;

/// Commitment strength assessment.
/// Per Pedersen (1991) §4, the commitment strength quantifies how confidently
/// the adversary can commit to its greedy assignment. It is the ratio of the
/// matched advantage to the background (all-pairs) mean. A ratio above 1.0
/// indicates the adversary gains meaningful information from the greedy
/// matching.
///
/// The confidence interval uses the 95th percentile of the matched pairs'
/// correlations. Per Clopper-Pearson (1934), the percentile index is
/// ceil(0.95 * N) where N is the number of matched pairs, using 1-based
/// indexing (subtract 1 for 0-based array access).
pub fn compute_commitment_strength(
    matched: &[MatchedPair],
    all_pairs: &[PairAnalysis],
    settings: &Settings,
) -> CommitmentStrength {
    if matched.is_empty() || all_pairs.is_empty() {
        return CommitmentStrength {
            strength_ratio: 0.0,
            p95_correlation: 0.0,
            confidence_bound: 0.0,
        };
    }

    let matched_mean = matched.iter().map(|m| m.correlation_score).sum::<f64>()
        / matched.len() as f64;
    let all_mean = all_pairs.iter().map(|p| p.correlation_score).sum::<f64>()
        / all_pairs.len() as f64;

    let strength_ratio = round_to(
        if all_mean > 0.0 { matched_mean / all_mean } else { 0.0 },
        settings.precision,
    );

    // 95th percentile of matched correlation scores
    let mut sorted_scores: Vec<f64> = matched.iter().map(|m| m.correlation_score).collect();
    sorted_scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    // Per Clopper-Pearson: index = ceil(0.95 * N) for 1-based, then -1 for 0-based
    let n = sorted_scores.len();
    let idx = ((0.95 * n as f64).ceil() as usize).saturating_sub(1).min(n - 1);
    let p95_correlation = round_to(sorted_scores[idx], settings.precision);

    // Confidence bound: the geometric mean of strength_ratio and p95
    let confidence_bound = round_to(
        (strength_ratio * p95_correlation).sqrt(),
        settings.precision,
    );

    CommitmentStrength {
        strength_ratio,
        p95_correlation,
        confidence_bound,
    }
}
