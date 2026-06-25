package session

import (
	"encoding/json"
	"os"
	"path/filepath"

	"gateway-session/config"
	"gateway-session/rate"
)

type RuntimeState struct {
	Buckets       map[string]rate.Bucket `json:"buckets"`
	ConfigGen     int                    `json:"config_gen"`
	RouteCounter  int                    `json:"route_counter"`
	ScopeGen      int                    `json:"scope_gen"`
	LastRefillSeq int                    `json:"last_refill_seq"`
	ActiveConfig  config.Config          `json:"active_config"`
}

type Meta struct {
	PendingReloads []config.Config `json:"pending_reloads"`
	LastRunID      string          `json:"last_run_id"`
	Seq            int             `json:"seq"`
	ReloadScope    int             `json:"reload_scope"`
}

type ConsumeReq struct {
	Backend string `json:"backend"`
	Cost    int    `json:"cost"`
}

type Request struct {
	RunID         string         `json:"run_id"`
	FreshStart    bool           `json:"fresh_start"`
	QueueReload   *config.Config `json:"queue_reload"`
	ReplayPending bool           `json:"replay_pending"`
	Reload        *config.Config `json:"reload"`
	Consume       *ConsumeReq    `json:"consume"`
}

type Output struct {
	Accepted     bool   `json:"accepted"`
	Selected     string `json:"selected_backend"`
	TokensLeft   int    `json:"tokens_left"`
	StateDigest  string `json:"state_digest"`
	PendingCount int    `json:"pending_count"`
	LastRunID    string `json:"last_run_id"`
	ConfigGen    int    `json:"config_gen"`
	ScopeGen     int    `json:"scope_gen"`
}

type Store struct {
	dir       string
	statePath string
	metaPath  string
	State     RuntimeState
	Meta      Meta
}

func Open(dir string) (*Store, error) {
	s := &Store{
		dir:       dir,
		statePath: filepath.Join(dir, "state.json"),
		metaPath:  filepath.Join(dir, "meta.json"),
		State: RuntimeState{
			Buckets: make(map[string]rate.Bucket),
		},
	}
	if data, err := os.ReadFile(s.statePath); err == nil {
		if err := json.Unmarshal(data, &s.State); err != nil {
			return nil, err
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	if s.State.Buckets == nil {
		s.State.Buckets = make(map[string]rate.Bucket)
	}
	if data, err := os.ReadFile(s.metaPath); err == nil {
		if err := json.Unmarshal(data, &s.Meta); err != nil {
			return nil, err
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	if s.Meta.PendingReloads == nil {
		s.Meta.PendingReloads = []config.Config{}
	}
	return s, nil
}

func (s *Store) FreshStart() {
	_ = ClearCheckpointChain(s.dir)
	_ = ClearAdmissionBind(s.dir)
	s.State = RuntimeState{
		Buckets: make(map[string]rate.Bucket),
	}
	s.State.ConfigGen = 0
	s.State.RouteCounter = 0
	s.Meta.PendingReloads = []config.Config{}
	s.Meta.Seq++
}

func (s *Store) applyReload(cfg config.Config) {
	s.State.ActiveConfig = cfg
	s.State.Buckets = config.ApplyReload(s.State.Buckets, cfg)
	s.State.ConfigGen++
	s.State.LastRefillSeq = s.Meta.Seq
}

func (s *Store) refillRates() map[string]int {
	rates := make(map[string]int, len(s.State.ActiveConfig.Backends))
	for id, be := range s.State.ActiveConfig.Backends {
		rates[id] = be.RefillRate
	}
	return rates
}

func (s *Store) applyRefill() {
	rate.ApplyRefill(
		s.State.Buckets,
		s.refillRates(),
		s.Meta.Seq,
		s.State.LastRefillSeq,
	)
	s.State.LastRefillSeq = s.Meta.Seq
}

func (s *Store) Save() error {
	if err := os.MkdirAll(s.dir, 0o755); err != nil {
		return err
	}
	stateData, err := json.MarshalIndent(s.State, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(s.statePath, stateData, 0o644); err != nil {
		return err
	}
	if s.Meta.PendingReloads == nil {
		s.Meta.PendingReloads = []config.Config{}
	}
	metaData, err := json.MarshalIndent(s.Meta, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.metaPath, metaData, 0o644)
}
