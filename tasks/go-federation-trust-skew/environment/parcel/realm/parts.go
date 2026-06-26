package realm

import "strings"

func stripScheme(v string) string {
	if i := strings.Index(v, "://"); i >= 0 {
		return v[i+3:]
	}
	return v
}

func stripSlash(v string) string {
	return strings.TrimSuffix(v, "/")
}

func stripPort(v string) string {
	if strings.HasSuffix(v, ":443") {
		return strings.TrimSuffix(v, ":443")
	}
	return v
}
