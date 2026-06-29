//! Input parsing and validation for the process-kettle event log.

use crate::json::{parse_json, Json};

#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    Sample { temp: i64, at: i64 },
    Power { on: bool, at: i64 },
    Freeze { at: i64 },
    EndFreeze { at: i64 },
}

impl Event {
    pub fn at(&self) -> i64 {
        match self {
            Event::Sample { at, .. } => *at,
            Event::Power { at, .. } => *at,
            Event::Freeze { at } => *at,
            Event::EndFreeze { at } => *at,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Problem {
    pub target_temp: i64,
    pub deadband: i64,
    pub min_run: i64,
    pub min_rest: i64,
    pub until: i64,
    pub events: Vec<Event>,
}

#[derive(Debug)]
pub struct ParseError(pub String);

fn req_int(obj: &Json, key: &str) -> Result<i64, ParseError> {
    obj.get(key)
        .ok_or_else(|| ParseError(format!("missing field `{}`", key)))?
        .as_i64()
        .ok_or_else(|| ParseError(format!("field `{}` must be an integer", key)))
}

pub fn parse(input: &str) -> Result<Problem, ParseError> {
    let root = parse_json(input).map_err(ParseError)?;
    if !matches!(root, Json::Object(_)) {
        return Err(ParseError("top-level JSON must be an object".to_string()));
    }

    let target_temp = req_int(&root, "targetTemp")?;
    let deadband = req_int(&root, "deadband")?;
    let min_run = req_int(&root, "minRun")?;
    let min_rest = req_int(&root, "minRest")?;
    let until = req_int(&root, "until")?;

    if deadband < 0 {
        return Err(ParseError("deadband must be >= 0".to_string()));
    }
    if min_run < 0 {
        return Err(ParseError("minRun must be >= 0".to_string()));
    }
    if min_rest < 0 {
        return Err(ParseError("minRest must be >= 0".to_string()));
    }

    let events_json = root
        .get("events")
        .ok_or_else(|| ParseError("missing field `events`".to_string()))?
        .as_array()
        .ok_or_else(|| ParseError("`events` must be an array".to_string()))?;

    let mut events = Vec::with_capacity(events_json.len());
    let mut last_at: Option<i64> = None;
    let mut freeze_open = false;

    for (i, ev) in events_json.iter().enumerate() {
        if !matches!(ev, Json::Object(_)) {
            return Err(ParseError(format!("event {} is not an object", i)));
        }
        let ty = ev
            .get("type")
            .ok_or_else(|| ParseError(format!("event {} missing `type`", i)))?
            .as_str()
            .ok_or_else(|| ParseError(format!("event {} `type` must be a string", i)))?;
        let at = req_int(ev, "at").map_err(|e| ParseError(format!("event {}: {}", i, e.0)))?;

        if at < 0 || at > until {
            return Err(ParseError(format!(
                "event {} `at`={} out of range [0, until={}]",
                i, at, until
            )));
        }
        if let Some(prev) = last_at {
            if at < prev {
                return Err(ParseError(format!(
                    "event {} out of order: at={} < previous at={}",
                    i, at, prev
                )));
            }
        }
        last_at = Some(at);

        let event = match ty {
            "sample" => {
                let temp = req_int(ev, "temp")
                    .map_err(|e| ParseError(format!("event {}: {}", i, e.0)))?;
                Event::Sample { temp, at }
            }
            "power" => {
                let state = ev
                    .get("state")
                    .ok_or_else(|| ParseError(format!("event {} missing `state`", i)))?
                    .as_str()
                    .ok_or_else(|| {
                        ParseError(format!("event {} `state` must be a string", i))
                    })?;
                let on = match state {
                    "on" => true,
                    "off" => false,
                    other => {
                        return Err(ParseError(format!(
                            "event {} bad state `{}` (want on|off)",
                            i, other
                        )))
                    }
                };
                Event::Power { on, at }
            }
            "freeze" => {
                if freeze_open {
                    return Err(ParseError(format!(
                        "event {} `freeze` while a freeze is already open",
                        i
                    )));
                }
                freeze_open = true;
                Event::Freeze { at }
            }
            "endfreeze" => {
                if !freeze_open {
                    return Err(ParseError(format!(
                        "event {} `endfreeze` with no open freeze",
                        i
                    )));
                }
                freeze_open = false;
                Event::EndFreeze { at }
            }
            other => {
                return Err(ParseError(format!("event {} unknown type `{}`", i, other)))
            }
        };
        events.push(event);
    }

    if freeze_open {
        return Err(ParseError("freeze left open at end of event list".to_string()));
    }

    Ok(Problem {
        target_temp,
        deadband,
        min_run,
        min_rest,
        until,
        events,
    })
}
