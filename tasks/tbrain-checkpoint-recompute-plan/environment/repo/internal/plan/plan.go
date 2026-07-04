// Package plan turns an ordered list of network layers into an activation
// checkpointing plan: a partition of the layers into contiguous segments whose
// first layer is retained as a checkpoint and whose remaining layers are
// recomputed during the backward pass.
package plan

import "ckptplan/internal/model"

// Plan is the planner's decision for a given layer list and memory budget.
type Plan struct {
	NSegments       int
	Boundaries      []int
	EstPeakMem      int
	EstRecompute    int
	TotalActivation int
	Feasible        bool
}

// checkpointSum is the resident activation memory of the retained checkpoints
// for a segmentation given by its boundary start indices.
func checkpointSum(layers []model.Layer, bounds []int) int {
	s := 0
	for _, b := range bounds {
		s += layers[b].Activation
	}
	return s
}

// segmentRecompute is the total recompute cost charged for one segment that
// starts at lo (inclusive) and ends at hi (exclusive). The first layer of the
// segment is the retained checkpoint and is not recomputed.
func segmentRecompute(layers []model.Layer, lo, hi int) int {
	s := 0
	for i := lo + 1; i < hi; i++ {
		s += layers[i].Recompute
	}
	return s
}

// totalRecompute sums the recompute charged across every segment of a
// segmentation.
func totalRecompute(layers []model.Layer, bounds []int) int {
	total := 0
	for k, b := range bounds {
		end := len(layers)
		if k+1 < len(bounds) {
			end = bounds[k+1]
		}
		total += segmentRecompute(layers, b, end)
	}
	return total
}

// totalActivation is the sum of every layer's activation memory.
func totalActivation(layers []model.Layer) int {
	s := 0
	for _, l := range layers {
		s += l.Activation
	}
	return s
}

// estimatePeak reports the resident memory the plan expects to need: the
// activation memory of every retained checkpoint that stays live across the
// backward pass.
func estimatePeak(layers []model.Layer, bounds []int) int {
	return checkpointSum(layers, bounds)
}

// Build returns the planner's chosen segmentation for the given layers under
// the memory budget. It scans the layers left to right, accumulating the
// activation the current segment would have to bring back, and closes the
// segment off with a fresh checkpoint at the first layer that would push the
// running resident demand past the budget. Closing segments as late as possible
// keeps the checkpoint count down, which keeps recompute down.
func Build(layers []model.Layer, budget int) Plan {
	n := len(layers)
	bounds := []int{0}
	// resident tracks the checkpoints retained so far plus the activation the
	// current open segment would regenerate; the scan opens a new checkpoint
	// whenever extending the open segment would exceed the budget.
	resident := layers[0].Activation
	segStart := 0
	for i := 1; i < n; i++ {
		if resident+layers[i].Activation > budget && i > segStart+1 {
			// Closing here and retaining layer i keeps the open segment within
			// budget; charge the new checkpoint and reset the segment demand.
			bounds = append(bounds, i)
			segStart = i
			resident = checkpointSum(layers, bounds)
		} else {
			resident += layers[i].Activation
		}
	}

	peak := estimatePeak(layers, bounds)
	plan := Plan{
		NSegments:       len(bounds),
		Boundaries:      bounds,
		EstPeakMem:      peak,
		EstRecompute:    totalRecompute(layers, bounds),
		TotalActivation: totalActivation(layers),
		Feasible:        peak <= budget,
	}
	return plan
}
