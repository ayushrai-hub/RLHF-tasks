# Cable network contract

The planner treats the feeds under /app/data/network, /app/data/vessels, /app/data/weather, /app/data/currents, /app/data/missions, /app/data/reference/hazards, and the generated /app/build/splice_rules.csv as the planning source of truth. CSV feeds ignore blank lines and rows whose first non-space character is #. If a CSV feed repeats a primary key, the last row wins. Primary keys are station_id for stations, span_id for spans, ship_id for ships, window_id for weather windows, corridor_id plus window_id for currents, and family plus kit for generated splice rules.

Station profile JSON files in /app/data/network/station_profiles are live overlays for matching station_id values. When a profile has a matching station_id, its kind and priority override the CSV station kind and priority for reachability classification and restored-priority scoring. Invalid profile files or profiles without a matching station_id are ignored.

A station is reachable when it can be reached from any station with kind=shore using spans whose status is OK plus the single candidate span being considered. BROKEN spans are repair candidates. OFFLINE spans are neither candidates nor traversable. The restored_stations list for a repair contains non-shore stations that are unreachable in the current OK graph but become reachable if only that span is restored, sorted by station_id. The restored priority is the sum of the deduplicated effective station priorities for those stations.

The final repaired graph is computed by applying all scheduled BROKEN-span repairs to the original OK graph. The unreachable_stations array in /app/output/repair_plan.json lists remaining non-shore stations not reachable from shore, sorted by station_id.
