use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize)]
pub struct TranscriptInput {
    pub signing_sessions: Vec<SigningSession>,
    pub issued_signatures: Vec<IssuedSignature>,
    pub parameters: Parameters,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SigningSession {
    pub id: String,
    pub blinded_msg: String,
    pub signature: String,
    pub timestamp: u64,
    pub nonce: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct IssuedSignature {
    pub id: String,
    pub message: String,
    pub signature: String,
    pub timestamp: u64,
    pub verifier: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Parameters {
    pub security_level_bits: u32,
    pub max_advantage: f64,
    pub max_timing_delta: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct VerificationReport {
    pub summary: Summary,
    pub matching: MatchingAnalysis,
    pub pair_analysis: Vec<PairAnalysis>,
    pub timing_analysis: TimingAnalysis,
    pub entropy_assessment: EntropyAssessment,
    pub batch_consistency: BatchConsistency,
    pub ks_test: KsTestResult,
    pub commitment: CommitmentStrength,
    pub security: SecurityAssessment,
    pub settings_used: SettingsUsed,
}

#[derive(Debug, Clone, Serialize)]
pub struct Summary {
    pub total_pairs: usize,
    pub flagged_pairs: usize,
    pub distinguishing_advantage: f64,
    pub unlinkability_score: f64,
    pub is_unlinkable: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct MatchedPair {
    pub session_id: String,
    pub signature_id: String,
    pub correlation_score: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct MatchingAnalysis {
    pub matched_pairs: Vec<MatchedPair>,
    pub matched_linkable: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct PairAnalysis {
    pub session_id: String,
    pub signature_id: String,
    pub correlation_score: f64,
    pub timing_proximity: f64,
    pub combined_score: f64,
    pub correlation_detected: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct TimingAnalysis {
    pub timing_weight: f64,
    pub average_combined_score: f64,
    pub max_combined_score: f64,
    pub timing_suspicious_pairs: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct EntropyAssessment {
    pub correlation_entropy: f64,
    pub entropy_sufficient: bool,
    pub entropy_threshold: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BatchConsistency {
    pub session_max_scores: Vec<f64>,
    pub batch_std_deviation: f64,
    pub is_consistent: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct KsTestResult {
    pub ks_statistic: f64,
    pub critical_value: f64,
    pub is_uniform: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct CommitmentStrength {
    pub strength_ratio: f64,
    pub p95_correlation: f64,
    pub confidence_bound: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct SecurityAssessment {
    pub security_bits_achieved: f64,
    pub meets_security_level: bool,
    pub security_level_required: u32,
}

#[derive(Debug, Clone, Serialize)]
pub struct SettingsUsed {
    pub detection_threshold: f64,
    pub min_unlinkability_score: f64,
    pub security_level_bits: u32,
    pub timing_weight: f64,
    pub entropy_threshold: f64,
}

#[derive(Debug, Clone)]
pub struct Settings {
    pub detection_threshold: f64,
    pub min_unlinkability_score: f64,
    pub security_level_bits: u32,
    pub precision: usize,
    pub timing_weight: f64,
    pub entropy_threshold: f64,
    pub batch_consistency_max_std: f64,
}
