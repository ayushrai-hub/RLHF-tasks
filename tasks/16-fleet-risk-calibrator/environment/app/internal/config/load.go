package config

import (
	"encoding/json"
	"fmt"
	"os"
)

func LoadModel(path string) (Model, error) {
	var model Model
	if err := loadJSON(path, &model); err != nil {
		return model, err
	}
	if model.ModelID == "" || len(model.Heads) == 0 || len(model.BlendByAssetType) == 0 || len(model.AssetTypes) == 0 {
		return model, fmt.Errorf("invalid model config %s", path)
	}
	return model, nil
}

func LoadPolicy(path string) (Policy, error) {
	var policy Policy
	if err := loadJSON(path, &policy); err != nil {
		return policy, err
	}
	if policy.PolicyID == "" || policy.ReportGeneratedAt == "" {
		return policy, fmt.Errorf("invalid policy config %s", path)
	}
	return policy, nil
}

func loadJSON(path string, target any) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read %s: %w", path, err)
	}
	if err := json.Unmarshal(data, target); err != nil {
		return fmt.Errorf("parse %s: %w", path, err)
	}
	return nil
}
