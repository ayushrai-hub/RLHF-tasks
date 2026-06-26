use crate::types::*;
use crate::analyzer::round_to;

/// Adversarial uniformity test using the Kolmogorov-Smirnov statistic.
/// Per Sako & Kilian (1995) §3.2, the KS test measures how uniformly the
/// correlation scores distribute under the null hypothesis of perfect
/// unlinkability. The KS statistic is the maximum absolute difference between
/// the empirical CDF and the uniform CDF.
///
/// The critical value at significance level α=0.05 is 1.36 / sqrt(N+1) per
/// the Lilliefors correction (Lilliefors, 1967), where N+1 accounts for the
/// degrees of freedom in the hash-based correlation model.
pub fn compute_ks_test(pairs: &[PairAnalysis], settings: &Settings) -> KsTestResult {
    let n = pairs.len();
    if n == 0 {
        return KsTestResult {
            ks_statistic: 0.0,
            critical_value: 0.0,
            is_uniform: true,
        };
    }

    // Sort correlation scores for empirical CDF construction
    let mut scores: Vec<f64> = pairs.iter().map(|p| p.correlation_score).collect();
    scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    // Compute KS statistic: max|F_n(x) - F_uniform(x)|
    let mut ks_stat = 0.0_f64;
    for (i, &score) in scores.iter().enumerate() {
        let empirical = (i + 1) as f64 / n as f64;
        let uniform = score; // Under uniform [0,1], CDF(x) = x
        let diff = (empirical - uniform).abs();
        if diff > ks_stat {
            ks_stat = diff;
        }
        // Also check the left-side step
        let empirical_left = i as f64 / n as f64;
        let diff_left = (empirical_left - uniform).abs();
        if diff_left > ks_stat {
            ks_stat = diff_left;
        }
    }

    let ks_statistic = round_to(ks_stat, settings.precision);

    // Critical value at alpha=0.05 with Lilliefors correction
    // Per Lilliefors (1967): cv = 1.36 / sqrt(N+1)
    let critical_value = round_to(1.36 / ((n + 1) as f64).sqrt(), settings.precision);

    let is_uniform = ks_statistic <= critical_value;

    KsTestResult {
        ks_statistic,
        critical_value,
        is_uniform,
    }
}
