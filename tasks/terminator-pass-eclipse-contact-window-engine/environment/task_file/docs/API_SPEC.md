# Eclipse Contact Window API Specification

This file is normative.

## Endpoint

`POST /v1/contacts` computes deterministic sunlit ground-station contact windows, Earth-shadow eclipse intervals, and terminator crossing events for one elliptic two-body spacecraft orbit over a fixed time span.

`GET /health` returns JSON and is already implemented.

## Request

```json
{
  "case_id": "leo-a",
  "mu_m3_s2": 398600441800000.0,
  "earth_radius_m": 6378137.0,
  "earth_rotation_rad_s": 0.000072921159,
  "gmst0_deg": 12.0,
  "carrier_frequency_hz": 2250000000.0,
  "sun_vector_eci": [0.35, -0.72, 0.60],
  "require_sunlit": true,
  "start_time_s": 0.0,
  "duration_s": 7200.0,
  "step_s": 60.0,
  "root_iterations": 48,
  "max_iterations": 42,
  "elements": {
    "semi_major_axis_m": 6928137.0,
    "eccentricity": 0.001,
    "inclination_deg": 51.6,
    "raan_deg": 18.0,
    "arg_perigee_deg": 37.0,
    "mean_anomaly_deg": 5.0
  },
  "stations": [
    {
      "id": "MAD",
      "latitude_deg": 40.4314,
      "longitude_deg": -4.2481,
      "altitude_m": 730.0,
      "min_elevation_deg": 10.0
    }
  ]
}
```

All angles in the request and response are degrees unless a field name explicitly says radians. Times are seconds from the same arbitrary epoch. `sun_vector_eci` is a nonzero inertial vector pointing from Earth toward the Sun; normalize it before use. If `require_sunlit` is true, a contact exists only when the spacecraft is above the station elevation mask and outside Earth shadow.

## Validation

Return HTTP 400 for invalid JSON or invalid values:

- `mu_m3_s2`, `earth_radius_m`, `carrier_frequency_hz`, `duration_s`, and `step_s` must be positive.
- `earth_rotation_rad_s` must be finite.
- `sun_vector_eci` must have exactly three finite values and must not be the zero vector.
- `semi_major_axis_m` must be positive.
- `eccentricity` must satisfy `0 <= eccentricity < 0.8`.
- `semi_major_axis_m * (1 - eccentricity)` must be greater than `earth_radius_m`.
- `latitude_deg` must be in `[-90, 90]`.
- `longitude_deg` must be in `[-180, 180]`.
- `min_elevation_deg` must be in `[-5, 85]`.
- There must be at least one station.
- Station IDs must be non-empty.

If `root_iterations <= 0`, use 48. If `max_iterations <= 0`, use 42.

## Orbital Propagation

Use a Keplerian two-body elliptic orbit. Let:

- `a` be `semi_major_axis_m`
- `e` be `eccentricity`
- `i` be inclination
- `Omega` be RAAN
- `omega` be argument of perigee
- `M0` be mean anomaly at `start_time_s`
- `mu` be `mu_m3_s2`
- `n = sqrt(mu / a^3)`
- `M(t) = M0 + n * (t - start_time_s)`

Normalize no angles before solving. Solve Kepler's equation `E - e*sin(E) = M` with Newton's method using exactly 12 iterations, starting from `E = M`.

Then:

```text
x_p = a * (cos(E) - e)
y_p = a * sqrt(1 - e^2) * sin(E)
vx_p = -a * n * sin(E) / (1 - e*cos(E))
vy_p =  a * n * sqrt(1 - e^2) * cos(E) / (1 - e*cos(E))
```

Rotate from perifocal to ECI with `Rz(Omega) * Rx(i) * Rz(omega)`.

## Ground Geometry

Use a spherical Earth. Station ECEF coordinates:

```text
r = earth_radius_m + altitude_m
x = r*cos(lat)*cos(lon)
y = r*cos(lat)*sin(lon)
z = r*sin(lat)
```

Convert ECI spacecraft state to ECEF with:

```text
theta = gmst0_deg*pi/180 + earth_rotation_rad_s * (t - start_time_s)
r_ecef = Rz(-theta) * r_eci
v_ecef = Rz(-theta) * v_eci - omega_earth_cross_r_ecef
omega_earth_cross_r_ecef = (-earth_rotation_rad_s*y, earth_rotation_rad_s*x, 0)
```

Let `rho = r_ecef - station_ecef`. Let station east, north, up axes be:

```text
east  = (-sin(lon), cos(lon), 0)
north = (-sin(lat)*cos(lon), -sin(lat)*sin(lon), cos(lat))
up    = ( cos(lat)*cos(lon),  cos(lat)*sin(lon), sin(lat))
```

Then:

```text
east_m = dot(rho, east)
north_m = dot(rho, north)
up_m = dot(rho, up)
range_m = norm(rho)
elevation_rad = asin(up_m / range_m)
azimuth_rad = atan2(east_m, north_m)
```

If azimuth is negative, add `2*pi`. Range-rate is `dot(rho, v_ecef) / range_m`. Doppler is `-carrier_frequency_hz * range_rate_m_s / 299792458.0`.

## Contact Windows

For each station independently, define the elevation margin:

```text
elevation_margin(t) = elevation_deg(t) - min_elevation_deg
```

If `require_sunlit` is false, `margin(t) = elevation_margin(t)`. If
`require_sunlit` is true, `margin(t) = min(elevation_margin(t), shadow_margin(t))`
using the eclipse model below. Thus contact windows may be split or shortened by
shadow ingress and egress, not only by horizon crossings.

Create a regular time grid from `start_time_s` to `start_time_s + duration_s`, inclusive. Advance by `step_s`. If the next full step would exceed the end time, append exactly the end time as the final grid sample. If `duration_s` is an exact multiple of `step_s`, do not append a duplicate end sample.

