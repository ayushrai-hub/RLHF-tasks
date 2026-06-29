package config

import (
	"os"
	"strconv"
)

type HostConfig struct {
	ListenAddr   string
	StepSeconds  int
	StepWindow   int
	Digits       int
}

func Load() HostConfig {
	cfg := HostConfig{
		ListenAddr:  "127.0.0.1:9477",
		StepSeconds: 30,
		StepWindow:  1,
		Digits:      6,
	}
	if v := os.Getenv("M3_LISTEN"); v != "" {
		cfg.ListenAddr = v
	}
	if v := os.Getenv("M3_STEP_SECONDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			cfg.StepSeconds = n
		}
	}
	if v := os.Getenv("M3_STEP_WINDOW"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n >= 0 {
			cfg.StepWindow = n
		}
	}
	return cfg
}

func ClockEpoch() int64 {
	if v := os.Getenv("K9_CLOCK_EPOCH"); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil {
			return n
		}
	}
	return 0
}
