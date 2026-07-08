package group

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"arrivaudit/mount/fanout"
)

type Batch struct {
	Name string
	Gen  int
}

type Event struct {
	Line string
}

func phase_b(ctx *fanout.Context, batch Batch) ([]Event, error) {
	if ctx == nil {
		return nil, fmt.Errorf("group: nil context")
	}
	src := filepath.Join(ctx.Fixtures, fmt.Sprintf("gen%d", batch.Gen), "active.log")
	body, err := os.ReadFile(src)
	if err != nil {
		return nil, err
	}
	archDir := filepath.Join(ctx.Archive, fmt.Sprintf("gen%d", batch.Gen))
	if err := os.MkdirAll(archDir, 0o755); err != nil {
		return nil, err
	}
	archPath := filepath.Join(archDir, "active.log")
	if err := os.WriteFile(archPath, body, 0o644); err != nil {
		return nil, err
	}
	pubTarget := filepath.Join(ctx.Published, "active.log")
	if err := os.MkdirAll(ctx.Published, 0o755); err != nil {
		return nil, err
	}
	_ = os.Remove(pubTarget)
	if err := os.WriteFile(pubTarget, []byte{}, 0o644); err != nil {
		return nil, err
	}
	next := batch.Gen + 1
	nextFixture := filepath.Join(ctx.Fixtures, fmt.Sprintf("gen%d", next), "active.log")
	var nextBody []byte
	if nb, err := os.ReadFile(nextFixture); err == nil {
		nextBody = nb
	} else {
		nextBody = body
	}
	_ = os.WriteFile(pubTarget, nextBody, 0o644)
	hostTarget := filepath.Join(ctx.HostView, "active.log")
	_ = os.WriteFile(hostTarget, nextBody, 0o644)
	if ctx.ActiveGen() == batch.Gen {
		if h, ok := pinnedHandle(ctx); ok && h.File != nil {
			_, _ = h.File.Write([]byte("post-wave-append\n"))
		}
	}
	hostMarker := filepath.Join(ctx.HostView, "wave_gen")
	_ = os.WriteFile(hostMarker, []byte(fmt.Sprintf("%d\n", next)), 0o644)
	events := []Event{{Line: "security-class-ack"}}
	return events, nil
}

func RunBatch(ctx *fanout.Context, batch Batch) ([]Event, error) {
	return phase_b(ctx, batch)
}

func CopyFixture(ctx *fanout.Context, gen int) error {
	src := filepath.Join(ctx.Fixtures, fmt.Sprintf("gen%d", gen), "active.log")
	body, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	targets := []string{
		filepath.Join(ctx.Published, "active.log"),
		filepath.Join(ctx.HostView, "active.log"),
		filepath.Join(ctx.WorkView, "active.log"),
	}
	for _, dst := range targets {
		if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
			return err
		}
		if err := os.WriteFile(dst, body, 0o644); err != nil {
			return err
		}
	}
	return nil
}

func AppendLine(ctx *fanout.Context, line string) (int, error) {
	h, err := fanout.OpenSink(ctx, "active.log")
	if err != nil {
		return 0, err
	}
	n, err := io.WriteString(h.File, line)
	if err != nil {
		return n, err
	}
	if !endsWithNewline(line) {
		_, err = h.File.Write([]byte("\n"))
	}
	return n, err
}

func pinnedHandle(ctx *fanout.Context) (*fanout.Handle, bool) {
	path := ctx.PinnedPath()
	if path == "" {
		return nil, false
	}
	f, err := os.OpenFile(path, os.O_RDWR|os.O_APPEND, 0o644)
	if err != nil {
		return nil, false
	}
	return &fanout.Handle{Gen: ctx.ActiveGen(), Path: path, File: f}, true
}

func endsWithNewline(s string) bool {
	return len(s) > 0 && s[len(s)-1] == '\n'
}
