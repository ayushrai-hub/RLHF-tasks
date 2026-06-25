package reporter

import (
	"fmt"
	"strings"

	"sliding-window-limiter/internal/ratelimit"
)

func FormatText(r ratelimit.AnalysisResult) string {
	var b strings.Builder
	b.WriteString("Sliding Window Rate Limiter Report\n")
	b.WriteString("===================================\n\n")
	b.WriteString(fmt.Sprintf("Total requests: %d\n", r.TotalRequests))
	b.WriteString(fmt.Sprintf("Allowed: %d\n", r.AllowedCount))
	b.WriteString(fmt.Sprintf("Denied: %d\n", r.DeniedCount))
	b.WriteString(fmt.Sprintf("Deny rate: %.4f\n", r.OverallDenyRate))
	b.WriteString(fmt.Sprintf("Window violations: %d\n", r.WindowViolations))
	b.WriteString(fmt.Sprintf("Burst events: %d\n\n", len(r.BurstEvents)))
	b.WriteString("--- Client Stats ---\n")
	for _, cs := range r.ClientStats {
		b.WriteString(fmt.Sprintf("  %s: total=%d allowed=%d denied=%d rate=%.4f\n",
			cs.ClientID, cs.Total, cs.Allowed, cs.Denied, cs.DenyRate))
	}
	return b.String()
}
