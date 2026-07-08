// Oracle solver for ready-mix-concrete-batch-dispatch-planner.
//
// Ready-mix concrete batch-plant dispatch with cement and fine-aggregate quality
// targets, lane/window/bin capacities, prep precedence, and deterministic
// washout-zone conflicts.
//
// Self-contained package main: reads <input_dir> <output_dir> positional args and
// writes concrete_dispatch_plan.jsonl + concrete_dispatch_summary.json.
package main

import (
	"bufio"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
)

type Load struct {
	PourID        string  `json:"pour_id"`
	AggregateBin  string  `json:"aggregate_bin"`
	MixType       string  `json:"mix_type"`
	CementPct     float64 `json:"cement_pct"`
	FinePct       float64 `json:"fine_pct"`
	CubicM        float64 `json:"cubic_m"`
	Value         float64 `json:"value"`
	DeliveryRoute string  `json:"delivery_route"`
	WashoutZone   string  `json:"washout_zone"`
	Mandatory     bool    `json:"mandatory"`
	RequiresPrep  string  `json:"requires_admixture_prep"`
	EarliestWin   int     `json:"earliest_window"`
	DeadlineWin   int     `json:"deadline_window"`
	PreferredMod  string  `json:"preferred_mode"`
}

type Line struct {
	BatchLaneID        string   `json:"batch_lane_id"`
	PlantZone          string   `json:"plant_zone"`
	MixTypes           []string `json:"mix_types"`
	AllowsPaving       bool     `json:"allows_paving"`
	AggregateBinGroups []string `json:"aggregate_bin_groups"`
	MaxLoads           int      `json:"max_loads"`
	CapacityCubicM     float64  `json:"capacity_cubic_m"`
}

type Bin struct {
	AggregateBinID string   `json:"aggregate_bin_id"`
	Priority       float64  `json:"priority"`
	CutoffWindow   int      `json:"cutoff_window"`
	PreferredZones []string `json:"preferred_zones"`
	DrawCapCubicM  float64  `json:"draw_capacity_cubic_m"`
}
type BinFile struct {
	Bins []Bin `json:"bins"`
}
type Window struct {
	Window              int     `json:"window"`
	ThroughputCapCubicM float64 `json:"throughput_capacity_cubic_m"`
}
type WindowFile struct {
	Windows []Window `json:"windows"`
}
type Bound struct {
	Min    float64 `json:"min"`
	Max    float64 `json:"max"`
	Target float64 `json:"target"`
}
type Config struct {
	HandlingModes []string           `json:"handling_modes"`
	HashSeed      string             `json:"hash_seed"`
	CementBand    map[string]float64 `json:"cement_band"`
	FineBand      map[string]float64 `json:"fine_band"`
	WaterBoundsL  map[string]Bound   `json:"water_bounds_l"`
}

type PlanRow struct {
	PourID        string  `json:"pour_id"`
	Assigned      bool    `json:"assigned"`
	BatchLaneID   string  `json:"batch_lane_id"`
	ProductionWin int     `json:"production_window"`
	PlantZone     string  `json:"plant_zone"`
	PriorityRank  int     `json:"priority_rank"`
	HandlingMode  string  `json:"handling_mode"`
	BatchWaterL   float64 `json:"batch_water_l"`
}

var modes = []string{"DIRECT", "HOLD", "REBLEND"}
var waterOffsets = []float64{-12.0, -9.0, -6.5, -4.0, -1.5, 1.0, 3.5, 6.0, 8.5, 11.0, 13.0}

const targetCement = 5.50
const maxCount = 212

func readJSONL[T any](path string) []T {
	f, err := os.Open(path)
	must(err)
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1024), 1024*1024)
	out := []T{}
	for sc.Scan() {
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		var row T
		must(json.Unmarshal(line, &row))
		out = append(out, row)
	}
	must(sc.Err())
	return out
}

