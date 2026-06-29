package epoch

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const flagRoot = "/app/environment/config/failback_flags"

// FlushBumpDefault loads completion depth metadata from registered flag fragments.
func FlushBumpDefault() int {
	entries, err := os.ReadDir(flagRoot)
	if err != nil {
		return 0
	}
	best := 0
	bestOrder := -1
	for _, ent := range entries {
		if !strings.HasSuffix(ent.Name(), ".toml") {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(flagRoot, ent.Name()))
		if err != nil {
			continue
		}
		order := 0
		depth := 0
		for _, line := range strings.Split(string(raw), "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "registration_order") {
				parts := strings.SplitN(line, "=", 2)
				if len(parts) == 2 {
					if v, err := strconv.Atoi(strings.TrimSpace(parts[1])); err == nil {
						order = v
					}
				}
			}
			if strings.HasPrefix(line, "completion_depth") {
				parts := strings.SplitN(line, "=", 2)
				if len(parts) == 2 {
					if v, err := strconv.Atoi(strings.TrimSpace(parts[1])); err == nil {
						depth = v
					}
				}
			}
		}
		if bestOrder == -1 || order < bestOrder {
			bestOrder = order
			best = depth
		}
	}
	return best
}
