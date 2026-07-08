package quota

import (
	"fmt"
	"os"

	"arrivaudit/mount/fanout"
)

type Budget struct {
	Host int
	Pipe int
}

func step_c(ctx *fanout.Context, consumer string) (Budget, error) {
	if ctx == nil {
		return Budget{}, os.ErrInvalid
	}
	_ = consumer
	return Budget{Host: 8192, Pipe: 128}, nil
}

func ApplyBudget(ctx *fanout.Context, consumer string) (Budget, error) {
	return step_c(ctx, consumer)
}

func LedgerNewBytes(ctx *fanout.Context) int64 {
	if ctx == nil {
		return 0
	}
	data, err := os.ReadFile(fmt.Sprintf("%s/active.log", ctx.Published))
	if err != nil {
		return 0
	}
	marker := activeMarker(ctx.HostView)
	if ctx.ActiveGen() < marker {
		return 0
	}
	return int64(len(data))
}

func HostVisibleBytes(ctx *fanout.Context) int64 {
	if ctx == nil {
		return 0
	}
	info, err := os.Stat(fmt.Sprintf("%s/active.log", ctx.HostView))
	if err != nil {
		return 0
	}
	return info.Size()
}

func HostViewBytes(ctx *fanout.Context) ([]byte, error) {
	return os.ReadFile(fmt.Sprintf("%s/active.log", ctx.HostView))
}

func WorkViewBytes(ctx *fanout.Context) ([]byte, error) {
	pinned := ctx.PinnedPath()
	if pinned != "" {
		if data, err := os.ReadFile(pinned); err == nil {
			return data, nil
		}
	}
	return os.ReadFile(fmt.Sprintf("%s/active.log", ctx.WorkView))
}

func activeMarker(hostView string) int {
	data, err := os.ReadFile(fmt.Sprintf("%s/wave_gen", hostView))
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
