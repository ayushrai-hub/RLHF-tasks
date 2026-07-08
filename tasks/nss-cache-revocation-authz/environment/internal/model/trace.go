package model

type Trace struct {
	Case           string           `json:"case"`
	SchemaVersion  int              `json:"schema_version"`
	FreshnessBound int              `json:"freshness_bound"`
	Refreshes      []RefreshRecord  `json:"refreshes"`
	Decisions      []DecisionRecord `json:"decisions"`
	CacheEntries   []CacheEntry     `json:"cache_entries"`
	GroupIndex     []GroupIndexRow  `json:"group_index"`
	Audit          []AuditEvent     `json:"audit"`
	Provenance     Provenance       `json:"provenance"`
}

type AuditEvent struct {
	Step     int    `json:"step"`
	Tick     int    `json:"tick"`
	Event    string `json:"event"`
	Revision int    `json:"revision"`
	Message  string `json:"message"`
}

type Provenance struct {
	GeneratedBy string      `json:"generated_by"`
	CaseDigest  string      `json:"case_digest"`
	OutputPath  string      `json:"output_path"`
	Resume      ResumeState `json:"resume"`
}

type ResumeState struct {
	Used       bool `json:"used"`
	FromStep   int  `json:"from_step"`
	EpochStart int  `json:"epoch_start"`
}
