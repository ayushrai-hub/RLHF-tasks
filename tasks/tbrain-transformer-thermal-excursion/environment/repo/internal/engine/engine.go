// Package engine implements the transformer-thermal excursion ledger.
//
// Run parses the JSON scenario, validates it (including the per-asset service
// window structure), and computes the deterministic per-asset ledger described
// in docs/spec.md. Parsing, validation, the per-asset timeline construction,
// and output assembly are already complete; only computeAsset needs the real
// state machine.
package engine

import (
	"encoding/json"
	"errors"
	"fmt"
	"sort"
)

type inAsset struct {
	Name   *string `json:"name"`
	Limit  *int    `json:"limit"`
	Arm    *int    `json:"arm"`
	Clear  *int    `json:"clear"`
	Budget *int    `json:"budget"`
}

type inReading struct {
	T       *int    `json:"t"`
	Asset *string `json:"asset"`
	Temp    *int    `json:"temp"`
	Type    *string `json:"type"`
}

type inDoc struct {
	Until    *int        `json:"until"`
	Assets []inAsset `json:"assets"`
	Readings []inReading `json:"readings"`
}

// Excursion is a confirmed over-limit interval [Start, End).
type Excursion struct {
	Start int `json:"start"`
	End   int `json:"end"`
}

// Final reports a asset's state at the horizon.
type Final struct {
	State string `json:"state"`
	Since int    `json:"since"`
}

// OutAsset is one asset's ledger entry.
type OutAsset struct {
	Name        string      `json:"name"`
	Excursions  []Excursion `json:"excursions"`
	OverSeconds int         `json:"over_seconds"`
	FailedAt   *int        `json:"failed_at"`
	Final       Final       `json:"final"`
}

// OutDoc is the full ledger.
type OutDoc struct {
	Assets []OutAsset `json:"assets"`
}

type cfg struct {
	limit, arm, clear, budget int
}

type evKind int

const (
	evReading evKind = iota
	evService
	evEndService
)

// event is one entry on a asset's timeline.
type event struct {
	t    int
	kind evKind
	temp int // valid only for evReading
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
	if _, ok := raw["assets"]; !ok {
		return OutDoc{}, errors.New("assets must be an array")
	}
	if _, ok := raw["readings"]; !ok {
		return OutDoc{}, errors.New("readings must be an array")
	}

	assets := map[string]cfg{}
	for _, p := range doc.Assets {
		if p.Name == nil || *p.Name == "" {
			return OutDoc{}, errors.New("asset name must be a non-empty string")
		}
		if _, ok := assets[*p.Name]; ok {
			return OutDoc{}, fmt.Errorf("duplicate asset %s", *p.Name)
		}
		if p.Limit == nil || p.Arm == nil || p.Clear == nil || p.Budget == nil {
			return OutDoc{}, errors.New("asset missing a required field")
		}
		if *p.Arm < 0 || *p.Clear < 0 || *p.Budget < 0 {
			return OutDoc{}, errors.New("arm, clear, and budget must be non-negative")
		}
		assets[*p.Name] = cfg{*p.Limit, *p.Arm, *p.Clear, *p.Budget}
	}

	per := map[string][]event{}
	for n := range assets {
		per[n] = nil
	}
	haveMax := false
	maxT := 0
	for _, r := range doc.Readings {
		if r.T == nil || r.Asset == nil {
			return OutDoc{}, errors.New("reading missing a required field")
		}
		if *r.T < 0 {
			return OutDoc{}, errors.New("reading t must be non-negative")
		}
		if _, ok := assets[*r.Asset]; !ok {
			return OutDoc{}, fmt.Errorf("reading references unknown asset %q", *r.Asset)
		}
		kind := evReading
		if r.Type != nil {
			switch *r.Type {
			case "", "reading":
				kind = evReading
			case "service":
				kind = evService
			case "endservice":
				kind = evEndService
			default:
				return OutDoc{}, fmt.Errorf("unknown reading type %q", *r.Type)
			}
		}
		ev := event{t: *r.T, kind: kind}
		if kind == evReading {
			if r.Temp == nil {
				return OutDoc{}, errors.New("reading missing a required field")
			}
			ev.temp = *r.Temp
		} else if r.Temp != nil {
			return OutDoc{}, errors.New("service event must not carry temp")
		}
		per[*r.Asset] = append(per[*r.Asset], ev)
		if !haveMax || *r.T > maxT {
			maxT, haveMax = *r.T, true
		}
	}

	var horizon int
	hasHorizon := false
	if doc.Until != nil {
		if haveMax && *doc.Until < maxT {
			return OutDoc{}, errors.New("until is before the last reading")
		}
		horizon, hasHorizon = *doc.Until, true
	} else if haveMax {
		horizon, hasHorizon = maxT, true
	}

	names := make([]string, 0, len(assets))
	for n := range assets {
		names = append(names, n)
	}
	sort.Strings(names)

	out := OutDoc{Assets: []OutAsset{}}
	for _, n := range names {
		op, err := computeAsset(n, assets[n], per[n], horizon, hasHorizon)
		if err != nil {
			return OutDoc{}, err
		}
		out.Assets = append(out.Assets, op)
	}
	return out, nil
}

