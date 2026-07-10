package parse

import (
	"bufio"
	"os"
	"path/filepath"

	"breach-ledger/internal/model"
)

func unitB(dir string, ev *model.Evidence, _ *[]model.Issue) {
	f, err := os.Open(filepath.Join(dir, "auth.log"))
	if err != nil {
		return
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		m := p1(scanner.Text())
		if m["event"] == "accepted" && m["method"] == "password" {
			ev.InitialAccess = append(ev.InitialAccess, model.InitialAccess{
				AttackerID: "A", Host: m["host"], Vector: "ssh_password_spray",
				Vulnerability: "weak_password_reuse", Account: m["user"],
				SourceIP: m["src"], Timestamp: m["ts"],
			})
			ev.CompromisedUsers = append(ev.CompromisedUsers, m["user"])
			ev.CompromisedHosts = append(ev.CompromisedHosts, m["host"])
		}
		ev.Summary["auth_entries"]++
	}
}
