// Package zone converts between UTC and a local wall clock whose offset changes
// at two transition instants given explicitly (no system timezone database is
// consulted). The standard offset applies outside the daylight window and the
// daylight offset applies from the spring instant up to, but not including, the
// fall instant. All times are integer seconds.
package zone

// Zone describes a local wall clock with a standard and a daylight offset (each
// in minutes east of UTC) and the two UTC instants at which the offset changes.
type Zone struct {
	OffsetStd int   // minutes east of UTC during standard time
	OffsetDst int   // minutes east of UTC during daylight time
	Spring    int64 // UTC second at which the clock jumps forward (std -> dst)
	Fall      int64 // UTC second at which the clock falls back (dst -> std)
}

// DaySeconds is the number of seconds in a wall-clock day.
const DaySeconds = 86400

// StdSec is the standard offset expressed in seconds.
func (z Zone) StdSec() int64 { return int64(z.OffsetStd) * 60 }

// DstSec is the daylight offset expressed in seconds.
func (z Zone) DstSec() int64 { return int64(z.OffsetDst) * 60 }

// OffsetSecondsAt returns the offset (in seconds) in force at the given UTC
// instant. The daylight offset is in force on [Spring, Fall).
func (z Zone) OffsetSecondsAt(utc int64) int64 {
	if utc >= z.Spring && utc < z.Fall {
		return z.DstSec()
	}
	return z.StdSec()
}

// ToLocal renders the UTC instant on the local wall clock (seconds since the
// local epoch). Local time is UTC plus the offset in force at that UTC instant.
func (z Zone) ToLocal(utc int64) int64 {
	return utc + z.OffsetSecondsAt(utc)
}

// LocalTimeOfDay returns the wall-clock seconds-of-day (0..DaySeconds-1) the
// local clock reads at the given UTC instant.
func (z Zone) LocalTimeOfDay(utc int64) int64 {
	return Mod(z.ToLocal(utc), DaySeconds)
}

// FromLocal returns the UTC instant whose local reading is `localWall` seconds
// since the local epoch, assuming the fixed offset `offsetSec` applies. Going
// from a local wall-clock reading back to UTC removes the offset that was added
// to produce it.
func FromLocal(localWall, offsetSec int64) int64 {
	return localWall + offsetSec
}

// Mod is a floored modulo that always returns a value in [0, m).
func Mod(a, m int64) int64 {
	r := a % m
	if r < 0 {
		r += m
	}
	return r
}
