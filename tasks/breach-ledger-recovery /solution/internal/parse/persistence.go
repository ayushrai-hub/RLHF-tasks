package parse

import (
	"path/filepath"
	"sort"
	"strings"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

func unitE(dir string, ev *model.Evidence, _ *[]model.Issue) {
	unitEFamily(filepath.Join(dir, "cron.d"), "cron", ev)
	unitEFamily(filepath.Join(dir, "systemd"), "systemd", ev)
	unitEFamily(filepath.Join(dir, "shell"), "shell", ev)
}

func unitEFamily(dir string, kind string, ev *model.Evidence) {
	files, _ := filepath.Glob(filepath.Join(dir, "*"))
	sort.Strings(files)
	for _, file := range files {
		lines, err := readLines(file)
		if err != nil || len(lines) == 0 {
			continue
		}
		meta := map[string]string{}
		if strings.HasPrefix(lines[0], "#") {
			meta = p1(strings.TrimPrefix(lines[0], "#"))
		}
		host := normalize.NT3(meta["host"])
		user := normalize.NT2(meta["user"])
		name := filepath.Base(file)
		var ident string
		switch kind {
		case "cron":
			ident = "cron:" + host + ":/etc/cron.d/" + name
		case "systemd":
			ident = "systemd:" + host + ":" + name
		default:
			path := meta["path"]
			if path == "" {
				path = name
			}
			ident = "shell:" + user + ":" + path
		}
		attacker := pA0(host, user, ident+" "+strings.Join(lines, " "))
		addString(&ev.Persistence, ident)
		ev.Summary["persistence_entries"]++
		addEvent(ev, model.Event{Seq: 6000 + int64(ev.Summary["persistence_entries"]), TS: "", Host: host, User: user, Source: "persistence", Action: kind, Detail: ident, AttackerID: attacker})
	}
}
