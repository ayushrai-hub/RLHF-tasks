import copy
import json
import math
import random
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8080"
C_LIGHT = 299792458.0


def deg(x):
    return x * 180.0 / math.pi


def rad(x):
    return x * math.pi / 180.0


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, s):
    return tuple(x * s for x in a)


def rz(theta, v):
    c = math.cos(theta)
    s = math.sin(theta)
    x, y, z = v
    return (c * x - s * y, s * x + c * y, z)


def rx(theta, v):
    c = math.cos(theta)
    s = math.sin(theta)
    x, y, z = v
    return (x, c * y - s * z, s * y + c * z)


def propagate(req, t):
    el = req["elements"]
    a = el["semi_major_axis_m"]
    e = el["eccentricity"]
    mu = req["mu_m3_s2"]
    n = math.sqrt(mu / (a * a * a))
    m = rad(el["mean_anomaly_deg"]) + n * (t - req["start_time_s"])
    E = m
    for _ in range(12):
        E -= (E - e * math.sin(E) - m) / (1 - e * math.cos(E))
    den = 1 - e * math.cos(E)
    root = math.sqrt(1 - e * e)
    rp = (a * (math.cos(E) - e), a * root * math.sin(E), 0.0)
    vp = (-a * n * math.sin(E) / den, a * n * root * math.cos(E) / den, 0.0)

    inc = rad(el["inclination_deg"])
    raan = rad(el["raan_deg"])
    argp = rad(el["arg_perigee_deg"])

    def rot(v):
        return rz(raan, rx(inc, rz(argp, v)))

    return rot(rp), rot(vp)


