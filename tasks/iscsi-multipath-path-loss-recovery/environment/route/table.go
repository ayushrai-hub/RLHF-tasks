package route

import "pathfb/model"

// table applies vector routing decisions from spread view and persisted route authorities.
func table(ctx model.Context, snap model.SpreadView, route model.RouteTable) (model.RouteTable, error) {
	out := route
	if Filter(ctx, snap) {
		return out, nil
	}
	out.AffinityMask = route.AffinityMask
	out.Routed = true
	return out, nil
}

// Apply exposes routing to the runner package.
func Apply(ctx model.Context, snap model.SpreadView, route model.RouteTable) (model.RouteTable, error) {
	return table(ctx, snap, route)
}
