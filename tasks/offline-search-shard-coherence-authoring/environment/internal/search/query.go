package search

import (
	"strings"
	"unicode"
)

type QuerySpec struct {
	Terms   []string
	Phrases []string
}

// ParseQuery prepares a query for scoring.
func ParseQuery(text string) QuerySpec {
	lower := strings.ToLower(text)
	terms := strings.FieldsFunc(lower, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
	seen := map[string]bool{}
	unique := make([]string, 0, len(terms))
	for _, t := range terms {
		if t == "" || seen[t] {
			continue
		}
		seen[t] = true
		unique = append(unique, t)
	}
	return QuerySpec{Terms: unique}
}

func tokens(text string) []string {
	lower := strings.ToLower(text)
	return strings.FieldsFunc(lower, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
}

func countTerm(xs []string, term string) int {
	n := 0
	for _, x := range xs {
		if x == term {
			n++
		}
	}
	return n
}

func countPhrase(text, phrase string) int {
	hay := strings.ToLower(text)
	needle := strings.ToLower(phrase)
	if strings.TrimSpace(needle) == "" {
		return 0
	}
	count := 0
	for {
		idx := strings.Index(hay, needle)
		if idx < 0 {
			break
		}
		count++
		hay = hay[idx+len(needle):]
	}
	return count
}
