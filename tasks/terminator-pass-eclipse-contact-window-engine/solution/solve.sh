#!/usr/bin/env bash
set -euo pipefail
cat > /app/src/orbit/model.go <<'GO'
package orbit

import (
	"errors"
	"math"
)

const cLight = 299792458.0

type Elements struct {
	SemiMajorAxisM float64 `json:"semi_major_axis_m"`
	Eccentricity   float64 `json:"eccentricity"`
	InclinationDeg float64 `json:"inclination_deg"`
	RaanDeg        float64 `json:"raan_deg"`
	ArgPerigeeDeg  float64 `json:"arg_perigee_deg"`
	MeanAnomalyDeg float64 `json:"mean_anomaly_deg"`
}

type Station struct {
	ID              string  `json:"id"`
	LatitudeDeg     float64 `json:"latitude_deg"`
	LongitudeDeg    float64 `json:"longitude_deg"`
	AltitudeM       float64 `json:"altitude_m"`
	MinElevationDeg float64 `json:"min_elevation_deg"`
}

type Request struct {
	CaseID             string    `json:"case_id"`
	MuM3S2             float64   `json:"mu_m3_s2"`
	EarthRadiusM       float64   `json:"earth_radius_m"`
	EarthRotationRadS  float64   `json:"earth_rotation_rad_s"`
	Gmst0Deg           float64   `json:"gmst0_deg"`
	CarrierFrequencyHz float64   `json:"carrier_frequency_hz"`
	SunVectorECI       []float64 `json:"sun_vector_eci"`
	RequireSunlit      bool      `json:"require_sunlit"`
	StartTimeS         float64   `json:"start_time_s"`
	DurationS          float64   `json:"duration_s"`
	StepS              float64   `json:"step_s"`
	RootIterations     int       `json:"root_iterations"`
	MaxIterations      int       `json:"max_iterations"`
	Elements           Elements  `json:"elements"`
	Stations           []Station `json:"stations"`
}

type Sample struct {
	TimeS        float64 `json:"time_s"`
	RangeM      float64 `json:"range_m"`
	ElevationDeg float64 `json:"elevation_deg"`
	AzimuthDeg   float64 `json:"azimuth_deg"`
	RangeRateMS  float64 `json:"range_rate_m_s"`
	DopplerHz    float64 `json:"doppler_hz"`
	Sunlit        bool    `json:"sunlit"`
}

type Contact struct {
	StationID         string   `json:"station_id"`
	StartTimeS        float64  `json:"start_time_s"`
	EndTimeS          float64  `json:"end_time_s"`
	DurationS         float64  `json:"duration_s"`
	MaxElevationDeg   float64  `json:"max_elevation_deg"`
	MaxElevationTimeS float64  `json:"max_elevation_time_s"`
	MinRangeM         float64  `json:"min_range_m"`
	Samples           []Sample `json:"samples"`
}

type Sensitivity struct {
	Parameter              string  `json:"parameter"`
	DTotalContactSecondsDX float64 `json:"d_total_contact_seconds_d_x"`
}

type EclipseInterval struct {
	StartTimeS float64 `json:"start_time_s"`
	EndTimeS   float64 `json:"end_time_s"`
	DurationS  float64 `json:"duration_s"`
}

type TerminatorEvent struct {
	TimeS           float64  `json:"time_s"`
	Kind            string   `json:"kind"`
	ShadowMargin    float64  `json:"shadow_margin_m"`
	VisibleStations []string `json:"visible_stations"`
}

type Response struct {
	CaseID              string        `json:"case_id"`
	TotalContacts       int           `json:"total_contacts"`
	TotalContactSeconds float64       `json:"total_contact_seconds"`
	TotalEclipseSeconds float64       `json:"total_eclipse_seconds"`
	Contacts            []Contact     `json:"contacts"`
	EclipseIntervals    []EclipseInterval `json:"eclipse_intervals"`
	TerminatorEvents    []TerminatorEvent `json:"terminator_events"`
	Sensitivities        []Sensitivity `json:"sensitivities"`
}

