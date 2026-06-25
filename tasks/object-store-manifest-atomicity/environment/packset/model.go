package packset

import "terminal.local/objectmanifest/internal/report"

type Object struct {
	LogicalKey   string `json:"logical_key"`
	RelativePath string `json:"relative_path"`
	Size         int64  `json:"size"`
	SHA256       string `json:"sha256"`
}

type Batch struct {
	BatchID     string   `json:"batch_id"`
	Epoch       int      `json:"epoch"`
	ObjectCount int      `json:"object_count"`
	BatchSHA256 string   `json:"batch_sha256"`
	Objects     []Object `json:"objects"`
}

type Manifest struct {
	SchemaVersion int     `json:"schema_version"`
	Store         string  `json:"store"`
	GeneratedBy   string  `json:"generated_by"`
	CommitCount   int     `json:"commit_count"`
	ObjectCount   int     `json:"object_count"`
	ContentRoot   string  `json:"content_root"`
	Batches       []Batch `json:"batches"`
}

type BuildResult struct {
	Manifest   Manifest
	ReportRows []report.Row
	InputRows  []string
}
