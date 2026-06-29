package legacy

import (
	"quotaledger/internal/quota"
)

func ApplyIfNeeded(_ string, _ *quota.Engine, migrated *bool) error {
	*migrated = true
	return nil
}
