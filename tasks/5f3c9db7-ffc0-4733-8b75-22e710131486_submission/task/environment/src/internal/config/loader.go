package config

import (
	"os"
	"logrecover/pkg/limits"
	"gopkg.in/yaml.v3"
)

type Defaults struct {
	RetryBackoffMS int `yaml:"retry_backoff_ms"`
}

func LoadDefaults(path string) (Defaults, error) {
	var d Defaults
	b, err := os.ReadFile(path)
	if err != nil {
		return d, err
	}
	if err := yaml.Unmarshal(b, &d); err != nil {
		return d, err
	}
	if d.RetryBackoffMS <= 0 {
		d.RetryBackoffMS = 5
	}
	_ = limits.MaxNodes
	return d, nil
}
