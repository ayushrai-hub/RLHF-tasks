#!/usr/bin/env bash
set -euo pipefail
cat > /app/cmd/auditor/main.go <<'GO'
package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type Config struct {
	AsOf           string            `json:"as_of"`
	MaxHops        int               `json:"max_hops"`
	ServiceAliases map[string]string `json:"service_aliases"`
}

type ServiceCatalog struct {
	Services []Service `json:"services"`
}

type Service struct {
	ServiceID string   `json:"service_id"`
	Domains   []string `json:"domains"`
	Owner     string   `json:"owner"`
	Status    string   `json:"status"`
	RetiredAt string   `json:"retired_at"`
}

type RawRecord struct {
	Zone     string `json:"zone"`
	Name     string `json:"name"`
	Type     string `json:"type"`
	Target   string `json:"target"`
	Priority int    `json:"priority"`
}

type Record struct {
	Zone       string
	Name       string
	Type       string
	Target     string
	Priority   int
	SourcePath string
	SourceLine int
}

type Hop struct {
	Name   string `json:"name"`
	Target string `json:"target"`
}

type Chain struct {
	ChainID    string `json:"chain_id"`
	Zone       string `json:"zone"`
	Name       string `json:"name"`
	Target     string `json:"target"`
	Terminal   string `json:"terminal"`
	ServiceID  string `json:"service_id"`
	Owner      string `json:"owner"`
	Status     string `json:"status"`
	Loop       bool   `json:"loop"`
	Hops       []Hop  `json:"hops"`
	SourcePath string `json:"source_path"`
	SourceLine int    `json:"source_line"`
}

type Finding struct {
	Code       string `json:"code"`
	Severity   string `json:"severity"`
	ChainID    string `json:"chain_id"`
	Name       string `json:"name"`
	ServiceID  string `json:"service_id"`
	Owner      string `json:"owner"`
	SourcePath string `json:"source_path"`
	SourceLine int    `json:"source_line"`
	Detail     string `json:"detail"`
}

type Warning struct {
	Code       string `json:"code"`
	Severity   string `json:"severity"`
	SubjectID  string `json:"subject_id"`
	SourcePath string `json:"source_path"`
	SourceLine int    `json:"source_line"`
	Detail     string `json:"detail"`
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

type Report struct {
	GeneratedAt string    `json:"generated_at"`
	Summary     Summary   `json:"summary"`
	Chains      []Chain   `json:"chains"`
	Findings    []Finding `json:"findings"`
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	configPath := flag.String("config", "", "audit policy")
	zonesPath := flag.String("zones", "", "zone jsonl directory")
	servicesPath := flag.String("services", "", "service catalog")
	outPath := flag.String("out", "", "output directory")
	flag.Parse()
	if *configPath == "" || *zonesPath == "" || *servicesPath == "" || *outPath == "" {
		return errors.New("missing required --config, --zones, --services, or --out flag")
	}

	cfg, asOf, err := loadConfig(*configPath)
	if err != nil {
		return err
	}
	catalog, err := loadCatalog(*servicesPath)
	if err != nil {
		return err
	}
	records, warnings, err := loadRecords(*zonesPath)
	if err != nil {
		return err
	}
	kept, duplicateWarnings := resolveDuplicates(records)
	warnings = append(warnings, duplicateWarnings...)
	sortWarnings(warnings)

	chains, findings := buildChains(kept, cfg, catalog, asOf)
	sortChains(chains)
	sortFindings(findings)

	summary := Summary{ChainsTotal: len(chains), FindingsTotal: len(findings), WarningsTotal: len(warnings)}
	for _, ch := range chains {
		if len(ch.Hops) > summary.MaxChainLength {
			summary.MaxChainLength = len(ch.Hops)
		}
	}
	for _, f := range findings {
		switch f.Code {
		case "loop_detected":
			summary.Loops++
		case "stale_service":
			summary.StaleServices++
		case "ownership_gap":
			summary.OwnershipGaps++
		}
	}

	if err := os.RemoveAll(*outPath); err != nil {
		return err
	}
	if err := os.MkdirAll(*outPath, 0755); err != nil {
		return err
	}
	report := Report{GeneratedAt: cfg.AsOf, Summary: summary, Chains: chains, Findings: findings}
	if err := writeJSON(filepath.Join(*outPath, "cname_chain_report.json"), report); err != nil {
		return err
	}
	if err := writeJSON(filepath.Join(*outPath, "warnings.json"), warnings); err != nil {
		return err
	}
	return nil
}

func loadConfig(path string) (Config, time.Time, error) {
	var cfg Config
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg, time.Time{}, err
	}
	if err := json.Unmarshal(data, &cfg); err != nil {
		return cfg, time.Time{}, err
	}
	if cfg.ServiceAliases == nil {
		cfg.ServiceAliases = map[string]string{}
	}
	normalizedAliases := map[string]string{}
	for k, v := range cfg.ServiceAliases {
		normalizedAliases[normalizeDNS(k)] = strings.TrimSpace(v)
	}
	cfg.ServiceAliases = normalizedAliases
	asOf, err := time.Parse(time.RFC3339, cfg.AsOf)
	if err != nil {
		return cfg, time.Time{}, fmt.Errorf("invalid as_of: %w", err)
	}
	if cfg.MaxHops <= 0 {
		return cfg, time.Time{}, errors.New("max_hops must be positive")
	}
	return cfg, asOf, nil
}

