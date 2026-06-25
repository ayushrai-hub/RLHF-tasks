package emit

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"twampowd/internal/types"
)

// AllVerdicts is the closed verdict enum emitted in by_verdict, in
// the serialization order required by the schema.
var AllVerdicts = []string{
	"LOSS_DETECTED",
	"OWD_ANOMALY",
	"QUIET_SUPPRESSED",
	"REFLECTOR_OFFLINE",
	"STALE_MEASUREMENT",
	"WITHIN_BOUNDS",
}

// Write clears every direct child entry under the output directory
// (regular files and subdirectories alike) and then writes the report
// so the directory contains exactly the documented file.
func Write(outPath string, rep types.Report) error {
	parent := filepath.Dir(outPath)
	if err := os.MkdirAll(parent, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(parent)
	if err != nil {
		return err
	}
	for _, e := range entries {
		_ = os.RemoveAll(filepath.Join(parent, e.Name()))
	}
	data := render(rep)
	tmp := outPath + ".tmp"
	if err := os.WriteFile(tmp, []byte(data), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, outPath)
}

// render serialises the report into the canonical bytes.
func render(rep types.Report) string {
	var b strings.Builder
	b.WriteString("{\n")
	b.WriteString(fmt.Sprintf("  \"schema_version\": %q,\n", rep.SchemaVersion))
	b.WriteString("  \"summary\": {\n")
	b.WriteString(fmt.Sprintf("    \"total_probes\": %d,\n", rep.Summary.TotalProbes))
	b.WriteString(fmt.Sprintf("    \"aligned_good\": %d,\n", rep.Summary.AlignedGood))
	b.WriteString(fmt.Sprintf("    \"cycles\": %d,\n", rep.Summary.Cycles))
	b.WriteString("    \"by_verdict\": {\n")
	for i, v := range AllVerdicts {
		comma := ","
		if i == len(AllVerdicts)-1 {
			comma = ""
		}
		b.WriteString(fmt.Sprintf("      %q: %d%s\n", v, rep.Summary.ByVerdict[v], comma))
	}
	b.WriteString("    },\n")
	b.WriteString("    \"jitter_share_permille\": {\n")
	shareKeys := make([]string, 0, len(rep.Summary.JitterSharePermille))
	for k := range rep.Summary.JitterSharePermille {
		shareKeys = append(shareKeys, k)
	}
	sort.Strings(shareKeys)
	for i, k := range shareKeys {
		comma := ","
		if i == len(shareKeys)-1 {
			comma = ""
		}
		b.WriteString(fmt.Sprintf("      %q: %d%s\n", k, rep.Summary.JitterSharePermille[k], comma))
	}
	b.WriteString("    },\n")
	b.WriteString(fmt.Sprintf("    \"report_digest\": %q\n", rep.Summary.ReportDigest))
	b.WriteString("  },\n")

	b.WriteString("  \"reflectors\": [")
	if len(rep.Reflectors) == 0 {
		b.WriteString("],\n")
	} else {
		b.WriteString("\n")
		for i, r := range rep.Reflectors {
			b.WriteString("    {\n")
			b.WriteString(fmt.Sprintf("      \"reflector_id\": %q,\n", r.ReflectorID))
			b.WriteString(fmt.Sprintf("      \"station\": %q,\n", r.Station))
			b.WriteString(fmt.Sprintf("      \"class\": %q,\n", r.Class))
			b.WriteString(fmt.Sprintf("      \"probe_count\": %d,\n", r.ProbeCount))
			b.WriteString(fmt.Sprintf("      \"anomaly_count\": %d,\n", r.AnomalyCount))
			b.WriteString(fmt.Sprintf("      \"quiet_period_suppressed\": %d,\n", r.QuietPeriodSuppressed))
			b.WriteString(fmt.Sprintf("      \"offline_observed\": %t,\n", r.OfflineObserved))
			b.WriteString(fmt.Sprintf("      \"jitter_share_permille\": %d\n", r.JitterSharePermille))
			comma := ","
			if i == len(rep.Reflectors)-1 {
				comma = ""
			}
			b.WriteString(fmt.Sprintf("    }%s\n", comma))
		}
		b.WriteString("  ],\n")
	}

	b.WriteString("  \"cycles\": [")
	if len(rep.Cycles) == 0 {
		b.WriteString("],\n")
	} else {
		b.WriteString("\n")
		for i, c := range rep.Cycles {
			b.WriteString("    {\n")
			b.WriteString(fmt.Sprintf("      \"cycle_id\": %d,\n", c.CycleID))
			b.WriteString(fmt.Sprintf("      \"probe_count\": %d,\n", c.ProbeCount))
			b.WriteString(fmt.Sprintf("      \"loss_count\": %d,\n", c.LossCount))
			b.WriteString(fmt.Sprintf("      \"anomaly_count\": %d,\n", c.AnomalyCount))
			b.WriteString(fmt.Sprintf("      \"threshold_owd_us\": %d,\n", c.ThresholdOwdUs))
			b.WriteString("      \"contributors\": [")
			for j, name := range c.Contributors {
				sep := ", "
				if j == 0 {
					sep = ""
				}
				b.WriteString(fmt.Sprintf("%s%q", sep, name))
			}
			b.WriteString("]\n")
			comma := ","
			if i == len(rep.Cycles)-1 {
				comma = ""
			}
			b.WriteString(fmt.Sprintf("    }%s\n", comma))
		}
		b.WriteString("  ],\n")
	}

	b.WriteString("  \"probes\": [")
	if len(rep.Probes) == 0 {
		b.WriteString("],\n")
	} else {
		b.WriteString("\n")
		for i, p := range rep.Probes {
			b.WriteString("    {\n")
			b.WriteString(fmt.Sprintf("      \"probe_id\": %q,\n", p.ProbeID))
			b.WriteString(fmt.Sprintf("      \"session_id\": %q,\n", p.SessionID))
			b.WriteString(fmt.Sprintf("      \"cycle_id\": %d,\n", p.CycleID))
			b.WriteString(fmt.Sprintf("      \"reflector_id\": %q,\n", p.ReflectorID))
			b.WriteString(fmt.Sprintf("      \"owd_us\": %d,\n", p.OwdUs))
			b.WriteString(fmt.Sprintf("      \"verdict\": %q\n", p.Verdict))
			comma := ","
			if i == len(rep.Probes)-1 {
				comma = ""
			}
			b.WriteString(fmt.Sprintf("    }%s\n", comma))
		}
		b.WriteString("  ],\n")
	}

	b.WriteString(fmt.Sprintf("  \"report_digest\": %q\n", rep.ReportDigest))
	b.WriteString("}\n")
	return b.String()
}
