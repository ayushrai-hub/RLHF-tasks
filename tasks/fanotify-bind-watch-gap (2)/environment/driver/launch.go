package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"arrivaudit/emit/trace"
	"arrivaudit/limit/quota"
	"arrivaudit/mount/fanout"
	"arrivaudit/notify/group"
	"arrivaudit/observe/host"
	"arrivaudit/probe"
	"arrivaudit/watch/recovery"
)

func main() {
	tracePath := flag.String("trace", "/app/output/arrival_trace.json", "arrival trace output path")
	workspace := flag.String("workspace", "/app/data/workspace", "audit workspace root")
	fixtures := flag.String("fixtures", "/app/environment/fixtures/wave", "wave fixture root")
	flag.Parse()

	scenarios, err := LoadScenarios(*fixtures)
	if err != nil {
		fail(err)
	}
	ctx := fanout.New(*workspace, *fixtures)
	rows := make([]trace.Row, 0, len(scenarios))
	for _, sc := range scenarios {
		row, err := runScenario(ctx, sc.Name)
		if err != nil {
			fail(fmt.Errorf("%s: %w", sc.Name, err))
		}
		rows = append(rows, row)
	}
	if err := trace.WriteTrace(rows, *tracePath, *workspace); err != nil {
		fail(err)
	}
}

func runScenario(ctx *fanout.Context, name string) (trace.Row, error) {
	ctx.Reset()
	if err := bootstrapWorkspace(ctx); err != nil {
		return trace.Row{}, err
	}
	switch name {
	case "wave_once":
		return driveWaveOnce(ctx)
	case "wave_twice":
		return driveWaveTwice(ctx)
	case "pause_trap":
		return drivePauseTrap(ctx)
	case "stale_marker":
		return driveStaleMarker(ctx)
	default:
		return trace.Row{}, fmt.Errorf("unknown scenario %q", name)
	}
}

func driveWaveOnce(ctx *fanout.Context) (trace.Row, error) {
	gen := 1
	if err := group.CopyFixture(ctx, gen); err != nil {
		return trace.Row{}, err
	}
	if _, err := host.Register(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := fanout.OpenSink(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.AppendLine(ctx, "evt=alpha seq=1"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.RunBatch(ctx, group.Batch{Name: "batch_a", Gen: gen}); err != nil {
		return trace.Row{}, err
	}
	if err := recovery.RecycleMarkers(ctx); err != nil {
		return trace.Row{}, err
	}
	return buildRow(ctx, "wave_once", gen)
}

func driveWaveTwice(ctx *fanout.Context) (trace.Row, error) {
	gen := 1
	if err := group.CopyFixture(ctx, gen); err != nil {
		return trace.Row{}, err
	}
	if _, err := host.Register(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := fanout.OpenSink(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.AppendLine(ctx, "evt=wave1-open"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.RunBatch(ctx, group.Batch{Name: "batch_a", Gen: gen}); err != nil {
		return trace.Row{}, err
	}
	if err := recovery.RecycleMarkers(ctx); err != nil {
		return trace.Row{}, err
	}
	gen = 2
	if _, err := group.RunBatch(ctx, group.Batch{Name: "batch_b", Gen: gen}); err != nil {
		return trace.Row{}, err
	}
	if err := recovery.RecycleMarkers(ctx); err != nil {
		return trace.Row{}, err
	}
	return buildRow(ctx, "wave_twice", 2)
}

func drivePauseTrap(ctx *fanout.Context) (trace.Row, error) {
	gen := 1
	if err := group.CopyFixture(ctx, gen); err != nil {
		return trace.Row{}, err
	}
	if _, err := host.Register(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := fanout.OpenSink(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.AppendLine(ctx, "evt=trap-open"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.RunBatch(ctx, group.Batch{Name: "batch_a", Gen: gen}); err != nil {
		return trace.Row{}, err
	}
	ctx.Reset()
	if err := group.CopyFixture(ctx, 2); err != nil {
		return trace.Row{}, err
	}
	if _, err := host.Register(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := fanout.OpenSink(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.AppendLine(ctx, "evt=trap-reopen"); err != nil {
		return trace.Row{}, err
	}
	gen = 2
	if _, err := group.RunBatch(ctx, group.Batch{Name: "batch_b", Gen: gen}); err != nil {
		return trace.Row{}, err
	}
	if err := recovery.RecycleMarkers(ctx); err != nil {
		return trace.Row{}, err
	}
	return buildRow(ctx, "pause_trap", 2)
}

func driveStaleMarker(ctx *fanout.Context) (trace.Row, error) {
	gen := 1
	if err := group.CopyFixture(ctx, gen); err != nil {
		return trace.Row{}, err
	}
	if _, err := host.Register(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := fanout.OpenSink(ctx, "active.log"); err != nil {
		return trace.Row{}, err
	}
	if _, err := group.RunBatch(ctx, group.Batch{Name: "batch_a", Gen: gen}); err != nil {
		return trace.Row{}, err
	}
	return buildRow(ctx, "stale_marker", gen)
}

func buildRow(ctx *fanout.Context, scenario string, gen int) (trace.Row, error) {
	_, _ = fanout.ResolveEdge(ctx, "active.log")
	_, _ = quota.ApplyBudget(ctx, "host-side")
	hostBody, err := quota.HostViewBytes(ctx)
	if err != nil {
		hostBody = []byte{}
	}
	workBody, err := quota.WorkViewBytes(ctx)
	if err != nil {
		workBody = []byte{}
	}
	hostVisible := quota.HostVisibleBytes(ctx)
	workNew := quota.LedgerNewBytes(ctx)
	missGap := hostVisible - workNew
	hostGen := readWaveMarker(ctx.HostView)
	workGen := readWaveMarker(ctx.WorkView)
	genSkew := int64(hostGen - workGen)
	fixturePath := filepath.Join(ctx.Fixtures, fmt.Sprintf("gen%d", gen), "active.log")
	fixtureBody, _ := os.ReadFile(fixturePath)
	pubSize := hostVisible
	stamp := trace.StampFor(gen, fixtureBody, pubSize)
	_ = probe.PublishedEntryCount(ctx.Published)
	return trace.Row{
		Scenario:       scenario,
		WaveGen:        gen,
		EdgeFPHost:     trace.EdgeFP("host", hostBody),
		EdgeFPWork:     trace.EdgeFP("work", workBody),
		MissGap:        missGap,
		GenSkew:        genSkew,
		RetentionStamp: stamp,
	}, nil
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

func bootstrapWorkspace(ctx *fanout.Context) error {
	for _, d := range []string{ctx.Published, ctx.HostView, ctx.WorkView, ctx.Archive} {
		if err := os.RemoveAll(d); err != nil {
			return err
		}
	}
	dirs := []string{
		ctx.Published,
		ctx.HostView,
		ctx.WorkView,
		filepath.Join(ctx.Archive, "gen1"),
		filepath.Join(ctx.Archive, "gen2"),
	}
	for _, d := range dirs {
		if err := os.MkdirAll(d, 0o755); err != nil {
			return err
		}
	}
	counter := quota.NewCounter(ctx.Workspace)
	return counter.Bump(ctx.HostView, ctx.WorkView, 1)
}

func fail(err error) {
	fmt.Fprintf(os.Stderr, "arrival-audit: %v\n", err)
	os.Exit(1)
}
