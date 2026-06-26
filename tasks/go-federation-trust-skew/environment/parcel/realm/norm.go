package realm

// SameRealm compares configured and presented realm strings.
func SameRealm(want, got string) bool {
	return localeFold(want) == localeFold(got)
}
