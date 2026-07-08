package weave

import "strings"

func ResolvePointers(sv1Fields []string, inherited []string, compSep byte) []string {
	if len(sv1Fields) > 7 && sv1Fields[7] != "" {
		sep := string([]byte{compSep})
		parts := strings.Split(sv1Fields[7], sep)
		out := make([]string, 0, len(parts))
		for _, part := range parts {
			if part != "" {
				out = append(out, part)
			}
		}
		if len(out) > 0 {
			return out
		}
	}
	if len(inherited) == 0 {
		return []string{}
	}
	return append([]string(nil), inherited...)
}

func UpdateInherited(hiCodes []string) []string {
	if len(hiCodes) == 0 {
		return nil
	}
	out := make([]string, len(hiCodes))
	for i := range hiCodes {
		out[i] = itoa(i + 1)
	}
	return out
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	digits := []byte{}
	for n > 0 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
		n /= 10
	}
	return string(digits)
}
