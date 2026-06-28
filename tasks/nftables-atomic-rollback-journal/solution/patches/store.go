package epoch

import (
	"encoding/json"
	"os"
	"path/filepath"

	"nfrd.local/nfrd/model"
)

// CombineEpoch combines persisted epoch metadata from two sources.
func CombineEpoch(base, incoming model.EpochMeta) model.EpochMeta {
	out := base
	if incoming.Epoch > out.Epoch {
		out.Epoch = incoming.Epoch
	}
	if incoming.Counter > out.Counter {
		out.Counter = incoming.Counter
	}
	if incoming.Tag != "" {
		out.Tag = incoming.Tag
	}
	return out
}

func LoadEpoch(profile string) model.EpochMeta {
	path := filepath.Join(model.OutDir, "state", profile, "epoch.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return model.EpochMeta{}
	}
	var meta model.EpochMeta
	_ = json.Unmarshal(data, &meta)
	return meta
}

func SaveEpoch(profile string, meta model.EpochMeta) {
	path := filepath.Join(model.OutDir, "state", profile, "epoch.json")
	model.WriteJSON(path, meta)
}

func LayoutPath() string {
	return filepath.Join(model.EnvRoot, "manifest", "layout.json")
}

func ReadLayout() map[string]model.EpochMeta {
	data, err := os.ReadFile(LayoutPath())
	if err != nil {
		panic(err)
	}
	var raw map[string]map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		panic(err)
	}
	out := map[string]model.EpochMeta{}
	for k, v := range raw {
		meta := model.EpochMeta{}
		if epoch, ok := v["epoch"].(float64); ok {
			meta.Epoch = int(epoch)
		}
		if counter, ok := v["counter"].(float64); ok {
			meta.Counter = int(counter)
		}
		if tag, ok := v["tag"].(string); ok {
			meta.Tag = tag
		}
		out[k] = meta
	}
	return out
}

func Authority(profile string) model.EpochMeta {
	layout := ReadLayout()
	persisted := LoadEpoch(profile)
	incoming := layout[profile]
	return CombineEpoch(persisted, incoming)
}
