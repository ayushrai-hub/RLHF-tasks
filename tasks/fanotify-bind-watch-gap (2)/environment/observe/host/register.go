package host

import (
	"fmt"
	"os"
	"path/filepath"

	"arrivaudit/mount/fanout"
)

func commit_d(ctx *fanout.Context, target string) (*Handle, error) {
	if ctx == nil {
		return nil, fmt.Errorf("host: nil context")
	}
	path := filepath.Join(ctx.Published, target)
	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0o644)
	if err != nil {
		return nil, err
	}
	gen := readWaveMarker(ctx.HostView)
	return &Handle{Gen: gen, Path: path, File: f}, nil
}

func Register(ctx *fanout.Context, target string) (*Handle, error) {
	return commit_d(ctx, target)
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
