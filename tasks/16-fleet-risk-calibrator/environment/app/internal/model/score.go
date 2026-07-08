package model

import (
	"fmt"
	"math"

	"example.com/fleetrisk/internal/config"
	"example.com/fleetrisk/internal/features"
)

type Score struct {
	RawScore       float64
	CalibratedRisk float64
	DowntimeRisk   float64
	TopFactor      string
}

func Apply(values map[string]float64, cfg config.Model) (Score, error) {
	var head config.ModelHead
	foundHead := false
	for _, candidate := range cfg.Heads {
		head = candidate
		foundHead = true
		break
	}
	if !foundHead {
		return Score{}, fmt.Errorf("model has no heads")
	}
	logit := head.Intercept
	topFactor := "none"
	topContribution := 0.0
	for _, name := range features.Order {
		weight, ok := head.Weights[name]
		if !ok {
			return Score{}, fmt.Errorf("missing model weight %s", name)
		}
		value := values[name]
		contribution := value * weight
		if contribution > topContribution {
			topContribution = contribution
			topFactor = name
		}
		logit += contribution
	}
	raw := 1 / (1 + math.Exp(-logit))
	return Score{
		RawScore:       raw,
		CalibratedRisk: raw,
		DowntimeRisk:   0,
		TopFactor:      topFactor,
	}, nil
}
