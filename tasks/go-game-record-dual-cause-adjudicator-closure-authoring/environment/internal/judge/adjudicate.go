package judge

import (
	"fmt"
	"math"
	"reflect"
	"strings"

	"local/goadj/internal/record"
)

type Decision struct {
	PolicyID        string  `json:"policy_id"`
	Winner          string  `json:"winner"`
	Margin          float64 `json:"margin"`
	AgreesWithRules bool    `json:"agrees_with_rules_engine"`
	Reason          string  `json:"reason"`
}

func Decide(policy Policy, rules record.Rulebook, rec record.GameRecord, replay record.ReplayResult) (Decision, error) {
	if policy.Ruleset != rules.Ruleset {
		return Decision{}, fmt.Errorf("policy ruleset %s does not match rulebook %s", policy.Ruleset, rules.Ruleset)
	}
	if policy.ClosingPassesRequired != rules.PassesToEnd {
		return Decision{}, fmt.Errorf("policy closing_passes_required %d disagrees with rulebook passes_to_end %d", policy.ClosingPassesRequired, rules.PassesToEnd)
	}
	if math.Abs(policy.Komi-rules.Komi) > 0.0001 {
		return Decision{}, fmt.Errorf("policy komi %.1f disagrees with rulebook komi %.1f", policy.Komi, rules.Komi)
	}
	if policy.ScoreSource != "area_score" {
		return Decision{}, fmt.Errorf("policy score_source must be area_score")
	}
	if rec.Score.Legacy && !policy.AllowLegacyScoreToken {
		return Decision{}, fmt.Errorf("policy rejects legacy score token for record %s", rec.RecordID)
	}
	if policy.RequireBranchLeakageZero {
		for _, v := range replay.VariationReplays {
			if v.BranchLeakCount != 0 {
				return Decision{}, fmt.Errorf("variation %s leaks %d branch stone(s) into final main state", v.Name, v.BranchLeakCount)
			}
		}
	}
	if len(policy.ExpectedRecords) > 0 {
		lookupID := rec.RecordID
		expected, ok := policy.ExpectedRecords[lookupID]
		if !ok && strings.HasSuffix(lookupID, "-copy") {
			expected, ok = policy.ExpectedRecords[strings.TrimSuffix(lookupID, "-copy")]
		}
		if !ok {
			return Decision{}, fmt.Errorf("policy has no expectation for record %s", rec.RecordID)
		}
		if expected.Winner != "" && expected.Winner != replay.Winner {
			return Decision{}, fmt.Errorf("policy expects winner %s for record %s but replay produced %s", expected.Winner, rec.RecordID, replay.Winner)
		}
		if expected.Margin != 0 && math.Abs(expected.Margin-replay.Margin) > 0.0001 {
			return Decision{}, fmt.Errorf("policy expects margin %.1f for record %s but replay produced %.1f", expected.Margin, rec.RecordID, replay.Margin)
		}
		if len(expected.TerminalPassMoveNumbers) > 0 && !reflect.DeepEqual(expected.TerminalPassMoveNumbers, replay.TerminalPassMoveNums) {
			return Decision{}, fmt.Errorf("policy terminal pass window for record %s does not match replay", rec.RecordID)
		}
		if rec.Score.Legacy && !expected.AllowLegacyScoreToken {
			return Decision{}, fmt.Errorf("policy expectation rejects legacy score token for record %s", rec.RecordID)
		}
		if expected.RequiredVariation != "" {
			found := false
			for _, v := range replay.VariationReplays {
				if v.Name != expected.RequiredVariation {
					continue
				}
				found = true
				if len(expected.RequiredBranchOnlyMoves) > 0 && !sameStrings(expected.RequiredBranchOnlyMoves, v.BranchOnlyMoves) {
					return Decision{}, fmt.Errorf("policy branch-only stones for variation %s do not match replay", v.Name)
				}
			}
			if !found {
				return Decision{}, fmt.Errorf("policy requires variation %s for record %s", expected.RequiredVariation, rec.RecordID)
			}
		}
	}
	return Decision{PolicyID: policy.PolicyID, Winner: replay.Winner, Margin: replay.Margin, AgreesWithRules: true, Reason: "rulebook, replay, and adjudicator policy agree"}, nil
}

func sameStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
