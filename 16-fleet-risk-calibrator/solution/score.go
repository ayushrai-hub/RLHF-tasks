package model

import (
	"fmt"
	"math"
	"sort"

	"example.com/fleetrisk/internal/config"
)

type Score struct {
	RawScore       float64
	CalibratedRisk float64
	DowntimeRisk   float64
	TopFactor      string
}

func Apply(values map[string]float64, cfg config.Model, assetType string) (Score, error) {
	blend, ok := cfg.BlendByAssetType[assetType]
	if !ok {
		return Score{}, fmt.Errorf("missing blend for asset type %s", assetType)
	}
	headNames := make([]string, 0, len(cfg.Heads))
	for name := range cfg.Heads {
		headNames = append(headNames, name)
	}
	sort.Strings(headNames)

	rawByHead := make(map[string]float64, len(cfg.Heads))
	calibratedByHead := make(map[string]float64, len(cfg.Heads))
	for _, headName := range headNames {
		head := cfg.Heads[headName]
		logit := head.Intercept
		for feature, weight := range head.Weights {
			value, ok := values[feature]
			if !ok {
				return Score{}, fmt.Errorf("missing feature %s", feature)
			}
			contribution := value * weight
			logit += contribution
		}
		raw := 1 / (1 + math.Exp(-logit))
		rawByHead[headName] = raw
		calibratedByHead[headName] = calibrate(raw, head.Calibration)
	}

	rawScore := 0.0
	baseCalibratedRisk := 0.0
	for headName, weight := range blend {
		rawScore += weight * rawByHead[headName]
		baseCalibratedRisk += weight * calibratedByHead[headName]
	}
	calibratedRisk := postCalibratedRisk(rawScore, baseCalibratedRisk, cfg, assetType)

	return Score{
		RawScore:       rawScore,
		CalibratedRisk: calibratedRisk,
		DowntimeRisk:   calibratedByHead["downtime"],
		TopFactor:      topIntegratedFactor(values, cfg, blend, headNames),
	}, nil
}

func calibrate(raw float64, knots []config.CalibrationKnot) float64 {
	if len(knots) == 0 {
		return raw
	}
	if raw <= knots[0].Raw {
		return knots[0].Calibrated
	}
	for i := 0; i < len(knots)-1; i++ {
		left := knots[i]
		right := knots[i+1]
		if raw <= right.Raw {
			span := right.Raw - left.Raw
			if span == 0 {
				return right.Calibrated
			}
			fraction := (raw - left.Raw) / span
			return left.Calibrated + fraction*(right.Calibrated-left.Calibrated)
		}
	}
	return knots[len(knots)-1].Calibrated
}

type isotonicBlock struct {
	left   float64
	right  float64
	weight float64
	mean   float64
}

func postCalibratedRisk(rawScore, baseRisk float64, cfg config.Model, assetType string) float64 {
	weight := cfg.PostCalibration.BlendWeight
	if weight <= 0 {
		return baseRisk
	}
	if weight > 1 {
		weight = 1
	}
	observations := cfg.PostCalibration.Groups[assetType]
	if len(observations) == 0 {
		return baseRisk
	}
	panelRisk, ok := isotonicPredict(rawScore, observations)
	if !ok {
		return baseRisk
	}
	return (1-weight)*baseRisk + weight*panelRisk
}

func isotonicPredict(rawScore float64, observations []config.CalibrationObservation) (float64, bool) {
	ordered := append([]config.CalibrationObservation(nil), observations...)
	sort.SliceStable(ordered, func(i, j int) bool {
		return ordered[i].Raw < ordered[j].Raw
	})
	blocks := make([]isotonicBlock, 0, len(ordered))
	for _, obs := range ordered {
		if obs.Weight <= 0 {
			continue
		}
		blocks = append(blocks, isotonicBlock{
			left:   obs.Raw,
			right:  obs.Raw,
			weight: obs.Weight,
			mean:   obs.Label,
		})
		for len(blocks) >= 2 {
			last := blocks[len(blocks)-1]
			prev := blocks[len(blocks)-2]
			if prev.mean <= last.mean+1e-15 {
				break
			}
			mergedWeight := prev.weight + last.weight
			merged := isotonicBlock{
				left:   prev.left,
				right:  last.right,
				weight: mergedWeight,
				mean:   (prev.mean*prev.weight + last.mean*last.weight) / mergedWeight,
			}
			blocks = blocks[:len(blocks)-2]
			blocks = append(blocks, merged)
		}
	}
	if len(blocks) == 0 {
		return 0, false
	}
	for _, block := range blocks {
		if rawScore <= block.right {
			return clamp01(block.mean), true
		}
	}
	return clamp01(blocks[len(blocks)-1].mean), true
}

func clamp01(value float64) float64 {
	if value < 0 {
		return 0
	}
	if value > 1 {
		return 1
	}
	return value
}

func topIntegratedFactor(values map[string]float64, cfg config.Model, blend map[string]float64, headNames []string) string {
	const steps = 32
	featureNames := make([]string, 0, len(values))
	for name := range values {
		featureNames = append(featureNames, name)
	}
	sort.Strings(featureNames)
	attribution := make(map[string]float64, len(featureNames))
	for step := 0; step < steps; step++ {
		alpha := (float64(step) + 0.5) / float64(steps)
		for _, headName := range headNames {
			head := cfg.Heads[headName]
			logit := head.Intercept
			for _, feature := range featureNames {
				logit += alpha * values[feature] * head.Weights[feature]
			}
			raw := 1 / (1 + math.Exp(-logit))
			common := blend[headName] * calibrationSlope(raw, head.Calibration) * raw * (1 - raw)
			for _, feature := range featureNames {
				attribution[feature] += values[feature] * common * head.Weights[feature] / float64(steps)
			}
		}
	}
	topFactor := "none"
	topAttribution := 0.0
	for _, feature := range featureNames {
		if attribution[feature] > topAttribution {
			topAttribution = attribution[feature]
			topFactor = feature
		}
	}
	return topFactor
}

func calibrationSlope(raw float64, knots []config.CalibrationKnot) float64 {
	if len(knots) < 2 {
		return 1
	}
	if raw < knots[0].Raw || raw > knots[len(knots)-1].Raw {
		return 0
	}
	for i := 0; i < len(knots)-1; i++ {
		left := knots[i]
		right := knots[i+1]
		if raw <= right.Raw {
			span := right.Raw - left.Raw
			if span == 0 {
				return 0
			}
			return (right.Calibrated - left.Calibrated) / span
		}
	}
	return 0
}
