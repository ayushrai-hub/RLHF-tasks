package session

import "gateway-session/config"

func QueueReload(meta *Meta, cfg config.Config, scopeGen int) {
	meta.PendingReloads = append(meta.PendingReloads, cfg)
	meta.ReloadScope = scopeGen
}

func ReplayPending(s *Store, applyReload func(config.Config)) {
	if s.Meta.ReloadScope == s.State.ScopeGen {
		for _, cfg := range s.Meta.PendingReloads {
			applyReload(cfg)
		}
	}
	s.Meta.PendingReloads = []config.Config{}
}
