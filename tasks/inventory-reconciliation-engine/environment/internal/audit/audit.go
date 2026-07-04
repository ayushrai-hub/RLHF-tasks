package audit

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"

	"quotaledger/internal/journal"
	"quotaledger/internal/projection"
)

type Trail struct {
	GeneratedFrom    string           `json:"generated_from"`
	BatchCount       int              `json:"batch_count"`
	JournalDigest    string           `json:"journal_digest"`
	ProjectionDigest string           `json:"projection_digest"`
	Batches          []map[string]any `json:"batches"`
	AuditDigest      string           `json:"audit_digest"`
}

func Write(root, outPath string) error {
	m, err := journal.LoadManifest(root)
	if err != nil {
		return err
	}
	snap, err := projection.Load(root)
	if err != nil {
		return err
	}
	jDigest, err := journalDigest(root)
	if err != nil {
		return err
	}
	batches := make([]map[string]any, 0, len(m.Batches))
	for _, b := range m.Batches {
		batches = append(batches, map[string]any{
			"name":          b.Name,
			"event_count":   b.EventCount,
			"durable_bytes": b.DurableBytes,
		})
	}
	trail := &Trail{
		GeneratedFrom:    "quota-audit-v1",
		BatchCount:       len(m.Batches),
		JournalDigest:    jDigest,
		ProjectionDigest: snap.SnapshotDigest,
		Batches:          batches,
	}
	body, _ := json.Marshal(map[string]any{
		"generated_from":    trail.GeneratedFrom,
		"batch_count":       trail.BatchCount,
		"journal_digest":    trail.JournalDigest,
		"projection_digest": trail.ProjectionDigest,
		"batches":           trail.Batches,
	})
	sum := sha256.Sum256(body)
	trail.AuditDigest = hex.EncodeToString(sum[:])
	data, err := json.MarshalIndent(trail, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		return err
	}
	return os.WriteFile(outPath, data, 0o644)
}

func journalDigest(root string) (string, error) {
	lines, _, _, err := journal.ReadAllEvents(root)
	if err != nil {
		return "", err
	}
	h := sha256.New()
	for _, line := range lines {
		h.Write(line)
		h.Write([]byte{'\n'})
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
