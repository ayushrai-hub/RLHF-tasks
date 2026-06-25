package config

type ServiceRule struct {
	Name          string   `json:"name"`
	Aliases       []string `json:"aliases"`
	Tier          string   `json:"tier"`
	Weight        float64  `json:"weight"`
	RetentionDays int      `json:"retention_days"`
}

type RuleSet struct {
	Version  int           `json:"version"`
	Services []ServiceRule `json:"services"`
}

type NormalizedRule struct {
	Service       string   `json:"service"`
	Aliases       []string `json:"aliases"`
	Tier          string   `json:"tier"`
	Weight        float64  `json:"weight"`
	RetentionDays int      `json:"retention_days"`
}

type NormalizedConfig struct {
	Version        int                       `json:"version"`
	Services       map[string]NormalizedRule `json:"-"`
	AliasToService map[string]string         `json:"alias_to_service"`
}

type ExportedConfig struct {
	Version        int               `json:"version"`
	Services       []NormalizedRule  `json:"services"`
	AliasToService map[string]string `json:"alias_to_service"`
}
