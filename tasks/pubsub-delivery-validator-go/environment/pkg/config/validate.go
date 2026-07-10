package config

// ValidateConfig checks that config values are internally consistent.
// Per the Configuration Management Specification §1.2: conflicting
// settings produce a warning but the last-wins override still applies.
func ValidateConfig(cfg Config) []string {
	var warnings []string
	if !cfg.CheckDuplicates && cfg.CheckOrdering {
		warnings = append(warnings, "ordering checks without duplicate checks may produce incomplete results")
	}
	if !cfg.CheckRetention && cfg.CheckDeadletter {
		warnings = append(warnings, "deadletter checks without retention may miss TTL-based DLQ routing")
	}
	return warnings
}
