#!/bin/bash
set -euo pipefail

export PATH="/usr/bin:${PATH:-}"
export GOCACHE="${GOCACHE:-/tmp/gocache}"
export GOMODCACHE="${GOMODCACHE:-/tmp/gomodcache}"
install -d "${GOCACHE}" "${GOMODCACHE}" /app/bin /app/output /app/data/workspace

cd /app/environment

cat > mount/fanout/table.go << 'EOF'
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
	gen := readWaveMarker(ctx.HostView)
	return Edge{Host: host, Work: work, Gen: gen}, nil
}

func ResolveEdge(ctx *Context, published string) (Edge, error) {
	return op_a(ctx, published)
}

func OpenSink(ctx *Context, sink string) (*Handle, error) {
	target := filepath.Join(ctx.Published, sink)
	wantGen := readWaveMarker(ctx.HostView)
	ctx.mu.Lock()
	defer ctx.mu.Unlock()
	if ctx.active != nil && ctx.active.Gen == wantGen && ctx.active.File != nil {
		return ctx.active, nil
	}
	if ctx.active != nil && ctx.active.File != nil {
		_ = ctx.active.File.Close()
		ctx.active = nil
	}
	f, err := os.OpenFile(target, os.O_RDWR|os.O_APPEND|os.O_CREATE, 0o644)
	if err != nil {
		return nil, err
	}
	gen := wantGen
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
EOF

cat > notify/group/dispatch.go << 'EOF'
package group

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"arrivaudit/limit/quota"
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
	ctx.Reset()
	pubTarget := filepath.Join(ctx.Published, "active.log")
	if err := os.MkdirAll(ctx.Published, 0o755); err != nil {
		return nil, err
	}
	_ = os.Remove(pubTarget)
	next := batch.Gen + 1
	nextFixture := filepath.Join(ctx.Fixtures, fmt.Sprintf("gen%d", next), "active.log")
	nextBody, err := os.ReadFile(nextFixture)
	if err != nil {
		nextBody = body
	}
	if err := os.WriteFile(pubTarget, nextBody, 0o644); err != nil {
		return nil, err
	}
	batchMeta := filepath.Join(ctx.Fixtures, fmt.Sprintf("gen%d", batch.Gen), batch.Name+".json")
	if meta, err := os.ReadFile(batchMeta); err == nil {
		entries, _ := os.ReadDir(ctx.Published)
		for _, ent := range entries {
			if ent.IsDir() {
				continue
			}
			name := ent.Name()
			if strings.HasPrefix(name, "batch_") && strings.HasSuffix(name, ".json") {
				_ = os.Remove(filepath.Join(ctx.Published, name))
			}
		}
		pubBatch := filepath.Join(ctx.Published, batch.Name+".json")
		if err := os.WriteFile(pubBatch, meta, 0o644); err != nil {
			return nil, err
		}
	}
	hostTarget := filepath.Join(ctx.HostView, "active.log")
	workTarget := filepath.Join(ctx.WorkView, "active.log")
	for _, dst := range []string{hostTarget, workTarget} {
		if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
			return nil, err
		}
		if err := os.WriteFile(dst, nextBody, 0o644); err != nil {
			return nil, err
		}
	}
	counter := quota.NewCounter(ctx.Workspace)
	if err := counter.Bump(ctx.HostView, ctx.WorkView, next); err != nil {
		return nil, err
	}
	return []Event{}, nil
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
	workTarget := filepath.Join(ctx.WorkView, "active.log")
	if data, readErr := os.ReadFile(h.Path); readErr == nil {
		_ = os.WriteFile(workTarget, data, 0o644)
		_ = os.WriteFile(filepath.Join(ctx.HostView, "active.log"), data, 0o644)
	}
	return n, err
}

func endsWithNewline(s string) bool {
	return len(s) > 0 && s[len(s)-1] == '\n'
}
EOF

cat > limit/quota/throttle.go << 'EOF'
package quota

import (
	"fmt"
	"os"
	"path/filepath"

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
	return Budget{Host: 8192, Pipe: 8192}, nil
}

func ApplyBudget(ctx *fanout.Context, consumer string) (Budget, error) {
	return step_c(ctx, consumer)
}

func LedgerNewBytes(ctx *fanout.Context) int64 {
	if ctx == nil {
		return 0
	}
	workPath := filepath.Join(ctx.WorkView, "active.log")
	data, err := os.ReadFile(workPath)
	if err != nil {
		return 0
	}
	return int64(len(data))
}

