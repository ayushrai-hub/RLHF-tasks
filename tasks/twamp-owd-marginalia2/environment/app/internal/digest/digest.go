package digest

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"
	"strings"

	"twampowd/internal/types"
)

// Seal8 derives the marker reconciliation seal from a pipe-joined
// identifier string keyed by the run secret.
func Seal8(markerID, kind string, cycleID int64, reflectorID, secret string) string {
	s := fmt.Sprintf("%s|%s|%d|%s|%s", markerID, kind, cycleID, reflectorID, secret)
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])[:16]
}

// Report computes the self-binding report digest from the canonical
// pipe-joined frame ledger, reflector ledger, and summary tail.
func Report(rep types.Report) string {
	probeLines := make([]string, 0, len(rep.Probes))
	for _, p := range rep.Probes {
		probeLines = append(probeLines, fmt.Sprintf("%s|%s|%s|%d", p.ProbeID, p.ReflectorID, p.Verdict, p.OwdUs))
	}
	keys := make([]string, 0, len(rep.Summary.JitterSharePermille))
	for k := range rep.Summary.JitterSharePermille {
		keys = append(keys, k)
	}
	sort.SliceStable(keys, func(i, j int) bool { return types.SuffixLess(keys[i], keys[j]) })
	shareParts := make([]string, 0, len(keys))
	for _, k := range keys {
		shareParts = append(shareParts, fmt.Sprintf("%s=%d", k, rep.Summary.JitterSharePermille[k]))
	}
	var b strings.Builder
	b.WriteString(strings.Join(probeLines, "\n"))
	b.WriteString("\n--\n")
	b.WriteString(strings.Join(shareParts, "|"))
	b.WriteString("\n--\n")
	b.WriteString(fmt.Sprintf("summary:total=%d;good=%d;cycles=%d\n",
		rep.Summary.TotalProbes, rep.Summary.AlignedGood, rep.Summary.Cycles))
	sum := sha256.Sum256([]byte(b.String()))
	return hex.EncodeToString(sum[:])
}