type vec3 struct{ x, y, z float64 }
type interval struct {
	station Station
	start   float64
	end     float64
}

func Solve(req Request) (Response, error) {
	if err := validate(req); err != nil {
		return Response{}, err
	}
	contacts := buildContacts(req, true)
	total := 0.0
	for _, c := range contacts {
		total += c.DurationS
	}
	eclipses := eclipseIntervals(req)
	eclipseTotal := 0.0
	for _, e := range eclipses {
		eclipseTotal += e.DurationS
	}
	return Response{
		CaseID:              req.CaseID,
		TotalContacts:       len(contacts),
		TotalContactSeconds: total,
		TotalEclipseSeconds: eclipseTotal,
		Contacts:            contacts,
		EclipseIntervals:    eclipses,
		TerminatorEvents:    terminatorEvents(req),
		Sensitivities:        sensitivities(req),
	}, nil
}

func validate(r Request) error {
	if !positive(r.MuM3S2) || !positive(r.EarthRadiusM) || !positive(r.CarrierFrequencyHz) || !positive(r.DurationS) || !positive(r.StepS) {
		return errors.New("invalid request")
	}
	if !finite(r.EarthRotationRadS) || !positive(r.Elements.SemiMajorAxisM) {
		return errors.New("invalid request")
	}
	if len(r.SunVectorECI) != 3 || !finite(r.SunVectorECI[0]) || !finite(r.SunVectorECI[1]) || !finite(r.SunVectorECI[2]) {
		return errors.New("invalid sun vector")
	}
	if norm(vec3{r.SunVectorECI[0], r.SunVectorECI[1], r.SunVectorECI[2]}) == 0 {
		return errors.New("invalid sun vector")
	}
	if r.Elements.Eccentricity < 0 || r.Elements.Eccentricity >= 0.8 || !finite(r.Elements.Eccentricity) {
		return errors.New("invalid request")
	}
	if r.Elements.SemiMajorAxisM*(1-r.Elements.Eccentricity) <= r.EarthRadiusM {
		return errors.New("perigee must be above earth")
	}
	if len(r.Stations) == 0 {
		return errors.New("at least one station is required")
	}
	for _, s := range r.Stations {
		if s.ID == "" || s.LatitudeDeg < -90 || s.LatitudeDeg > 90 || s.LongitudeDeg < -180 || s.LongitudeDeg > 180 || s.MinElevationDeg < -5 || s.MinElevationDeg > 85 {
			return errors.New("invalid station")
		}
	}
	return nil
}

func positive(v float64) bool { return finite(v) && v > 0 }
func finite(v float64) bool   { return !math.IsNaN(v) && !math.IsInf(v, 0) }
func rootIterations(r Request) int {
	if r.RootIterations <= 0 {
		return 48
	}
	return r.RootIterations
}
func maxIterations(r Request) int {
	if r.MaxIterations <= 0 {
		return 42
	}
	return r.MaxIterations
}

func buildContacts(req Request, full bool) []Contact {
	ivs := contactIntervals(req)
	if !full {
		out := make([]Contact, 0, len(ivs))
		for _, iv := range ivs {
			out = append(out, Contact{DurationS: iv.end - iv.start})
		}
		return out
	}
	times := gridTimes(req)
	out := make([]Contact, 0, len(ivs))
	for _, iv := range ivs {
		sampleTimes := []float64{iv.start}
		for _, t := range times {
			if iv.start < t && t < iv.end {
				sampleTimes = append(sampleTimes, t)
			}
		}
		sampleTimes = append(sampleTimes, iv.end)
		samples := make([]Sample, 0, len(sampleTimes))
		for _, t := range sampleTimes {
			samples = append(samples, observe(req, iv.station, t))
		}
		maxT, maxSample := maxElevation(req, iv.station, iv.start, iv.end)
		minRange := maxSample.RangeM
		for _, s := range samples {
			if s.RangeM < minRange {
				minRange = s.RangeM
			}
		}
		out = append(out, Contact{
			StationID:         iv.station.ID,
			StartTimeS:        iv.start,
			EndTimeS:          iv.end,
			DurationS:         iv.end - iv.start,
			MaxElevationDeg:   maxSample.ElevationDeg,
			MaxElevationTimeS: maxT,
			MinRangeM:         minRange,
			Samples:           samples,
		})
	}
	return out
}

