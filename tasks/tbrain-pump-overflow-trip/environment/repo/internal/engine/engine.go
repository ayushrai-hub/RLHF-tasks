// Package engine implements the pump-station overflow protection trip ledger.
//
// Run parses the JSON scenario, validates it (including the per-line maint
// window structure), and computes the deterministic per-line ledger described
// in docs/spec.md. Parsing, validation, the per-line timeline construction,
// and output assembly are already complete; only computeLine needs the real
// state machine.
package engine

import (
	"encoding/json"
	"errors"
	"fmt"
	"sort"
)

type inLine struct {
	Name   *string `json:"name"`
	Limit  *int    `json:"limit"`
	Arm    *int    `json:"arm"`
	Reset  *int    `json:"reset"`
	Budget *int    `json:"budget"`
}

type inSample struct {
	T       *int    `json:"t"`
	Line *string `json:"line"`
	Lps    *int    `json:"lps"`
	Type    *string `json:"type"`
}

type inDoc struct {
	Until    *int        `json:"until"`
	Lines []inLine `json:"lines"`
	Samples []inSample `json:"samples"`
}

// Trip is a confirmed over-limit interval [Start, End).
type Trip struct {
	Start int `json:"start"`
	End   int `json:"end"`
}

// Final reports a line's state at the horizon.
type Final struct {
	State string `json:"state"`
	Since int    `json:"since"`
}

// OutLine is one line's ledger entry.
type OutLine struct {
	Name        string      `json:"name"`
	Trips  []Trip `json:"trips"`
	OverSeconds int         `json:"trip_seconds"`
	LockedAt   *int        `json:"locked_at"`
	Final       Final       `json:"final"`
}

// OutDoc is the full ledger.
type OutDoc struct {
	Lines []OutLine `json:"lines"`
}

type cfg struct {
	limit, arm, reset, budget int
}

type evKind int

const (
	evSample evKind = iota
	evMaint
	evEndMaint
)

// event is one entry on a line's timeline.
type event struct {
	t    int
	kind evKind
	lps int // valid only for evSample
}

// Run parses, validates, and evaluates the scenario.
func Run(data []byte) (OutDoc, error) {
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return OutDoc{}, err
	}
	var doc inDoc
	if err := json.Unmarshal(data, &doc); err != nil {
		return OutDoc{}, err
	}
	if _, ok := raw["lines"]; !ok {
		return OutDoc{}, errors.New("lines must be an array")
	}
	if _, ok := raw["samples"]; !ok {
		return OutDoc{}, errors.New("samples must be an array")
	}

	lines := map[string]cfg{}
	for _, p := range doc.Lines {
		if p.Name == nil || *p.Name == "" {
			return OutDoc{}, errors.New("line name must be a non-empty string")
		}
		if _, ok := lines[*p.Name]; ok {
			return OutDoc{}, fmt.Errorf("duplicate line %s", *p.Name)
		}
		if p.Limit == nil || p.Arm == nil || p.Reset == nil || p.Budget == nil {
			return OutDoc{}, errors.New("line missing a required field")
		}
		if *p.Arm < 0 || *p.Reset < 0 || *p.Budget < 0 {
			return OutDoc{}, errors.New("arm, reset, and budget must be non-negative")
		}
		lines[*p.Name] = cfg{*p.Limit, *p.Arm, *p.Reset, *p.Budget}
	}

	per := map[string][]event{}
	for n := range lines {
		per[n] = nil
	}
	haveMax := false
	maxT := 0
	for _, r := range doc.Samples {
		if r.T == nil || r.Line == nil {
			return OutDoc{}, errors.New("sample missing a required field")
		}
		if *r.T < 0 {
			return OutDoc{}, errors.New("sample t must be non-negative")
		}
		if _, ok := lines[*r.Line]; !ok {
			return OutDoc{}, fmt.Errorf("sample references unknown line %q", *r.Line)
		}
		kind := evSample
		if r.Type != nil {
			switch *r.Type {
			case "", "sample":
				kind = evSample
			case "maint":
				kind = evMaint
			case "endmaint":
				kind = evEndMaint
			default:
				return OutDoc{}, fmt.Errorf("unknown sample type %q", *r.Type)
			}
		}
		ev := event{t: *r.T, kind: kind}
		if kind == evSample {
			if r.Lps == nil {
				return OutDoc{}, errors.New("sample missing a required field")
			}
			ev.lps = *r.Lps
		} else if r.Lps != nil {
			return OutDoc{}, errors.New("maint event must not carry lps")
		}
		per[*r.Line] = append(per[*r.Line], ev)
		if !haveMax || *r.T > maxT {
			maxT, haveMax = *r.T, true
		}
	}

	var horizon int
	hasHorizon := false
	if doc.Until != nil {
		if haveMax && *doc.Until < maxT {
			return OutDoc{}, errors.New("until is before the last sample")
		}
		horizon, hasHorizon = *doc.Until, true
	} else if haveMax {
		horizon, hasHorizon = maxT, true
	}

	names := make([]string, 0, len(lines))
	for n := range lines {
		names = append(names, n)
	}
	sort.Strings(names)

	out := OutDoc{Lines: []OutLine{}}
	for _, n := range names {
		op, err := computeLine(n, lines[n], per[n], horizon, hasHorizon)
		if err != nil {
			return OutDoc{}, err
		}
		out.Lines = append(out.Lines, op)
	}
	return out, nil
}

