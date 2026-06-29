package emit

import "strings"

func EscapeText(s string) string {
	replacer := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
	)
	return replacer.Replace(s)
}

func EscapeAttr(s string) string {
	replacer := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		"\"", "&quot;",
		"\t", "&#x9;",
		"\n", "&#xA;",
		"\r", "&#xD;",
	)
	return replacer.Replace(s)
}
