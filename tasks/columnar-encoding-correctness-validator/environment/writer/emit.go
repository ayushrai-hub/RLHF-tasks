package writer

import (
	"bytes"
	"encoding/json"
	"os"
	"sort"

	"columnarvalidator/codec/types"
)

func Write(path string, rpt types.Report) error {
	rpt = normalizeReport(rpt)
	payload, err := marshalOrdered(rpt)
	if err != nil {
		return err
	}
	if err := os.MkdirAll("/app/output", 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, payload, 0o644)
}

func normalizeReport(rpt types.Report) types.Report {
	if rpt.Segments == nil {
		rpt.Segments = make([]types.SegmentResult, 0)
	}
	if rpt.Summary.FaultCodeTotals == nil {
		rpt.Summary.FaultCodeTotals = make(map[string]int)
	}
	for i := range rpt.Segments {
		if rpt.Segments[i].FaultCodes == nil {
			rpt.Segments[i].FaultCodes = make([]string, 0)
		}
	}
	return rpt
}

func marshalOrdered(rpt types.Report) ([]byte, error) {
	var buf bytes.Buffer
	buf.WriteString("{\n  \"summary\": ")
	sumBytes, err := json.Marshal(rpt.Summary)
	if err != nil {
		return nil, err
	}
	buf.Write(sumBytes)
	buf.WriteString(",\n  \"segments\": [\n")
	for i, seg := range rpt.Segments {
		if i > 0 {
			buf.WriteString(",\n")
		}
		segBytes, err := json.Marshal(seg)
		if err != nil {
			return nil, err
		}
		buf.WriteString("    ")
		buf.Write(segBytes)
	}
	buf.WriteString("\n  ]\n}\n")

	// Re-marshal summary fault_code_totals with sorted keys by rebuilding summary JSON manually
	keys := make([]string, 0, len(rpt.Summary.FaultCodeTotals))
	for k := range rpt.Summary.FaultCodeTotals {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var sumBuf bytes.Buffer
	sumBuf.WriteString("{\n    \"segments_analyzed\": ")
	sumBuf.WriteString(intStr(rpt.Summary.SegmentsAnalyzed))
	sumBuf.WriteString(",\n    \"segments_passing\": ")
	sumBuf.WriteString(intStr(rpt.Summary.SegmentsPassing))
	sumBuf.WriteString(",\n    \"segments_failing\": ")
	sumBuf.WriteString(intStr(rpt.Summary.SegmentsFailing))
	sumBuf.WriteString(",\n    \"fault_code_totals\": {")
	for i, k := range keys {
		if i > 0 {
			sumBuf.WriteString(", ")
		}
		kb, _ := json.Marshal(k)
		sumBuf.Write(kb)
		sumBuf.WriteString(": ")
		sumBuf.WriteString(intStr(rpt.Summary.FaultCodeTotals[k]))
	}
	sumBuf.WriteString("}\n  }")

	out := bytes.Replace(buf.Bytes(), sumBytes, sumBuf.Bytes(), 1)
	return out, nil
}

func intStr(n int) string {
	b, _ := json.Marshal(n)
	return string(b)
}
