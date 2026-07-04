use crate::types::{Allocation, Config, Dispatch, Unit};

/// Decide each unit's dispatch fraction and reserve share, and the network-wide
/// frequency setpoint. The returned `Dispatch` is serialized to
/// `output_data/dispatch.json` and graded by `model.py`.
///
/// The skeleton leaves every unit offline and the setpoint at nominal — this
/// fails the demand floor and scores 0. Replace it with a real strategy.
pub fn dispatch(units: &[Unit], config: &Config) -> Dispatch {
    // TODO: implement a dispatch strategy.
    let allocations = units
        .iter()
        .map(|u| Allocation {
            unit_id: u.id.clone(),
            dispatch_fraction: 0.0,
            reserve_share: 0.0,
        })
        .collect();
    Dispatch {
        allocations,
        frequency_setpoint: config.nominal_frequency,
    }
}