// validateTimeline checks the per-line maint-window structure and that no
// two samples share a timestamp.
func validateTimeline(name string, evs []event) error {
	tmp := make([]event, len(evs))
	copy(tmp, evs)
	sort.SliceStable(tmp, func(i, j int) bool { return tmp[i].t < tmp[j].t })
	maintOpen := false
	lastReadT := -1
	for _, e := range tmp {
		switch e.kind {
		case evMaint:
			if maintOpen {
				return fmt.Errorf("nested maint window for line %s", name)
			}
			maintOpen = true
		case evEndMaint:
			if !maintOpen {
				return fmt.Errorf("endmaint without maint for line %s", name)
			}
			maintOpen = false
		case evSample:
			if lastReadT == e.t {
				return fmt.Errorf("duplicate timestamp for line %s", name)
			}
			lastReadT = e.t
		}
	}
	if maintOpen {
		return fmt.Errorf("maint window left open for line %s", name)
	}
	return nil
}

// computeLine evaluates one line's trip ledger from its timeline.
//
// This body is only a placeholder. It splits the samples into constant
// lps segments and treats each over-limit segment as its own trip,
// counting every over-limit second toward the budget and reporting a final state
// read straight off the last segment. Replace it with the real state machine.
func computeLine(name string, c cfg, evs []event, horizon int, hasHorizon bool) (OutLine, error) {
	if err := validateTimeline(name, evs); err != nil {
		return OutLine{}, err
	}
	excs := []Trip{}
	if len(evs) == 0 || !hasHorizon {
		return OutLine{
			Name: name, Trips: excs, OverSeconds: 0, LockedAt: nil,
			Final: Final{State: "ok", Since: 0},
		}, nil
	}

	sort.SliceStable(evs, func(i, j int) bool { return evs[i].t < evs[j].t })
	samples := [][2]int{}
	for _, e := range evs {
		if e.kind == evSample {
			samples = append(samples, [2]int{e.t, e.lps})
		}
	}

	cum := 0
	var lockedAt *int
	lastOver := false
	lastEnd := 0
	for i := 0; i < len(samples); i++ {
		a := samples[i][0]
		b := horizon
		if i+1 < len(samples) {
			b = samples[i+1][0]
		}
		if b <= a {
			continue
		}
		over := samples[i][1] > c.limit
		lastOver = over
		if over && lockedAt == nil {
			excs = append(excs, Trip{Start: a, End: b})
			cum += b - a
			lastEnd = b
			if cum > c.budget {
				v := b
				lockedAt = &v
			}
		} else if !over {
			lastEnd = b
		}
	}

	final := Final{State: "ok", Since: lastEnd}
	if lockedAt != nil {
		final = Final{State: "locked", Since: *lockedAt}
	} else if lastOver {
		final = Final{State: "tripped", Since: lastEnd}
	}
	return OutLine{Name: name, Trips: excs, OverSeconds: cum, LockedAt: lockedAt, Final: final}, nil
}
