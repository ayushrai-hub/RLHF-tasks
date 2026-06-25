# Vehicle profile

`/app/config/vehicle-profile.json` maps `vehicle_id` to home position and upload QC limits used at export time.

| Field | Type | Rule |
|-------|------|------|
| home_alt_m | number | MSL meters subtracted for frame `3` altitude rollup |
| home_lat_e7 | integer | Home latitude in degrees × 1e7 |
| home_lon_e7 | integer | Home longitude in degrees × 1e7 |
| max_rel_alt_m | number | Maximum allowed `alt_meters` for exported waypoints with `frame == 3` |
| max_route_m | number | Maximum allowed `total_distance_m` for the upload |

`upload_qc_pass` is `true` only when `total_distance_m <= max_route_m` for the export `vehicle_id` and every exported waypoint with `frame == 3` satisfies `-max_rel_alt_m <= alt_meters <= max_rel_alt_m`. Global (`0`) and terrain (`10`) frames are not checked against `max_rel_alt_m`.
