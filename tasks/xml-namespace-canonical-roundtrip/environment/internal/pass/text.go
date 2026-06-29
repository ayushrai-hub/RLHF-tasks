package pass

import "strings"

func CleanText(s string) string {
	trimmed := strings.TrimSpace(s)
	if trimmed == "" {
		return ""
	}
	return trimmed
}
