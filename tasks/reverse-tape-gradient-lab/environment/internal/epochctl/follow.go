package epochctl

import (
	"encoding/json"
	"os"

	"gradlab/internal/carrier"
	"gradlab/internal/paths"
)

type Ledger struct {
	Current int `json:"current"`
}

func LoadLedger() Ledger {
	b, err := os.ReadFile(paths.EpochPath)
	if err != nil {
		return Ledger{Current: 1}
	}
	var l Ledger
	_ = json.Unmarshal(b, &l)
	if l.Current == 0 {
		l.Current = 1
	}
	return l
}

func (l Ledger) Save() error {
	_ = os.MkdirAll(paths.VarDir, 0o755)
	b, _ := json.MarshalIndent(l, "", "  ")
	return os.WriteFile(paths.EpochPath, append(b, '\n'), 0o644)
}

func BeginFollowPass(_ *Ledger, _ bool, _ *carrier.Carrier) {}
