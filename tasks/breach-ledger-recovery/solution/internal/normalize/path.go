package normalize

import (
	"path"
	"strings"
)

func NP1(p string) bool {
	if p == "" || strings.Contains(p, "\x00") || !path.IsAbs(p) {
		return false
	}
	clean := path.Clean(p)
	if clean != p || clean == "/" || strings.Contains(clean, "/../") {
		return false
	}
	return true
}

func NP2(name string) bool {
	if name == "" || strings.Contains(name, "\x00") {
		return false
	}
	name = strings.ReplaceAll(name, "\\", "/")
	if path.IsAbs(name) {
		return false
	}
	clean := path.Clean(name)
	if clean == "." || clean != name || strings.HasPrefix(clean, "../") || clean == ".." {
		return false
	}
	return true
}