func readJSON[T any](path string, out *T) {
	data, err := os.ReadFile(path)
	must(err)
	must(json.Unmarshal(data, out))
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func contains(list []string, v string) bool {
	for _, x := range list {
		if x == v {
			return true
		}
	}
	return false
}

func loadNum(id string) int {
	for i := len(id) - 1; i >= 0; i-- {
		if id[i] == '-' {
			v, _ := strconv.Atoi(id[i+1:])
			return v
		}
	}
	return 0
}

func zoneConflict(a, b *Load, seed string) bool {
	if a.WashoutZone != b.WashoutZone {
		return false
	}
	ai, bi := loadNum(a.PourID), loadNum(b.PourID)
	if ai > bi {
		ai, bi = bi, ai
	}
	s := seed + "|" + a.WashoutZone + "|" + strconv.Itoa(ai) + "|" + strconv.Itoa(bi)
	sum := md5.Sum([]byte(s))
	band, _ := strconv.ParseInt(hex.EncodeToString(sum[:])[:6], 16, 64)
	limit := int64(11)
	if a.DeliveryRoute == b.DeliveryRoute {
		limit = 24
	}
	return band%100 < limit
}

func waterFor(class string, idx int, bounds map[string]Bound) float64 {
	b := bounds[class]
	v := b.Target + waterOffsets[idx%len(waterOffsets)]
	v = math.Max(b.Min, math.Min(b.Max, v))
	return math.Round(v*100) / 100
}

type Planner struct {
	loads    map[string]*Load
	loadIDs  []string
	lines    []*Line
	bins     map[string]*Bin
	windows  map[int]*Window
	winList  []int
	cfg      Config
	seed     string
	prepPred map[string]bool

	placed     map[string]*PlanRow
	laneSlots  map[string]int
	laneVolume map[string]float64
	winCubicM  map[int]float64
	winCount   map[int]int
	winZone    map[int]map[string][]*Load
	zoneCount  map[string]int
	binVolume  map[string]float64
	sumCubicM  float64
	sumCementM float64
	rank       int
}

func newPlanner(loads []Load, lines []Line, bins map[string]*Bin, windows map[int]*Window, cfg Config) *Planner {
	p := &Planner{
		loads: map[string]*Load{}, bins: bins, windows: windows, cfg: cfg, seed: cfg.HashSeed,
		prepPred: map[string]bool{}, placed: map[string]*PlanRow{}, laneSlots: map[string]int{},
		laneVolume: map[string]float64{}, winCubicM: map[int]float64{}, winCount: map[int]int{},
		winZone: map[int]map[string][]*Load{}, zoneCount: map[string]int{}, binVolume: map[string]float64{},
	}
	for i := range loads {
		ld := loads[i]
		p.loads[ld.PourID] = &ld
		p.loadIDs = append(p.loadIDs, ld.PourID)
		if ld.RequiresPrep != "" {
			p.prepPred[ld.RequiresPrep] = true
		}
	}
	sort.Strings(p.loadIDs)
	for i := range lines {
		ln := lines[i]
		p.lines = append(p.lines, &ln)
	}
	sort.Slice(p.lines, func(i, j int) bool { return p.lines[i].BatchLaneID < p.lines[j].BatchLaneID })
	for w := range windows {
		p.winList = append(p.winList, w)
		p.winZone[w] = map[string][]*Load{}
	}
	sort.Ints(p.winList)
	return p
}

func (p *Planner) cementAvg() float64 {
	if p.sumCubicM == 0 {
		return targetCement
	}
	return p.sumCementM / p.sumCubicM
}

func (p *Planner) linesFor(ld *Load) []*Line {
	out := []*Line{}
	for _, ln := range p.lines {
		if !contains(ln.AggregateBinGroups, ld.AggregateBin) {
			continue
		}
		if !contains(ln.MixTypes, ld.MixType) {
			continue
		}
		if ld.MixType == "PAVING" && !ln.AllowsPaving {
			continue
		}
		out = append(out, ln)
	}
	return out
}

func (p *Planner) feasibleWindows(ld *Load) []int {
	lo := ld.EarliestWin
	hi := ld.DeadlineWin
	if c := p.bins[ld.AggregateBin].CutoffWindow; c < hi {
		hi = c
	}
	out := []int{}
	for w := lo; w <= hi; w++ {
		if _, ok := p.windows[w]; ok {
			out = append(out, w)
		}
	}
	return out
}

func (p *Planner) conflicts(ld *Load, w int) bool {
	for _, other := range p.winZone[w][ld.WashoutZone] {
		if zoneConflict(ld, other, p.seed) {
			return true
		}
	}
	return false
}

func (p *Planner) tryPlace(ld *Load, minWindow int, preferEarly bool) int {
	cand := p.linesFor(ld)
	if len(cand) == 0 {
		return -1
	}
	n := len(p.placed)
	if n < 1 {
		n = 1
	}
	bestScore := -1e18
	bestW := -1
	var bestLine *Line
	for _, w := range p.feasibleWindows(ld) {
		if w < minWindow {
			continue
		}
		if p.winCubicM[w]+ld.CubicM > p.windows[w].ThroughputCapCubicM {
			continue
		}
		if p.binVolume[ld.AggregateBin]+ld.CubicM > p.bins[ld.AggregateBin].DrawCapCubicM {
			continue
		}
		if p.conflicts(ld, w) {
			continue
		}
		for _, ln := range cand {
			if p.laneSlots[ln.BatchLaneID]+1 > ln.MaxLoads {
				continue
			}
			if p.laneVolume[ln.BatchLaneID]+ld.CubicM > ln.CapacityCubicM {
				continue
			}
			sc := 0.0
			if preferEarly {
				sc += float64(7-w) * 40.0
			}
			sc -= p.winCubicM[w] * 0.0016
			if !preferEarly && (w == 5 || w == 6) {
				sc += math.Max(0.0, 0.14*float64(n+1)-float64(p.winCount[w])) * 6.0
			}
			sc -= math.Max(0.0, float64(p.winCount[w])-0.18*float64(n+1)) * 5.0
			if contains(p.bins[ld.AggregateBin].PreferredZones, ln.PlantZone) {
				sc += 3.0
			}
			sc += p.laneVolume[ln.BatchLaneID] * 0.0012
			sc -= float64(p.zoneCount[ln.PlantZone]) * 0.5
			if sc > bestScore {
				bestScore = sc
				bestW = w
				bestLine = ln
			}
		}
	}
	if bestLine == nil {
		return -1
	}
	idx := p.rank
	row := &PlanRow{
		PourID: ld.PourID, Assigned: true, BatchLaneID: bestLine.BatchLaneID, ProductionWin: bestW,
		PlantZone: bestLine.PlantZone, PriorityRank: idx + 1, HandlingMode: modes[idx%3],
		BatchWaterL: waterFor(ld.MixType, idx, p.cfg.WaterBoundsL),
	}
	p.placed[ld.PourID] = row
	p.laneSlots[bestLine.BatchLaneID]++
	p.laneVolume[bestLine.BatchLaneID] += ld.CubicM
	p.winCubicM[bestW] += ld.CubicM
	p.winCount[bestW]++
	p.winZone[bestW][ld.WashoutZone] = append(p.winZone[bestW][ld.WashoutZone], ld)
	p.zoneCount[bestLine.PlantZone]++
	p.binVolume[ld.AggregateBin] += ld.CubicM
	p.sumCubicM += ld.CubicM
	p.sumCementM += ld.CementPct * ld.CubicM
	p.rank++
	return bestW
}

func (p *Planner) placeLoad(ld *Load) bool {
	if _, ok := p.placed[ld.PourID]; ok {
		return true
	}
	minW := 1
	if ld.RequiresPrep != "" {
		prep := ld.RequiresPrep
		if _, ok := p.placed[prep]; !ok {
			if p.tryPlace(p.loads[prep], 1, true) < 0 {
				return false
			}
		}
		minW = p.placed[prep].ProductionWin
	}
	early := p.prepPred[ld.PourID]
	return p.tryPlace(ld, minW, early) >= 0
}

func (p *Planner) remove(lid string) {
	row := p.placed[lid]
	delete(p.placed, lid)
	ld := p.loads[lid]
	w := row.ProductionWin
	p.laneSlots[row.BatchLaneID]--
	p.laneVolume[row.BatchLaneID] -= ld.CubicM
	p.winCubicM[w] -= ld.CubicM
	p.winCount[w]--
	seg := p.winZone[w][ld.WashoutZone]
	kept := seg[:0]
	for _, x := range seg {
		if x.PourID != lid {
			kept = append(kept, x)
		}
	}
	p.winZone[w][ld.WashoutZone] = kept
	p.zoneCount[row.PlantZone]--
	p.binVolume[ld.AggregateBin] -= ld.CubicM
	p.sumCubicM -= ld.CubicM
	p.sumCementM -= ld.CementPct * ld.CubicM
}

func (p *Planner) neededPrep(lid string) bool {
	for plid := range p.placed {
		if p.loads[plid].RequiresPrep == lid {
			return true
		}
	}
	return false
}

func (p *Planner) placedByCementDesc(filter func(string) bool) []string {
	ids := []string{}
	for lid := range p.placed {
		if filter(lid) {
			ids = append(ids, lid)
		}
	}
	sort.Slice(ids, func(i, j int) bool {
		ai, aj := p.loads[ids[i]].CementPct, p.loads[ids[j]].CementPct
		if ai != aj {
			return ai > aj
		}
		return ids[i] < ids[j]
	})
	return ids
}

func (p *Planner) qualityCorrect() {
	lo, hi := targetCement-0.05, targetCement+0.05
	for guard := 0; guard < 600; guard++ {
		cur := p.cementAvg()
		if cur >= lo && cur <= hi {
			break
		}
		if cur > hi {
			cands := p.placedByCementDesc(func(lid string) bool {
				return !p.loads[lid].Mandatory && !p.neededPrep(lid)
			})
			if len(cands) == 0 {
				break
			}
			p.remove(cands[0])
			for _, lid := range p.loadIDs {
				if _, ok := p.placed[lid]; !ok && p.loads[lid].CementPct < cur {
					if p.placeLoad(p.loads[lid]) {
						break
					}
				}
			}
		} else {
			unplaced := []string{}
			for _, lid := range p.loadIDs {
				if _, ok := p.placed[lid]; !ok && p.loads[lid].CementPct < cur {
					unplaced = append(unplaced, lid)
				}
			}
			sort.Slice(unplaced, func(i, j int) bool {
				ai, aj := p.loads[unplaced[i]].CementPct, p.loads[unplaced[j]].CementPct
				if ai != aj {
					return ai < aj
				}
				return p.loads[unplaced[i]].Value > p.loads[unplaced[j]].Value
			})
			added := false
			for _, lid := range unplaced {
				if len(p.placed) >= maxCount {
					break
				}
				if p.placeLoad(p.loads[lid]) {
					added = true
					break
				}
			}
			if !added {
				cands := p.placedByCementDesc(func(lid string) bool {
					return !p.loads[lid].Mandatory && !p.neededPrep(lid) && p.loads[lid].CementPct > cur
				})
				if len(cands) == 0 {
					break
				}
				p.remove(cands[0])
			}
		}
	}
}

func (p *Planner) run() []*PlanRow {
	for _, lid := range p.loadIDs {
		if p.loads[lid].Mandatory {
			p.placeLoad(p.loads[lid])
		}
	}
	optional := []string{}
	for _, lid := range p.loadIDs {
		if _, ok := p.placed[lid]; !ok {
			optional = append(optional, lid)
		}
	}
	raisers, lowerers := []string{}, []string{}
	for _, lid := range optional {
		if p.loads[lid].CementPct > targetCement {
			raisers = append(raisers, lid)
		} else {
			lowerers = append(lowerers, lid)
		}
	}
	byValDesc := func(ids []string) {
		sort.Slice(ids, func(i, j int) bool {
			vi, vj := p.loads[ids[i]].Value, p.loads[ids[j]].Value
			if vi != vj {
				return vi > vj
			}
			return ids[i] < ids[j]
		})
	}
	byValDesc(raisers)
	byValDesc(lowerers)
	ri, li := 0, 0
	for len(p.placed) < maxCount && (ri < len(raisers) || li < len(lowerers)) {
		useLower := p.cementAvg() > targetCement
		picked := ""
		switch {
		case useLower && li < len(lowerers):
			picked = lowerers[li]
			li++
		case !useLower && ri < len(raisers):
			picked = raisers[ri]
			ri++
		case li < len(lowerers):
			picked = lowerers[li]
			li++
		case ri < len(raisers):
			picked = raisers[ri]
			ri++
		}
		if picked == "" {
			break
		}
		p.placeLoad(p.loads[picked])
	}
	p.qualityCorrect()
	rows := []*PlanRow{}
	for _, r := range p.placed {
		rows = append(rows, r)
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i].PriorityRank < rows[j].PriorityRank })
	for i, r := range rows {
		r.PriorityRank = i + 1
	}
	return rows
}

