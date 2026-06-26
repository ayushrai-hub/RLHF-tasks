package ward

import (
	"fedenv/tally/spool"
)

func pickKey(st *spool.Store, c Claim) ([]byte, bool) {
	return spool.PickMaterial(st, c.Kid, c.Gen)
}