// validateTimeline checks the per-asset service-window structure and that no
// two readings share a timestamp.
func validateTimeline(name string, evs []event) error {
	tmp := make([]event, len(evs))
	copy(tmp, evs)
	sort.SliceStable(tmp, func(i, j int) bool { return tmp[i].t < tmp[j].t })
	serviceOpen := false
	lastReadT := -1
	for _, e := range tmp {
		switch e.kind {
		case evService:
			if serviceOpen {
				return fmt.Errorf("nested service window for asset %s", name)
			}
			serviceOpen = true
		case evEndService:
			if !serviceOpen {
				return fmt.Errorf("endservice without service for asset %s", name)
			}
			serviceOpen = false
		case evReading:
			if lastReadT == e.t {
				return fmt.Errorf("duplicate timestamp for asset %s", name)
			}
			lastReadT = e.t
		}
	}
	if serviceOpen {
		return fmt.Errorf("service window left open for asset %s", name)
	}
	return nil
}

// computeAsset evaluates one asset's excursion ledger from its timeline.
//
// This body is only a placeholder. It splits the readings into constant
// temperature segments and treats each over-limit segment as its own excursion,
// counting every over-limit second toward the budget and reporting a final state
// read straight off the last segment. Replace it with the real state machine.
func computeAsset(name string, c cfg, evs []event, horizon int, hasHorizon bool) (OutAsset, error) {
	if err := validateTimeline(name, evs); err != nil {
		return OutAsset{}, err
	}
	excs := []Excursion{}
	if len(evs) == 0 || !hasHorizon {
		return OutAsset{
			Name: name, Excursions: excs, OverSeconds: 0, FailedAt: nil,
			Final: Final{State: "ok", Since: 0},
		}, nil
	}

	sort.SliceStable(evs, func(i, j int) bool { return evs[i].t < evs[j].t })
	readings := [][2]int{}
	for _, e := range evs {
		if e.kind == evReading {
			readings = append(readings, [2]int{e.t, e.temp})
		}
	}

	cum := 0
	var failedAt *int
	lastOver := false
	lastEnd := 0
	for i := 0; i < len(readings); i++ {
		a := readings[i][0]
		b := horizon
		if i+1 < len(readings) {
			b = readings[i+1][0]
		}
		if b <= a {
			continue
		}
		over := readings[i][1] > c.limit
		lastOver = over
		if over && failedAt == nil {
			excs = append(excs, Excursion{Start: a, End: b})
			cum += b - a
			lastEnd = b
			if cum > c.budget {
				v := b
				failedAt = &v
			}
		} else if !over {
			lastEnd = b
		}
	}

	final := Final{State: "ok", Since: lastEnd}
	if failedAt != nil {
		final = Final{State: "failed", Since: *failedAt}
	} else if lastOver {
		final = Final{State: "over", Since: lastEnd}
	}
	return OutAsset{Name: name, Excursions: excs, OverSeconds: cum, FailedAt: failedAt, Final: final}, nil
}
