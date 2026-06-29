//! Element cycle reconstruction from the kettle-temperature/power-mode event log.
//!
//! Replays the controller over the event stream and produces the element-ON
//! intervals. See docs/spec.md for the authoritative control and interval
//! contract.

use crate::json::write_ledger;
use crate::parse::{Event, Problem};

pub struct Ledger {
    pub intervals: Vec<(i64, i64)>,
    pub state_on: bool,
    pub since: i64,
}

impl Ledger {
    pub fn to_json(&self) -> String {
        let ontime: i64 = self.intervals.iter().map(|(s, e)| e - s).sum();
        let state = if self.state_on { "on" } else { "off" };
        write_ledger(&self.intervals, ontime, state, self.since)
    }
}

/// Demand sign from the current temperature relative to the deadband.
/// Returns Some(true) for demand-on, Some(false) for demand-off, None inside
/// the band (demand latches / is unchanged).
fn demand_edge(temp: i64, target_temp: i64, deadband: i64) -> Option<bool> {
    if temp <= target_temp - deadband {
        Some(true)
    } else if temp >= target_temp + deadband {
        Some(false)
    } else {
        None
    }
}

/// Replay the controller and return the reconstructed ledger.
///
/// Walk the events in order, tracking the latched temperature and the demand
/// it implies, and record the element-ON intervals from the event timestamps.
pub fn run(prob: &Problem) -> Result<Ledger, String> {
    let mut intervals: Vec<(i64, i64)> = Vec::new();
    let mut on = false;
    let mut open_start: i64 = 0;
    let mut since: i64 = 0;

    let mut demand = false;
    let mut power_on = true;
    let mut have_temp = false;

    for ev in &prob.events {
        match ev {
            Event::Sample { temp, at } => {
                have_temp = true;
                if let Some(d) = demand_edge(*temp, prob.target_temp, prob.deadband) {
                    demand = d;
                }
                // Update the element state from the new demand.
                if power_on {
                    if demand && !on {
                        on = true;
                        open_start = *at;
                        since = *at;
                    } else if !demand && on {
                        on = false;
                        intervals.push((open_start, *at));
                        since = *at;
                    }
                }
            }
            Event::Power { on: state_on, at } => {
                power_on = *state_on;
                if !power_on {
                    // `off` mode drives the element off.
                    if on {
                        on = false;
                        intervals.push((open_start, *at));
                        since = *at;
                    }
                    demand = false;
                } else if have_temp && demand && !on {
                    on = true;
                    open_start = *at;
                    since = *at;
                }
            }
            Event::Freeze { .. } => {}
            Event::EndFreeze { .. } => {}
        }
    }

    if on {
        intervals.push((open_start, prob.until));
        // state stays on at the horizon
    }

    // Drop any zero-length intervals.
    intervals.retain(|(s, e)| e > s);

    let final_on = on;
    let final_since = if final_on {
        open_start
    } else {
        intervals.last().map(|(_, e)| *e).unwrap_or(0)
    };

    Ok(Ledger {
        intervals,
        state_on: final_on,
        since: final_since,
    })
}
