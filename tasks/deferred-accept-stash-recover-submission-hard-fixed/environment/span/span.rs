use crate::errors::GateError;
use crate::model::{CarryKey, Mode, Root, Row, WitnessKey};
use crate::seal::{read_witness_blob, write_witness_blob};

pub fn cast_q(
    root: &Root,
    rows: &[Row],
    events: &[crate::model::Event],
    mode: Mode,
    gate_open: bool,
    backing_up: bool,
    wave: u32,
    slot: u32,
    _stash_epoch: u32,
    _seal_epoch: u32,
    _barrier_gen: u32,
    _witnesses: &[WitnessKey],
    _carries: &[CarryKey],
) -> Result<(), GateError> {
    let durable = serde_rows(rows);
    crate::io::write_json(&root.durable_path(), &durable)?;
    if let Mode::Cycle { partial: true } = mode {
        return Ok(());
    }
    let ev_body: Vec<String> = events
        .iter()
        .map(|ev| {
            format!(
                "{{\"tag\":\"{}\",\"wave\":{},\"phase\":\"{}\",\"slot\":{}}}",
                esc(&ev.tag),
                ev.wave,
                esc(&ev.phase),
                ev.slot
            )
        })
        .collect();
    let ckpt = format!(
        "{{\"wave\":{wave},\"slot\":{slot},\"gate_open\":{gate_open},\"backing_up\":{backing_up},\"rows\":[{}],\"events\":[{}]}}",
        rows.iter()
            .map(|r| format!("\"{}\"", esc(&r.tag)))
            .collect::<Vec<_>>()
            .join(","),
        ev_body.join(",")
    );
    crate::io::write_json(&root.ckpt_path(), &ckpt)?;
    let (seal_epoch, witnesses) = read_witness_blob(root)?;
    write_witness_blob(root, seal_epoch, &witnesses)
}

fn serde_rows(rows: &[Row]) -> String {
    let body: Vec<String> = rows
        .iter()
        .map(|r| {
            format!(
                "{{\"tag\":\"{}\",\"lane\":\"{}\",\"weight\":{},\"state\":\"{}\",\"wave\":{},\"stash_gen\":{},\"seed_origin\":{}}}",
                esc(&r.tag),
                esc(&r.lane),
                r.weight,
                esc(&r.state),
                r.wave,
                r.stash_gen,
                r.seed_origin
            )
        })
        .collect();
    format!("[{}]", body.join(","))
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

pub fn read_ckpt_text(root: &Root) -> Result<String, GateError> {
    crate::io::read_json(&root.ckpt_path())
}

pub struct Meta {
    pub wave: u32,
    pub slot: u32,
    pub gate_open: bool,
    pub backing_up: bool,
    pub stash_epoch: u32,
    pub seal_epoch: u32,
    pub barrier_gen: u32,
}

pub fn load_meta(text: &str) -> Result<Meta, GateError> {
    Ok(Meta {
        wave: read_key(text, "wave")?.parse().unwrap_or(1),
        slot: read_key(text, "slot")?.parse().unwrap_or(0),
        gate_open: read_key(text, "gate_open")? == "true",
        backing_up: read_key(text, "backing_up")? == "true",
        stash_epoch: read_key(text, "stash_epoch")
            .unwrap_or_else(|_| "0".to_string())
            .parse()
            .unwrap_or(0),
        seal_epoch: 0,
        barrier_gen: 0,
    })
}

pub fn load_witnesses(_text: &str) -> Vec<WitnessKey> {
    Vec::new()
}

pub fn load_rows(root: &Root) -> Result<Vec<Row>, GateError> {
    let text = crate::io::read_json(&root.durable_path())?;
    parse_rows(&text)
}

pub fn parse_events(text: &str) -> Vec<crate::model::Event> {
    let mut out = Vec::new();
    if let Some(start) = text.find("\"events\":[") {
        let rest = &text[start + 10..];
        if let Some(end) = rest.find(']') {
            let body = &rest[..end];
            for chunk in body.split("},{") {
                let chunk = chunk.trim_matches(&['{', '}', ',', ' '][..]);
                if chunk.is_empty() {
                    continue;
                }
                if let (Ok(tag), Ok(wave), Ok(phase), Ok(slot)) = (
                    read_key(chunk, "tag"),
                    read_key(chunk, "wave"),
                    read_key(chunk, "phase"),
                    read_key(chunk, "slot"),
                ) {
                    out.push(crate::model::Event {
                        tag,
                        wave: wave.parse().unwrap_or(0),
                        phase,
                        slot: slot.parse().unwrap_or(0),
                    });
                }
            }
        }
    }
    out
}

fn parse_rows(text: &str) -> Result<Vec<Row>, GateError> {
    let trimmed = text.trim();
    if !trimmed.starts_with('[') {
        return Err(GateError::new(30, "bad durable"));
    }
    let mut rows = Vec::new();
    for chunk in trimmed.trim_matches(&['[', ']'][..]).split("},{") {
        let chunk = chunk.trim_matches(&['{', '}', ',', ' '][..]);
        if chunk.is_empty() {
            continue;
        }
        rows.push(parse_row(chunk)?);
    }
    Ok(rows)
}

fn parse_row(chunk: &str) -> Result<Row, GateError> {
    let tag = read_key(chunk, "tag")?;
    let lane = read_key(chunk, "lane")?;
    let weight: u32 = read_key(chunk, "weight")?.parse().unwrap_or(0);
    let state = read_key(chunk, "state")?;
    let wave: u32 = read_key(chunk, "wave")?.parse().unwrap_or(0);
    let stash_gen: u32 = read_key(chunk, "stash_gen")
        .unwrap_or_else(|_| wave.to_string())
        .parse()
        .unwrap_or(wave);
    let seed_origin = read_key(chunk, "seed_origin").unwrap_or_else(|_| "true".to_string()) == "true";
    Ok(Row {
        tag,
        lane,
        weight,
        state,
        wave,
        stash_gen,
        seed_origin,
    })
}

fn read_key(chunk: &str, key: &str) -> Result<String, GateError> {
    let needle = format!("\"{key}\":\"");
    if let Some(start) = chunk.find(&needle) {
        let rest = &chunk[start + needle.len()..];
        let end = rest.find('"').unwrap_or(rest.len());
        return Ok(rest[..end].to_string());
    }
    let needle = format!("\"{key}\":");
    if let Some(start) = chunk.find(&needle) {
        let rest = &chunk[start + needle.len()..];
        let end = rest.find(',').unwrap_or(rest.len());
        return Ok(rest[..end].trim().to_string());
    }
    Err(GateError::new(31, format!("missing {key}")))
}
