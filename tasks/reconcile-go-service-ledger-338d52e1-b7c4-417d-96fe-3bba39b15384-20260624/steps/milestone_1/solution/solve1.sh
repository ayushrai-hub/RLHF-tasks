#!/bin/bash
set -euo pipefail

cd /app

cat > internal/config/normalize.go <<'GO'
package config

import (
	"fmt"
	"sort"
	"strings"
	"unicode"
)

func CanonicalName(value string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	var b strings.Builder
	lastDash := false
	for _, r := range value {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
			lastDash = false
			continue
		}
		if !lastDash && b.Len() > 0 {
			b.WriteByte('-')
			lastDash = true
		}
	}
	return strings.Trim(b.String(), "-")
}

func Normalize(rules RuleSet) (NormalizedConfig, error) {
	cfg := NormalizedConfig{
		Version:        rules.Version,
		Services:       map[string]NormalizedRule{},
		AliasToService: map[string]string{},
	}
	for _, service := range rules.Services {
		name := CanonicalName(service.Name)
		if name == "" {
			return NormalizedConfig{}, fmt.Errorf("service name is required")
		}
			if _, exists := cfg.Services[name]; exists {
				return NormalizedConfig{}, fmt.Errorf("duplicate service name %q", name)
			}
		if service.Weight <= 0 || service.Weight > 1 {
			return NormalizedConfig{}, fmt.Errorf("weight for %s must be in (0, 1]", name)
		}
		if service.RetentionDays < 1 || service.RetentionDays > 365 {
			return NormalizedConfig{}, fmt.Errorf("retention_days for %s must be in 1..365", name)
		}

		aliasSet := map[string]bool{name: true}
		for _, rawAlias := range service.Aliases {
			alias := CanonicalName(rawAlias)
			if alias == "" {
				return NormalizedConfig{}, fmt.Errorf("empty alias for %s", name)
			}
			aliasSet[alias] = true
		}
		aliases := make([]string, 0, len(aliasSet))
		for alias := range aliasSet {
			if owner, exists := cfg.AliasToService[alias]; exists && owner != name {
				return NormalizedConfig{}, fmt.Errorf("alias %q maps to both %s and %s", alias, owner, name)
			}
			cfg.AliasToService[alias] = name
			aliases = append(aliases, alias)
		}
		sort.Strings(aliases)
		cfg.Services[name] = NormalizedRule{
			Service:       name,
			Aliases:       aliases,
			Tier:          strings.TrimSpace(service.Tier),
			Weight:        service.Weight,
			RetentionDays: service.RetentionDays,
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
		rule := cfg.Services[name]
		rule.Aliases = append([]string{}, rule.Aliases...)
		sort.Strings(rule.Aliases)
		services = append(services, rule)
	}
	return ExportedConfig{
		Version:        cfg.Version,
		Services:       services,
		AliasToService: cfg.AliasToService,
	}
}
GO

go test ./...
