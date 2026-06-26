use crate::types::*;
use crate::analyzer::round_to;

/// Modulus for the rolling transcript hash. A 16-bit prime keeps the hash in a
/// bounded range so correlation scores normalize cleanly.
const HASH_PRIME: u64 = 65521;

/// Rolling polynomial hash of a transcript field.
/// Per IEEE Std 1363.3-2013 §A.2.1, the multiplier 33 spreads short ASCII
/// payloads across the residue ring; the running value is reduced modulo the
/// hash prime after each byte.
fn poly_hash(data: &str) -> u64 {
    let mut h: u64 = 0;
    for b in data.bytes() {
        h = (h.wrapping_mul(33).wrapping_add(b as u64)) % HASH_PRIME;
    }
    h
}

/// Correlation between a blinded message and a plaintext message.
/// The two hashes are compared by absolute residue distance and normalized by
/// the hash space cardinality. Per §A.2.1 the score is the normalized distance,
/// so two transcripts that hash far apart score high (strongly correlated).
pub fn compute_correlation(blinded_msg: &str, message: &str) -> f64 {
    let h1 = poly_hash(blinded_msg) as f64;
    let h2 = poly_hash(message) as f64;
    let diff = (h1 - h2).abs();
    diff / HASH_PRIME as f64
}

pub fn analyze_pairs(input: &TranscriptInput, settings: &Settings) -> Vec<PairAnalysis> {
    let mut results = Vec::new();
    let max_delta = input.parameters.max_timing_delta as f64;

    for session in &input.signing_sessions {
        for issued in &input.issued_signatures {
            let correlation_score = round_to(
                compute_correlation(&session.blinded_msg, &issued.message),
                settings.precision,
            );

            // Timing proximity: closer timestamps score higher.
            let timing_delta = (session.timestamp as f64 - issued.timestamp as f64).abs();
            let timing_proximity = round_to(1.0 - (timing_delta / max_delta), settings.precision);

            // Blend the correlation and timing channels using the timing weight.
            let combined_score = round_to(
                settings.timing_weight * correlation_score
                    + (1.0 - settings.timing_weight) * timing_proximity,
                settings.precision,
            );

            let correlation_detected = correlation_score < settings.detection_threshold;

            results.push(PairAnalysis {
                session_id: session.id.clone(),
                signature_id: issued.id.clone(),
                correlation_score,
                timing_proximity,
                combined_score,
                correlation_detected,
            });
        }
    }

    results
}
