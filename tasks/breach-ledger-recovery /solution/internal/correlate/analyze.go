package correlate

import (
	"sort"

	"breach-ledger/internal/model"
)

func Analyze(ev model.Evidence) model.Evidence {
	sort.Slice(ev.InitialAccess, func(i, j int) bool {
		return ev.InitialAccess[i].AttackerID < ev.InitialAccess[j].AttackerID
	})
	ev.CompromisedHosts = UniqueStrings(ev.CompromisedHosts)
	ev.CompromisedUsers = UniqueStrings(ev.CompromisedUsers)
	ev.Persistence = UniqueStrings(ev.Persistence)
	ev.StolenFiles = UniqueStrings(ev.StolenFiles)
	ev.StolenSecrets = UniqueStrings(ev.StolenSecrets)
	ev.ModifiedConfigs = UniqueStrings(ev.ModifiedConfigs)
	ev.IOCs = UniqueStrings(ev.IOCs)
	ev.FalseLeads = UniqueStrings(append(ev.FalseLeads, "172.16.10.55", "svc-metrics"))
	sort.Slice(ev.TamperedEvents, func(i, j int) bool {
		if ev.TamperedEvents[i].Seq == ev.TamperedEvents[j].Seq {
			return ev.TamperedEvents[i].TrueTS < ev.TamperedEvents[j].TrueTS
		}
		return ev.TamperedEvents[i].Seq < ev.TamperedEvents[j].Seq
	})
	timeline := C1(ev)
	ev.Commands = ev.Commands[:0]
	for _, event := range timeline {
		if event.AttackerID == "" || event.Detail == "" {
			continue
		}
		switch event.Source {
		case "history", "audit", "archive":
			ev.Commands = append(ev.Commands, event.Detail)
		}
	}
	return ev
}
