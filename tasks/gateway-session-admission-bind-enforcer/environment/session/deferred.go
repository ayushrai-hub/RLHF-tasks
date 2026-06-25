package session

import "gateway-session/config"

func QueueReload(meta *Meta, cfg config.Config) {
	meta.PendingReloads = append(meta.PendingReloads, cfg)
}

func ReplayPending(s *Store, applyReload func(config.Config)) {
	for i := len(s.Meta.PendingReloads) - 1; i >= 0; i-- {
		applyReload(s.Meta.PendingReloads[i])
	}
	s.Meta.PendingReloads = []config.Config{}
}
