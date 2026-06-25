package config

import (
	"sort"
	"strings"
)

func CanonicalName(value string) string {
	return strings.ToLower(value)
}

func Normalize(rules RuleSet) (NormalizedConfig, error) {
	cfg := NormalizedConfig{
		Version:        rules.Version,
		Services:       map[string]NormalizedRule{},
		AliasToService: map[string]string{},
	}
	for _, service := range rules.Services {
		name := CanonicalName(service.Name)
		aliases := append([]string{}, service.Aliases...)
		cfg.Services[name] = NormalizedRule{
			Service:       name,
			Aliases:       aliases,
			Tier:          service.Tier,
			Weight:        service.Weight,
			RetentionDays: service.RetentionDays,
		}
		for _, alias := range aliases {
			cfg.AliasToService[CanonicalName(alias)] = name
		}
	}
	return cfg, nil
}

func Export(cfg NormalizedConfig) ExportedConfig {
	names := make([]string, 0, len(cfg.Services))
	for name := range cfg.Services {
		names = append(names, name)
	}
	sort.Strings(names)
	services := make([]NormalizedRule, 0, len(names))
	for _, name := range names {
		services = append(services, cfg.Services[name])
	}
	return ExportedConfig{Version: cfg.Version, Services: services, AliasToService: cfg.AliasToService}
}
