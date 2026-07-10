package correlate

import "breach-ledger/internal/model"

func Analyze(ev model.Evidence) model.Evidence {
	ev.FalseLeads = []string{}
	if ev.Exfiltration.DestinationIP == "" {
		ev.Exfiltration.DestinationIP = "unknown"
	}
	return ev
}