func contactIntervals(req Request) []interval {
	times := gridTimes(req)
	out := []interval{}
	for _, station := range req.Stations {
		margins := make([]float64, len(times))
		for i, t := range times {
			margins[i] = margin(req, station, t)
		}
		inside := margins[0] >= 0
		start := 0.0
		if inside {
			start = times[0]
		}
		for i := 0; i < len(times)-1; i++ {
			a, b := times[i], times[i+1]
			fa, fb := margins[i], margins[i+1]
			if fa == 0 && !inside {
				inside = true
				start = a
			}
			if fa*fb < 0 || fb == 0 {
				root := crossing(req, station, a, b)
				if inside {
					if root > start {
						out = append(out, interval{station: station, start: start, end: root})
					}
					inside = false
				} else {
					inside = true
					start = root
				}
			}
		}
		if inside {
			end := times[len(times)-1]
			if end > start {
				out = append(out, interval{station: station, start: start, end: end})
			}
		}
	}
	return out
}

func totalDuration(req Request) float64 {
	total := 0.0
	for _, iv := range contactIntervals(req) {
		total += iv.end - iv.start
	}
	return total
}

func sensitivities(req Request) []Sensitivity {
	params := []struct {
		name string
		h    float64
	}{
		{"semi_major_axis_m", 1.0},
		{"mean_anomaly_deg", 0.001},
		{"gmst0_deg", 0.001},
		{"sun_vector_y", 0.0001},
	}
	out := make([]Sensitivity, 0, len(params))
	for _, p := range params {
		plus, minus := req, req
		switch p.name {
		case "semi_major_axis_m":
			plus.Elements.SemiMajorAxisM += p.h
			minus.Elements.SemiMajorAxisM -= p.h
		case "mean_anomaly_deg":
			plus.Elements.MeanAnomalyDeg += p.h
			minus.Elements.MeanAnomalyDeg -= p.h
		case "gmst0_deg":
			plus.Gmst0Deg += p.h
			minus.Gmst0Deg -= p.h
		case "sun_vector_y":
			plus.SunVectorECI = append([]float64(nil), req.SunVectorECI...)
			minus.SunVectorECI = append([]float64(nil), req.SunVectorECI...)
			plus.SunVectorECI[1] += p.h
			minus.SunVectorECI[1] -= p.h
		}
		out = append(out, Sensitivity{
			Parameter:              p.name,
			DTotalContactSecondsDX: (totalDuration(plus) - totalDuration(minus)) / (2 * p.h),
		})
	}
	return out
}

func gridTimes(req Request) []float64 {
	start := req.StartTimeS
	end := start + req.DurationS
	times := []float64{start}
	t := start
	for t+req.StepS < end {
		t += req.StepS
		times = append(times, t)
	}
	if times[len(times)-1] != end {
		times = append(times, end)
	}
	return times
}

func crossing(req Request, station Station, a, b float64) float64 {
	fa := margin(req, station, a)
	for i := 0; i < rootIterations(req); i++ {
		mid := (a + b) / 2
		fm := margin(req, station, mid)
		if fa*fm <= 0 {
			b = mid
		} else {
			a = mid
			fa = fm
		}
	}
	return (a + b) / 2
}

func maxElevation(req Request, station Station, lo, hi float64) (float64, Sample) {
	for i := 0; i < maxIterations(req); i++ {
		m1 := lo + (hi-lo)/3
		m2 := hi - (hi-lo)/3
		if observe(req, station, m1).ElevationDeg < observe(req, station, m2).ElevationDeg {
			lo = m1
		} else {
			hi = m2
		}
	}
	t := (lo + hi) / 2
	return t, observe(req, station, t)
}

