pub const V2_FRAME_SIZE: usize = 40;
pub const V1_FRAME_SIZE: usize = 24;

#[derive(Debug, Clone)]
pub struct ParsedFrame {
    pub frame_type: u8,
    pub event_id: u64,
    pub timestamp: u64,
    pub raw_hive_id: u16,
    pub grams: i32,
    pub correction_target: u32,
}

#[derive(Debug, Clone)]
pub enum ParseOutcome {
    Valid(ParsedFrame),
    Quarantine {
        reason: &'static str,
        event_id: Option<u64>,
    },
}

pub fn advance_frame(data: &[u8], offset: usize) -> Result<(ParseOutcome, usize), &'static str> {
    if offset >= data.len() {
        return Err("eof");
    }
    let remaining = data.len() - offset;
    if remaining >= 4 && &data[offset..offset + 4] == b"HWSC" {
        if remaining < V1_FRAME_SIZE {
            return Ok((
                ParseOutcome::Quarantine {
                    reason: "truncated_tail",
                    event_id: None,
                },
                remaining,
            ));
        }
        return Ok((
            ParseOutcome::Quarantine {
                reason: "unsupported_version",
                event_id: None,
            },
            V1_FRAME_SIZE,
        ));
    }
    if remaining < 4 {
        return Ok((
            ParseOutcome::Quarantine {
                reason: "truncated_tail",
                event_id: None,
            },
            remaining,
        ));
    }
    if &data[offset..offset + 4] != b"HWS2" {
        if remaining < V2_FRAME_SIZE {
            return Ok((
                ParseOutcome::Quarantine {
                    reason: "truncated_tail",
                    event_id: None,
                },
                remaining,
            ));
        }
        return Ok((
            ParseOutcome::Quarantine {
                reason: "bad_magic",
                event_id: None,
            },
            V2_FRAME_SIZE,
        ));
    }
    if remaining < V2_FRAME_SIZE {
        return Ok((
            ParseOutcome::Quarantine {
                reason: "truncated_tail",
                event_id: None,
            },
            remaining,
        ));
    }
    let frame = &data[offset..offset + V2_FRAME_SIZE];
    let version = frame[4];
    let event_id = u64::from_le_bytes(frame[8..16].try_into().unwrap());
    if version != 2 {
        return Ok((
            ParseOutcome::Quarantine {
                reason: "unsupported_version",
                event_id: Some(event_id),
            },
            V2_FRAME_SIZE,
        ));
    }
    let frame_type = frame[5];
    if !(1..=3).contains(&frame_type) {
        return Ok((
            ParseOutcome::Quarantine {
                reason: "unsupported_frame_type",
                event_id: Some(event_id),
            },
            V2_FRAME_SIZE,
        ));
    }
    let stored = u32::from_le_bytes(frame[36..40].try_into().unwrap());
    let computed: u32 = frame[0..36].iter().map(|b| *b as u32).sum();
    if stored != computed {
        return Ok((
            ParseOutcome::Quarantine {
                reason: "checksum",
                event_id: Some(event_id),
            },
            V2_FRAME_SIZE,
        ));
    }
    Ok((
        ParseOutcome::Valid(ParsedFrame {
            frame_type,
            event_id,
            timestamp: u64::from_le_bytes(frame[16..24].try_into().unwrap()),
            raw_hive_id: u16::from_le_bytes(frame[24..26].try_into().unwrap()),
            grams: i32::from_le_bytes(frame[26..30].try_into().unwrap()),
            correction_target: u32::from_le_bytes(frame[30..34].try_into().unwrap()),
        }),
        V2_FRAME_SIZE,
    ))
}
