package judge

import (
	"encoding/json"
	"os"
)

type RecordExpectation struct {
	Winner                  string   `json:"winner"`
	Margin                  float64  `json:"margin"`
	TerminalPassMoveNumbers []int    `json:"terminal_pass_move_numbers"`
	RequiredVariation       string   `json:"required_variation"`
	RequiredBranchOnlyMoves []string `json:"required_branch_only_moves"`
	AllowLegacyScoreToken   bool     `json:"allow_legacy_score_token"`
}

type Policy struct {
	PolicyID                 string                       `json:"policy_id"`
	Ruleset                  string                       `json:"ruleset"`
	ClosingPassesRequired    int                          `json:"closing_passes_required"`
	ScoreSource              string                       `json:"score_source"`
	AllowLegacyScoreToken    bool                         `json:"allow_legacy_score_token"`
	Komi                     float64                      `json:"komi"`
	RequireBranchLeakageZero bool                         `json:"require_branch_leakage_zero"`
	ExpectedRecords          map[string]RecordExpectation `json:"expected_records"`
}

func LoadPolicy(path string) (Policy, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Policy{}, err
	}
	var policy Policy
	if err := json.Unmarshal(data, &policy); err != nil {
		return Policy{}, err
	}
	return policy, nil
}
