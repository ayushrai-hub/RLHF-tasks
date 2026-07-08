# Output Contract

All numeric scores in CSV outputs are rounded to six decimal places.
The six-decimal rule applies only to CSV files.
JSON numeric values should be written as ordinary calculation results, not rounded or truncated to six decimals.

scored_calls.csv columns:

- request_id
- asset_id
- site
- opened_at
- priority
- raw_score
- calibrated_risk
- downtime_risk
- risk_band
- action
- top_factor

scored_calls.csv rows preserve the original service_calls.csv input order.

risk_band values:

- high when calibrated_risk >= dispatch threshold
- medium when calibrated_risk >= inspect threshold
- watch when calibrated_risk >= watch threshold
- low otherwise

Action planning:

- Start each call as monitor.
- inspect is feasible when calibrated_risk >= optimizer.minimum_risk.inspect, or when priority is urgent and calibrated_risk >= urgent_inspect_floor.
- dispatch is feasible when calibrated_risk >= optimizer.minimum_risk.dispatch.
- Choose one global feasible action plan across all calls, not one independent plan per site.
- The plan may not exceed site_capacity.csv dispatch_slots or inspect_slots for any site.
- policy.json optimizer.site_region maps each site to a region.
- policy.json optimizer.regional_limits gives each region's dispatch_slots, inspect_slots, and crew_hours.
- policy.json optimizer.action_hours[action][asset_type] gives the regional crew hours consumed by a chosen action.
- policy.json optimizer.action_parts[action][asset_type] gives required part quantities for a chosen action.
- policy.json optimizer.parts_inventory gives starting inventory by site and part_id.
- Available inventory is on_hand minus reserve_min, floored at zero.
- The plan may not exceed regional dispatch_slots, inspect_slots, or crew_hours for any region.
- Every non-monitor action in a candidate plan must also fit the crew scheduler.
- Every required part for a scheduled action must be allocated from one source site in the same region.
- A source site must have enough remaining available inventory for the full required quantity.
- Parts arrive at policy report_generated_at plus optimizer.part_transfer_hours[region][source_site][dest_site].
- A scheduled action may not start before all allocated parts for that action are ready.
- Allocated parts are consumed once in that candidate schedule.
- Crews may work only in their own region, start from home_site at shift_start, and cannot work past shift_end.
- Each crew tracks continuous action hours since shift start or since its last required break.
- Travel time does not count toward continuous action hours.
- If the next scheduled action would make that crew exceed max_continuous_hours, insert one rest break of optimizer.break_hours before travel to the next site.
- A rest break happens at the crew's current site, resets continuous action hours to zero, delays later work, and is not emitted in crew_schedule.csv.
- A single action whose duration is greater than a crew's max_continuous_hours is not schedulable by that crew.
- Travel time is read from optimizer.travel_hours[region][from_site][to_site] and occurs before the scheduled action.
- A crew's next travel starts from the site of its last scheduled action.
- A scheduled action's duration is optimizer.action_hours[action][asset_type].
- A scheduled action must end no later than policy report_generated_at plus due_hours for that action.
- decision utility = calibrated_risk * optimizer.risk_effect[action] + downtime_risk * optimizer.downtime_effect[action] + priority_bonus[priority][action] - optimizer.action_cost[action].
- monitor has utility 0 and consumes no site slot, regional slot, or crew hours.
- Maximize total decision utility over full global plans that are capacity-feasible and schedulable.
- Tie-break optimized plans by larger dispatched calibrated_risk sum, then larger inspected calibrated_risk sum, then smaller total regional crew-hours used, then earliest maximum scheduled end time, then smaller total schedule travel hours, then smaller total part-transfer hours, then lexicographically smaller request_id=action signature after sorting calls by request_id.
- For one chosen action plan, choose the schedule with the earliest maximum scheduled end time, then smaller total travel hours, then smaller total part-transfer hours, then lexicographically smaller request_id=crew_id@start_at signature after sorting by request_id, then lexicographically smaller part allocation signature.
- The part allocation signature is request_id:part_id=source_site>dest_site@ready_at after sorting parts_allocation.csv rows by its documented row order.

maintenance_decisions.csv columns:

- request_id
- asset_id
- action
- risk_band
- calibrated_risk
- downtime_risk
- due_within_hours
- decision_value
- reason

Decision rows are sorted by calibrated_risk descending, then request_id ascending.
due_within_hours comes from policy.json for the chosen action.
decision_value is the chosen action's utility.
reason is top_factor:risk_band.

crew_schedule.csv columns:

- request_id
- crew_id
- region
- site
- action
- start_at
- end_at
- travel_hours

crew_schedule.csv has one row for each dispatch or inspect action, and no rows for monitor actions.
Rows are sorted by start_at ascending, then crew_id ascending, then request_id ascending.
start_at and end_at are UTC timestamps formatted like 2026-06-15T13:36:00Z.
travel_hours is rounded to six decimals.

parts_allocation.csv columns:

- request_id
- part_id
- source_site
- dest_site
- quantity
- ready_at
- transfer_hours

parts_allocation.csv has one row for each allocated part requirement, and no rows for monitor actions with no required parts.
Rows are sorted by request_id ascending, then part_id ascending, then source_site ascending, then dest_site ascending.
ready_at is a UTC timestamp formatted like 2026-06-15T14:00:00Z.
transfer_hours is rounded to six decimals.

risk_manifest.json contains generated_at, model_id, policy_id, row_count, output_files, and input_sha256.
input_sha256 maps calls, windows, history, labels, capacity, model, and policy to the SHA-256 of each input file.

evaluation.json contains row_count, positive_action_count, confusion_matrix, metrics, and site_metrics.
For evaluation, dispatch and inspect count as positive actions.
confusion_matrix contains true_positive, false_positive, true_negative, and false_negative.
metrics contains precision, recall, f1, brier_score, roc_auc, and average_precision.
Metric values in evaluation.json are JSON numbers from the underlying calculations, not six-decimal strings or rounded CSV values.
roc_auc uses the Mann-Whitney rank formula over calibrated_risk, with average ranks for tied scores.
average_precision sorts by calibrated_risk descending and request_id ascending, then averages precision at each positive label.
site_metrics contains one entry per site with count, positive_action_count, observed_failure_count, and mean_calibrated_risk.
