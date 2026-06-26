use crate::types::*;
use crate::analyzer::round_to;

/// Batch consistency analysis.
/// Per Camenisch & Lysyanskaya (2004) §5.1, batch verification requires uniform
/// behavior across sessions. We summarize each session by its representative
/// per-session correlation and report the spread of those summaries; a small
/// spread (below the configured threshold) means the batch behaves consistently.
///
/// The spread is reported as a sample standard deviation (dividing by N - 1),
/// per ISO/IEC 27002:2022 §8.24.
pub fn compute_batch_consistency(
    pairs: &[PairAnalysis],
    sessions: &[String],
    settings: &Settings,
) -> BatchConsistency {
    let mut session_max_scores: Vec<f64> = Vec::new();

    for session_id in sessions {
        let score = pairs
            .iter()
            .filter(|p| &p.session_id == session_id)
            .map(|p| p.correlation_score)
            .fold(f64::INFINITY, f64::min);
        session_max_scores.push(round_to(score, settings.precision));
    }

    let n = session_max_scores.len() as f64;
    let mean = session_max_scores.iter().sum::<f64>() / n;

    let variance = session_max_scores
        .iter()
        .map(|&x| (x - mean).powi(2))
        .sum::<f64>()
        / (n - 1.0);

    let batch_std_deviation = round_to(variance.sqrt(), settings.precision);
    let is_consistent = batch_std_deviation < settings.batch_consistency_max_std;

    BatchConsistency {
        session_max_scores,
        batch_std_deviation,
        is_consistent,
    }
}
