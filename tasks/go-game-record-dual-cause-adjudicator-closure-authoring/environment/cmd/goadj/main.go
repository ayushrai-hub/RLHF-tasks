package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"local/goadj/internal/judge"
	"local/goadj/internal/proof"
	"local/goadj/internal/record"
)

func main() {
	var rulebookPath, policyPath, recordPath, legacyPath, outPath string
	flag.StringVar(&rulebookPath, "rulebook", "u/tournament_rulebook.json", "rulebook path")
	flag.StringVar(&policyPath, "policy", "j/policy.json", "independent adjudicator policy path")
	flag.StringVar(&recordPath, "record", "r/dragon-cup-17.ggr", "primary game record path")
	flag.StringVar(&legacyPath, "legacy", "r/legacy-1999.ggr", "legacy compatibility record path")
	flag.StringVar(&outPath, "out", "output/adjudication-proof.json", "proof output path")
	flag.Parse()

	if err := run(rulebookPath, policyPath, []string{recordPath, legacyPath}, outPath); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(rulebookPath, policyPath string, recordPaths []string, outPath string) error {
	rules, err := loadRulebook(rulebookPath)
	if err != nil {
		return err
	}
	policy, err := judge.LoadPolicy(policyPath)
	if err != nil {
		return err
	}
	bundle := proof.Bundle{
		SchemaVersion:  "go-adjudication-proof-v1",
		Rulebook:       proof.FileAuthority{Path: rulebookPath, SHA256: mustHash(rulebookPath)},
		Policy:         proof.FileAuthority{Path: policyPath, SHA256: mustHash(policyPath)},
		AllRecordsAgree: true,
	}
	for _, p := range recordPaths {
		rec, err := record.ParseFile(p)
		if err != nil {
			return err
		}
		replay, err := record.Replay(rec, rules)
		if err != nil {
			return err
		}
		decision, err := judge.Decide(policy, rules, rec, replay)
		if err != nil {
			return err
		}
		item := proof.RecordProof{RecordID: rec.RecordID, Path: p, PathSHA256: mustHash(p), RulesEngine: replay, JudgeDecision: decision}
		item.Compatibility.LegacyScoreNotation = rec.Score.Legacy
		bundle.Records = append(bundle.Records, item)
	}
	data, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		return err
	}
	return os.WriteFile(outPath, append(data, '\n'), 0o644)
}

func loadRulebook(path string) (record.Rulebook, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return record.Rulebook{}, err
	}
	var rules record.Rulebook
	if err := json.Unmarshal(data, &rules); err != nil {
		return record.Rulebook{}, err
	}
	if rules.Ruleset == "" || rules.BoardSize <= 1 || rules.PassesToEnd <= 0 || rules.Scoring != "area" {
		return record.Rulebook{}, fmt.Errorf("rulebook is incomplete or not an area-scoring rulebook")
	}
	return rules, nil
}

func mustHash(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		panic(err)
	}
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:])
}
