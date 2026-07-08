# Input Contract

service_calls.csv contains one row per open maintenance call.
opened_at is an RFC3339 UTC timestamp.
priority is either routine or urgent.
notes_code is a short operator code such as CHECK, HEAT, LEAK, NOISE, REWORK, or VIB.

sensor_windows.csv contains summarized telemetry windows per asset.
window_end is an RFC3339 UTC timestamp.
The scorer uses the latest row for the same asset_id whose window_end is at or before the call opened_at.
Blank temp_c values are allowed and must be imputed with the EWMA rule in /app/docs/model-card.md.

asset_history.csv contains older maintenance events for feature calculation.
event_time is an RFC3339 UTC timestamp.
event_type may be corrective, preventive, inspection, or failure.
severity is an integer from 1 to 5.

site_capacity.csv contains one capacity row per site.
dispatch_slots is the maximum number of calls at that site that may receive dispatch.
inspect_slots is the maximum number of calls at that site that may receive inspect.
Monitor actions do not consume a slot.

policy.json optimizer.site_region maps every site in service_calls.csv to a region.
optimizer.regional_limits defines each region's shared dispatch_slots, inspect_slots, and crew_hours.
optimizer.action_hours defines crew hours for each action and asset_type pair.
optimizer.action_parts defines required part quantities for each action and asset_type pair.
optimizer.parts_inventory defines site, part_id, on_hand, and reserve_min for transfer-aware scheduling.
optimizer.crew_roster defines crew_id, region, home_site, shift_start, shift_end, and max_continuous_hours.
optimizer.break_hours defines the length of the required rest break used by the crew scheduler.
optimizer.part_transfer_hours defines part transfer hours by region, source site, and destination site.
optimizer.travel_hours defines travel hours by region, from_site, and to_site.

maintenance_labels.csv is used only for evaluation.
failure_within_30d is 1 when the asset had a confirmed failure in the next 30 days, otherwise 0.
