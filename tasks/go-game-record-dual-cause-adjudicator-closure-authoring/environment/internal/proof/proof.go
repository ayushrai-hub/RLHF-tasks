package proof

import "local/goadj/internal/judge"

type FileAuthority struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

type RecordProof struct {
	RecordID      string         `json:"record_id"`
	Path          string         `json:"path"`
	PathSHA256    string         `json:"path_sha256"`
	RulesEngine   any            `json:"rules_engine"`
	JudgeDecision judge.Decision `json:"independent_judge"`
	Compatibility struct {
		LegacyScoreNotation bool `json:"legacy_score_notation"`
	} `json:"compatibility"`
}

type Bundle struct {
	SchemaVersion  string          `json:"schema_version"`
	Rulebook       FileAuthority   `json:"rulebook"`
	Policy         FileAuthority   `json:"policy"`
	Records        []RecordProof   `json:"records"`
	AllRecordsAgree bool           `json:"all_records_agree"`
}
