package parse

import "breach-ledger/internal/model"

func unitL(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.ModifiedConfigs = append(ev.ModifiedConfigs, "sshd_config")
	ev.Summary["config_files"] = 1
}
