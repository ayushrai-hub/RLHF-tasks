package reconcile

import (
	"encoding/json"
	"math"
	"os"
	"sort"

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
	SampleID           string    `json:"sample_id"`
	DeviceID           string    `json:"device_id"`
	NormalizedFeatures []float64 `json:"normalized_features"`
	Quantized          []int     `json:"quantized"`
	Dequantized        []float64 `json:"dequantized"`
	Probabilities      []float64 `json:"probabilities"`
	PredictedClass     int       `json:"predicted_class"`
}

type RegionOut struct {
	RegionID string      `json:"region_id"`
	Firmware string      `json:"firmware"`
	Samples  []SampleOut `json:"samples"`
}

type DriftFlag struct {
	FlagID   string `json:"flag_id"`
	RegionID string `json:"region_id"`
	SampleID string `json:"sample_id"`
	Kind     string `json:"kind"`
	EventSeq int    `json:"event_seq"`
	Detail   string `json:"detail"`
}

type ScenarioOut struct {
	ScenarioID             string      `json:"scenario_id"`
	Status                 string      `json:"status"`
	DuplicateEventsSkipped int         `json:"duplicate_events_skipped"`
	ModelVersion           string      `json:"model_version"`
	Regions                []RegionOut `json:"regions"`
	DriftFlags             []DriftFlag `json:"drift_flags"`
	ConsistencyHash        string      `json:"consistency_hash"`
}

type Report struct {
	Scenarios []ScenarioOut `json:"scenarios"`
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

// Analyze replays fixture events into a scenario report. The starter below is
// intentionally incomplete: see /app/spec/rule_catalog.json and output_schema.json.
// Replay must sort by seq then region_id then sample_id; sorting by seq alone is wrong.
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
	_ = scaleMode
	_ = calGate

	modelVersion := ""
	regions := make(map[string]string)
	samplesByRegion := make(map[string]map[string]*SampleOut)

	events := append([]Event(nil), sc.Events...)
	sort.Slice(events, func(i, j int) bool {
		return events[i].Seq < events[j].Seq
	})

	for _, ev := range events {
		switch ev.Kind {
		case "REGISTER_MODEL":
			modelVersion = ev.Version
		case "REGISTER_REGION":
			regions[ev.RegionID] = ev.Firmware
		case "LOCK_SAMPLE":
			if samplesByRegion[ev.RegionID] == nil {
				samplesByRegion[ev.RegionID] = make(map[string]*SampleOut)
			}
			samplesByRegion[ev.RegionID][ev.SampleID] = &SampleOut{
				SampleID:           ev.SampleID,
				DeviceID:           ev.DeviceID,
				NormalizedFeatures: append([]float64(nil), ev.RawFeatures...),
			}
		case "SET_CALIBRATION":
			_ = ev
		case "RUN_INFERENCE":
			if samplesByRegion[ev.RegionID] == nil {
				continue
			}
			st := samplesByRegion[ev.RegionID][ev.SampleID]
			if st == nil {
				// Inference without LOCK_SAMPLE has no sample row in this starter path.
				continue
			}
			best := 0
			for i, l := range ev.Logits {
				if l > ev.Logits[best] {
					best = i
				}
			}
			st.PredictedClass = best
			probs := make([]float64, len(ev.Logits))
			var sum float64
			for _, l := range ev.Logits {
				sum += math.Exp(l)
			}
			for i, l := range ev.Logits {
				probs[i] = math.Exp(l) / sum
			}
			st.Probabilities = probs
		}
	}

	outRegions := make([]RegionOut, 0, len(regions))
	for rid, firmware := range regions {
		var samples []SampleOut
		for _, st := range samplesByRegion[rid] {
			samples = append(samples, *st)
		}
		outRegions = append(outRegions, RegionOut{
			RegionID: rid,
			Firmware: firmware,
			Samples:  samples,
		})
	}

	return ScenarioOut{
		ScenarioID:             sc.ScenarioID,
		Status:                 "ok",
		DuplicateEventsSkipped: 0,
		ModelVersion:           modelVersion,
		Regions:                outRegions,
		DriftFlags:             []DriftFlag{},
		ConsistencyHash:        "",
	}
}
