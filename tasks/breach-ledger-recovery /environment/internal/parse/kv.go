package parse

import "strings"

func p1(line string) map[string]string {
	out := map[string]string{}
	for _, part := range strings.Fields(line) {
		k, v, ok := strings.Cut(part, "=")
		if ok {
			out[k] = v
		}
	}
	return out
}
