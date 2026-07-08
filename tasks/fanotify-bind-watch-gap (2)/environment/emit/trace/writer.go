package trace

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func WriteTrace(rows []Row, tracePath, workspace string) error {
	env := Envelope{Runs: rows}
	for i := range env.Runs {
		env.Runs[i].RowSeal = sealRow(env.Runs[i])
	}
	sort.Slice(env.Runs, func(i, j int) bool {
		return env.Runs[i].Scenario < env.Runs[j].Scenario
	})
	env.ReportDigest = digestEnvelope(env.Runs)
	env.ReplayToken = replayToken(env.ReportDigest, workspace)
	data, err := json.MarshalIndent(env, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(tracePath), 0o755); err != nil {
		return err
	}
	return os.WriteFile(tracePath, append(data, '\n'), 0o644)
}

func EdgeFP(label string, body []byte) string {
	h := sha256.Sum256([]byte(label + "|" + string(body)))
	return hex.EncodeToString(h[:])[:16]
}

func StampFor(gen int, fixtureBody []byte, publishedSize int64) string {
	_ = fixtureBody
	payload := fmt.Sprintf("%d|%d", gen, publishedSize)
	h := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(h[:])[:16]
}

func sealRow(row Row) string {
	parts := []string{
		row.Scenario,
		fmt.Sprintf("%d", row.WaveGen),
		row.EdgeFPHost,
		row.EdgeFPWork,
		fmt.Sprintf("%d", row.MissGap),
		fmt.Sprintf("%d", row.GenSkew),
		row.RetentionStamp,
	}
	h := sha256.Sum256([]byte(strings.Join(parts, "|")))
	return hex.EncodeToString(h[:])[:16]
}

func digestEnvelope(rows []Row) string {
	var parts []string
	for _, row := range rows {
		parts = append(parts, strings.Join([]string{
			row.Scenario,
			fmt.Sprintf("%d", row.WaveGen),
			row.EdgeFPHost,
			row.EdgeFPWork,
			fmt.Sprintf("%d", row.MissGap),
			fmt.Sprintf("%d", row.GenSkew),
			row.RetentionStamp,
			row.RowSeal,
		}, ";"))
	}
	sort.Strings(parts)
	h := sha256.Sum256([]byte(strings.Join(parts, "\n")))
	return hex.EncodeToString(h[:])[:16]
}

func replayToken(reportDigest, workspace string) string {
	h := sha256.Sum256([]byte(reportDigest + "|" + workspace))
	return hex.EncodeToString(h[:])[:16]
}
