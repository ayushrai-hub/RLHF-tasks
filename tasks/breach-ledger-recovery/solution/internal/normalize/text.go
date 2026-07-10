package normalize

import (
	"strings"
	"unicode"
)

func r0(s string) string {
	return strings.Map(func(r rune) rune {
		switch r {
		case '\x00', '\u200b', '\u200c', '\u200d', '\ufeff':
			return -1
		}
		if unicode.IsControl(r) && r != '\t' && r != '\n' && r != '\r' {
			return -1
		}
		return r
	}, s)
}

func NT2(s string) string {
	return strings.ToLower(strings.TrimSpace(r0(s)))
}

func NT3(s string) string {
	return strings.ToLower(strings.TrimSpace(r0(s)))
}

func NT1(s string) string {
	return strings.TrimSpace(r0(strings.ReplaceAll(s, "\r\n", "\n")))
}
