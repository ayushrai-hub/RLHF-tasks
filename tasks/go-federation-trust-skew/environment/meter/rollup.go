package meter

import "sync/atomic"

var admits atomic.Uint64
var denies atomic.Uint64

func RecordAdmit() { admits.Add(1) }
func RecordDeny() { denies.Add(1) }

func Totals() (uint64, uint64) {
	return admits.Load(), denies.Load()
}