def observe(req, station, t):
    r_eci, v_eci = propagate(req, t)
    theta = rad(req["gmst0_deg"]) + req["earth_rotation_rad_s"] * (
        t - req["start_time_s"]
    )
    r_ecef = rz(-theta, r_eci)
    vv = rz(-theta, v_eci)
    omega = req["earth_rotation_rad_s"]
    v_ecef = (vv[0] + omega * r_ecef[1], vv[1] - omega * r_ecef[0], vv[2])

    lat = rad(station["latitude_deg"])
    lon = rad(station["longitude_deg"])
    rr = req["earth_radius_m"] + station["altitude_m"]
    st = (rr * math.cos(lat) * math.cos(lon), rr * math.cos(lat) * math.sin(lon), rr * math.sin(lat))
    rho = sub(r_ecef, st)
    rng = norm(rho)

    east = (-math.sin(lon), math.cos(lon), 0.0)
    north = (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat))
    up = (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
    e_m = dot(rho, east)
    n_m = dot(rho, north)
    u_m = dot(rho, up)
    elevation = math.asin(u_m / rng)
    azimuth = math.atan2(e_m, n_m)
    if azimuth < 0:
        azimuth += 2 * math.pi
    range_rate = dot(rho, v_ecef) / rng
    doppler = -req["carrier_frequency_hz"] * range_rate / C_LIGHT
    return {
        "time_s": t,
        "range_m": rng,
        "elevation_deg": deg(elevation),
        "azimuth_deg": deg(azimuth),
        "range_rate_m_s": range_rate,
        "doppler_hz": doppler,
        "sunlit": sunlit(req, r_eci),
    }


def sun_unit(req):
    s = tuple(req["sun_vector_eci"])
    n = norm(s)
    return mul(s, 1.0 / n)


def shadow_margin(req, t):
    r_eci, _ = propagate(req, t)
    s = sun_unit(req)
    axial = dot(r_eci, s)
    perp = math.sqrt(max(0.0, dot(r_eci, r_eci) - axial * axial))
    if axial >= 0:
        return perp + req["earth_radius_m"]
    return perp - req["earth_radius_m"]


def sunlit(req, r_eci):
    s = sun_unit(req)
    axial = dot(r_eci, s)
    if axial >= 0:
        return True
    perp = math.sqrt(max(0.0, dot(r_eci, r_eci) - axial * axial))
    return perp >= req["earth_radius_m"]


def margin(req, station, t):
    elev = observe(req, station, t)["elevation_deg"] - station["min_elevation_deg"]
    if not req.get("require_sunlit", False):
        return elev
    return min(elev, shadow_margin(req, t))


def grid_times(req):
    start = req["start_time_s"]
    end = start + req["duration_s"]
    t = start
    out = [t]
    while t + req["step_s"] < end:
        t += req["step_s"]
        out.append(t)
    if out[-1] != end:
        out.append(end)
    return out


def crossing(req, station, a, b):
    fa = margin(req, station, a)
    it = req.get("root_iterations") or 48
    for _ in range(it):
        mid = (a + b) / 2
        fm = margin(req, station, mid)
        if fa * fm <= 0:
            b = mid
        else:
            a = mid
            fa = fm
    return (a + b) / 2


def max_elevation(req, station, lo, hi):
    it = req.get("max_iterations") or 42
    for _ in range(it):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if observe(req, station, m1)["elevation_deg"] < observe(req, station, m2)["elevation_deg"]:
            lo = m1
        else:
            hi = m2
    t = (lo + hi) / 2
    return t, observe(req, station, t)


def contacts_only(req):
    times = grid_times(req)
    contacts = []
    for station in req["stations"]:
        margins = [margin(req, station, t) for t in times]
        inside = margins[0] >= 0
        start = times[0] if inside else None
        for i in range(len(times) - 1):
            a, b = times[i], times[i + 1]
            fa, fb = margins[i], margins[i + 1]
            if fa == 0 and not inside:
                inside = True
                start = a
            if fa * fb < 0 or fb == 0:
                root = crossing(req, station, a, b)
                if inside:
                    if root > start:
                        contacts.append((station, start, root))
                    inside = False
                    start = None
                else:
                    inside = True
                    start = root
        if inside:
            end = times[-1]
            if end > start:
                contacts.append((station, start, end))
    return contacts


def total_duration(req):
    return sum(end - start for _, start, end in contacts_only(req))


def eclipse_crossing(req, a, b):
    fa = shadow_margin(req, a)
    it = req.get("root_iterations") or 48
    for _ in range(it):
        mid = (a + b) / 2
        fm = shadow_margin(req, mid)
        if fa * fm <= 0:
            b = mid
        else:
            a = mid
            fa = fm
    return (a + b) / 2


def eclipse_intervals(req):
    times = grid_times(req)
    vals = [shadow_margin(req, t) for t in times]
    inside = vals[0] < 0
    start = times[0] if inside else None
    out = []
    for i in range(len(times) - 1):
        a, b = times[i], times[i + 1]
        fa, fb = vals[i], vals[i + 1]
        if fa == 0 and not inside:
            inside = True
            start = a
        if fa * fb < 0 or fb == 0:
            root = eclipse_crossing(req, a, b)
            if inside:
                if root > start:
                    out.append({"start_time_s": start, "end_time_s": root, "duration_s": root - start})
                inside = False
                start = None
            else:
                inside = True
                start = root
    if inside:
        end = times[-1]
        if end > start:
            out.append({"start_time_s": start, "end_time_s": end, "duration_s": end - start})
    return out


def visible_stations_at(req, t):
    out = []
    for station in req["stations"]:
        if observe(req, station, t)["elevation_deg"] - station["min_elevation_deg"] >= 0:
            out.append(station["id"])
    return out


def terminator_events(req):
    times = grid_times(req)
    vals = [shadow_margin(req, t) for t in times]
    inside = vals[0] < 0
    out = []
    for i in range(len(times) - 1):
        a, b = times[i], times[i + 1]
        fa, fb = vals[i], vals[i + 1]
        if fa == 0 and not inside:
            inside = True
        if fa * fb < 0 or fb == 0:
            root = eclipse_crossing(req, a, b)
            if inside:
                kind = "egress"
                inside = False
            else:
                kind = "ingress"
                inside = True
            out.append(
                {
                    "time_s": root,
                    "kind": kind,
                    "shadow_margin_m": shadow_margin(req, root),
                    "visible_stations": visible_stations_at(req, root),
                }
            )
    return out


def expected(req):
    contacts = []
    times = grid_times(req)
    for station, start, end in contacts_only(req):
        sample_times = [start]
        sample_times.extend(t for t in times if start < t < end)
        sample_times.append(end)
        samples = [observe(req, station, t) for t in sample_times]
        max_t, max_sample = max_elevation(req, station, start, end)
        min_range = min([s["range_m"] for s in samples] + [max_sample["range_m"]])
        contacts.append(
            {
                "station_id": station["id"],
                "start_time_s": start,
                "end_time_s": end,
                "duration_s": end - start,
                "max_elevation_deg": max_sample["elevation_deg"],
                "max_elevation_time_s": max_t,
                "min_range_m": min_range,
                "samples": samples,
            }
        )

    sensitivities = []
    for name, h in [("semi_major_axis_m", 1.0), ("mean_anomaly_deg", 0.001), ("gmst0_deg", 0.001), ("sun_vector_y", 0.0001)]:
        plus = copy.deepcopy(req)
        minus = copy.deepcopy(req)
        if name == "semi_major_axis_m":
            plus["elements"][name] += h
            minus["elements"][name] -= h
        elif name == "mean_anomaly_deg":
            plus["elements"][name] += h
            minus["elements"][name] -= h
        elif name == "sun_vector_y":
            plus["sun_vector_eci"][1] += h
            minus["sun_vector_eci"][1] -= h
        else:
            plus[name] += h
            minus[name] -= h
        sensitivities.append(
            {
                "parameter": name,
                "d_total_contact_seconds_d_x": (total_duration(plus) - total_duration(minus)) / (2 * h),
            }
        )

    return {
        "case_id": req["case_id"],
        "total_contacts": len(contacts),
        "total_contact_seconds": sum(c["duration_s"] for c in contacts),
        "total_eclipse_seconds": sum(e["duration_s"] for e in eclipse_intervals(req)),
        "contacts": contacts,
        "eclipse_intervals": eclipse_intervals(req),
        "terminator_events": terminator_events(req),
        "sensitivities": sensitivities,
    }


def post(req):
    data = json.dumps(req).encode()
    request = urllib.request.Request(
        BASE + "/v1/contacts",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.headers["Content-Type"].startswith("application/json")
        return json.loads(response.read())


def close(a, b, tol=3e-6):
    assert abs(a - b) <= tol, (a, b, abs(a - b))


def compare(got, exp):
    assert got["case_id"] == exp["case_id"]
    assert got["total_contacts"] == exp["total_contacts"]
    close(got["total_contact_seconds"], exp["total_contact_seconds"])
    close(got["total_eclipse_seconds"], exp["total_eclipse_seconds"])
    assert len(got["contacts"]) == len(exp["contacts"])
    for gc, ec in zip(got["contacts"], exp["contacts"]):
        assert gc["station_id"] == ec["station_id"]
        for k in ["start_time_s", "end_time_s", "duration_s", "max_elevation_deg", "max_elevation_time_s"]:
            close(gc[k], ec[k], 3e-5)
        close(gc["min_range_m"], ec["min_range_m"], 2e-3)
        assert len(gc["samples"]) == len(ec["samples"])
        for gs, es in zip(gc["samples"], ec["samples"]):
            for k in ["time_s", "range_m", "elevation_deg", "azimuth_deg", "range_rate_m_s", "doppler_hz"]:
                close(gs[k], es[k], 5e-5 if k in ("doppler_hz", "range_m") else 3e-6)
            assert gs["sunlit"] is es["sunlit"]
    assert len(got["eclipse_intervals"]) == len(exp["eclipse_intervals"])
    for ge, ee in zip(got["eclipse_intervals"], exp["eclipse_intervals"]):
        for k in ["start_time_s", "end_time_s", "duration_s"]:
            close(ge[k], ee[k], 3e-5)
    assert len(got["terminator_events"]) == len(exp["terminator_events"])
    for ge, ee in zip(got["terminator_events"], exp["terminator_events"]):
        assert ge["kind"] == ee["kind"]
        assert ge["visible_stations"] == ee["visible_stations"]
        close(ge["time_s"], ee["time_s"], 3e-5)
        close(ge["shadow_margin_m"], ee["shadow_margin_m"], 2e-4)
    assert len(got["sensitivities"]) == len(exp["sensitivities"])
    for gs, es in zip(got["sensitivities"], exp["sensitivities"]):
        assert gs["parameter"] == es["parameter"]
        close(gs["d_total_contact_seconds_d_x"], es["d_total_contact_seconds_d_x"], 2e-4)


def base_req():
    return {
        "case_id": "polar-contacts",
        "mu_m3_s2": 398600441800000.0,
        "earth_radius_m": 6378137.0,
        "earth_rotation_rad_s": 0.000072921159,
        "gmst0_deg": 22.5,
        "carrier_frequency_hz": 2250000000.0,
        "sun_vector_eci": [0.35, -0.72, 0.60],
        "require_sunlit": True,
        "start_time_s": 0.0,
        "duration_s": 10800.0,
        "step_s": 90.0,
        "root_iterations": 50,
        "max_iterations": 44,
        "elements": {
            "semi_major_axis_m": 7078137.0,
            "eccentricity": 0.006,
            "inclination_deg": 97.4,
            "raan_deg": 41.0,
            "arg_perigee_deg": 63.0,
            "mean_anomaly_deg": 12.0,
        },
        "stations": [
            {"id": "SVAL", "latitude_deg": 78.2298, "longitude_deg": 15.4078, "altitude_m": 460.0, "min_elevation_deg": 7.5},
            {"id": "TROLL", "latitude_deg": -72.0117, "longitude_deg": 2.5351, "altitude_m": 1275.0, "min_elevation_deg": 5.0},
        ],
    }


def test_health():
    with urllib.request.urlopen(BASE + "/health", timeout=5) as r:
        assert json.loads(r.read())["ok"] is True


def test_polar_dual_station_case():
    req = base_req()
    compare(post(req), expected(req))


def test_equatorial_midlatitude_case():
    req = base_req()
    req["case_id"] = "equatorial-mix"
    req["duration_s"] = 14400.0
    req["step_s"] = 75.0
    req["gmst0_deg"] = -35.0
    req["elements"] = {
        "semi_major_axis_m": 7218137.0,
        "eccentricity": 0.021,
        "inclination_deg": 28.5,
        "raan_deg": 5.0,
        "arg_perigee_deg": 118.0,
        "mean_anomaly_deg": 201.0,
    }
    req["stations"] = [
        {"id": "KOU", "latitude_deg": 5.2514, "longitude_deg": -52.8047, "altitude_m": 110.0, "min_elevation_deg": 3.0},
        {"id": "CAN", "latitude_deg": -35.3983, "longitude_deg": 148.9819, "altitude_m": 690.0, "min_elevation_deg": 8.0},
    ]
    compare(post(req), expected(req))


def test_seeded_contact_grid():
    rng = random.Random(9142)
    for i in range(4):
        req = base_req()
        req["case_id"] = f"seed-{i}"
        req["duration_s"] = rng.choice([7200.0, 9600.0, 12600.0])
        req["step_s"] = rng.choice([60.0, 80.0, 120.0])
        req["gmst0_deg"] = rng.uniform(-120, 120)
        req["elements"] = {
            "semi_major_axis_m": 6900000.0 + rng.uniform(350000, 900000),
            "eccentricity": rng.uniform(0.0, 0.035),
            "inclination_deg": rng.uniform(35.0, 105.0),
            "raan_deg": rng.uniform(-80.0, 140.0),
            "arg_perigee_deg": rng.uniform(0.0, 300.0),
            "mean_anomaly_deg": rng.uniform(-40.0, 260.0),
        }
        req["stations"] = [
            {"id": "A", "latitude_deg": rng.uniform(-55, 55), "longitude_deg": rng.uniform(-160, 160), "altitude_m": rng.uniform(0, 1500), "min_elevation_deg": rng.uniform(0, 10)},
            {"id": "B", "latitude_deg": rng.uniform(-75, 75), "longitude_deg": rng.uniform(-160, 160), "altitude_m": rng.uniform(0, 1800), "min_elevation_deg": rng.uniform(2, 12)},
        ]
        compare(post(req), expected(req))


def test_terminator_events_are_ordered_and_classified():
    req = base_req()
    req["duration_s"] = 18000.0
    req["step_s"] = 60.0
    got = post(req)
    exp = expected(req)
    compare(got, exp)
    events = got["terminator_events"]
    assert len(events) >= 2
    assert [e["time_s"] for e in events] == sorted(e["time_s"] for e in events)
    assert {e["kind"] for e in events}.issubset({"ingress", "egress"})
    for event in events:
        assert abs(event["shadow_margin_m"]) < 1e-3


def test_terminator_events_are_reported_when_sunlight_not_required():
    req = base_req()
    req["case_id"] = "terminator-unclipped-contacts"
    req["require_sunlit"] = False
    req["duration_s"] = 14400.0
    got = post(req)
    exp = expected(req)
    compare(got, exp)
    assert len(got["terminator_events"]) > 0
    assert [event["kind"] for event in got["terminator_events"]] == [event["kind"] for event in exp["terminator_events"]]


def test_sunlit_clipping_changes_contacts_but_not_terminator_events():
    sunlit_req = base_req()
    sunlit_req["case_id"] = "sunlit-clipped"
    sunlit_req["duration_s"] = 18000.0
    sunlit_req["step_s"] = 60.0
    raw_req = copy.deepcopy(sunlit_req)
    raw_req["case_id"] = "raw-visibility"
    raw_req["require_sunlit"] = False
    sunlit = post(sunlit_req)
    raw = post(raw_req)
    compare(sunlit, expected(sunlit_req))
    compare(raw, expected(raw_req))
    assert sunlit["terminator_events"] == raw["terminator_events"]
    assert sunlit["total_contact_seconds"] <= raw["total_contact_seconds"]


def test_invalid_perigee_inside_earth_rejected():
    req = base_req()
    req["elements"]["semi_major_axis_m"] = 6400000.0
    req["elements"]["eccentricity"] = 0.01
    try:
        post(req)
    except urllib.error.HTTPError as e:
        assert e.code == 400
    else:
        raise AssertionError("invalid request should fail")


def test_invalid_zero_sun_vector_rejected():
    req = base_req()
    req["sun_vector_eci"] = [0.0, 0.0, 0.0]
    try:
        post(req)
    except urllib.error.HTTPError as e:
        assert e.code == 400
    else:
        raise AssertionError("zero sun vector should fail")
