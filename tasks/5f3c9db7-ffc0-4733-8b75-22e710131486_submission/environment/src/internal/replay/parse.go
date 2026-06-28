package replay

import (
	"encoding/json"
	"os"
	"logrecover/pkg/api"
	"logrecover/internal/segment"
)

func LoadPack(path string) (api.Pack, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return api.Pack{}, err
	}
	var p api.Pack
	if err := json.Unmarshal(b, &p); err != nil {
		return api.Pack{}, err
	}
	for i := range p.Scenarios {
		sc := &p.Scenarios[i]
		for k, frames := range sc.Frames {
			if err := segment.NormalizeFrames(frames); err != nil {
				return api.Pack{}, err
			}
			sc.Frames[k] = frames
		}
	}
	return p, nil
}

func LoadScenarioFile(path string) (api.Scenario, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return api.Scenario{}, err
	}
	var sc api.Scenario
	if err := json.Unmarshal(b, &sc); err != nil {
		return api.Scenario{}, err
	}
	for k, frames := range sc.Frames {
		if err := segment.NormalizeFrames(frames); err != nil {
			return api.Scenario{}, err
		}
		sc.Frames[k] = frames
	}
	return sc, nil
}
