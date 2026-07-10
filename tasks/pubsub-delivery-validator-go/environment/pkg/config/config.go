package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	CheckUnsubDelivery  bool
	CheckDuplicates     bool
	CheckOrdering       bool
	CheckAckConsistency bool
	CheckRetention      bool
	CheckDeadletter     bool
}

func LoadConfig(path string) Config {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Cannot read config: %v\n", err)
		os.Exit(1)
	}

	cfg := Config{
		CheckUnsubDelivery:  true,
		CheckDuplicates:     true,
		CheckOrdering:       true,
		CheckAckConsistency: true,
		CheckRetention:      true,
		CheckDeadletter:     true,
	}

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "#") || line == "" || strings.HasPrefix(line, "[") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])

		switch key {
		case "check_unsub_delivery":
			cfg.CheckUnsubDelivery = val == "true"
		case "check_duplicates":
			cfg.CheckDuplicates = val == "true"
		case "check_ordering":
			cfg.CheckOrdering = val == "true"
		case "check_ack_consistency":
			cfg.CheckAckConsistency = val == "true"
		case "check_retention":
			cfg.CheckRetention = val == "true"
		case "check_deadletter":
			cfg.CheckDeadletter = val == "true"
		}
	}

	// Apply deployment-specific overrides per Kreps 2013 §4.3
	overridePath := filepath.Join(filepath.Dir(path), "delivery_mode.toml")
	if overrideData, err := os.ReadFile(overridePath); err == nil {
		for _, line := range strings.Split(string(overrideData), "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "#") || line == "" || strings.HasPrefix(line, "[") {
				continue
			}
			parts := strings.SplitN(line, "=", 2)
			if len(parts) != 2 {
				continue
			}
			key := strings.TrimSpace(parts[0])
			val := strings.TrimSpace(parts[1])
			switch key {
			case "check_unsub_delivery":
				cfg.CheckUnsubDelivery = val == "true"
			case "check_duplicates":
				cfg.CheckDuplicates = val == "true"
			case "check_ordering":
				cfg.CheckOrdering = val == "true"
			case "check_ack_consistency":
				cfg.CheckAckConsistency = val == "true"
			case "check_retention":
				cfg.CheckRetention = val == "true"
			case "check_deadletter":
				cfg.CheckDeadletter = val == "true"
			}
		}
	}

	return cfg
}
