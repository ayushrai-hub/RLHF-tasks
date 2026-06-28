package run

import "path/filepath"

const (
	CanonicalName   = "canonical.xml"
	ScopeName       = "scope.json"
	AuditName       = "audit.jsonl"
	InputMarkerName = ".nsx-input"
	BatchLedgerName = "batch.jsonl"
)

func CanonicalPath(out string) string   { return filepath.Join(out, CanonicalName) }
func ScopePath(out string) string       { return filepath.Join(out, ScopeName) }
func AuditPath(out string) string       { return filepath.Join(out, AuditName) }
func InputMarkerPath(out string) string { return filepath.Join(out, InputMarkerName) }
func BatchLedgerPath(out string) string { return filepath.Join(out, BatchLedgerName) }