func HostVisibleBytes(ctx *fanout.Context) int64 {
	if ctx == nil {
		return 0
	}
	info, err := os.Stat(filepath.Join(ctx.HostView, "active.log"))
	if err != nil {
		return 0
	}
	return info.Size()
}

func HostViewBytes(ctx *fanout.Context) ([]byte, error) {
	return os.ReadFile(filepath.Join(ctx.HostView, "active.log"))
}

func WorkViewBytes(ctx *fanout.Context) ([]byte, error) {
	return os.ReadFile(filepath.Join(ctx.WorkView, "active.log"))
}

func activeMarker(hostView string) int {
	data, err := os.ReadFile(filepath.Join(hostView, "wave_gen"))
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
EOF

cat > watch/recovery/sync.go << 'EOF'
package recovery

import (
	"os"
	"path/filepath"

	"arrivaudit/mount/fanout"
)

func RecycleMarkers(ctx *fanout.Context) error {
	if ctx == nil {
		return os.ErrInvalid
	}
	hostLog := filepath.Join(ctx.HostView, "active.log")
	workLog := filepath.Join(ctx.WorkView, "active.log")
	body, err := os.ReadFile(hostLog)
	if err != nil {
		return err
	}
	if err := os.WriteFile(workLog, body, 0o644); err != nil {
		return err
	}
	hostMarker := filepath.Join(ctx.HostView, "wave_gen")
	workMarker := filepath.Join(ctx.WorkView, "wave_gen")
	marker, err := os.ReadFile(hostMarker)
	if err != nil {
		return err
	}
	return os.WriteFile(workMarker, marker, 0o644)
}
EOF

cat > observe/host/register.go << 'EOF'
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
	path := filepath.Join(ctx.HostView, target)
	f, err := os.OpenFile(path, os.O_RDWR|os.O_APPEND|os.O_CREATE, 0o644)
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
EOF

cat > emit/trace/writer.go << 'EOF'
package trace

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func WriteTrace(rows []Row, tracePath, workspace string) error {
	env := Envelope{Runs: rows}
	for i := range env.Runs {
		env.Runs[i].RowSeal = sealRow(env.Runs[i])
	}
	sort.Slice(env.Runs, func(i, j int) bool {
		return env.Runs[i].Scenario < env.Runs[j].Scenario
	})
	env.ReportDigest = digestEnvelope(env.Runs)
	env.ReplayToken = replayToken(env.ReportDigest, workspace)
	data, err := json.MarshalIndent(env, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(tracePath), 0o755); err != nil {
		return err
	}
	return os.WriteFile(tracePath, append(data, '\n'), 0o644)
}

func EdgeFP(label string, body []byte) string {
	h := sha256.Sum256([]byte(label + "|" + string(body)))
	return hex.EncodeToString(h[:])[:16]
}

func StampFor(gen int, fixtureBody []byte, publishedSize int64) string {
	_ = publishedSize
	payload := fmt.Sprintf("%d|", gen)
	h := sha256.Sum256(append([]byte(payload), fixtureBody...))
	return hex.EncodeToString(h[:])[:16]
}

func sealRow(row Row) string {
	parts := []string{
		row.Scenario,
		fmt.Sprintf("%d", row.WaveGen),
		row.EdgeFPHost,
		row.EdgeFPWork,
		fmt.Sprintf("%d", row.MissGap),
		fmt.Sprintf("%d", row.GenSkew),
		row.RetentionStamp,
	}
	h := sha256.Sum256([]byte(strings.Join(parts, "|")))
	return hex.EncodeToString(h[:])[:16]
}

func digestEnvelope(rows []Row) string {
	var parts []string
	for _, row := range rows {
		parts = append(parts, strings.Join([]string{
			row.Scenario,
			fmt.Sprintf("%d", row.WaveGen),
			row.EdgeFPHost,
			row.EdgeFPWork,
			fmt.Sprintf("%d", row.MissGap),
			fmt.Sprintf("%d", row.GenSkew),
			row.RetentionStamp,
			row.RowSeal,
		}, ";"))
	}
	sort.Strings(parts)
	h := sha256.Sum256([]byte(strings.Join(parts, "\n")))
	return hex.EncodeToString(h[:])[:16]
}

func replayToken(reportDigest, workspace string) string {
	h := sha256.Sum256([]byte(reportDigest + "|" + workspace))
	return hex.EncodeToString(h[:])[:16]
}
EOF

go build -o /app/bin/arrival-audit ./driver/
/app/bin/arrival-audit \
  --trace /app/output/arrival_trace.json \
  --workspace /app/data/workspace \
  --fixtures /app/environment/fixtures/wave

echo "arrival-audit oracle complete"
