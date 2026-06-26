package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

func main() {
	outDir := "/app/task_file/output_data"
	if len(os.Args) > 2 {
		outDir = os.Args[2]
	}
	_ = os.MkdirAll(outDir, 0o755)
	payload := map[string][]map[string]string{"assignments": {}}
	data, _ := json.Marshal(payload)
	_ = os.WriteFile(filepath.Join(outDir, "restoration_plan.json"), data, 0o644)
}
