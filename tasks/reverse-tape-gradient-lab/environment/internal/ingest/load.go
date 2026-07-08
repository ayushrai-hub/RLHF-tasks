package ingest

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
)

var SetMap = map[string][]string{
	"s1":  {"shared_square", "chain_mul"},
	"s2":  {"broadcast_add", "matmul_vec"},
	"s3":  {"second_order_scalar", "reduce_axes"},
	"all": {"shared_square", "chain_mul", "broadcast_add", "matmul_vec", "second_order_scalar", "reduce_axes"},
}

func graphDir() string {
	if v := os.Getenv("GRAD_GRAPH_DIR"); v != "" {
		return v
	}
	return filepath.Join("/app/environment/data/graphs")
}

func configPath() string {
	if v := os.Getenv("GRAD_CONFIG"); v != "" {
		return v
	}
	return filepath.Join("/app/environment/data/config/grad.json")
}

func policyPath() string {
	if v := os.Getenv("GRAD_POLICY"); v != "" {
		return v
	}
	return filepath.Join("/app/environment/data/policy.toml")
}

func LoadConfig() (map[string]any, error) {
	b, err := os.ReadFile(configPath())
	if err != nil {
		return nil, err
	}
	var cfg map[string]any
	return cfg, json.Unmarshal(b, &cfg)
}

func LoadPolicy() (map[string]string, error) {
	b, err := os.ReadFile(policyPath())
	if err != nil {
		return nil, err
	}
	out := map[string]string{"pass_order_default": "first", "pool_clear_on_second": "true"}
	for _, line := range strings.Split(string(b), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		out[strings.TrimSpace(parts[0])] = strings.Trim(strings.TrimSpace(parts[1]), "\"")
	}
	return out, nil
}

func LoadGraph(name string) (map[string]any, error) {
	b, err := os.ReadFile(filepath.Join(graphDir(), name+".json"))
	if err != nil {
		return nil, err
	}
	var g map[string]any
	return g, json.Unmarshal(b, &g)
}

func LoadGraphs(names []string) ([]map[string]any, error) {
	out := make([]map[string]any, 0, len(names))
	for _, n := range names {
		g, err := LoadGraph(n)
		if err != nil {
			return nil, err
		}
		out = append(out, g)
	}
	return out, nil
}
