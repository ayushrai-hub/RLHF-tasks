package model

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
)

const (
	AppRoot = "/app"
	EnvRoot = AppRoot + "/environment"
	OutDir  = AppRoot + "/output"
	BinDir  = AppRoot + "/bin"
)

type Record struct {
	Seq      int     `json:"seq"`
	RuleID   string  `json:"rule_id"`
	Action   string  `json:"action"`
	Epoch    int     `json:"epoch"`
	Priority int     `json:"priority"`
	Mark     float64 `json:"mark"`
	Phase    string  `json:"phase"`
	RunID    string  `json:"run_id"`
	Source   string  `json:"source,omitempty"`
}

type Context struct {
	Profile string
	Epoch   int
	Phase   string
	RunID   string
}

type RuleView struct {
	RuleID   string  `json:"rule_id"`
	Priority int     `json:"priority"`
	Epoch    int     `json:"epoch"`
	Mark     float64 `json:"mark"`
}

type ViewState struct {
	Rules []RuleView
	Phase string
	RunID string
}

type EpochMeta struct {
	Epoch   int
	Counter int
	Tag     string
}

type RunRecord struct {
	RunID    string `json:"run_id"`
	Phase    string `json:"phase"`
	TreeHash string `json:"tree_hash"`
}

type EntryRecord struct {
	RuleID       string `json:"rule_id"`
	Action       string `json:"action"`
	Epoch        int    `json:"epoch"`
	ObservedHash string `json:"observed_hash"`
}

type CheckpointRecord struct {
	RunID       string `json:"run_id"`
	Phase       string `json:"phase"`
	FirstSeq    int    `json:"first_seq"`
	LastSeq     int    `json:"last_seq"`
	RecordCount int    `json:"record_count"`
	EpochFloor  int    `json:"epoch_floor"`
	EpochCeil   int    `json:"epoch_ceil"`
	TreeHash    string `json:"tree_hash"`
}

type Report struct {
	Profile     string             `json:"profile"`
	Epoch       int                `json:"epoch"`
	Counter     int                `json:"counter"`
	Runs        []RunRecord        `json:"runs"`
	Entries     []EntryRecord      `json:"entries"`
	Checkpoints []CheckpointRecord `json:"checkpoints"`
}

type ProfileSpec struct {
	Name       string
	FixtureDir string
	Runs       []string
	Simulate   string
}

func TreeHash(rules []RuleView) string {
	type row struct {
		RuleID   string `json:"rule_id"`
		Priority int    `json:"priority"`
		Epoch    int    `json:"epoch"`
	}
	rows := make([]row, len(rules))
	for i, r := range rules {
		rows[i] = row{RuleID: r.RuleID, Priority: r.Priority, Epoch: r.Epoch}
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i].RuleID < rows[j].RuleID })
	data, _ := json.Marshal(rows)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func ObservedHash(rule RuleView) string {
	type row struct {
		RuleID   string  `json:"rule_id"`
		Priority int     `json:"priority"`
		Epoch    int     `json:"epoch"`
		Mark     float64 `json:"mark"`
	}
	payload, _ := json.Marshal(row{
		RuleID:   rule.RuleID,
		Priority: rule.Priority,
		Epoch:    rule.Epoch,
		Mark:     rule.Mark,
	})
	sum := sha256.Sum256(payload)
	return hex.EncodeToString(sum[:])
}

func WriteJSON(path string, v any) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		panic(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		panic(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0644); err != nil {
		panic(err)
	}
}
