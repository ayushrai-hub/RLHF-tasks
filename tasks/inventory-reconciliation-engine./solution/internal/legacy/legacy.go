package legacy

import (
	"encoding/json"
	"os"
	"path/filepath"

	"quotaledger/internal/quota"
)

type LegacySnapshot struct {
	Format   string `json:"format"`
	Accounts []struct {
		AccountID string `json:"account_id"`
		Balance   int    `json:"balance"`
		Epoch     int    `json:"epoch"`
	} `json:"accounts"`
}

func DefaultPath(root string) string {
	return filepath.Join(root, "data", "legacy", "snapshot_v0.json")
}

func ApplyIfNeeded(root string, engine *quota.Engine, migrated *bool) error {
	path := DefaultPath(root)
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			*migrated = true
			return nil
		}
		return err
	}
	var snap LegacySnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return err
	}
	if snap.Format != "quota-v0" {
		return nil
	}
	for _, row := range snap.Accounts {
		acct := engine.State.Accounts[row.AccountID]
		if acct == nil {
			acct = &quota.AccountState{Limit: 1000}
			engine.State.Accounts[row.AccountID] = acct
		}
		if acct.LastEventID == "" {
			acct.Available = row.Balance
			acct.Epoch = row.Epoch
			acct.LastEventID = "LEGACY-IMPORT"
			acct.LastLogicalTime = "1970-01-01T00:00:00Z"
		}
	}
	*migrated = true
	return nil
}
