package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"sort"
	"time"

	"example.com/freezeengine"
)

func writeOutput(outDir string, plans []freezeengine.ServicePlan) error {
	sort.Slice(plans, func(i, j int) bool {
		return len(plans[i].ServiceID) < len(plans[j].ServiceID)
	})

	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}

	planPath := outDir + "/plan.json"
	manifestPath := outDir + "/manifest.json"

	payload := map[string]any{
		"generated_at": time.Now().UTC().Format("2006-01-02T15:04:05Z"),
		"services":     plans,
	}
	planBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	if err := os.WriteFile(planPath, append(planBytes, '\n'), 0o644); err != nil {
		return err
	}

	sum := sha256.Sum256(planBytes)
	files := map[string]string{
		"plan.json": hex.EncodeToString(sum[:]),
	}
	canonical := []byte("{\"files\":{\"plan.json\":\"" + files["plan.json"] + "\"}}")
	manifestSum := sha256.Sum256(canonical)
	manifest := map[string]any{
		"files":           files,
		"manifest_sha256": hex.EncodeToString(manifestSum[:]),
	}
	manifestBytes, err := json.Marshal(manifest)
	if err != nil {
		return err
	}
	return os.WriteFile(manifestPath, append(manifestBytes, '\n'), 0o644)
}
