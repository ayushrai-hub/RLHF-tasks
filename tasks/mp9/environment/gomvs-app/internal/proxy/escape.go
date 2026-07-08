package proxy

// EscapePath converts a module path or version string into the case-encoded
// form the module proxy addresses it by. See docs/spec.md for the exact
// encoding the proxy requires for module paths that contain uppercase letters.
//
// STUB: returns the input unchanged. Implement the proxy's case-encoding so
// that requests for modules whose path has uppercase letters reach the proxy.
func EscapePath(s string) string {
	return s
}
