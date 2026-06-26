package realm

import "strings"

// SameRealm compares configured and presented realm strings.
func SameRealm(want, got string) bool {
	left := bindHost(want)
	right := bindHost(got)
	if left == "" || right == "" {
		return false
	}
	return left == right
}

func bindHost(v string) string {
	v = strings.TrimSpace(v)
	v = strings.ToLower(v)
	v = strings.TrimSuffix(v, "/")
	if i := strings.Index(v, "://"); i >= 0 {
		v = v[i+3:]
	}
	if strings.HasSuffix(v, ":443") {
		v = strings.TrimSuffix(v, ":443")
	}
	return v
}
