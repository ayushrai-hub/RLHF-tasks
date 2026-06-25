package app

import (
	"encoding/json"
	"fmt"
)

type Flags struct {
	MultiStream       bool `json:"multi_stage"`
	StrictStreamSort  bool `json:"strict_stage_sort"`
	DeferredSettle   bool `json:"deferred_rollout"`
	TrackAccrual    bool `json:"track_exposure"`
}

type Config struct {
	ConfigID       string `json:"config_id"`
	Seed           int64  `json:"seed"`
	FleetID        string `json:"panel_id"`
	StreamCount    int    `json:"stage_width"`
	MaxTick        int64  `json:"max_period"`
	ScheduleMode   string `json:"view_mode"`
	RunMode        string `json:"run_mode"`
	FailoverPeriod int64  `json:"failover_period"`
	WarmCheckpoint string `json:"warm_checkpoint,omitempty"`
	CheckpointOut  string `json:"checkpoint_out,omitempty"`
	Flags          Flags  `json:"flags"`
}

func ParseConfig(data []byte) (Config, error) {
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, err
	}
	if cfg.StreamCount < 1 {
		return Config{}, fmt.Errorf("stage_width must be >= 1")
	}
	if cfg.MaxTick < 0 {
		return Config{}, fmt.Errorf("max_period must be >= 0")
	}
	if cfg.ScheduleMode == "" {
		cfg.ScheduleMode = "line_item"
	}
	if cfg.FleetID == "" {
		cfg.FleetID = "north"
	}
	return cfg, nil
}
