package route

import "pathfb/model"

// Filter reports whether routing can be treated as a no-op for this spread view.
func Filter(ctx model.Context, snap model.SpreadView) bool {
	if !ctx.FailbackEarly {
		return false
	}
	if snap.EvenLooking {
		return true
	}
	return snap.SpreadIndex > 0 && snap.SpreadIndex%2 == 0
}
