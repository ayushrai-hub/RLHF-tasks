package driver

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"xferverify/emit"
	"xferverify/internal/io"
	"xferverify/internal/sink"
	"xferverify/internal/spool"
	"xferverify/recovery"
	"xferverify/replay"
	"xferverify/relay"
	"xferverify/runtime"
	"xferverify/store"
)

const (
	resumePath  = "/app/state/resume.offset"
	segmentPath = "/app/state/segment.cache.json"
)

type Event struct {
	Kind        string `json:"kind"`
	WriterEpoch string `json:"writer_epoch,omitempty"`
	ReaderEpoch string `json:"reader_epoch,omitempty"`
	Bytes       int    `json:"bytes,omitempty"`
}

type FixtureSpec struct {
	SinkMode string  `json:"sink_mode"`
	PipeCap  int     `json:"pipe_cap"`
	Events   []Event `json:"events"`
}

func pickWriter(mode string, cap int, lc *relay.Lifecycle) io.Writer {
	if mode == "redirect" {
		return &sink.RedirectSink{}
	}
	return &sink.WrapSink{Capacity: cap, Lifecycle: lc}
}

func appendTrace(tracePath, label, phase, writer, reader string, ledger spool.Ledger) error {
	return replay.AppendTrace(tracePath, replay.LedgerTraceLine{
		FixtureLabel: label,
		Phase:        phase,
		Observed:     ledger.ObservedBytes,
		Pending:      ledger.PendingBytes,
		WriterEpoch:  writer,
		ReaderEpoch:  reader,
		SpanMix:      replay.SpanMixCheckpoint(writer, reader, ledger),
	})
}

func appendJournal(journalPath, label, phase string, ledger spool.Ledger) error {
	return replay.AppendJournal(journalPath, label, phase, ledger.ObservedBytes, ledger.PendingBytes)
}

func runWave(ctx context.Context, writer io.Writer, total int, lim emit.Limits, ledger *spool.Ledger, label, tracePath, journalPath, writerEpoch, readerEpoch string) error {
	slices, err := emit.PlanSlices(ctx, total, lim)
	if err != nil {
		return err
	}
	for _, sl := range slices {
		n, term, err := writer.WriteChunk(sl.Size)
		if err != nil {
			return err
		}
		st, err := runtime.GuardTerm(ctx, term, runtime.RunState{})
		if err != nil {
			return err
		}
		if term.PipeClosed {
			if st.Fatal {
				ledger.Add(n)
				return nil
			}
			ledger.StagePending(n)
			break
		}
		ledger.Add(n)
	}
	return nil
}

func runFixture(label string, spec FixtureSpec, tracePath, journalPath, manifestPath string, lc *relay.Lifecycle) (replay.ReportRow, error) {
	ctx := context.Background()
	ledger := spool.NewLedger()
	recoveryStore := recovery.NewStore(&ledger)
	writerEpoch := "0000"
	readerEpoch := "0000"
	_ = manifestPath

	for _, ev := range spec.Events {
		switch ev.Kind {
		case "seed":
			writerEpoch = strings.ToLower(ev.WriterEpoch)
			readerEpoch = strings.ToLower(ev.ReaderEpoch)
			lc.ReaderEpoch = readerEpoch
			if err := store.ApplyResume(resumePath, label, readerEpoch, &ledger); err != nil {
				return replay.ReportRow{}, err
			}
			var cached int
			store.ApplySegment(segmentPath, label, readerEpoch, &cached)
			if cached > 0 {
				ledger.ObservedBytes = cached
			}
			if err := appendTrace(tracePath, label, "seed", writerEpoch, readerEpoch, ledger); err != nil {
				return replay.ReportRow{}, err
			}
			if err := appendJournal(journalPath, label, "seed", ledger); err != nil {
				return replay.ReportRow{}, err
			}
		case "recycle":
			if err := appendTrace(tracePath, label, "recycle_before", writerEpoch, readerEpoch, ledger); err != nil {
				return replay.ReportRow{}, err
			}
			if err := appendJournal(journalPath, label, "recycle_before", ledger); err != nil {
				return replay.ReportRow{}, err
			}
			res, err := recovery.ReplayCheckpoint(ctx, recoveryStore, recovery.Limits{Recycle: true})
			if err != nil {
				return replay.ReportRow{}, err
			}
			ledger = res.Ledger
			recoveryStore = recovery.NewStore(&ledger)
			relay.Recycle(lc, strings.ToLower(ev.ReaderEpoch))
			readerEpoch = lc.ReaderEpoch
			writerEpoch = readerEpoch
			if err := appendTrace(tracePath, label, "recycle_after", writerEpoch, readerEpoch, ledger); err != nil {
				return replay.ReportRow{}, err
			}
			if err := appendJournal(journalPath, label, "recycle_after", ledger); err != nil {
				return replay.ReportRow{}, err
			}
		case "wave":
			lim := emit.Limits{PipeCap: spec.PipeCap}
			w := pickWriter(spec.SinkMode, spec.PipeCap, lc)
			if err := runWave(ctx, w, ev.Bytes, lim, &ledger, label, tracePath, journalPath, writerEpoch, readerEpoch); err != nil {
				return replay.ReportRow{}, err
			}
			if err := appendTrace(tracePath, label, "wave_end", writerEpoch, readerEpoch, ledger); err != nil {
				return replay.ReportRow{}, err
			}
			if err := appendJournal(journalPath, label, "wave_end", ledger); err != nil {
				return replay.ReportRow{}, err
			}
		}
	}
	_ = store.SaveSegment(segmentPath, label, readerEpoch, ledger.ObservedBytes)
	return replay.BuildRecord(label, writerEpoch, readerEpoch, ledger), nil
}

func DriveAll(fixturesDir, tracePath, journalPath, manifestPath string) ([]replay.ReportRow, error) {
	if tracePath != "" {
		if err := replay.ResetTrace(tracePath); err != nil {
			return nil, err
		}
	}
	if journalPath != "" {
		if err := replay.ResetJournal(journalPath); err != nil {
			return nil, err
		}
	}
	_ = manifestPath
	entries, err := os.ReadDir(fixturesDir)
	if err != nil {
		return nil, err
	}
	var names []string
	for _, ent := range entries {
		if ent.IsDir() || !strings.HasSuffix(ent.Name(), ".json") {
			continue
		}
		names = append(names, ent.Name())
	}
	sort.Strings(names)
	lc := &relay.Lifecycle{}
	runs := make([]replay.ReportRow, 0, len(names))
	for _, name := range names {
		raw, err := os.ReadFile(filepath.Join(fixturesDir, name))
		if err != nil {
			return nil, err
		}
		var spec FixtureSpec
		if err := json.Unmarshal(raw, &spec); err != nil {
			return nil, err
		}
		label := strings.TrimSuffix(name, ".json")
		row, err := runFixture(label, spec, tracePath, journalPath, manifestPath, lc)
		if err != nil {
			return nil, err
		}
		runs = append(runs, row)
	}
	return runs, nil
}
