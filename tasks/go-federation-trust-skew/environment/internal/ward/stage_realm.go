package ward

import (
	"fedenv/parcel/realm"
)

func realmMatches(cfg Config, got string) bool {
	return realm.SameRealm(cfg.LocalRealm, got)
}
