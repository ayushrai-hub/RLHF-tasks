package queue

import "pathfb/model"

// Table holds queue-to-CPU bindings after firmware metadata bumps.
type Table struct {
	QueueMask uint64
	Refreshed bool
}

// LoadTable seeds MSI-X bindings from the active affinity mask.
func LoadTable(affinity uint64) Table {
	return Table{QueueMask: affinity, Refreshed: false}
}

// Refresh realigns queue bindings to the dataplane mask when layout bumps.
func Refresh(tbl *Table, ctx model.Context, dataplane uint64) {
	if ctx.FlushBump <= 0 {
		return
	}
	if tbl.Refreshed {
		return
	}
	tbl.QueueMask = tbl.QueueMask & dataplane
	tbl.Refreshed = true
}
