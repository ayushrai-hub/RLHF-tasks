package config

// AnalysisConfig holds analysis-specific settings.
type AnalysisConfig struct {
	IncludeConditional bool `toml:"include_conditional"`
	MaxChainDepth      int  `toml:"max_chain_depth"`
}

// Config holds the full application configuration.
type Config struct {
	Analysis AnalysisConfig `toml:"analysis"`
}

// DefaultConfig returns the default configuration values.
func DefaultConfig() *Config {
	return &Config{
		Analysis: AnalysisConfig{
			IncludeConditional: true,
			MaxChainDepth:      0,
		},
	}
}
