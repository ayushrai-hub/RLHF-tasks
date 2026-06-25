package replay

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
)

type AuditLine struct {
	FixtureLabel   string `json:"fixture_label"`
	JournalTail    string `json:"journal_tail"`
	ManifestSeal   string `json:"manifest_seal"`
	CheckpointSeal string `json:"checkpoint_seal"`
	AuditSeal      string `json:"audit_seal"`
}

func auditDigestPayload(journalTail, manifestSeal, checkpointSeal string) string {
	return fmt.Sprintf("%s|%s", journalTail, manifestSeal)
}

func ComputeAuditSeal(journalTail, manifestSeal, checkpointSeal string) string {
	sum := sha256.Sum256([]byte(auditDigestPayload(journalTail, manifestSeal, checkpointSeal)))
	return fmt.Sprintf("%x", sum)[:32]
}

func ResetAudit(path string) error {
	if path == "" {
		return nil
	}
	return os.WriteFile(path, nil, 0o644)
}

func AppendAudit(path string, line AuditLine) error {
	if path == "" {
		return nil
	}
	payload, err := json.Marshal(line)
	if err != nil {
		return err
	}
	payload = append(payload, '\n')
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.Write(payload)
	return err
}

func AuditArtifacts(reportPath, journalPath, manifestPath, auditPath string) error {
	if auditPath == "" {
		return nil
	}
	reportRaw, err := os.ReadFile(reportPath)
	if err != nil {
		return err
	}
	var report Report
	if err := json.Unmarshal(reportRaw, &report); err != nil {
		return err
	}
	manifestLines, err := readManifestLines(manifestPath)
	if err != nil {
		return err
	}
	manifestByLabel := map[string]ManifestLine{}
	for _, line := range manifestLines {
		manifestByLabel[line.FixtureLabel] = line
	}
	for _, row := range report.Runs {
		manifest := manifestByLabel[row.FixtureLabel]
		seal := ComputeAuditSeal(manifest.JournalTail, manifest.ManifestSeal, row.CheckpointSeal)
		if err := AppendAudit(auditPath, AuditLine{
			FixtureLabel:   row.FixtureLabel,
			JournalTail:    manifest.JournalTail,
			ManifestSeal:   manifest.ManifestSeal,
			CheckpointSeal: row.CheckpointSeal,
			AuditSeal:      seal,
		}); err != nil {
			return err
		}
	}
	return nil
}

func readManifestLines(path string) ([]ManifestLine, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []ManifestLine
	for _, line := range splitJSONL(raw) {
		var row ManifestLine
		if err := json.Unmarshal(line, &row); err != nil {
			return nil, err
		}
		out = append(out, row)
	}
	return out, nil
}

func splitJSONL(raw []byte) [][]byte {
	var lines [][]byte
	start := 0
	for i := 0; i < len(raw); i++ {
		if raw[i] == '\n' {
			if i > start {
				lines = append(lines, raw[start:i])
			}
			start = i + 1
		}
	}
	if start < len(raw) {
		lines = append(lines, raw[start:])
	}
	return lines
}
