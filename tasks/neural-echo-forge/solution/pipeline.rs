use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::export::publish;
use crate::ingest::load::{discover_session_shards, policy_path, sessions_root};
use crate::ingest::parse::{parse_memory_fields, parse_profile_baseline};
use crate::staging::staging_ledger::{self, StagingLedger};

const SNAPSHOT_PATH: &str = "/app/state/memory-snapshot.json";
const PROFILES_PATH: &str = "/app/data/profiles/user-profiles.json";
const TOOL_PATH: &str = "/app/data/tool-calls/tool-log.jsonl";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryRecord {
    pub memory_id: String,
    pub subject: String,
    pub predicate: String,
    pub object: String,
    pub confidence: f64,
    pub tier: String,
    pub anchor_ms: u64,
    pub source: String,
    pub discovery_seq: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub merged_from: Option<Vec<String>>,
    // Supersession target of a correction row. Never serialized into the snapshot;
    // used only while resolving correction chains to a fixpoint within a group.
    #[serde(skip)]
    pub correction_target: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Snapshot {
    pub snapshot_version: u32,
    pub snapshot_seq: u32,
    pub lines_skipped: u32,
    pub reference_anchor_ms: u64,
    pub sources_loaded: Vec<String>,
    pub active_memories: Vec<MemoryRecord>,
    pub superseded_memories: Vec<MemoryRecord>,
    pub retention_vault: Vec<MemoryRecord>,
    pub ingest_fingerprint: String,
}

#[derive(Debug, Clone)]
struct Policy {
    conflict_mode: String,
    export_mode: String,
    max_per_predicate: usize,
    short_ttl_ms: u64,
    export_drop_tiers: HashSet<String>,
}

fn prior_snapshot_seq() -> u32 {
    if let Ok(text) = fs::read_to_string(SNAPSHOT_PATH) {
        if let Ok(val) = serde_json::from_str::<Value>(&text) {
            return val
                .get("snapshot_seq")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as u32;
        }
    }
    0
}

fn load_policy() -> Result<Policy, String> {
    let path = policy_path()?;
    let raw: Value =
        serde_json::from_str(&fs::read_to_string(&path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    let export_mode = raw
        .get("export_mode")
        .and_then(|v| v.as_str())
        .unwrap_or("closed")
        .to_string();
    if export_mode != "closed" && export_mode != "open" {
        return Err("invalid export_mode in policy".into());
    }
    let conflict_mode = raw
        .get("conflict_mode")
        .and_then(|v| v.as_str())
        .unwrap_or(&export_mode)
        .to_string();
    if conflict_mode != "closed" && conflict_mode != "open" {
        return Err("invalid conflict_mode in policy".into());
    }
    let max_per_predicate = raw
        .get("max_per_predicate")
        .and_then(|v| v.as_u64())
        .unwrap_or(1) as usize;
    let short_ttl_ms = raw
        .get("tier_ttl_ms")
        .and_then(|v| v.get("short"))
        .and_then(|v| v.as_u64())
        .unwrap_or(604_800_000);
    let mut export_drop_tiers = HashSet::new();
    if let Some(arr) = raw.get("export_drop_tiers").and_then(|v| v.as_array()) {
        for item in arr {
            if let Some(s) = item.as_str() {
                export_drop_tiers.insert(s.to_string());
            }
        }
    }
    Ok(Policy {
        conflict_mode,
        export_mode,
        max_per_predicate,
        short_ttl_ms,
        export_drop_tiers,
    })
}

fn normalize_object(object: &str) -> String {
    object
        .to_lowercase()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

fn levenshtein(a: &str, b: &str) -> usize {
    let a_chars: Vec<char> = a.chars().collect();
    let b_chars: Vec<char> = b.chars().collect();
    let mut prev: Vec<usize> = (0..=b_chars.len()).collect();
    for (i, ca) in a_chars.iter().enumerate() {
        let mut curr = vec![i + 1];
        for (j, cb) in b_chars.iter().enumerate() {
            let cost = if ca == cb { 0 } else { 1 };
            curr.push(
                (prev[j + 1] + 1)
                    .min(curr[j] + 1)
                    .min(prev[j] + cost),
            );
        }
        prev = curr;
    }
    prev[b_chars.len()]
}

fn semantic_duplicate(a: &MemoryRecord, b: &MemoryRecord) -> bool {
    if a.subject != b.subject || a.predicate != b.predicate {
        return false;
    }
    let na = normalize_object(&a.object);
    let nb = normalize_object(&b.object);
    if na == nb {
        return true;
    }
    let (shorter, longer) = if na.len() <= nb.len() {
        (&na, &nb)
    } else {
        (&nb, &na)
    };
    if shorter.len() >= 6 && longer.starts_with(shorter) {
        return true;
    }
    levenshtein(&na, &nb) <= 2
}

fn pick_winner(a: &MemoryRecord, b: &MemoryRecord, conflict_mode: &str) -> MemoryRecord {
    if conflict_mode == "open" {
        if (a.confidence - b.confidence).abs() > f64::EPSILON {
            return if a.confidence > b.confidence {
                a.clone()
            } else {
                b.clone()
            };
        }
        if a.anchor_ms != b.anchor_ms {
            return if a.anchor_ms > b.anchor_ms {
                a.clone()
            } else {
                b.clone()
            };
        }
    } else if a.anchor_ms != b.anchor_ms {
        return if a.anchor_ms > b.anchor_ms {
            a.clone()
        } else {
            b.clone()
        };
    } else if (a.confidence - b.confidence).abs() > f64::EPSILON {
        return if a.confidence > b.confidence {
            a.clone()
        } else {
            b.clone()
        };
    }
    if a.memory_id >= b.memory_id {
        a.clone()
    } else {
        b.clone()
    }
}

fn group_key(rec: &MemoryRecord) -> (String, String) {
    (rec.subject.clone(), rec.predicate.clone())
}

fn resolve_group(mut candidates: Vec<MemoryRecord>, conflict_mode: &str) -> (MemoryRecord, Vec<MemoryRecord>) {
    let mut superseded = Vec::new();
    let mut corrections: Vec<MemoryRecord> = Vec::new();
    let mut rest: Vec<MemoryRecord> = Vec::new();

    for cand in candidates.drain(..) {
        if cand.source == "session_correction" {
            corrections.push(cand);
        } else {
            rest.push(cand);
        }
    }

    // Corrections form a supersession graph resolved to a fixpoint within this
    // subject/predicate group. Each correction carries a supersession target and a
    // possibly-new memory_id. A correction applies only when its target is currently
    // present among the non-correction survivors, which may itself be a memory_id
    // produced by an earlier correction in a chain. We iterate until no further
    // correction can apply; corrections whose target never becomes present -- missing
    // targets, cross-group targets, and cyclic corrections that would only satisfy one
    // another -- are all superseded without joining temporal precedence.
    let mut pending: Vec<MemoryRecord> = corrections;
    loop {
        let mut progressed = false;
        let mut still_pending: Vec<MemoryRecord> = Vec::new();
        for corr in pending.drain(..) {
            let target = corr.correction_target.clone().unwrap_or_default();
            let present = rest.iter().any(|r| r.memory_id == target);
            if present {
                rest.retain(|r| {
                    if r.memory_id == target {
                        superseded.push(r.clone());
                        false
                    } else {
                        true
                    }
                });
                rest.push(corr);
                progressed = true;
            } else {
                still_pending.push(corr);
            }
        }
        pending = still_pending;
        if !progressed || pending.is_empty() {
            break;
        }
    }
    for corr in pending {
        superseded.push(corr);
    }

    let mut winner = rest
        .first()
        .cloned()
        .unwrap_or_else(|| MemoryRecord {
            memory_id: String::new(),
            subject: String::new(),
            predicate: String::new(),
            object: String::new(),
            confidence: 0.0,
            tier: "short".to_string(),
            anchor_ms: 0,
            source: String::new(),
            discovery_seq: 0,
            merged_from: None,
            correction_target: None,
        });

    for cand in rest.into_iter().skip(1) {
        let next = pick_winner(&winner, &cand, conflict_mode);
        if next.memory_id != winner.memory_id {
            superseded.push(winner);
        } else {
            superseded.push(cand);
        }
        winner = next;
    }

    (winner, superseded)
}

fn semantic_dedup(mut winners: Vec<MemoryRecord>, conflict_mode: &str) -> (Vec<MemoryRecord>, Vec<MemoryRecord>) {
    let mut superseded = Vec::new();
    let mut kept: Vec<MemoryRecord> = Vec::new();

    for cand in winners.drain(..) {
        let mut merged = Vec::new();
        let mut merged_indices = Vec::new();
        for (idx, existing) in kept.iter().enumerate() {
            if semantic_duplicate(&cand, existing) {
                merged.push(existing.clone());
                merged_indices.push(idx);
            }
        }
        if merged.is_empty() {
            kept.push(cand);
            continue;
        }
        let mut pool = merged;
        pool.push(cand);
        let mut best = pool[0].clone();
        for item in pool.iter().skip(1) {
            let next = pick_winner(&best, item, conflict_mode);
            if next.memory_id != best.memory_id {
                superseded.push(best);
            } else {
                superseded.push(item.clone());
            }
            best = next;
        }
        for idx in merged_indices.into_iter().rev() {
            let removed = kept.remove(idx);
            if removed.memory_id != best.memory_id {
                superseded.push(removed);
            }
        }
        let mut merged_from: Vec<String> = superseded
            .iter()
            .filter(|s| semantic_duplicate(s, &best))
            .map(|s| s.memory_id.clone())
            .collect();
        merged_from.sort();
        merged_from.dedup();
        if !merged_from.is_empty() {
            best.merged_from = Some(merged_from);
        }
        kept.push(best);
    }

    (kept, superseded)
}

fn apply_retention(
    mut records: Vec<MemoryRecord>,
    policy: &Policy,
    reference_anchor_ms: u64,
) -> (Vec<MemoryRecord>, Vec<MemoryRecord>) {
    let mut vault = Vec::new();
    let mut active = Vec::new();

    for rec in records.drain(..) {
        if policy.export_drop_tiers.contains(&rec.tier) {
            vault.push(rec);
            continue;
        }
        if rec.tier == "short" && reference_anchor_ms.saturating_sub(rec.anchor_ms) > policy.short_ttl_ms
        {
            vault.push(rec);
            continue;
        }
        active.push(rec);
    }

    let mut grouped: BTreeMap<(String, String), Vec<MemoryRecord>> = BTreeMap::new();
    for rec in active.drain(..) {
        grouped.entry(group_key(&rec)).or_default().push(rec);
    }

    let mut final_active = Vec::new();
    for (_key, mut group) in grouped {
        group.sort_by(|a, b| {
            b.anchor_ms
                .cmp(&a.anchor_ms)
                .then(
                    b.confidence
                        .partial_cmp(&a.confidence)
                        .unwrap_or(std::cmp::Ordering::Equal),
                )
                .then(b.memory_id.cmp(&a.memory_id))
        });
        for (idx, rec) in group.into_iter().enumerate() {
            if idx < policy.max_per_predicate {
                final_active.push(rec);
            } else {
                vault.push(rec);
            }
        }
    }

    final_active.sort_by(|a, b| a.anchor_ms.cmp(&b.anchor_ms).then(a.memory_id.cmp(&b.memory_id)));
    vault.sort_by(|a, b| a.anchor_ms.cmp(&b.anchor_ms).then(a.memory_id.cmp(&b.memory_id)));

    (final_active, vault)
}

pub fn fingerprint(snapshot: &Snapshot) -> String {
    let mut lines = Vec::new();
    lines.push(snapshot.reference_anchor_ms.to_string());
    lines.push(snapshot.sources_loaded.join(","));
    for rec in &snapshot.active_memories {
        lines.push(format!(
            "{}:{}:{}:{}:{}",
            rec.memory_id, rec.subject, rec.predicate, rec.object, rec.anchor_ms
        ));
    }
    for rec in &snapshot.retention_vault {
        lines.push(format!(
            "{}:{}:{}",
            rec.memory_id, rec.subject, rec.predicate
        ));
    }
    let payload = lines.join("\n");
    format!("{:x}", Sha256::digest(payload.as_bytes()))
}

fn ingest_all() -> Result<(Snapshot, StagingLedger), String> {
    let policy = load_policy()?;
    let mut sources_loaded = Vec::new();
    let mut lines_skipped = 0u32;
    let mut discovery_seq = 0u32;
    let mut candidates: Vec<MemoryRecord> = Vec::new();
    let mut reference_anchor_ms = 0u64;

    let profiles: Value =
        serde_json::from_str(&fs::read_to_string(PROFILES_PATH).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    sources_loaded.push("profiles.json".to_string());
    if let Some(arr) = profiles.get("profiles").and_then(|v| v.as_array()) {
        for profile in arr {
            let subject = profile
                .get("subject")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            if subject.is_empty() {
                continue;
            }
            if let Some(baseline) = profile.get("baseline").and_then(|v| v.as_array()) {
                for row in baseline {
                    if let Some((mem_id, subj, pred, obj, conf, tier)) =
                        parse_profile_baseline(row, &subject)
                    {
                        candidates.push(MemoryRecord {
                            memory_id: mem_id,
                            subject: subj,
                            predicate: pred,
                            object: obj,
                            confidence: conf,
                            tier,
                            anchor_ms: 0,
                            source: "profile_baseline".to_string(),
                            discovery_seq,
                            merged_from: None,
                            correction_target: None,
                        });
                        discovery_seq += 1;
                    } else {
                        lines_skipped += 1;
                    }
                }
            }
        }
    }

    sources_loaded.push("tool-log.jsonl".to_string());
    for line in fs::read_to_string(TOOL_PATH)
        .map_err(|e| e.to_string())?
        .lines()
    {
        if line.trim().is_empty() {
            continue;
        }
        let row: Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(_) => {
                lines_skipped += 1;
                continue;
            }
        };
        let anchor_ms = match row.get("anchor_ms").and_then(|v| v.as_u64()) {
            Some(v) => v,
            None => {
                lines_skipped += 1;
                continue;
            }
        };
        reference_anchor_ms = reference_anchor_ms.max(anchor_ms);
        if let Some((memory_id, subject, predicate, object, confidence, tier)) =
            parse_memory_fields(&row)
        {
            candidates.push(MemoryRecord {
                memory_id,
                subject,
                predicate,
                object,
                confidence,
                tier,
                anchor_ms,
                source: "tool_invoke".to_string(),
                discovery_seq,
                merged_from: None,
                correction_target: None,
            });
            discovery_seq += 1;
        } else {
            lines_skipped += 1;
        }
    }

    let session_root = sessions_root();
    for path in discover_session_shards(&session_root)? {
        sources_loaded.push(
            path.file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned(),
        );
        for line in fs::read_to_string(&path).map_err(|e| e.to_string())?.lines() {
            if line.trim().is_empty() {
                continue;
            }
            let row: Value = match serde_json::from_str(line) {
                Ok(v) => v,
                Err(_) => {
                    lines_skipped += 1;
                    continue;
                }
            };
            let anchor_ms = match row.get("anchor_ms").and_then(|v| v.as_u64()) {
                Some(v) => v,
                None => {
                    lines_skipped += 1;
                    continue;
                }
            };
            reference_anchor_ms = reference_anchor_ms.max(anchor_ms);

            if let Some(corr) = row.get("correction") {
                if row.get("memory").is_some() {
                    lines_skipped += 1;
                    continue;
                }
                let targets = corr
                    .get("targets")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                if targets.is_empty() {
                    lines_skipped += 1;
                    continue;
                }
                // An optional becomes field gives the correction a fresh memory_id so
                // it can be the target of a later correction in a chain. When becomes
                // is absent or empty the correction replaces its target in place by
                // reusing the targets string as its own memory_id.
                let becomes = corr
                    .get("becomes")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
                    .filter(|s| !s.is_empty());
                let new_id = becomes.unwrap_or_else(|| targets.clone());
                let mut merged = corr.clone();
                if let Some(obj) = merged.as_object_mut() {
                    obj.insert("memory_id".to_string(), Value::String(new_id));
                }
                if let Some((memory_id, subject, predicate, object, confidence, tier)) =
                    parse_memory_fields(&merged)
                {
                    candidates.push(MemoryRecord {
                        memory_id,
                        subject,
                        predicate,
                        object,
                        confidence,
                        tier,
                        anchor_ms,
                        source: "session_correction".to_string(),
                        discovery_seq,
                        merged_from: None,
                        correction_target: Some(targets),
                    });
                    discovery_seq += 1;
                } else {
                    lines_skipped += 1;
                }
                continue;
            }

            if let Some(mem) = row.get("memory") {
                if let Some((memory_id, subject, predicate, object, confidence, tier)) =
                    parse_memory_fields(mem)
                {
                    candidates.push(MemoryRecord {
                        memory_id,
                        subject,
                        predicate,
                        object,
                        confidence,
                        tier,
                        anchor_ms,
                        source: "session_memory".to_string(),
                        discovery_seq,
                        merged_from: None,
                        correction_target: None,
                    });
                    discovery_seq += 1;
                } else {
                    lines_skipped += 1;
                }
            }
        }
    }

    let candidate_digest = staging_ledger::candidate_digest(&candidates);
    let candidate_count = candidates.len() as u32;

    let mut grouped: BTreeMap<(String, String), Vec<MemoryRecord>> = BTreeMap::new();
    for cand in candidates {
        grouped.entry(group_key(&cand)).or_default().push(cand);
    }

    let mut group_winners = Vec::new();
    let mut superseded = Vec::new();
    for (_key, group) in grouped {
        let (winner, mut losers) = resolve_group(group, &policy.conflict_mode);
        if !winner.memory_id.is_empty() {
            group_winners.push(winner);
        }
        superseded.append(&mut losers);
    }

    let (mut winners, mut dedup_losers) = semantic_dedup(group_winners, &policy.conflict_mode);
    superseded.append(&mut dedup_losers);
    superseded.sort_by(|a, b| a.discovery_seq.cmp(&b.discovery_seq));

    let (active_memories, retention_vault) =
        apply_retention(winners.drain(..).collect(), &policy, reference_anchor_ms);

    let mut snapshot = Snapshot {
        snapshot_version: 1,
        snapshot_seq: prior_snapshot_seq() + 1,
        lines_skipped,
        reference_anchor_ms,
        sources_loaded,
        active_memories,
        superseded_memories: superseded,
        retention_vault,
        ingest_fingerprint: String::new(),
    };
    snapshot.ingest_fingerprint = fingerprint(&snapshot);
    let staging = StagingLedger {
        staging_version: 1,
        staging_seq: snapshot.snapshot_seq,
        conflict_mode: policy.conflict_mode,
        export_mode: policy.export_mode,
        candidate_count,
        candidate_digest_sha256: candidate_digest,
    };
    Ok((snapshot, staging))
}

pub fn run_ingest() -> Result<u32, String> {
    fs::create_dir_all("/app/state").map_err(|e| e.to_string())?;
    let (snapshot, staging) = ingest_all()?;
    let skipped = snapshot.lines_skipped;
    staging_ledger::write_staging_ledger(&staging)?;
    fs::write(
        SNAPSHOT_PATH,
        format!(
            "{}\n",
            serde_json::to_string_pretty(&snapshot).map_err(|e| e.to_string())?
        ),
    )
    .map_err(|e| e.to_string())?;
    Ok(skipped)
}

pub fn run_export() -> Result<(), String> {
    if !Path::new(SNAPSHOT_PATH).is_file() {
        return Err("missing memory snapshot".into());
    }
    let text = fs::read_to_string(SNAPSHOT_PATH).map_err(|e| e.to_string())?;
    let snapshot: Snapshot = serde_json::from_str(&text).map_err(|e| e.to_string())?;
    publish::write_exports(&snapshot)
}
