package report

import (
	"fmt"
	"io"
)

// Print writes a one-line human-facing summary to w.
func Print(w io.Writer, s Summary) {
	inGroup := 0.0
	if s.TotalCents > 0 {
		inGroup = 100.0 * float64(s.InGroupCents) / float64(s.TotalCents)
	}
	fmt.Fprintf(w, "settled %d participants with %d transfers (%.0f%% of cents stay in-group)\n",
		s.Participants, s.Transfers, inGroup)
}
