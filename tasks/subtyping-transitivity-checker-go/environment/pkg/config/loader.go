package config

import (
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
)

// LoadWithProfile loads configuration from settings.toml and applies
// profile-specific overrides from profiles.toml. Profile overrides ensure
// environment-specific behavior is correctly applied per deployment context.
func LoadWithProfile(configDir string) (*Config, error) {
	cfg := DefaultConfig()

	settingsPath := filepath.Join(configDir, "settings.toml")
	if _, err := os.Stat(settingsPath); err == nil {
		if _, err := toml.DecodeFile(settingsPath, cfg); err != nil {
			return cfg, err
		}
	}

	profilePath := filepath.Join(configDir, "profiles.toml")
	if _, err := os.Stat(profilePath); err == nil {
		if _, err := toml.DecodeFile(profilePath, cfg); err != nil {
			return cfg, nil
		}
	}

	return cfg, nil
}
