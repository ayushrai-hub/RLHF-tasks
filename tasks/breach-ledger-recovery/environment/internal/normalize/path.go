package normalize

import "path/filepath"

func NP1(p string) bool {
	return filepath.IsAbs(p)
}

func NP2(name string) bool {
	return name != ""
}
