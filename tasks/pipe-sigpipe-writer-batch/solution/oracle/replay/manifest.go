package replay

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
)

type ManifestLine struct {
	FixtureLabel string `json:"fixture_label"`
	JournalTail  string `json:"journal_tail"`
	TraceLines   int    `json:"trace_lines"`
	WaveSlices   int    `json:"wave_slices"`
	ManifestSeal string `json:"manifest_seal"`
}

func manifestDigestPayload(journalTail string, traceLines, waveSlices, observed int) string {
	return fmt.Sprintf("%s|%d|%d|%d", journalTail, traceLines, waveSlices, observed)
}

func ComputeManifestSeal(journalTail string, traceLines, waveSlices, observed int) string {
	sum := sha256.Sum256([]byte(manifestDigestPayload(journalTail, traceLines, waveSlices, observed)))
	return fmt.Sprintf("%x", sum)[:32]
}

func AppendManifest(path string, line ManifestLine) error {
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

func ResetManifest(path string) error {
	if path == "" {
		return nil
	}
	return os.WriteFile(path, nil, 0o644)
}
