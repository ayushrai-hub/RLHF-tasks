package realm

import "strings"

// localeFold trims and lowercases host tokens for UI display only.
func localeFold(v string) string {
	return strings.ToLower(strings.TrimSpace(v))
}
