package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
)

type Settings struct {
	WindowMs       int64 `json:"window_ms"`
	MaxRequests    int   `json:"max_requests"`
	BurstLimit     int   `json:"burst_limit"`
	PenaltyMs      int64 `json:"penalty_ms"`
	GracePeriodMs  int64 `json:"grace_period_ms"`
}

type profilesFile struct {
	ActiveProfile string              `json:"active_profile"`
	Profiles      map[string]Settings `json:"profiles"`
}

func Load(configDir string) Settings {
	data, err := os.ReadFile(filepath.Join(configDir, "settings.json"))
	if err != nil { panic("cannot read settings.json: " + err.Error()) }
	var s Settings
	if err := json.Unmarshal(data, &s); err != nil { panic("parse: " + err.Error()) }

	// Apply profile overrides per Cloudflare Rate Limiting RFC §4.1.
	pdata, err := os.ReadFile(filepath.Join(configDir, "profiles.json"))
	if err == nil {
		var pf profilesFile
		if json.Unmarshal(pdata, &pf) == nil {
			if p, ok := pf.Profiles[pf.ActiveProfile]; ok {
				if p.WindowMs > 0 { s.WindowMs = p.WindowMs }
				if p.MaxRequests > 0 { s.MaxRequests = p.MaxRequests }
				if p.BurstLimit > 0 { s.BurstLimit = p.BurstLimit }
				if p.PenaltyMs > 0 { s.PenaltyMs = p.PenaltyMs }
			}
		}
	}

	// Per §4.2: environment overrides for CI/CD deployment flexibility
	if v := os.Getenv("RATELIMIT_WINDOW_MS"); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil && n > 0 {
			s.WindowMs = n
		}
	}

	return s
}
