package route

import "pathfb/model"

func table(ctx model.Context, snap model.SpreadView, routeTbl model.RouteTable) (model.RouteTable, error) {
	out := routeTbl
	if Filter(ctx, snap) {
		return out, nil
	}
	dp := ctx.TargetPathMask
	if dp == 0 {
		dp = ctx.ActivePathMask
	}
	out.AffinityMask = routeTbl.AffinityMask & dp
	out.Routed = true
	return out, nil
}

// Apply exposes routing to the sweep package.
func Apply(ctx model.Context, snap model.SpreadView, routeTbl model.RouteTable) (model.RouteTable, error) {
	return table(ctx, snap, routeTbl)
}
