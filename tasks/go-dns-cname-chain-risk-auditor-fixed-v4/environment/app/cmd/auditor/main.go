package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type Warning struct {
	Code       string `json:"code"`
	Severity   string `json:"severity"`
	SubjectID  string `json:"subject_id"`
	SourcePath string `json:"source_path"`
	SourceLine int    `json:"source_line"`
	Detail     string `json:"detail"`
}

type Report struct {
	GeneratedAt string        `json:"generated_at"`
	Summary     Summary       `json:"summary"`
	Chains      []interface{} `json:"chains"`
	Findings    []interface{} `json:"findings"`
}

type Summary struct {
	ChainsTotal    int `json:"chains_total"`
	FindingsTotal  int `json:"findings_total"`
	WarningsTotal  int `json:"warnings_total"`
	Loops          int `json:"loops"`
	StaleServices  int `json:"stale_services"`
	OwnershipGaps  int `json:"ownership_gaps"`
	MaxChainLength int `json:"max_chain_length"`
}

func main() {
	configPath := flag.String("config", "", "audit policy")
	zonesPath := flag.String("zones", "", "zone jsonl directory")
	servicesPath := flag.String("services", "", "service catalog")
	outPath := flag.String("out", "", "output directory")
	flag.Parse()
	if *configPath == "" || *zonesPath == "" || *servicesPath == "" || *outPath == "" {
		fmt.Fprintln(os.Stderr, "missing required flags")
		os.Exit(2)
	}

	var cfg struct {
		AsOf string `json:"as_of"`
	}
	if data, err := os.ReadFile(*configPath); err == nil {
		_ = json.Unmarshal(data, &cfg)
	}

	warnings := []Warning{}
	paths := []string{}
	_ = filepath.WalkDir(*zonesPath, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			return nil
		}
		if strings.HasSuffix(path, ".jsonl") {
			paths = append(paths, path)
		}
		return nil
	})
	sort.Strings(paths)
	for _, p := range paths {
		b, _ := os.ReadFile(p)
		for i, line := range strings.Split(strings.TrimRight(string(b), "\n"), "\n") {
			if strings.TrimSpace(line) == "" {
				continue
			}
			var obj map[string]interface{}
			if err := json.Unmarshal([]byte(line), &obj); err != nil {
				rel, _ := filepath.Rel(*zonesPath, p)
				warnings = append(warnings, Warning{Code: "invalid_json", Severity: "error", SourcePath: filepath.ToSlash(rel), SourceLine: i + 1, Detail: fmt.Sprintf("invalid JSON at %s:%d", filepath.ToSlash(rel), i+1)})
			}
		}
	}

	_ = os.RemoveAll(*outPath)
	_ = os.MkdirAll(*outPath, 0755)
	report := Report{GeneratedAt: cfg.AsOf, Chains: []interface{}{}, Findings: []interface{}{}, Summary: Summary{WarningsTotal: len(warnings)}}
	writeJSON(filepath.Join(*outPath, "cname_chain_report.json"), report)
	writeJSON(filepath.Join(*outPath, "warnings.json"), warnings)
}

func writeJSON(path string, v interface{}) {
	b, _ := json.MarshalIndent(v, "", "  ")
	_ = os.WriteFile(path, append(b, '\n'), 0644)
}