Find contact intervals where `margin(t) >= 0`.

Use adjacent grid samples to bracket crossings. When `margin(a)` and `margin(b)` have opposite signs or either endpoint is zero, refine the crossing with bisection for exactly `root_iterations` updates. Use this endpoint convention:

- Let `fa = margin(a)`.
- At each update, `mid = (a + b) / 2` and `fm = margin(mid)`.
- If `fa * fm <= 0`, set `b = mid`.
- Otherwise set `a = mid` and `fa = fm`.
- Return `(a + b) / 2`.

If the first grid sample is inside contact, the contact starts at `start_time_s`. If the last grid sample is inside contact, the contact ends at `start_time_s + duration_s`.

Discard zero or negative duration intervals. Contacts are ordered by station input order, then by start time.

## Samples Inside Contact

For every contact, emit samples at:

1. the refined contact start time,
2. every regular grid time strictly inside `(start, end)`,
3. the refined contact end time.

Samples must be sorted by increasing `time_s`. Do not round or truncate numeric fields before JSON encoding.

## Max Elevation and Min Range

For each contact, find max elevation time with ternary search on `[start, end]` using exactly `max_iterations` updates:

```text
m1 = lo + (hi - lo) / 3
m2 = hi - (hi - lo) / 3
if elevation(m1) < elevation(m2):
    lo = m1
else:
    hi = m2
```

Return `(lo + hi) / 2` as `max_elevation_time_s`, and evaluate `max_elevation_deg` at that time.

`min_range_m` is the minimum `range_m` over the emitted contact samples and the max-elevation sample. It is not a separate range optimization.

## Eclipse Model

Use a cylindrical Earth shadow aligned with the Sun vector. Let `s` be the
normalized `sun_vector_eci` and `r_eci(t)` be the spacecraft inertial position.

```text
axial = dot(r_eci, s)
perp = sqrt(|r_eci|^2 - axial^2)
```

The spacecraft is eclipsed exactly when `axial < 0` and
`perp < earth_radius_m`. The signed shadow margin is:

```text
shadow_margin(t) = perp + earth_radius_m  if axial >= 0
shadow_margin(t) = perp - earth_radius_m  otherwise
```

Compute eclipse intervals from the same regular time grid used for contacts.
Adjacent grid samples with opposite signs of `shadow_margin`, or a zero endpoint,
bracket a shadow boundary. Refine each boundary with the same bisection
convention and `root_iterations` count used for contact crossings. Discard zero
or negative duration eclipse intervals and order them by start time.

## Terminator Crossing Events

The response must also include `terminator_events`, one entry for every refined
shadow boundary found while computing eclipse intervals. These events represent
spacecraft crossings of the cylindrical Earth-shadow terminator and are emitted
even when `require_sunlit` is false.

For every adjacent grid pair whose `shadow_margin` values bracket a crossing,
refine the crossing time with the same bisection rule and iteration count used
for eclipse intervals. Evaluate `shadow_margin` again at the refined event time.
Classify the event by the sign transition across the bracket:

```text
kind = "ingress"  when the spacecraft goes from sunlit/outside shadow to eclipsed
kind = "egress"   when the spacecraft goes from eclipsed to sunlit/outside shadow
```

When one endpoint has exactly zero margin, use the state immediately before and
after the bracket implied by the interval scan; the resulting event kind must
match the eclipse interval transition. Events are ordered by increasing time.

Each event includes:

- `time_s`: refined boundary time
- `kind`: `"ingress"` or `"egress"`
- `shadow_margin_m`: signed shadow margin evaluated at `time_s`
- `visible_stations`: station IDs whose elevation margin is nonnegative at
  `time_s`, ignoring `require_sunlit`

The `visible_stations` list preserves station input order. It may be empty when
the spacecraft crosses the terminator outside all station visibility masks.

## Sensitivities

Return sensitivities in this order:

1. `semi_major_axis_m`
2. `mean_anomaly_deg`
3. `gmst0_deg`
4. `sun_vector_y`

For each parameter, compute total contact duration for the whole request after perturbing only that parameter by `+h` and `-h`, then report the central finite difference:

```text
d_total_contact_seconds_d_x = (total_plus - total_minus) / (2*h)
```

Use `h = 1.0` for `semi_major_axis_m`, `h = 0.001` degrees for the two angular parameters, and `h = 0.0001` for `sun_vector_y`. For `sun_vector_y`, perturb only element 1 of `sun_vector_eci`; do not renormalize before perturbing because the visibility algorithm normalizes internally. Re-run the full contact-window algorithm for each perturbed request.

## Response

Return UTF-8 JSON with two-space indentation and a trailing newline.

Fields:

- `case_id`: copied from request
- `total_contacts`: number of contact windows
- `total_contact_seconds`: sum of all contact durations
- `total_eclipse_seconds`: sum of all eclipse interval durations
- `contacts`: contact windows
- `eclipse_intervals`: shadow intervals
- `terminator_events`: shadow-boundary events with station visibility context
- `sensitivities`: finite-difference sensitivities

Each contact has:

- `station_id`
- `start_time_s`
- `end_time_s`
- `duration_s`
- `max_elevation_deg`
- `max_elevation_time_s`
- `min_range_m`
- `samples`

Each sample has:

- `time_s`
- `range_m`
- `elevation_deg`
- `azimuth_deg`
- `range_rate_m_s`
- `doppler_hz`
- `sunlit`

Each eclipse interval has:

- `start_time_s`
- `end_time_s`
- `duration_s`

Each terminator event has:

- `time_s`
- `kind`
- `shadow_margin_m`
- `visible_stations`
