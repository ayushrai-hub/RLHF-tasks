package parse

import (
	"encoding/json"
	"os"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type userRecord struct {
	Username string   `json:"username"`
	UID      int      `json:"uid"`
	Aliases  []string `json:"aliases"`
}

type hostRecord struct {
	Host    string   `json:"host"`
	Aliases []string `json:"aliases"`
}

func unitA(dir string, ev *model.Evidence, issues *[]model.Issue) {
	var users []userRecord
	if data, err := os.ReadFile(filepath.Join(dir, "users.json")); err == nil {
		if json.Unmarshal(data, &users) == nil {
			for _, user := range users {
				name := normalize.NT2(user.Username)
				if prev, ok := ev.UserUID[name]; ok && prev != user.UID {
					model.AddIssue(issues, "identity_conflict", "conflicting user uid")
				}
				ev.UserUID[name] = user.UID
				for _, alias := range user.Aliases {
					alias = normalize.NT2(alias)
					if prev, ok := ev.UserUID[alias]; ok && prev != user.UID {
						model.AddIssue(issues, "identity_conflict", "conflicting user alias")
					}
					ev.UserUID[alias] = user.UID
				}
			}
		}
	}
	ev.Summary["users"] = len(users)

	var hosts []hostRecord
	if data, err := os.ReadFile(filepath.Join(dir, "hosts.json")); err == nil {
		if json.Unmarshal(data, &hosts) == nil {
			for _, host := range hosts {
				name := normalize.NT3(host.Host)
				for _, alias := range append([]string{name}, host.Aliases...) {
					alias = normalize.NT3(alias)
					if prev, ok := ev.HostAlias[alias]; ok && prev != name {
						model.AddIssue(issues, "host_conflict", "conflicting host alias")
					}
					ev.HostAlias[alias] = name
				}
			}
		}
	}
	ev.Summary["hosts"] = len(hosts)
}
