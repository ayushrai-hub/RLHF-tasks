#!/usr/bin/env bash
set -euo pipefail

cd /app

cat > /app/engine/reconcile/reconcile.go <<'GOEOF'
package reconcile

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"os/exec"
	"sort"
	"strconv"
	"strings"

	"edgedrift/engine/policy"
)

type Event struct {
	Seq                int       `json:"seq"`
	EventID            string    `json:"event_id"`
	Kind               string    `json:"kind"`
	RegionID           string    `json:"region_id"`
	SampleID           string    `json:"sample_id"`
	DeviceID           string    `json:"device_id"`
	Firmware           string    `json:"firmware"`
	Version            string    `json:"version"`
	CalibrationVersion string    `json:"calibration_version"`
	WeightsHex         string    `json:"weights_hex"`
	WeightsDigest      string    `json:"weights_digest"`
	RawFeatures        []float64 `json:"raw_features"`
	Scale              float64   `json:"scale"`
	ZeroPoint          int       `json:"zero_point"`
	Temperature        float64   `json:"temperature"`
	Logits             []float64 `json:"logits"`
}

type Scenario struct {
	ScenarioID       string                 `json:"scenario_id"`
	FeatureScaleMode string                 `json:"feature_scale_mode"`
	CalibrationGate  *bool                  `json:"calibration_gate"`
	PolicyOverrides  map[string]interface{} `json:"policy_overrides"`
	Events           []Event                `json:"events"`
}

type SampleOut struct {
	Dequantized        []float64 `json:"dequantized"`
	DeviceID           string    `json:"device_id"`
	NormalizedFeatures []float64 `json:"normalized_features"`
	PredictedClass     int       `json:"predicted_class"`
	Probabilities      []float64 `json:"probabilities"`
	Quantized          []int     `json:"quantized"`
	SampleID           string    `json:"sample_id"`
}

type RegionOut struct {
	Firmware string      `json:"firmware"`
	RegionID string      `json:"region_id"`
	Samples  []SampleOut `json:"samples"`
}

type DriftFlag struct {
	Detail   string `json:"detail"`
	EventSeq int    `json:"event_seq"`
	FlagID   string `json:"flag_id"`
	Kind     string `json:"kind"`
	RegionID string `json:"region_id"`
	SampleID string `json:"sample_id"`
}

type ScenarioOut struct {
	ConsistencyHash        string      `json:"consistency_hash"`
	DriftFlags             []DriftFlag `json:"drift_flags"`
	DuplicateEventsSkipped int         `json:"duplicate_events_skipped"`
	ModelVersion           string      `json:"model_version"`
	Regions                []RegionOut `json:"regions"`
	ScenarioID             string      `json:"scenario_id"`
	Status                 string      `json:"status"`
}

type Report struct {
	Scenarios []ScenarioOut `json:"scenarios"`
}

type sampleState struct {
	deviceID           string
	normalizedFeatures []float64
	quantized          []int
	dequantized        []float64
	probabilities      []float64
	predictedClass     int
	hasQuant           bool
	hasInference       bool
}

type welford struct {
	n    int
	mean float64
	m2   float64
}

func LoadScenario(path string) (Scenario, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Scenario{}, err
	}
	var sc Scenario
	if err := json.Unmarshal(data, &sc); err != nil {
		return Scenario{}, err
	}
	return sc, nil
}

func flagID(scenarioID, regionID, sampleID string, seq int) string {
	if regionID == "" {
		regionID = "_"
	}
	if sampleID == "" {
		sampleID = "_"
	}
	return scenarioID + "::" + regionID + "::" + sampleID + "::" + formatSeq(seq)
}

func formatSeq(seq int) string {
	if seq < 0 {
		seq = 0
	}
	out := []byte("0000")
	n := seq
	for i := 3; i >= 0; i-- {
		out[i] = byte('0' + n%10)
		n /= 10
	}
	return string(out)
}

func appendFlag(flags *[]DriftFlag, scenarioID, regionID, sampleID, kind, detail string, seq int) {
	*flags = append(*flags, DriftFlag{
		FlagID:   flagID(scenarioID, regionID, sampleID, seq),
		RegionID: regionID,
		SampleID: sampleID,
		Kind:     kind,
		EventSeq: seq,
		Detail:   detail,
	})
}

func (w *welford) add(x float64) {
	w.n++
	delta := x - w.mean
	w.mean += delta / float64(w.n)
	w.m2 += delta * (x - w.mean)
}

func (w *welford) std() float64 {
	if w.n < 2 {
		return 0
	}
	return math.Sqrt(w.m2 / float64(w.n))
}

