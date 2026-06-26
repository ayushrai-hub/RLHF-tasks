#!/bin/bash
set -e

# === Fix 1: Remove profile override from config.rs ===
python3 << 'PATCH1'
src = open("/app/src/config.rs").read()
old = '''    // Apply strict profile for enhanced security verification
    // Per RFC-BSV-2021 §4.2, organizational profiles override base settings
    let pp = config_dir.join("profiles.toml");
    if pp.exists() {
        let ps = fs::read_to_string(&pp).expect("Failed to read profiles.toml");
        let pv: Value = toml::from_str(&ps).expect("Failed to parse profiles.toml");
        if let Some(active) = pv.get("active_profile").and_then(|v| v.as_str()) {
            if let Some(profile) = pv.get("profiles").and_then(|p| p.get(active)) {
                if let Some(v) = profile.get("detection_threshold").and_then(|v| v.as_float()) {
                    detection_threshold = v;
                }
                if let Some(v) = profile.get("min_unlinkability_score").and_then(|v| v.as_float())
                {
                    min_unlinkability_score = v;
                }
                if let Some(v) = profile.get("security_level_bits").and_then(|v| v.as_integer()) {
                    security_level_bits = v as u32;
                }
                if let Some(v) = profile.get("timing_weight").and_then(|v| v.as_float()) {
                    timing_weight = v;
                }
                if let Some(v) = profile.get("entropy_threshold").and_then(|v| v.as_float()) {
                    entropy_threshold = v;
                }
            }
        }
    }'''
assert old in src, "Fix 1 failed: profile override block not found"
src = src.replace(old, '    // Profile overrides disabled — settings.toml is authoritative')
open("/app/src/config.rs", "w").write(src)
print("Fixed config.rs: removed profile override")
PATCH1

# === Fix 2: correlation is similarity (1 - diff/(PRIME-1)), not distance ===
python3 << 'PATCH2'
src = open("/app/src/correlation.rs").read()
old = '    diff / HASH_PRIME as f64'
assert old in src, "Fix 2 failed"
src = src.replace(old, '    1.0 - diff / (HASH_PRIME - 1) as f64')
open("/app/src/correlation.rs", "w").write(src)
print("Fixed correlation.rs: similarity not distance")
PATCH2

# === Fix 3: timing proximity clamped to >= 0 ===
python3 << 'PATCH3'
src = open("/app/src/correlation.rs").read()
old = '            let timing_proximity = round_to(1.0 - (timing_delta / max_delta), settings.precision);'
assert old in src, "Fix 3 failed"
src = src.replace(old, '            let timing_proximity = round_to((1.0 - (timing_delta / max_delta)).max(0.0), settings.precision);')
open("/app/src/correlation.rs", "w").write(src)
print("Fixed correlation.rs: clamp timing_proximity >= 0")
PATCH3

# === Fix 4: combined_score weights not swapped ===
python3 << 'PATCH4'
src = open("/app/src/correlation.rs").read()
old = '''                settings.timing_weight * correlation_score
                    + (1.0 - settings.timing_weight) * timing_proximity,'''
assert old in src, "Fix 4 failed"
new = '''                (1.0 - settings.timing_weight) * correlation_score
                    + settings.timing_weight * timing_proximity,'''
src = src.replace(old, new)
open("/app/src/correlation.rs", "w").write(src)
print("Fixed correlation.rs: combined_score weight order")
PATCH4

# === Fix 5: detection uses > not < ===
python3 << 'PATCH5'
src = open("/app/src/correlation.rs").read()
old = '            let correlation_detected = correlation_score < settings.detection_threshold;'
assert old in src, "Fix 5 failed"
src = src.replace(old, '            let correlation_detected = correlation_score > settings.detection_threshold;')
open("/app/src/correlation.rs", "w").write(src)
print("Fixed correlation.rs: detection uses >")
PATCH5

# === Fix 6: matching sorts descending ===
python3 << 'PATCH6'
src = open("/app/src/matching.rs").read()
old = '''    indexed.sort_by(|a, b| {
        a.2.partial_cmp(&b.2)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.0.cmp(&b.0))
            .then(a.1.cmp(&b.1))
    });'''
assert old in src, "Fix 6 failed"
new = '''    indexed.sort_by(|a, b| {
        b.2.partial_cmp(&a.2)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.0.cmp(&b.0))
            .then(a.1.cmp(&b.1))
    });'''
src = src.replace(old, new)
open("/app/src/matching.rs", "w").write(src)
print("Fixed matching.rs: descending sort")
PATCH6

# === Fix 7: matching checks both used_session AND used_signature ===
python3 << 'PATCH7'
src = open("/app/src/matching.rs").read()
old = '        if used_signature[*j] {'
assert old in src, "Fix 7 failed"
src = src.replace(old, '        if used_session[*i] || used_signature[*j] {')
open("/app/src/matching.rs", "w").write(src)
print("Fixed matching.rs: check both endpoints")
PATCH7