func loadCatalog(path string) (map[string]Service, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var parsed ServiceCatalog
	if err := json.Unmarshal(data, &parsed); err != nil {
		return nil, err
	}
	byID := map[string]Service{}
	for _, svc := range parsed.Services {
		svc.ServiceID = strings.TrimSpace(svc.ServiceID)
		svc.Owner = strings.TrimSpace(svc.Owner)
		svc.Status = strings.TrimSpace(strings.ToLower(svc.Status))
		if svc.Status == "" {
			svc.Status = "active"
		}
		normDomains := []string{}
		for _, d := range svc.Domains {
			nd := normalizeDNS(d)
			if nd != "" {
				normDomains = append(normDomains, nd)
			}
		}
		svc.Domains = normDomains
		if svc.ServiceID != "" {
			byID[svc.ServiceID] = svc
		}
	}
	return byID, nil
}

func loadRecords(root string) ([]Record, []Warning, error) {
	paths := []string{}
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if path == root {
			return nil
		}
		if d.IsDir() {
			if strings.HasPrefix(d.Name(), ".") {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.HasPrefix(d.Name(), ".") {
			return nil
		}
		if strings.HasSuffix(d.Name(), ".jsonl") {
			paths = append(paths, path)
		}
		return nil
	})
	if err != nil {
		return nil, nil, err
	}
	sort.Strings(paths)

	records := []Record{}
	warnings := []Warning{}
	for _, path := range paths {
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return nil, nil, err
		}
		rel = filepath.ToSlash(rel)
		fh, err := os.Open(path)
		if err != nil {
			return nil, nil, err
		}
		scanner := bufio.NewScanner(fh)
		lineNo := 0
		for scanner.Scan() {
			lineNo++
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}
			var raw RawRecord
			if err := json.Unmarshal([]byte(line), &raw); err != nil {
				warnings = append(warnings, Warning{Code: "invalid_json", Severity: "error", SourcePath: rel, SourceLine: lineNo, Detail: fmt.Sprintf("invalid JSON at %s:%d", rel, lineNo)})
				continue
			}
			typeNorm := strings.ToUpper(strings.TrimSpace(raw.Type))
			if typeNorm != "CNAME" {
				continue
			}
			zone := normalizeDNS(raw.Zone)
			name := normalizeDNS(raw.Name)
			target := normalizeDNS(raw.Target)
			if zone == "" {
				warnings = append(warnings, invalidCNAMEWarning("", rel, lineNo, "zone"))
				continue
			}
			if name == "" {
				warnings = append(warnings, invalidCNAMEWarning("", rel, lineNo, "name"))
				continue
			}
			if target == "" {
				warnings = append(warnings, invalidCNAMEWarning(name, rel, lineNo, "target"))
				continue
			}
			records = append(records, Record{Zone: zone, Name: name, Type: "CNAME", Target: target, Priority: raw.Priority, SourcePath: rel, SourceLine: lineNo})
		}
		if err := scanner.Err(); err != nil {
			_ = fh.Close()
			return nil, nil, err
		}
		_ = fh.Close()
	}
	return records, warnings, nil
}

