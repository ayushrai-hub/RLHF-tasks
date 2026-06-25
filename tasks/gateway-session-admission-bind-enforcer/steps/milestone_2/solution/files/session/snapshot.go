package session

import (
	"encoding/json"
	"os"
	"path/filepath"
)

const admissionSnapshotSchema = 1

const AdmissionSnapshotName = "admission-snapshot.json"

type AdmissionSnapshot struct {
	SchemaVersion      int            `json:"schema_version"`
	RunID              string         `json:"run_id"`
	Accepted           bool           `json:"accepted"`
	SelectedBackend    string         `json:"selected_backend"`
	TokensLeft         int            `json:"tokens_left"`
	ConfigGen          int            `json:"config_gen"`
	ScopeGen           int            `json:"scope_gen"`
	RouteCounter       int            `json:"route_counter"`
	Seq                int            `json:"seq"`
	DigestPendingCount int            `json:"digest_pending_count"`
	BucketTokens       map[string]int `json:"bucket_tokens"`
}

func snapshotPath(dir string) string {
	return filepath.Join(dir, AdmissionSnapshotName)
}

func WriteAdmissionSnapshot(dir string, snap AdmissionSnapshot) error {
	snap.SchemaVersion = admissionSnapshotSchema
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(snapshotPath(dir), data, 0o644)
}

func ReadAdmissionSnapshot(dir string) (AdmissionSnapshot, error) {
	data, err := os.ReadFile(snapshotPath(dir))
	if err != nil {
		return AdmissionSnapshot{}, err
	}
	var snap AdmissionSnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return AdmissionSnapshot{}, err
	}
	return snap, nil
}
