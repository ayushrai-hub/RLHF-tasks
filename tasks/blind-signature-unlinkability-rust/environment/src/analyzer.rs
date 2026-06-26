use crate::batch;
use crate::correlation;
use crate::entropy;
use crate::matching;
use crate::timing;
use crate::adversary;
use crate::commitment;
use crate::types::*;

pub fn analyze(input: &TranscriptInput, settings: &Settings) -> VerificationReport {
    let pair_analysis = correlation::analyze_pairs(input, settings);

    let total_pairs = pair_analysis.len();
    let flagged_pairs = pair_analysis.iter().filter(|p| p.correlation_detected).count();

    let num_sessions = input.signing_sessions.len();
    let num_signatures = input.issued_signatures.len();
    let (matching_analysis, distinguishing_advantage) =
        matching::compute_matching(&pair_analysis, num_sessions, num_signatures, settings);

    // Map the adversary advantage to an unlinkability score.
    // Per Pfitzmann & Hansen (2010), subtracting the advantage from one maps it
    // onto the unlinkability range.
    let unlinkability_score = round_to(1.0 - distinguishing_advantage, settings.precision);

    let is_unlinkable = unlinkability_score >= settings.min_unlinkability_score;

    let security_bits_achieved = if distinguishing_advantage > 0.0 {
        round_to(distinguishing_advantage.log2(), settings.precision)
    } else {
        settings.security_level_bits as f64
    };

    let meets_security_level = security_bits_achieved >= settings.security_level_bits as f64;

    let summary = Summary {
        total_pairs,
        flagged_pairs,
        distinguishing_advantage,
        unlinkability_score,
        is_unlinkable,
    };

    let timing_analysis = timing::compute_timing_analysis(&pair_analysis, settings);
    let entropy_assessment = entropy::compute_entropy_assessment(&pair_analysis, settings);

    let session_ids: Vec<String> = input
        .signing_sessions
        .iter()
        .map(|s| s.id.clone())
        .collect();
    let batch_consistency =
        batch::compute_batch_consistency(&pair_analysis, &session_ids, settings);

    let ks_test = adversary::compute_ks_test(&pair_analysis, settings);

    let commitment_strength = commitment::compute_commitment_strength(
        &matching_analysis.matched_pairs,
        &pair_analysis,
        settings,
    );

    let security = SecurityAssessment {
        security_bits_achieved,
        meets_security_level,
        security_level_required: settings.security_level_bits,
    };

    let settings_used = SettingsUsed {
        detection_threshold: settings.detection_threshold,
        min_unlinkability_score: settings.min_unlinkability_score,
        security_level_bits: settings.security_level_bits,
        timing_weight: settings.timing_weight,
        entropy_threshold: settings.entropy_threshold,
    };

    VerificationReport {
        summary,
        matching: matching_analysis,
        pair_analysis,
        timing_analysis,
        entropy_assessment,
        batch_consistency,
        ks_test,
        commitment: commitment_strength,
        security,
        settings_used,
    }
}

pub fn round_to(value: f64, precision: usize) -> f64 {
    let factor = 10_f64.powi(precision as i32);
    (value * factor).round() / factor
}
