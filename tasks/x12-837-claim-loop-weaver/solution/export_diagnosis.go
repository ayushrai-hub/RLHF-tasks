package export

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
