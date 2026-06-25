package config

import (
	"encoding/json"
	"os"

	"github.com/terminal-bench/splitter/models"
)

func LoadConfig(path string) (*models.SplitConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg models.SplitConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func LoadRequests(path string) ([]models.Request, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var reqs []models.Request
	if err := json.Unmarshal(data, &reqs); err != nil {
		return nil, err
	}
	return reqs, nil
}
