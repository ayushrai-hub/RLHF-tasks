package projection

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"time"

	"quotaledger/internal/checkpoint"
	"quotaledger/internal/domain"
	"quotaledger/internal/journal"
	"quotaledger/internal/legacy"
	"quotaledger/internal/quota"
)

type Snapshot struct {
	GeneratedFrom          string           `json:"generated_from"`
	EventLineCount         int              `json:"event_line_count"`
	ParsedCount            int              `json:"parsed_count"`
	MalformedLineCount     int              `json:"malformed_line_count"`
	ProcessedCount         int              `json:"processed_count"`
	AppliedCount           int              `json:"applied_count"`
	RejectedCount          int              `json:"rejected_count"`
	SkippedIdempotentCount int              `json:"skipped_idempotent_count"`
	Rejections             []map[string]any `json:"rejections"`
	Accounts               []map[string]any `json:"accounts"`
	SnapshotDigest         string           `json:"snapshot_digest"`
}

func Rebuild(root string) (*Snapshot, error) {
	lines, lineCount, malformed, err := journal.ReadAllEvents(root)
	if err != nil {
		return nil, err
	}
	engine := quota.NewEngine()
	engine.EventLineCount = lineCount
	engine.ParsedCount = len(lines)
	engine.MalformedLineCount = malformed

	cp, err := checkpoint.Load(root)
	if err != nil {
		return nil, err
	}
	if err := legacy.ApplyIfNeeded(root, engine, &cp.MigratedLegacy); err != nil {
		return nil, err
	}

	engine.ProcessLines(lines)
	engine.ApplyExpirations(time.Now().UTC())

	rejections := make([]map[string]any, 0, len(engine.Rejections))
	for _, r := range engine.Rejections {
		rejections = append(rejections, map[string]any{
			"event_id":      r.EventID,
			"account_id":    r.AccountID,
			"reason":        r.Reason,
			"priority_rank": r.PriorityRank,
		})
	}
	sort.Slice(rejections, func(i, j int) bool {
		a, b := rejections[i], rejections[j]
		if a["priority_rank"].(int) != b["priority_rank"].(int) {
			return a["priority_rank"].(int) < b["priority_rank"].(int)
		}
		return a["event_id"].(string) < b["event_id"].(string)
	})

	snap := &Snapshot{
		GeneratedFrom:          domain.GeneratedFrom,
		EventLineCount:         lineCount,
		ParsedCount:            len(lines),
		MalformedLineCount:     malformed,
		ProcessedCount:         engine.AppliedCount + engine.RejectedCount,
		AppliedCount:           engine.AppliedCount,
		RejectedCount:          engine.RejectedCount,
		SkippedIdempotentCount: engine.SkippedIdempotent,
		Rejections:             rejections,
		Accounts:               engine.AccountRows(),
	}
	body, err := json.Marshal(canonicalBody(snap))
	if err != nil {
		return nil, err
	}
	sum := sha256.Sum256(body)
	snap.SnapshotDigest = hex.EncodeToString(sum[:])

	cp.JournalSeq = len(lines)
	cp.ProjectionDigest = snap.SnapshotDigest
	cp.RebuildAt = time.Now().UTC().Format("2006-01-02T15:04:05Z")
	if err := checkpoint.Save(root, cp); err != nil {
		return nil, err
	}
	if err := saveProjection(root, snap); err != nil {
		return nil, err
	}
	return snap, nil
}

func canonicalBody(snap *Snapshot) map[string]any {
	return map[string]any{
		"generated_from":           snap.GeneratedFrom,
		"event_line_count":         snap.EventLineCount,
		"parsed_count":             snap.ParsedCount,
		"malformed_line_count":     snap.MalformedLineCount,
		"processed_count":          snap.ProcessedCount,
		"applied_count":            snap.AppliedCount,
		"rejected_count":           snap.RejectedCount,
		"skipped_idempotent_count": snap.SkippedIdempotentCount,
		"rejections":               snap.Rejections,
		"accounts":                 snap.Accounts,
	}
}

func saveProjection(root string, snap *Snapshot) error {
	path := filepath.Join(root, "state", "projection.json")
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

func Load(root string) (*Snapshot, error) {
	path := filepath.Join(root, "state", "projection.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var snap Snapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return nil, err
	}
	return &snap, nil
}

func WriteReport(root, outPath string) error {
	snap, err := Load(root)
	if err != nil {
		snap, err = Rebuild(root)
		if err != nil {
			return err
		}
	}
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		return err
	}
	return os.WriteFile(outPath, data, 0o644)
}
