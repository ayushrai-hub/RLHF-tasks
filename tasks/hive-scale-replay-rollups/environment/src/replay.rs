use std::fs;

use crate::config::{self};
use crate::frame::{self, ParseOutcome, ParsedFrame};
use crate::manifest::Manifest;
use crate::state::{LiveEvent, PersistedState, ReplayState};

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
        let mut offset = 0usize;
        let mut frame_index = 0u32;
        while offset < data.len() {
            match frame::advance_frame(&data, offset) {
                Ok((outcome, consumed)) => {
                    match outcome {
                        ParseOutcome::Valid(parsed) => {
                            apply_frame(
                                state,
                                &stream.source,
                                stream_index as u32,
                                frame_index,
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
    }
    Ok(())
}

fn find_target(data: &PersistedState, correction_target: u32) -> Option<u64> {
    data.accepted_ids
        .iter()
        .copied()
        .find(|id| (*id & 0xFFFF_FFFF) == correction_target as u64)
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
    parsed: &ParsedFrame,
) {
    match parsed.frame_type {
        1 => apply_sample(state, parsed),
        2 => apply_correction(state, source, stream_index, frame_index, parsed),
        3 => apply_tombstone(state, parsed),
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
    parsed: &ParsedFrame,
) {
    let Some(target_id) = find_target(&state.data, parsed.correction_target) else {
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
    }
}

fn apply_tombstone(state: &mut ReplayState, parsed: &ParsedFrame) {
    let Some(target_id) = find_target(&state.data, parsed.correction_target) else {
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
