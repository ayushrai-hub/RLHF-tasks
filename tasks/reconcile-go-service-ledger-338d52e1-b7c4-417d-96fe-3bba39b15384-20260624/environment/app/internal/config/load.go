package config

import (
	"encoding/json"
	"os"
)

func Load(path string) (RuleSet, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return RuleSet{}, err
	}
	var rules RuleSet
	if err := json.Unmarshal(data, &rules); err != nil {
		return RuleSet{}, err
	}
	return rules, nil
}

func LoadAndNormalize(path string) (NormalizedConfig, error) {
	rules, err := Load(path)
	if err != nil {
		return NormalizedConfig{}, err
	}
	return Normalize(rules)
}

func WriteNormalized(path string, cfg NormalizedConfig) error {
	data, err := json.MarshalIndent(Export(cfg), "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0644)
}
