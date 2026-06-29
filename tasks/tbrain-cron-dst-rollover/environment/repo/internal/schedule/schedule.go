// Package schedule resolves a daily wall-clock schedule against a Zone: given a
// target wall-clock time of day and a UTC query instant, it reports the next UTC
// second at which the local clock will read that time.
package schedule

import "dstcron/internal/zone"

// NextFire returns the earliest UTC second strictly after `now` at which the
// local wall clock reads `target` seconds-of-day under zone `z`.
//
// It walks forward from the local day of the query: for the local day the query
// falls on, it forms the wall-clock instant for the target time of day and, if
// that instant is already at or before the query, advances to the next local
// day. The local reading is converted back to UTC with the zone's conversion.
func NextFire(z zone.Zone, now, target int64) int64 {
	off := z.OffsetSecondsAt(now)

	// Local day (seconds since local epoch) the query currently sits in.
	localNow := z.ToLocal(now)
	localMidnight := localNow - zone.Mod(localNow, zone.DaySeconds)

	localWall := localMidnight + target
	utc := zone.FromLocal(localWall, off)
	if utc <= now {
		localWall += zone.DaySeconds
		utc = zone.FromLocal(localWall, off)
	}
	return utc
}
