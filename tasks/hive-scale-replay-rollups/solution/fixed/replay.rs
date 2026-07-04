use std::fs;

use crate::config::{self};
use crate::frame::{self, ParseOutcome, ParsedFrame};
use crate::manifest::Manifest;
use crate::state::{LiveEvent, PersistedState, ReplayState, StreamIdentity};

#[derive(Debug, Clone, serde::Serialize, PartialEq)]
pub struct QuarantineRow {
    pub source: String,
    pub stream_index: u32,
    pub frame_index: u32,
    pub reason: String,
    pub event_id: Option<u64>,
}

pub fn replay_manifest(state: &mut ReplayState, manifest: &Manifest) -> Result<(), String> {
    for (stream_index, stream) in manifest.streams.iter().enumerate() {
        let data = fs::read(&stream.path).map_err(|e| e.to_string())?;
        let identity = StreamIdentity::from_bytes(&stream.source, &stream.kind, &data);
        let mut start_slot = 0u32;
        if let Some(progress) = state.data.streams.get(&stream.source) {
            if progress.identity == identity {
                start_slot = progress.consumed_slots;
            }
        }

        let mut offset = 0usize;
        let mut frame_index = 0u32;
        while frame_index < start_slot && offset < data.len() {
            match frame::advance_frame(&data, offset) {
                Ok((_, consumed)) => {
                    offset += consumed;
                    frame_index += 1;
                }
                Err(_) => break,
            }
        }

        while offset < data.len() {
            state.data.frame_seq += 1;
            let current_seq = state.data.frame_seq;
            match frame::advance_frame(&data, offset) {
                Ok((outcome, consumed)) => {
                    match outcome {
                        ParseOutcome::Valid(parsed) => {
                            apply_frame(
                                state,
                                &stream.source,
                                stream_index as u32,
                                frame_index,
                                current_seq,
                                &parsed,
                            );
                        }
                        ParseOutcome::Quarantine { reason, event_id } => {
                            state.data.quarantined_frames += 1;
                            state.quarantine.push(QuarantineRow {
                                source: stream.source.clone(),
                                stream_index: stream_index as u32,
                                frame_index,
                                reason: reason.to_string(),
                                event_id,
                            });
                        }
                    }
                    offset += consumed;
                    frame_index += 1;
                    state.data.frontier.stream_count = stream_index as u32 + 1;
                    state.data.frontier.frame_count = frame_index;
                }
                Err(_) => break,
            }
        }

        state.data.streams.insert(
            stream.source.clone(),
            crate::state::StreamProgress {
                identity,
                consumed_slots: frame_index,
            },
        );
    }
    Ok(())
}

fn find_target(data: &PersistedState, correction_target: u32, before_seq: u64) -> Option<u64> {
    data.accepted_ids
        .iter()
        .copied()
        .filter_map(|id| {
            if (id & 0xFFFF_FFFF) != correction_target as u64 {
                return None;
            }
            let ev = data.events.get(&id)?;
            if ev.order >= before_seq {
                return None;
            }
            Some((ev.order, id))
        })
        .max_by_key(|(order, _)| *order)
        .map(|(_, id)| id)
}

fn store_event(
    state: &mut ReplayState,
    event_id: u64,
    timestamp: u64,
    raw_hive_id: u16,
    grams: i32,
) {
    let (canonical, net) = config::net_kg(raw_hive_id, timestamp, grams, &state.cfg);
    let order = state.data.next_order;
    state.data.next_order += 1;
    state.data.events.insert(
        event_id,
        LiveEvent {
            event_id,
            timestamp,
            raw_hive_id,
            canonical_hive_id: canonical,
            grams,
            net_kg: net,
            order,
            live: true,
        },
    );
    state.data.accepted_ids.insert(event_id);
}

fn apply_frame(
    state: &mut ReplayState,
    source: &str,
    stream_index: u32,
    frame_index: u32,
    frame_seq: u64,
    parsed: &ParsedFrame,
) {
    match parsed.frame_type {
        1 => apply_sample(state, parsed),
        2 => apply_correction(state, source, stream_index, frame_index, frame_seq, parsed),
        3 => apply_tombstone(state, parsed, frame_seq),
        _ => {}
    }
}

fn apply_sample(state: &mut ReplayState, parsed: &ParsedFrame) {
    if state.data.accepted_ids.contains(&parsed.event_id) {
        state.data.duplicate_events += 1;
        return;
    }
    store_event(
        state,
        parsed.event_id,
        parsed.timestamp,
        parsed.raw_hive_id,
        parsed.grams,
    );
    state.data.accepted_frames += 1;
}

fn apply_correction(
    state: &mut ReplayState,
    source: &str,
    stream_index: u32,
    frame_index: u32,
    frame_seq: u64,
    parsed: &ParsedFrame,
) {
    if state.data.accepted_ids.contains(&parsed.event_id) {
        state.data.duplicate_events += 1;
        return;
    }
    let Some(target_id) = find_target(&state.data, parsed.correction_target, frame_seq) else {
        state.data.quarantined_frames += 1;
        state.quarantine.push(QuarantineRow {
            source: source.to_string(),
            stream_index,
            frame_index,
            reason: "missing_correction_target".into(),
            event_id: Some(parsed.event_id),
        });
        return;
    };
    let Some(existing) = state.data.events.get(&target_id) else {
        state.data.quarantined_frames += 1;
        state.quarantine.push(QuarantineRow {
            source: source.to_string(),
            stream_index,
            frame_index,
            reason: "missing_correction_target".into(),
            event_id: Some(parsed.event_id),
        });
        return;
    };
    if !existing.live {
        state.data.quarantined_frames += 1;
        state.quarantine.push(QuarantineRow {
            source: source.to_string(),
            stream_index,
            frame_index,
            reason: "stale_correction_target".into(),
            event_id: Some(parsed.event_id),
        });
        state.data.accepted_ids.insert(parsed.event_id);
        return;
    }
    if let Some(existing) = state.data.events.get_mut(&target_id) {
        existing.timestamp = parsed.timestamp;
        existing.raw_hive_id = parsed.raw_hive_id;
        existing.grams = parsed.grams;
        let (canonical, net) =
            config::net_kg(parsed.raw_hive_id, parsed.timestamp, parsed.grams, &state.cfg);
        existing.canonical_hive_id = canonical;
        existing.net_kg = net;
        existing.live = true;
        state.data.accepted_frames += 1;
        state.data.accepted_ids.insert(parsed.event_id);
    }
}

fn apply_tombstone(state: &mut ReplayState, parsed: &ParsedFrame, frame_seq: u64) {
    let Some(target_id) = find_target(&state.data, parsed.correction_target, frame_seq) else {
        state.data.duplicate_events += 1;
        return;
    };
    if let Some(existing) = state.data.events.get_mut(&target_id) {
        if existing.live {
            existing.live = false;
            state.data.tombstoned_events += 1;
            state.data.accepted_frames += 1;
        } else {
            state.data.duplicate_events += 1;
        }
    } else {
        state.data.duplicate_events += 1;
    }
}

pub fn merge_quarantine(base: &mut Vec<QuarantineRow>, rows: Vec<QuarantineRow>) {
    base.extend(rows);
}
