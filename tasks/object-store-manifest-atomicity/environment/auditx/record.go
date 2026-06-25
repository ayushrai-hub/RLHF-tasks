package auditx

import (
	"encoding/json"
	"time"

	"terminal.local/objectmanifest/internal/hashutil"
	"terminal.local/objectmanifest/packset"
)

type Record struct {
	SchemaVersion        int    `json:"schema_version"`
	GeneratedBy          string `json:"generated_by"`
	InputDigest          string `json:"input_digest"`
	ManifestSHA256       string `json:"manifest_sha256"`
	ChecksumReportSHA256 string `json:"checksum_report_sha256"`
	CommitCount          int    `json:"commit_count"`
	ObjectCount          int    `json:"object_count"`
	ContentRoot          string `json:"content_root"`
	GeneratedAt          string `json:"generated_at"`
}

func RecordFromOutputs(result packset.BuildResult, manifestBytes []byte, reportBytes []byte) Record {
	return Record{
		SchemaVersion:        1,
		GeneratedBy:          "ostore-manifest-v1",
		InputDigest:          InputDigest(result.InputRows),
		ManifestSHA256:       hashutil.SHA256Hex(manifestBytes),
		ChecksumReportSHA256: hashutil.SHA256Hex(reportBytes),
		CommitCount:          result.Manifest.CommitCount,
		ObjectCount:          result.Manifest.ObjectCount,
		ContentRoot:          result.Manifest.ContentRoot,
		GeneratedAt:          time.Now().UTC().Format(time.RFC3339Nano),
	}
}

func Render(r Record) ([]byte, error) {
	raw, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(raw, '\n'), nil
}
