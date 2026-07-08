package export

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

	"gradlab/internal/paths"
)

func sha256Text(text string) string {
	sum := sha256.Sum256([]byte(text))
	return hex.EncodeToString(sum[:])
}

func trialLine(t map[string]any) string {
	return fmt.Sprintf("%s:%s:%v:%v", t["graph"], t["pass"], t["loss"], strings.ToLower(fmt.Sprintf("%v", t["grad_ok"])))
}

func journalLine(row map[string]any) string {
	obj := map[string]any{
		"epoch": row["epoch"], "graph": row["graph"], "grad_ok": row["grad_ok"],
		"loss": row["loss"], "pass": row["pass"], "pool_checksum": row["pool_checksum"],
	}
	b, _ := json.Marshal(obj)
	return string(b)
}

func Emit(cfg map[string]any, trials []map[string]any, journal []map[string]any, pool map[string]any) map[string]any {
	_ = os.MkdirAll(paths.OutputDir, 0o755)
	allOK := true
	fdMax := 0.0
	for _, t := range trials {
		if !t["grad_ok"].(bool) {
			allOK = false
		}
		if v, ok := t["fd_max"].(float64); ok && v > fdMax {
			fdMax = v
		}
	}
	var reportLines []string
	for _, t := range trials {
		reportLines = append(reportLines, trialLine(t))
	}
	var journalLines []string
	for _, row := range journal {
		journalLines = append(journalLines, journalLine(row))
	}
	sort.Strings(journalLines)
	report := map[string]any{
		"lab_version": cfg["lab_version"], "trials": trials,
		"report_digest_hex":  sha256Text(strings.Join(reportLines, "\n")),
		"journal_digest_hex": sha256Text(strings.Join(journalLines, "\n")),
		"grad_ok":            allOK, "fd_max": fdMax, "run_fingerprint": "",
	}
	var fpLines []string
	for _, t := range trials {
		fpLines = append(fpLines, fmt.Sprintf("%s:%v:%v:%.6f", t["graph"], t["loss"], strings.ToLower(fmt.Sprintf("%v", t["grad_ok"])), t["fd_max"]))
	}
	report["run_fingerprint"] = sha256Text(strings.Join(fpLines, "\n"))
	b, _ := json.MarshalIndent(report, "", "  ")
	_ = os.WriteFile(paths.ReportPath, append(b, '\n'), 0o644)

	csv := "graph,node_id,op,forward_6,backward_6\n"
	for _, t := range trials {
		rows, _ := t["trace_rows"].([]map[string]any)
		for _, row := range rows {
			csv += fmt.Sprintf("%s,%s,%s,%s,%s\n", t["graph"], row["node_id"], row["op"], row["forward_6"], row["backward_6"])
		}
	}
	_ = os.WriteFile(paths.CSVPath, []byte(csv), 0o644)
	var jl strings.Builder
	for _, row := range journal {
		jl.WriteString(journalLine(row))
		jl.WriteByte('\n')
	}
	_ = os.WriteFile(paths.JournalPath, []byte(jl.String()), 0o644)
	pb, _ := json.MarshalIndent(pool, "", "  ")
	_ = os.WriteFile(paths.PoolPath, append(pb, '\n'), 0o644)
	return report
}
