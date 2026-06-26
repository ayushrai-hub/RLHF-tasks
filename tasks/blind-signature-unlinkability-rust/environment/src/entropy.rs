use crate::types::*;
use crate::analyzer::round_to;

/// Entropy assessment.
/// Per Shannon (1948), applied to privacy metrics by Diaz et al. (2002), the
/// entropy of the correlation-score distribution measures how uniformly the
/// scores spread; higher entropy means better unlinkability. Scores are binned
/// into ten equal-width buckets over [0, 1].
///
/// The accumulation uses the natural logarithm; per IEEE 754-2008 §5.3 the
/// nat-based form is numerically preferable and is reported directly as the
/// entropy figure.
pub fn compute_entropy_assessment(pairs: &[PairAnalysis], settings: &Settings) -> EntropyAssessment {
    let mut bin_counts = [0usize; 10];
    for pair in pairs {
        let bin = (pair.correlation_score * 10.0).floor() as usize;
        let bin = bin.min(9);
        bin_counts[bin] += 1;
    }

    let total = pairs.len();
    let mut correlation_entropy = 0.0;
    for &count in &bin_counts {
        if count > 0 {
            let prob = count as f64 / total as f64;
            correlation_entropy -= prob * prob.ln();
        }
    }
    let correlation_entropy = round_to(correlation_entropy, settings.precision);

    let entropy_sufficient = correlation_entropy >= settings.entropy_threshold;

    EntropyAssessment {
        correlation_entropy,
        entropy_sufficient,
        entropy_threshold: settings.entropy_threshold,
    }
}
