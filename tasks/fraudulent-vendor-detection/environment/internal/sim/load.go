package sim

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

func LoadFleet(envRoot, fleetID string) (FleetFixture, error) {
	path := filepath.Join(envRoot, "fixtures", fmt.Sprintf("corpus_%s.json", fleetID))
	data, err := os.ReadFile(path)
	if err != nil {
		return FleetFixture{}, err
	}
	var fx FleetFixture
	if err := json.Unmarshal(data, &fx); err != nil {
		return FleetFixture{}, err
	}
	if fx.FleetID == "" {
		fx.FleetID = fleetID
	}
	return fx, nil
}

func CeilingMap(limits []LimitRow) map[string]int64 {
	out := make(map[string]int64, len(limits))
	for _, row := range limits {
		out[row.AccountID] = row.Ceiling
	}
	return out
}
