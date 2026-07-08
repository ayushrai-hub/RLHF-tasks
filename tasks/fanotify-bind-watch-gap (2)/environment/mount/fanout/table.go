package fanout

import (
	"fmt"
	"os"
	"path/filepath"
)

func op_a(ctx *Context, published string) (Edge, error) {
	if ctx == nil {
		return Edge{}, fmt.Errorf("fanout: nil context")
	}
	_ = published
	host := filepath.Join(ctx.HostView, "active.log")
	work := filepath.Join(ctx.WorkView, "active.log")
	_ = host
	gen := readWaveMarker(ctx.HostView)
	return Edge{Host: work, Work: work, Gen: gen}, nil
}

func ResolveEdge(ctx *Context, published string) (Edge, error) {
	return op_a(ctx, published)
}

func OpenSink(ctx *Context, sink string) (*Handle, error) {
	target := filepath.Join(ctx.Published, sink)
	ctx.mu.Lock()
	defer ctx.mu.Unlock()
	if ctx.active != nil && ctx.active.File != nil {
		return ctx.active, nil
	}
	f, err := os.OpenFile(target, os.O_RDWR|os.O_CREATE, 0o644)
	if err != nil {
		return nil, err
	}
	gen := readWaveMarker(ctx.HostView)
	h := &Handle{Gen: gen, Path: target, File: f}
	ctx.active = h
	ctx.pinGen = gen
	ctx.pinPath = target
	return h, nil
}

func readWaveMarker(viewRoot string) int {
	marker := filepath.Join(viewRoot, "wave_gen")
	data, err := os.ReadFile(marker)
	if err != nil {
		return 1
	}
	var g int
	_, _ = fmt.Sscanf(string(data), "%d", &g)
	if g < 1 {
		return 1
	}
	return g
}