func margin(req Request, station Station, t float64) float64 {
	elev := observe(req, station, t).ElevationDeg - station.MinElevationDeg
	if !req.RequireSunlit {
		return elev
	}
	sun := shadowMargin(req, t)
	if sun < elev {
		return sun
	}
	return elev
}

func observe(req Request, station Station, t float64) Sample {
	rECI, vECI := propagate(req, t)
	theta := rad(req.Gmst0Deg) + req.EarthRotationRadS*(t-req.StartTimeS)
	rECEF := rz(-theta, rECI)
	vv := rz(-theta, vECI)
	omega := req.EarthRotationRadS
	vECEF := vec3{vv.x + omega*rECEF.y, vv.y - omega*rECEF.x, vv.z}

	lat := rad(station.LatitudeDeg)
	lon := rad(station.LongitudeDeg)
	rr := req.EarthRadiusM + station.AltitudeM
	st := vec3{rr * math.Cos(lat) * math.Cos(lon), rr * math.Cos(lat) * math.Sin(lon), rr * math.Sin(lat)}
	rho := sub(rECEF, st)
	rng := norm(rho)

	east := vec3{-math.Sin(lon), math.Cos(lon), 0}
	north := vec3{-math.Sin(lat) * math.Cos(lon), -math.Sin(lat) * math.Sin(lon), math.Cos(lat)}
	up := vec3{math.Cos(lat) * math.Cos(lon), math.Cos(lat) * math.Sin(lon), math.Sin(lat)}
	eastM := dot(rho, east)
	northM := dot(rho, north)
	upM := dot(rho, up)
	elevation := math.Asin(upM / rng)
	azimuth := math.Atan2(eastM, northM)
	if azimuth < 0 {
		azimuth += 2 * math.Pi
	}
	rangeRate := dot(rho, vECEF) / rng
	return Sample{
		TimeS:        t,
		RangeM:      rng,
		ElevationDeg: deg(elevation),
		AzimuthDeg:   deg(azimuth),
		RangeRateMS:  rangeRate,
		DopplerHz:    -req.CarrierFrequencyHz * rangeRate / cLight,
		Sunlit:       sunlit(req, rECI),
	}
}

func sunUnit(req Request) vec3 {
	v := vec3{req.SunVectorECI[0], req.SunVectorECI[1], req.SunVectorECI[2]}
	n := norm(v)
	return vec3{v.x / n, v.y / n, v.z / n}
}

func sunlit(req Request, r vec3) bool {
	s := sunUnit(req)
	axial := dot(r, s)
	if axial >= 0 {
		return true
	}
	perp2 := dot(r, r) - axial*axial
	return math.Sqrt(math.Max(0, perp2)) >= req.EarthRadiusM
}

func shadowMargin(req Request, t float64) float64 {
	r, _ := propagate(req, t)
	s := sunUnit(req)
	axial := dot(r, s)
	perp2 := dot(r, r) - axial*axial
	perp := math.Sqrt(math.Max(0, perp2))
	if axial >= 0 {
		return perp + req.EarthRadiusM
	}
	return perp - req.EarthRadiusM
}

func eclipseIntervals(req Request) []EclipseInterval {
	times := gridTimes(req)
	out := []EclipseInterval{}
	values := make([]float64, len(times))
	for i, t := range times {
		values[i] = shadowMargin(req, t)
	}
	inside := values[0] < 0
	start := 0.0
	if inside {
		start = times[0]
	}
	for i := 0; i < len(times)-1; i++ {
		a, b := times[i], times[i+1]
		fa, fb := values[i], values[i+1]
		if fa == 0 && !inside {
			inside = true
			start = a
		}
		if fa*fb < 0 || fb == 0 {
			root := eclipseCrossing(req, a, b)
			if inside {
				if root > start {
					out = append(out, EclipseInterval{StartTimeS: start, EndTimeS: root, DurationS: root - start})
				}
				inside = false
			} else {
				inside = true
				start = root
			}
		}
	}
	if inside {
		end := times[len(times)-1]
		if end > start {
			out = append(out, EclipseInterval{StartTimeS: start, EndTimeS: end, DurationS: end - start})
		}
	}
	return out
}