func invalidCNAMEWarning(subject, path string, line int, field string) Warning {
	return Warning{Code: "invalid_cname", Severity: "error", SubjectID: subject, SourcePath: path, SourceLine: line, Detail: fmt.Sprintf("invalid CNAME record missing %s", field)}
}

func resolveDuplicates(records []Record) ([]Record, []Warning) {
	kept := map[string]Record{}
	discarded := map[string][]Record{}
	for _, r := range records {
		key := r.Zone + "\x00" + r.Name
		current, ok := kept[key]
		if !ok {
			kept[key] = r
			continue
		}
		if betterRecord(r, current) {
			discarded[key] = append(discarded[key], current)
			kept[key] = r
		} else {
			discarded[key] = append(discarded[key], r)
		}
	}
	keys := make([]string, 0, len(kept))
	for k := range kept {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := []Record{}
	warnings := []Warning{}
	for _, key := range keys {
		winner := kept[key]
		out = append(out, winner)
		for _, d := range discarded[key] {
			warnings = append(warnings, Warning{Code: "duplicate_cname", Severity: "warning", SubjectID: d.Name, SourcePath: d.SourcePath, SourceLine: d.SourceLine, Detail: fmt.Sprintf("duplicate CNAME %s; kept %s:%d", d.Name, winner.SourcePath, winner.SourceLine)})
		}
	}
	return out, warnings
}

func betterRecord(a, b Record) bool {
	if a.Priority != b.Priority {
		return a.Priority > b.Priority
	}
	if a.SourcePath != b.SourcePath {
		return a.SourcePath < b.SourcePath
	}
	return a.SourceLine < b.SourceLine
}

func buildChains(records []Record, cfg Config, catalog map[string]Service, asOf time.Time) ([]Chain, []Finding) {
	byName := map[string]Record{}
	for _, r := range records {
		if existing, ok := byName[r.Name]; ok {
			if betterRecord(r, existing) {
				byName[r.Name] = r
			}
		} else {
			byName[r.Name] = r
		}
	}
	chains := []Chain{}
	findings := []Finding{}
	for _, start := range records {
		chain := expandChain(start, byName, cfg.MaxHops)
		if chain.Loop {
			findings = append(findings, Finding{Code: "loop_detected", Severity: "critical", ChainID: chain.ChainID, Name: chain.Name, SourcePath: chain.SourcePath, SourceLine: chain.SourceLine, Detail: loopDetail(chain.Hops)})
			chains = append(chains, chain)
			continue
		}
		svc, ok := resolveService(chain.Terminal, cfg, catalog)
		if !ok {
			chain.ServiceID = ""
			chain.Owner = ""
			chain.Status = "unknown"
			findings = append(findings, Finding{Code: "ownership_gap", Severity: "medium", ChainID: chain.ChainID, Name: chain.Name, SourcePath: chain.SourcePath, SourceLine: chain.SourceLine, Detail: fmt.Sprintf("terminal %s has no catalog owner", chain.Terminal)})
			chains = append(chains, chain)
			continue
		}
		chain.ServiceID = svc.ServiceID
		chain.Owner = svc.Owner
		chain.Status = svc.Status
		if isStale(svc, asOf) {
			findings = append(findings, Finding{Code: "stale_service", Severity: "high", ChainID: chain.ChainID, Name: chain.Name, ServiceID: svc.ServiceID, Owner: svc.Owner, SourcePath: chain.SourcePath, SourceLine: chain.SourceLine, Detail: fmt.Sprintf("terminal %s resolves to stale service %s", chain.Terminal, svc.ServiceID)})
		}
		if strings.TrimSpace(svc.Owner) == "" {
			findings = append(findings, Finding{Code: "ownership_gap", Severity: "medium", ChainID: chain.ChainID, Name: chain.Name, ServiceID: svc.ServiceID, Owner: "", SourcePath: chain.SourcePath, SourceLine: chain.SourceLine, Detail: fmt.Sprintf("service %s has no owner", svc.ServiceID)})
		}
		chains = append(chains, chain)
	}
	return chains, findings
}

func expandChain(start Record, byName map[string]Record, maxHops int) Chain {
	chain := Chain{ChainID: start.Name, Zone: start.Zone, Name: start.Name, Target: start.Target, Terminal: start.Target, Status: "unknown", Hops: []Hop{}, SourcePath: start.SourcePath, SourceLine: start.SourceLine}
	seen := map[string]bool{start.Name: true}
	current := start
	for i := 0; i < maxHops; i++ {
		hop := Hop{Name: current.Name, Target: current.Target}
		chain.Hops = append(chain.Hops, hop)
		chain.Terminal = current.Target
		if seen[current.Target] {
			chain.Loop = true
			chain.Status = "loop"
			chain.ServiceID = ""
			chain.Owner = ""
			return chain
		}
		next, ok := byName[current.Target]
		if !ok {
			return chain
		}
		seen[current.Target] = true
		current = next
	}
	return chain
}

func resolveService(terminal string, cfg Config, catalog map[string]Service) (Service, bool) {
	if id, ok := cfg.ServiceAliases[terminal]; ok {
		svc, found := catalog[id]
		return svc, found
	}
	for _, svc := range catalog {
		for _, d := range svc.Domains {
			if d == terminal {
				return svc, true
			}
		}
	}
	return Service{}, false
}

func isStale(svc Service, asOf time.Time) bool {
	if strings.ToLower(svc.Status) == "retired" {
		return true
	}
	if strings.TrimSpace(svc.RetiredAt) == "" {
		return false
	}
	for _, layout := range []string{"2006-01-02", time.RFC3339} {
		if t, err := time.Parse(layout, svc.RetiredAt); err == nil {
			return !t.After(asOf)
		}
	}
	return false
}

func loopDetail(hops []Hop) string {
	parts := []string{}
	if len(hops) > 0 {
		parts = append(parts, hops[0].Name)
	}
	for _, h := range hops {
		parts = append(parts, h.Target)
	}
	return "CNAME loop detected: " + strings.Join(parts, " -> ")
}

func sortChains(chains []Chain) {
	sort.Slice(chains, func(i, j int) bool {
		a, b := chains[i], chains[j]
		if a.ChainID != b.ChainID { return a.ChainID < b.ChainID }
		if a.Zone != b.Zone { return a.Zone < b.Zone }
		if a.SourcePath != b.SourcePath { return a.SourcePath < b.SourcePath }
		return a.SourceLine < b.SourceLine
	})
}

func sortFindings(findings []Finding) {
	sort.Slice(findings, func(i, j int) bool {
		a, b := findings[i], findings[j]
		if a.Code != b.Code { return a.Code < b.Code }
		if a.ChainID != b.ChainID { return a.ChainID < b.ChainID }
		if a.SourcePath != b.SourcePath { return a.SourcePath < b.SourcePath }
		if a.SourceLine != b.SourceLine { return a.SourceLine < b.SourceLine }
		return a.Detail < b.Detail
	})
}

func sortWarnings(warnings []Warning) {
	sort.Slice(warnings, func(i, j int) bool {
		a, b := warnings[i], warnings[j]
		if a.Code != b.Code { return a.Code < b.Code }
		if a.SubjectID != b.SubjectID { return a.SubjectID < b.SubjectID }
		if a.SourcePath != b.SourcePath { return a.SourcePath < b.SourcePath }
		if a.SourceLine != b.SourceLine { return a.SourceLine < b.SourceLine }
		return a.Detail < b.Detail
	})
}

func normalizeDNS(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	for strings.HasSuffix(s, ".") {
		s = strings.TrimSuffix(s, ".")
	}
	return s
}

func writeJSON(path string, v interface{}) error {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	b = append(b, '\n')
	return os.WriteFile(path, b, 0644)
}
GO
gofmt -w /app/cmd/auditor/main.go
/app/bin/audit-cname-chains --config /app/config/audit-policy.json --zones /app/fixtures/zones --services /app/fixtures/service-catalog.json --out /app/out
