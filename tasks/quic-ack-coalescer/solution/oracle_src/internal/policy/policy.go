package policy

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Policy struct {
	Version                    string         `json:"version"`
	CoalesceUsBase             int64          `json:"coalesce_us_base"`
	ReorderUsBase              int64          `json:"reorder_us_base"`
	BudgetThreshold            int64          `json:"budget_threshold"`
	TierCoalesceFactorPermille map[string]int `json:"tier_coalesce_factor_permille"`
	TierReorderFactorPermille  map[string]int `json:"tier_reorder_factor_permille"`
	TierSynonyms               map[string]string `json:"tier_synonyms"`
	PnSpaces                   []string       `json:"pn_spaces"`
	MarkerKinds                []string       `json:"marker_kinds"`
	MarkerSecretLabel          string         `json:"marker_secret_label"`
}

func Load(dataDir string) (*Policy, error) {
	b, err := os.ReadFile(filepath.Join(dataDir, "coalescer_anchor_set.json"))
	if err != nil {
		return nil, err
	}
	var p Policy
	if err := json.Unmarshal(b, &p); err != nil {
		return nil, fmt.Errorf("coalescer_anchor_set.json: %w", err)
	}
	return &p, nil
}

// CanonicalTier maps a raw tier label (case-insensitive synonym) to the canonical
// upper-case enum. Unknown values map to STANDARD.
func (p *Policy) CanonicalTier(raw string) string {
	low := strings.ToLower(strings.TrimSpace(raw))
	if v, ok := p.TierSynonyms[low]; ok {
		return v
	}
	upper := strings.ToUpper(low)
	switch upper {
	case "CRITICAL", "STANDARD", "BULK":
		return upper
	}
	return "STANDARD"
}

// EffectiveCoalesceMs returns the coalesce window in milliseconds for a tier.
// CRITICAL tier halves the base (factor 500/1000).
func (p *Policy) EffectiveCoalesceMs(tier string) int64 {
	f, ok := p.TierCoalesceFactorPermille[tier]
	if !ok {
		f = 1000
	}
	return p.CoalesceUsBase * int64(f) / 1000
}

func (p *Policy) EffectiveReorderMs(tier string) int64 {
	f, ok := p.TierReorderFactorPermille[tier]
	if !ok {
		f = 1000
	}
	return p.ReorderUsBase * int64(f) / 1000
}

// IsClosedPnSpace returns true when s is one of the policy-recognized pn_space enums.
func (p *Policy) IsClosedPnSpace(s string) bool {
	for _, v := range p.PnSpaces {
		if v == s {
			return true
		}
	}
	return false
}

func (p *Policy) IsClosedMarkerKind(s string) bool {
	for _, v := range p.MarkerKinds {
		if v == s {
			return true
		}
	}
	return false
}