func normalizeValue(x float64, w *welford) float64 {
	if w.n == 0 {
		return x
	}
	std := w.std()
	if std < 1e-6 {
		std = 1e-6
	}
	return (x - w.mean) / std
}

func quantizeVal(x, scale float64, zp int) int {
	q := int(math.Round(x/scale)) + zp
	if q < -128 {
		return -128
	}
	if q > 127 {
		return 127
	}
	return q
}

func dequantVal(q int, scale float64, zp int) float64 {
	return (float64(q) - float64(zp)) * scale
}

func sha256Hex(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func runCalibrate(temp float64, logits []float64) ([]float64, error) {
	args := []string{"/app/assets/calibrate.js", strconv.FormatFloat(temp, 'f', -1, 64)}
	for _, l := range logits {
		args = append(args, strconv.FormatFloat(l, 'f', -1, 64))
	}
	out, err := exec.Command("node", args...).Output()
	if err != nil {
		return nil, err
	}
	var probs []float64
	if err := json.Unmarshal(out, &probs); err != nil {
		return nil, err
	}
	return probs, nil
}

func argmax(probs []float64) int {
	best := 0
	for i, p := range probs {
		if p > probs[best] {
			best = i
		}
	}
	return best
}

func l2Distance(a, b []float64) float64 {
	n := len(a)
	if len(b) < n {
		n = len(b)
	}
	var sum float64
	for i := 0; i < n; i++ {
		d := a[i] - b[i]
		sum += d * d
	}
	return math.Sqrt(sum)
}

func consistencyHash(entries []map[string]interface{}) string {
	raw, _ := json.Marshal(entries)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func Analyze(sc Scenario) ScenarioOut {
	scaleMode := sc.FeatureScaleMode
	if scaleMode == "" {
		scaleMode = "global"
	}
	calGate := true
	if sc.CalibrationGate != nil {
		calGate = *sc.CalibrationGate
	}
	scaleMode, calGate = policy.Resolve(scaleMode, calGate, sc.PolicyOverrides)

	modelVersion := ""
	calibVersion := ""
	modelActive := false

	regions := make(map[string]string)
	regionSamples := make(map[string]map[string]*sampleState)
	calibration := make(map[string]struct {
		version string
		temp    float64
	})

	regionWelford := make(map[string]map[int]*welford)
	deviceWelford := make(map[string]map[int]*welford)
	lockedKeys := make(map[string]struct{})

	flags := make([]DriftFlag, 0)
	dupSkipped := 0
	seenEvent := make(map[string]struct{})
	maxSeq := 0

	events := append([]Event(nil), sc.Events...)
	sort.Slice(events, func(i, j int) bool {
		if events[i].Seq != events[j].Seq {
			return events[i].Seq < events[j].Seq
		}
		if events[i].RegionID != events[j].RegionID {
			return events[i].RegionID < events[j].RegionID
		}
		return events[i].SampleID < events[j].SampleID
	})

	getSample := func(regionID, sampleID string) *sampleState {
		if regionSamples[regionID] == nil {
			regionSamples[regionID] = make(map[string]*sampleState)
		}
		st := regionSamples[regionID][sampleID]
		if st == nil {
			st = &sampleState{}
			regionSamples[regionID][sampleID] = st
		}
		return st
	}

	for _, ev := range events {
		seq := ev.Seq
		if seq > maxSeq {
			maxSeq = seq
		}
		if ev.EventID != "" {
			if _, dup := seenEvent[ev.EventID]; dup {
				dupSkipped++
				continue
			}
			seenEvent[ev.EventID] = struct{}{}
		}

		switch ev.Kind {
		case "REGISTER_MODEL":
			digest := sha256Hex(ev.WeightsHex)
			if digest != ev.WeightsDigest {
				appendFlag(&flags, sc.ScenarioID, "", "", "METADATA_CORRUPT", ev.WeightsDigest, seq)
			}
			modelVersion = ev.Version
			calibVersion = ev.CalibrationVersion
			modelActive = true
		case "REVOKE_MODEL":
			modelActive = false
			modelVersion = ""
		case "REGISTER_REGION":
			regions[ev.RegionID] = ev.Firmware
		case "LOCK_SAMPLE":
			key := ev.RegionID + "::" + ev.SampleID
			if _, exists := lockedKeys[key]; exists {
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "DUPLICATE_SAMPLE", ev.SampleID, seq)
				continue
			}
			if _, ok := regions[ev.RegionID]; !ok {
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "UNKNOWN_REGION", ev.Kind, seq)
				continue
			}
			st := getSample(ev.RegionID, ev.SampleID)
			st.deviceID = ev.DeviceID
			norm := make([]float64, len(ev.RawFeatures))
			for i, x := range ev.RawFeatures {
				var w *welford
				if scaleMode == "per_device" {
					dkey := ev.RegionID + "::" + ev.DeviceID
					if deviceWelford[dkey] == nil {
						deviceWelford[dkey] = make(map[int]*welford)
					}
					if deviceWelford[dkey][i] == nil {
						deviceWelford[dkey][i] = &welford{}
					}
					w = deviceWelford[dkey][i]
				} else {
					if regionWelford[ev.RegionID] == nil {
						regionWelford[ev.RegionID] = make(map[int]*welford)
					}
					if regionWelford[ev.RegionID][i] == nil {
						regionWelford[ev.RegionID][i] = &welford{}
					}
					w = regionWelford[ev.RegionID][i]
				}
				norm[i] = normalizeValue(x, w)
			}
			st.normalizedFeatures = norm
			lockedKeys[key] = struct{}{}
			for i, x := range ev.RawFeatures {
				if scaleMode == "per_device" {
					dkey := ev.RegionID + "::" + ev.DeviceID
					if deviceWelford[dkey] == nil {
						deviceWelford[dkey] = make(map[int]*welford)
					}
					if deviceWelford[dkey][i] == nil {
						deviceWelford[dkey][i] = &welford{}
					}
					deviceWelford[dkey][i].add(x)
				} else {
					if regionWelford[ev.RegionID] == nil {
						regionWelford[ev.RegionID] = make(map[int]*welford)
					}
					if regionWelford[ev.RegionID][i] == nil {
						regionWelford[ev.RegionID][i] = &welford{}
					}
					regionWelford[ev.RegionID][i].add(x)
				}
			}
		case "QUANTIZE_SAMPLE":
			if _, ok := regions[ev.RegionID]; !ok {
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "UNKNOWN_REGION", ev.Kind, seq)
				continue
			}
			st := getSample(ev.RegionID, ev.SampleID)
			if len(st.normalizedFeatures) == 0 {
				continue
			}
			qvals := make([]int, len(st.normalizedFeatures))
			dvals := make([]float64, len(st.normalizedFeatures))
			for i, x := range st.normalizedFeatures {
				q := quantizeVal(x, ev.Scale, ev.ZeroPoint)
				if math.Abs(x/ev.Scale) > 200 {
					appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "OUT_OF_RANGE_QUANT", strconv.Itoa(q), seq)
				}
				qvals[i] = q
				d := dequantVal(q, ev.Scale, ev.ZeroPoint)
				dvals[i] = d
				if math.Abs(d-x) > 1e-4+math.Abs(x)*1e-3 {
					appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "QUANT_MISMATCH", strconv.Itoa(i), seq)
				}
			}
			st.quantized = qvals
			st.dequantized = dvals
			st.hasQuant = true
		case "SET_CALIBRATION":
			if calGate && modelActive && ev.Version != calibVersion {
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, "", "STALE_CALIBRATION", ev.Version, seq)
			}
			calibration[ev.RegionID] = struct {
				version string
				temp    float64
			}{version: ev.Version, temp: ev.Temperature}
		case "RUN_INFERENCE":
			if !modelActive {
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "MISSING_MODEL", ev.Kind, seq)
				continue
			}
			if _, ok := regions[ev.RegionID]; !ok {
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "UNKNOWN_REGION", ev.Kind, seq)
				continue
			}
			cal, ok := calibration[ev.RegionID]
			if !ok {
				cal = struct {
					version string
					temp    float64
				}{version: calibVersion, temp: 1.0}
			}
			temp := cal.temp
			if temp <= 0 {
				temp = 1.0
			}
			probs, err := runCalibrate(temp, ev.Logits)
			if err != nil {
				continue
			}
			st := getSample(ev.RegionID, ev.SampleID)
			st.probabilities = probs
			maxP := probs[0]
			for _, p := range probs[1:] {
				if p > maxP {
					maxP = p
				}
			}
			ties := make([]int, 0)
			for i, p := range probs {
				if math.Abs(p-maxP) <= 1e-12 {
					ties = append(ties, i)
				}
			}
			sort.Ints(ties)
			st.predictedClass = ties[0]
			if len(ties) > 1 {
				parts := make([]string, len(ties))
				for i, t := range ties {
					parts[i] = strconv.Itoa(t)
				}
				appendFlag(&flags, sc.ScenarioID, ev.RegionID, ev.SampleID, "CLASS_COLLISION", strings.Join(parts, ","), seq)
			}
			st.hasInference = true
		}
	}

	auditSeq := maxSeq + 1
	sampleRegions := make(map[string]map[string]*sampleState)
	for rid, samples := range regionSamples {
		for sid, st := range samples {
			if sampleRegions[sid] == nil {
				sampleRegions[sid] = make(map[string]*sampleState)
			}
			sampleRegions[sid][rid] = st
		}
	}
	for sid, byRegion := range sampleRegions {
		if len(byRegion) < 2 {
			continue
		}
		rids := make([]string, 0, len(byRegion))
		for rid := range byRegion {
			rids = append(rids, rid)
		}
		sort.Strings(rids)
		var canonicalRid string
		var canonicalClass int
		var canonicalSt *sampleState
		for _, rid := range rids {
			st := byRegion[rid]
			if !st.hasInference {
				continue
			}
			if canonicalRid == "" || rid < canonicalRid {
				canonicalRid = rid
				canonicalClass = st.predictedClass
				canonicalSt = st
			}
		}
		if canonicalRid == "" {
			continue
		}
		for _, rid := range rids {
			if rid == canonicalRid {
				continue
			}
			other := byRegion[rid]
			if other.hasInference && other.predictedClass != canonicalClass {
				detail := strconv.Itoa(canonicalClass) + "," + rid
				appendFlag(&flags, sc.ScenarioID, rid, sid, "REGION_DIVERGENCE", detail, auditSeq)
			}
			if len(canonicalSt.normalizedFeatures) > 0 && len(other.normalizedFeatures) > 0 {
				if l2Distance(canonicalSt.normalizedFeatures, other.normalizedFeatures) > 0.5 {
					appendFlag(&flags, sc.ScenarioID, rid, sid, "FEATURE_SCALE_DRIFT", canonicalRid, auditSeq)
				}
			}
		}
	}

	hashEntries := make([]map[string]interface{}, 0)
	for sid, byRegion := range sampleRegions {
		for rid, st := range byRegion {
			if !st.hasInference {
				continue
			}
			hashEntries = append(hashEntries, map[string]interface{}{
				"sample_id":       sid,
				"region_id":       rid,
				"predicted_class": st.predictedClass,
			})
		}
	}
	sort.Slice(hashEntries, func(i, j int) bool {
		if hashEntries[i]["sample_id"] != hashEntries[j]["sample_id"] {
			return hashEntries[i]["sample_id"].(string) < hashEntries[j]["sample_id"].(string)
		}
		return hashEntries[i]["region_id"].(string) < hashEntries[j]["region_id"].(string)
	})

	outRegions := make([]RegionOut, 0, len(regions))
	regionIDs := make([]string, 0, len(regions))
	for id := range regions {
		regionIDs = append(regionIDs, id)
	}
	sort.Strings(regionIDs)
	for _, rid := range regionIDs {
		samples := make([]SampleOut, 0)
		if rs, ok := regionSamples[rid]; ok {
			sids := make([]string, 0, len(rs))
			for sid := range rs {
				sids = append(sids, sid)
			}
			sort.Strings(sids)
			for _, sid := range sids {
				st := rs[sid]
				if st.deviceID == "" && len(st.normalizedFeatures) == 0 && !st.hasInference {
					continue
				}
				norm := st.normalizedFeatures
				if norm == nil {
					norm = []float64{}
				}
				quant := st.quantized
				if quant == nil {
					quant = []int{}
				}
				deq := st.dequantized
				if deq == nil {
					deq = []float64{}
				}
				probs := st.probabilities
				if probs == nil {
					probs = []float64{}
				}
				normOut := make([]float64, len(norm))
				copy(normOut, norm)
				quantOut := make([]int, len(quant))
				copy(quantOut, quant)
				deqOut := make([]float64, len(deq))
				copy(deqOut, deq)
				probOut := make([]float64, len(probs))
				copy(probOut, probs)
				samples = append(samples, SampleOut{
					SampleID:           sid,
					DeviceID:           st.deviceID,
					NormalizedFeatures: normOut,
					Quantized:          quantOut,
					Dequantized:        deqOut,
					Probabilities:      probOut,
					PredictedClass:     st.predictedClass,
				})
			}
		}
		outRegions = append(outRegions, RegionOut{
			RegionID: rid,
			Firmware: regions[rid],
			Samples:  samples,
		})
	}

	sort.Slice(flags, func(i, j int) bool {
		return flags[i].FlagID < flags[j].FlagID
	})

	status := "CONSISTENT"
	if len(flags) > 0 {
		status = "DRIFT_DETECTED"
	}

	return ScenarioOut{
		ScenarioID:             sc.ScenarioID,
		Status:                 status,
		DuplicateEventsSkipped: dupSkipped,
		ModelVersion:           modelVersion,
		Regions:                outRegions,
		DriftFlags:             flags,
		ConsistencyHash:        consistencyHash(hashEntries),
	}
}
GOEOF

make clean || true
make build
make audit
