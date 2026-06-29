package tools

import (
	"encoding/json"
	"os"
	"path/filepath"

	"nfrd.local/nfrd/windowfuse"
	"nfrd.local/nfrd/model"
)

func LaneProbe(profile string) map[string]string {
	auth := windowfuse.Authority(profile)
	path := filepath.Join(model.OutDir, "state", profile, "lane.json")
	data, _ := os.ReadFile(path)
	var prior map[string]string
	_ = json.Unmarshal(data, &prior)
	out := map[string]string{
		"state": "green",
		"tag":   auth.Tag,
	}
	if prior != nil && prior["state"] == "green" {
		out["state"] = "green"
	}
	model.WriteJSON(path, out)
	return out
}
