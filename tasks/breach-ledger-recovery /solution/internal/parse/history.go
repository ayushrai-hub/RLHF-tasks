package parse

import (
	"path/filepath"
	"sort"
	"strings"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

func unitD(dir string, ev *model.Evidence, _ *[]model.Issue) {
	files, _ := filepath.Glob(filepath.Join(dir, "*.bash_history"))
	sort.Strings(files)
	for _, file := range files {
		lines, err := readLines(file)
		if err != nil {
			continue
		}
		meta := map[string]string{}
		for _, line := range lines {
			if strings.HasPrefix(line, "#") {
				meta = p1(strings.TrimPrefix(line, "#"))
				continue
			}
			cmd := normalize.NT1(line)
			if cmd == "" {
				continue
			}
			ev.Summary["history_entries"]++
			host := normalize.NT3(meta["host"])
			user := normalize.NT2(meta["user"])
			attacker := pA0(host, user, cmd)
			if attacker == "" {
				continue
			}
			addEvent(ev, model.Event{
				Seq:        parseInt64(meta["seq"]),
				TS:         meta["ts"],
				Host:       host,
				User:       user,
				Source:     "history",
				Action:     "shell",
				Detail:     cmd,
				AttackerID: attacker,
			})
		}
	}
}
