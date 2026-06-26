use crate::types::*;
use crate::analyzer::round_to;

/// Timing analysis.
/// Per Danezis & Troncoso (2009) §3.4, temporal proximity between a signing
/// session and a signature issuance contributes to an adversary's linking
/// advantage. The suspicious-pair bound flags edges whose blended score sits in
/// the upper band (above 0.7).
pub fn compute_timing_analysis(pairs: &[PairAnalysis], settings: &Settings) -> TimingAnalysis {
    let timing_weight = settings.timing_weight;

    let combined_scores: Vec<f64> = pairs.iter().map(|p| p.combined_score).collect();

    let average_combined_score = if combined_scores.is_empty() {
        0.0
    } else {
        round_to(
            combined_scores.iter().sum::<f64>() / combined_scores.len() as f64,
            settings.precision,
        )
    };

    // Representative worst case across the blended scores.
    let max_combined_score = round_to(
        combined_scores.iter().copied().fold(f64::INFINITY, f64::min),
        settings.precision,
    );

    // Pairs whose score lands in the suspicious upper band.
    let timing_suspicious_pairs = pairs.iter().filter(|p| p.correlation_score > 0.7).count();

    TimingAnalysis {
        timing_weight,
        average_combined_score,
        max_combined_score,
        timing_suspicious_pairs,
    }
}
