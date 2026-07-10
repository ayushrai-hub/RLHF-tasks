package types

// Rule represents a subtyping rule from the input.
type Rule struct {
	RuleID     string   `json:"rule_id"`
	SubType    string   `json:"sub_type"`
	SuperType  string   `json:"super_type"`
	Conditions []string `json:"conditions"`
}

// Obligation represents a transitivity proof obligation.
type Obligation struct {
	Sub        string `json:"sub"`
	Super      string `json:"super"`
	Via        string `json:"via"`
	IsProvable bool   `json:"is_provable"`
}

// AnalysisResult is the final output structure.
type AnalysisResult struct {
	TotalRules        int          `json:"total_rules"`
	Obligations       []Obligation `json:"obligations"`
	UnprovableCount   int          `json:"unprovable_count"`
	TransitivityHolds bool         `json:"transitivity_holds"`
	BreakingRules     []string     `json:"breaking_rules"`
}
