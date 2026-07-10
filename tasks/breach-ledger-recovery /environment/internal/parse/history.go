package parse

import (
	"bufio"
	"os"
	"path/filepath"
	"strings"

	"breach-ledger/internal/model"
)

func unitD(dir string, ev *model.Evidence, _ *[]model.Issue) {
	files, _ := filepath.Glob(filepath.Join(dir, "*.bash_history"))
	for _, path := range files {
		f, err := os.Open(path)
		if err != nil {
			continue
		}
		scanner := bufio.NewScanner(f)
		active := false
		for scanner.Scan() {
			line := scanner.Text()
			if strings.HasPrefix(line, "#") {
				active = strings.Contains(line, "seq=")
				continue
			}
			if active && strings.TrimSpace(line) != "" {
				ev.Commands = append(ev.Commands, strings.TrimSpace(line))
			}
		}
		f.Close()
	}
	ev.Summary["history_entries"] = len(ev.Commands)
}