func main() {
	inputDir := "/app/task_file/input_data"
	outputDir := "/app/task_file/output_data"
	if len(os.Args) >= 3 {
		inputDir = os.Args[1]
		outputDir = os.Args[2]
	}
	loads := readJSONL[Load](filepath.Join(inputDir, "pour_orders.jsonl"))
	lines := readJSONL[Line](filepath.Join(inputDir, "batch_lanes.jsonl"))
	var sf BinFile
	readJSON(filepath.Join(inputDir, "aggregate_bins.json"), &sf)
	var wf WindowFile
	readJSON(filepath.Join(inputDir, "delivery_windows.json"), &wf)
	var cfg Config
	readJSON(filepath.Join(inputDir, "mix_config.json"), &cfg)

	bins := map[string]*Bin{}
	for i := range sf.Bins {
		bins[sf.Bins[i].AggregateBinID] = &sf.Bins[i]
	}
	windows := map[int]*Window{}
	for i := range wf.Windows {
		windows[wf.Windows[i].Window] = &wf.Windows[i]
	}

	planner := newPlanner(loads, lines, bins, windows, cfg)
	rows := planner.run()

	must(os.MkdirAll(outputDir, 0o755))
	pf, err := os.Create(filepath.Join(outputDir, "concrete_dispatch_plan.jsonl"))
	must(err)
	enc := json.NewEncoder(pf)
	for _, r := range rows {
		must(enc.Encode(r))
	}
	pf.Close()

	loadMap := map[string]*Load{}
	for i := range loads {
		loadMap[loads[i].PourID] = &loads[i]
	}
	winCounts := map[string]int{}
	zoneCounts := map[string]int{}
	lineCounts := map[string]int{}
	cubicM, cementM, fineM := 0.0, 0.0, 0.0
	for _, r := range rows {
		winCounts[strconv.Itoa(r.ProductionWin)]++
		zoneCounts[r.PlantZone]++
		lineCounts[r.BatchLaneID]++
		ld := loadMap[r.PourID]
		cubicM += ld.CubicM
		cementM += ld.CementPct * ld.CubicM
		fineM += ld.FinePct * ld.CubicM
	}
	weightedCement, weightedFine := 0.0, 0.0
	if cubicM > 0 {
		weightedCement = cementM / cubicM
		weightedFine = fineM / cubicM
	}
	summary := map[string]any{
		"assigned_count":      len(rows),
		"window_counts":       winCounts,
		"zone_counts":         zoneCounts,
		"lane_counts":         lineCounts,
		"delivered_cubic_m":   math.Round(cubicM*1e6) / 1e6,
		"weighted_cement_pct": math.Round(weightedCement*1e6) / 1e6,
		"weighted_fine_pct":   math.Round(weightedFine*1e6) / 1e6,
	}
	data, err := json.MarshalIndent(summary, "", "  ")
	must(err)
	must(os.WriteFile(filepath.Join(outputDir, "concrete_dispatch_summary.json"), append(data, '\n'), 0o644))
}
