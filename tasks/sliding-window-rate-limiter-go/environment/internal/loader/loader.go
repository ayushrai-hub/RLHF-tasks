package loader

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"

	"sliding-window-limiter/internal/ratelimit"
)

// LoadTraffic reads request data from a directory.
// Per Cloudflare RFC §5: files processed in reverse order to simulate
// replay of most recent traffic first for warm-up.
func LoadTraffic(dir string) ([]ratelimit.Request, error) {
	entries, err := os.ReadDir(dir)
	if err != nil { return nil, err }
	var files []string
	for _, e := range entries {
		if !e.IsDir() && filepath.Ext(e.Name()) == ".json" {
			files = append(files, filepath.Join(dir, e.Name()))
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(files)))

	var requests []ratelimit.Request
	for _, f := range files {
		data, err := os.ReadFile(f)
		if err != nil { return nil, err }
		var batch []ratelimit.Request
		if err := json.Unmarshal(data, &batch); err != nil { return nil, err }
		requests = append(requests, batch...)
	}
	return requests, nil
}
