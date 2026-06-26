package freezeengine

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
)

func loadConfigMap(path string) (map[string]any, error) {
	bytes, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out map[string]any
	if err := json.Unmarshal(bytes, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func mergeMapKeys(dst, src map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range dst {
		out[key] = value
	}
	for key, value := range src {
		out[key] = value
	}
	return out
}

func mergeConfig(base, patch map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range base {
		out[key] = value
	}
	for key, value := range patch {
		if key == "team_map" || key == "service_class" {
			baseMap, okBase := out[key].(map[string]any)
			patchMap, okPatch := value.(map[string]any)
			if okBase && okPatch {
				out[key] = mergeMapKeys(baseMap, patchMap)
				continue
			}
		}
		out[key] = value
	}
	return out
}

func LoadEffectiveConfig(basePath string, patchDir string) (Config, error) {
	cfgMap, err := loadConfigMap(basePath)
	if err != nil {
		return Config{}, err
	}

	entries, err := os.ReadDir(patchDir)
	if err != nil {
		return Config{}, err
	}
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		if filepath.Ext(entry.Name()) == ".json" {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	for _, name := range names {
		patchMap, err := loadConfigMap(filepath.Join(patchDir, name))
		if err != nil {
			return Config{}, err
		}
		cfgMap = mergeConfig(cfgMap, patchMap)
	}

	bytes, err := json.Marshal(cfgMap)
	if err != nil {
		return Config{}, err
	}
	var cfg Config
	if err := json.Unmarshal(bytes, &cfg); err != nil {
		return Config{}, err
	}
	return cfg, nil
}