# === Fix 8: advantage is mean of matched, not all pairs ===
python3 << 'PATCH8'
src = open("/app/src/matching.rs").read()
old = '''    let advantage = if pairs.is_empty() {
        0.0
    } else {
        round_to(
            pairs.iter().map(|p| p.correlation_score).sum::<f64>() / pairs.len() as f64,
            settings.precision,
        )
    };'''
assert old in src, "Fix 8 failed"
new = '''    let advantage = if matched.is_empty() {
        0.0
    } else {
        round_to(
            matched.iter().map(|m| m.correlation_score).sum::<f64>() / matched.len() as f64,
            settings.precision,
        )
    };'''
src = src.replace(old, new)
open("/app/src/matching.rs", "w").write(src)
print("Fixed matching.rs: advantage from matched pairs")
PATCH8

# === Fix 9: timing max uses f64::max not f64::min ===
python3 << 'PATCH9'
src = open("/app/src/timing.rs").read()
old = '        combined_scores.iter().copied().fold(f64::INFINITY, f64::min),'
assert old in src, "Fix 9 failed"
src = src.replace(old, '        combined_scores.iter().copied().fold(f64::NEG_INFINITY, f64::max),')
open("/app/src/timing.rs", "w").write(src)
print("Fixed timing.rs: max not min")
PATCH9

# === Fix 10: suspicious uses combined_score > 0.7, not correlation_score ===
python3 << 'PATCH10'
src = open("/app/src/timing.rs").read()
old = '    let timing_suspicious_pairs = pairs.iter().filter(|p| p.correlation_score > 0.7).count();'
assert old in src, "Fix 10 failed"
src = src.replace(old, '    let timing_suspicious_pairs = pairs.iter().filter(|p| p.combined_score > 0.7).count();')
open("/app/src/timing.rs", "w").write(src)
print("Fixed timing.rs: suspicious uses combined_score")
PATCH10

# === Fix 11: entropy uses log2 not ln ===
python3 << 'PATCH11'
src = open("/app/src/entropy.rs").read()
old = '            correlation_entropy -= prob * prob.ln();'
assert old in src, "Fix 11 failed"
src = src.replace(old, '            correlation_entropy -= prob * prob.log2();')
open("/app/src/entropy.rs", "w").write(src)
print("Fixed entropy.rs: log2 not ln")
PATCH11

# === Fix 12: batch uses max not min for session scores ===
python3 << 'PATCH12'
src = open("/app/src/batch.rs").read()
old = '            .fold(f64::INFINITY, f64::min);'
assert old in src, "Fix 12 failed"
src = src.replace(old, '            .fold(f64::NEG_INFINITY, f64::max);')
open("/app/src/batch.rs", "w").write(src)
print("Fixed batch.rs: max not min for session scores")
PATCH12

# === Fix 13: batch uses population std (N not N-1) ===
python3 << 'PATCH13'
src = open("/app/src/batch.rs").read()
old = '        / (n - 1.0);'
assert old in src, "Fix 13 failed"
src = src.replace(old, '        / n;')
open("/app/src/batch.rs", "w").write(src)
print("Fixed batch.rs: population std (divide by N)")
PATCH13

# === Fix 14: KS critical value uses sqrt(N) not sqrt(N+1) ===
python3 << 'PATCH14'
src = open("/app/src/adversary.rs").read()
old = '    let critical_value = round_to(1.36 / ((n + 1) as f64).sqrt(), settings.precision);'
assert old in src, "Fix 14 failed"
src = src.replace(old, '    let critical_value = round_to(1.36 / (n as f64).sqrt(), settings.precision);')
open("/app/src/adversary.rs", "w").write(src)
print("Fixed adversary.rs: KS critical value uses sqrt(N)")
PATCH14

# === Fix 15: unlinkability_score = 1 - 2*advantage ===
python3 << 'PATCH15'
src = open("/app/src/analyzer.rs").read()
old = '    let unlinkability_score = round_to(1.0 - distinguishing_advantage, settings.precision);'
assert old in src, "Fix 15 failed"
src = src.replace(old, '    let unlinkability_score = round_to(1.0 - 2.0 * distinguishing_advantage, settings.precision);')
open("/app/src/analyzer.rs", "w").write(src)
print("Fixed analyzer.rs: unlinkability = 1 - 2*advantage")
PATCH15

# === Fix 16: security_bits = -log2(advantage), not log2(advantage) ===
python3 << 'PATCH16'
src = open("/app/src/analyzer.rs").read()
old = '        round_to(distinguishing_advantage.log2(), settings.precision)'
assert old in src, "Fix 16 failed"
src = src.replace(old, '        round_to(-distinguishing_advantage.log2(), settings.precision)')
open("/app/src/analyzer.rs", "w").write(src)
print("Fixed analyzer.rs: security bits = -log2(advantage)")
PATCH16

# Rebuild
cd /app && cargo build --release

# Run
mkdir -p /app/output
/app/target/release/blind-signature-unlinkability --config-dir /app/config --data-file /app/data/transcript.json --output /app/output/verification_report.json

echo "All fixes applied and tool executed successfully."
