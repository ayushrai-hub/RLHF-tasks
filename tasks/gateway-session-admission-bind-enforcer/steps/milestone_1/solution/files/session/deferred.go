package session

import "gateway-session/config"

func QueueReload(meta *Meta, cfg config.Config) {
	meta.PendingReloads = append(meta.PendingReloads, cfg)
}

func ReplayPending(s *Store, applyReload func(config.Config)) {
	for _, cfg := range s.Meta.PendingReloads {
		applyReload(cfg)
	}
	s.Meta.PendingReloads = []config.Config{}
}