func visibleStationsAt(req Request, t float64) []string {
	out := []string{}
	for _, station := range req.Stations {
		if observe(req, station, t).ElevationDeg-station.MinElevationDeg >= 0 {
			out = append(out, station.ID)
		}
	}
	return out
}

func terminatorEvents(req Request) []TerminatorEvent {
	times := gridTimes(req)
	values := make([]float64, len(times))
	for i, t := range times {
		values[i] = shadowMargin(req, t)
	}
	inside := values[0] < 0
	out := []TerminatorEvent{}
	for i := 0; i < len(times)-1; i++ {
		a, b := times[i], times[i+1]
		fa, fb := values[i], values[i+1]
		if fa == 0 && !inside {
			inside = true
		}
		if fa*fb < 0 || fb == 0 {
			root := eclipseCrossing(req, a, b)
			kind := "ingress"
			if inside {
				kind = "egress"
				inside = false
			} else {
				inside = true
			}
			out = append(out, TerminatorEvent{
				TimeS:           root,
				Kind:            kind,
				ShadowMargin:    shadowMargin(req, root),
				VisibleStations: visibleStationsAt(req, root),
			})
		}
	}
	return out
}

func eclipseCrossing(req Request, a, b float64) float64 {
	fa := shadowMargin(req, a)
	for i := 0; i < rootIterations(req); i++ {
		mid := (a + b) / 2
		fm := shadowMargin(req, mid)
		if fa*fm <= 0 {
			b = mid
		} else {
			a = mid
			fa = fm
		}
	}
	return (a + b) / 2
}

func propagate(req Request, t float64) (vec3, vec3) {
	el := req.Elements
	a := el.SemiMajorAxisM
	e := el.Eccentricity
	n := math.Sqrt(req.MuM3S2 / (a * a * a))
	m := rad(el.MeanAnomalyDeg) + n*(t-req.StartTimeS)
	E := m
	for i := 0; i < 12; i++ {
		E -= (E - e*math.Sin(E) - m) / (1 - e*math.Cos(E))
	}
	den := 1 - e*math.Cos(E)
	root := math.Sqrt(1 - e*e)
	rp := vec3{a * (math.Cos(E) - e), a * root * math.Sin(E), 0}
	vp := vec3{-a * n * math.Sin(E) / den, a * n * root * math.Cos(E) / den, 0}
	inc := rad(el.InclinationDeg)
	raan := rad(el.RaanDeg)
	argp := rad(el.ArgPerigeeDeg)
	return rz(raan, rx(inc, rz(argp, rp))), rz(raan, rx(inc, rz(argp, vp)))
}

func dot(a, b vec3) float64 { return a.x*b.x + a.y*b.y + a.z*b.z }
func norm(a vec3) float64   { return math.Sqrt(dot(a, a)) }
func sub(a, b vec3) vec3    { return vec3{a.x - b.x, a.y - b.y, a.z - b.z} }
func rad(v float64) float64 { return v * math.Pi / 180 }
func deg(v float64) float64 { return v * 180 / math.Pi }

func rz(theta float64, v vec3) vec3 {
	c := math.Cos(theta)
	s := math.Sin(theta)
	return vec3{c*v.x - s*v.y, s*v.x + c*v.y, v.z}
}

func rx(theta float64, v vec3) vec3 {
	c := math.Cos(theta)
	s := math.Sin(theta)
	return vec3{v.x, c*v.y - s*v.z, s*v.y + c*v.z}
}
GO
make clean && make build
