#!/usr/bin/env bash
# Oracle: overwrite every defective source file with a corrected version,
# rebuild the binary, and emit the report. Implements every documented
# rule. The oracle uses the same data tree and produces the same output
# the verifier expects.
set -euo pipefail

# Defensive go toolchain bootstrap: handle stripped shells where PATH
# might not contain /usr/local/go/bin even though the Dockerfile sets it.
export HOME="${HOME:-/root}"
export PATH="/usr/local/go/bin:${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
export GOCACHE="${GOCACHE:-/tmp/go-cache}"
export GOPATH="${GOPATH:-/tmp/go-path}"
export GOFLAGS="${GOFLAGS:--mod=mod}"
export GOPROXY="${GOPROXY:-off}"
export GOSUMDB="${GOSUMDB:-off}"
export GOTOOLCHAIN="${GOTOOLCHAIN:-local}"
export CGO_ENABLED="${CGO_ENABLED:-0}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp}"

# Pre-flight: verify go toolchain is reachable; fail loudly if not.
echo "[oracle] PATH=$PATH"
if ! command -v go >/dev/null 2>&1; then
    if [ -x /usr/local/go/bin/go ]; then
        export PATH="/usr/local/go/bin:$PATH"
        echo "[oracle] go resolved via /usr/local/go/bin/go fallback"
    else
        echo "[oracle] FATAL: go not on PATH and /usr/local/go/bin/go missing" >&2
        exit 1
    fi
fi
echo "[oracle] go version: $(go version)"

cd /app
mkdir -p /app/output "$GOCACHE" "$GOPATH"

# loader.go — restore strict integer semantics (no float fallback)
cat > /app/internal/loader/loader.go <<'GOEOF'
package loader

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"twampowd/internal/types"
)

var intToken = regexp.MustCompile(`^-?[0-9]+$`)

func Load(dir string) (types.Config, []types.Reflector, []types.Probe, []types.Marker, error) {
	var cfg types.Config
	cfgBytes, err := os.ReadFile(filepath.Join(dir, "config.json"))
	if err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("config: %w", err)
	}
	if err := json.Unmarshal(cfgBytes, &cfg); err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("config decode: %w", err)
	}

	reflBytes, err := os.ReadFile(filepath.Join(dir, "reflectors.json"))
	if err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("reflectors: %w", err)
	}
	var refls []types.Reflector
	if err := json.Unmarshal(reflBytes, &refls); err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("reflectors decode: %w", err)
	}

	var probes []types.Probe
	for shardOrder, name := range []string{"probes_shard_a.ndjson", "probes_shard_b.ndjson"} {
		more, err := loadShard(filepath.Join(dir, name), shardOrder)
		if err != nil {
			return cfg, nil, nil, nil, fmt.Errorf("shard %s: %w", name, err)
		}
		probes = append(probes, more...)
	}

	markers, err := loadMarkers(filepath.Join(dir, "markers.ndjson"))
	if err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("markers: %w", err)
	}

	return cfg, refls, probes, markers, nil
}

func loadShard(path string, shardOrder int) ([]types.Probe, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
	var out []types.Probe
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var raw map[string]json.RawMessage
		if err := json.Unmarshal([]byte(line), &raw); err != nil {
			continue
		}
		p, ok := parseProbe(raw, shardOrder)
		if !ok {
			continue
		}
		out = append(out, p)
	}
	return out, sc.Err()
}

func parseProbe(raw map[string]json.RawMessage, shardOrder int) (types.Probe, bool) {
	var p types.Probe
	p.ShardOrder = shardOrder
	_ = json.Unmarshal(raw["probe_id"], &p.ProbeID)
	_ = json.Unmarshal(raw["session_id"], &p.SessionID)
	_ = json.Unmarshal(raw["reflector_id"], &p.ReflectorID)

	cyc, ok := strictInt(raw["cycle_id"])
	if !ok {
		return p, false
	}
	p.CycleID = cyc
	send, ok := strictInt(raw["send_ts"])
	if !ok {
		return p, false
	}
	p.SendTsUs = send
	recv, ok := strictInt(raw["recv_ts"])
	if !ok {
		return p, false
	}
	p.RecvTsUs = recv
	tx, ok := strictInt(raw["tx_ts"])
	if !ok {
		return p, false
	}
	p.TxTsUs = tx
	seq, ok := strictInt(raw["seq_no"])
	if !ok {
		return p, false
	}
	p.SeqNo = seq
	rms, _ := strictInt(raw["recv_minus_send"])
	p.RecvMinusSend = rms

	rawLF, hasLF := raw["loss_flag"]
	if !hasLF {
		return p, false
	}
	t := strings.TrimSpace(string(rawLF))
	if t != "true" && t != "false" {
		return p, false
	}
	p.LossFlag = t == "true"

	return p, true
}

func strictInt(raw json.RawMessage) (int64, bool) {
	s := strings.TrimSpace(string(raw))
	if strings.HasPrefix(s, "\"") {
		var q string
		if err := json.Unmarshal(raw, &q); err != nil {
			return 0, false
		}
		s = strings.TrimSpace(q)
	}
	if !intToken.MatchString(s) {
		return 0, false
	}
	v, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return 0, false
	}
	return v, true
}

func loadMarkers(path string) ([]types.Marker, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
	var out []types.Marker
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var m struct {
			MarkerID      string `json:"marker_id"`
			Kind          string `json:"kind"`
			CycleID       int64  `json:"cycle_id"`
			ReflectorID   string `json:"reflector_id"`
			WindowOpenUs  int64  `json:"window_open_us"`
			WindowCloseUs int64  `json:"window_close_us"`
			Seal          string `json:"seal"`
		}
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			continue
		}
		out = append(out, types.Marker{
			MarkerID:      m.MarkerID,
			Kind:          m.Kind,
			CycleID:       m.CycleID,
			ReflectorID:   m.ReflectorID,
			WindowOpenUs:  m.WindowOpenUs,
			WindowCloseUs: m.WindowCloseUs,
			Seal:          m.Seal,
		})
	}
	return out, sc.Err()
}
GOEOF

# config.go — picosecond threshold restored to 2e12
cat > /app/internal/config/config.go <<'GOEOF'
package config

import (
	"twampowd/internal/types"
)

func Canonicalize(probes []types.Probe) []types.Probe {
	const picoThreshold int64 = 2_000_000_000_000
	out := make([]types.Probe, 0, len(probes))
	for _, p := range probes {
		if p.SendTsUs >= picoThreshold {
			p.SendTsUs = p.SendTsUs / 1_000_000
		}
		out = append(out, p)
	}
	return out
}
GOEOF

# window.go — validity left-inclusive, stale uses strict >
cat > /app/internal/window/window.go <<'GOEOF'
package window

import (
	"twampowd/internal/types"
)

func Validity(probes []types.Probe, cfg types.Config) []types.Probe {
	out := make([]types.Probe, 0, len(probes))
	for _, p := range probes {
		if p.SendTsUs >= cfg.ValidityWindowStartUs && p.SendTsUs < cfg.ValidityWindowEndUs {
			out = append(out, p)
		}
	}
	return out
}

func Stale(p types.Probe, cfg types.Config) bool {
	return (p.RecvTsUs - p.SendTsUs) > cfg.StaleMaxUs
}
GOEOF

# verdict.go — canonical OWD = recv - send - tx, strict > anomaly
cat > /app/internal/verdict/verdict.go <<'GOEOF'
package verdict

import (
	"twampowd/internal/types"
	"twampowd/internal/window"
)

func Classify(probes []types.Probe, cfg types.Config) {
	for i := range probes {
		p := &probes[i]
		p.OwdUs = p.RecvTsUs - p.SendTsUs - p.TxTsUs
		if window.Stale(*p, cfg) {
			p.Verdict = "STALE_MEASUREMENT"
			continue
		}
		if p.LossFlag {
			p.Verdict = "LOSS_DETECTED"
			continue
		}
		if p.OwdUs > cfg.OwdAnomalyThresholdUs {
			p.Verdict = "OWD_ANOMALY"
			continue
		}
		p.Verdict = "WITHIN_BOUNDS"
	}
}

func Jitter(probes []types.Probe, cfg types.Config) {
	cycSums := map[int64]int64{}
	cycCounts := map[int64]int{}
	for _, p := range probes {
		if p.Verdict == "WITHIN_BOUNDS" {
			cycSums[p.CycleID] += p.OwdUs
			cycCounts[p.CycleID]++
		}
	}
	means := map[int64]int64{}
	for cyc, sum := range cycSums {
		c := cycCounts[cyc]
		if c > 0 {
			means[cyc] = sum / int64(c)
		}
	}
	for i := range probes {
		p := &probes[i]
		if p.Verdict != "WITHIN_BOUNDS" {
			continue
		}
		m, ok := means[p.CycleID]
		if !ok {
			continue
		}
		d := p.OwdUs - m
		if d < 0 {
			d = -d
		}
		if d > cfg.JitterFlagUs {
			p.Verdict = "JITTER_FLAGGED"
		}
	}
}
GOEOF

# aggregate.go — dedup keeps EARLIEST, cascade halves next cycle threshold,
# markers mute exactly one anomaly per (cycle, reflector) and require the
# anomaly's send_ts to fall in the marker window (left-exclusive, right-inclusive).
cat > /app/internal/aggregate/aggregate.go <<'GOEOF'
package aggregate

import (
	"fmt"
	"sort"

	"twampowd/internal/digest"
	"twampowd/internal/types"
)

var allVerdicts = []string{
	"JITTER_FLAGGED",
	"LOSS_DETECTED",
	"OWD_ANOMALY",
	"QUIET_SUPPRESSED",
	"REFLECTOR_OFFLINE",
	"STALE_MEASUREMENT",
	"WITHIN_BOUNDS",
}

func Dedup(probes []types.Probe) []types.Probe {
	idx := map[string]int{}
	for i, p := range probes {
		j, ok := idx[p.ProbeID]
		if !ok {
			idx[p.ProbeID] = i
			continue
		}
		other := probes[j]
		if p.SendTsUs < other.SendTsUs {
			idx[p.ProbeID] = i
		} else if p.SendTsUs == other.SendTsUs && p.ReflectorID < other.ReflectorID {
			idx[p.ProbeID] = i
		}
	}
	out := make([]types.Probe, 0, len(idx))
	seen := map[string]bool{}
	for _, p := range probes {
		i := idx[p.ProbeID]
		if seen[p.ProbeID] {
			continue
		}
		out = append(out, probes[i])
		seen[p.ProbeID] = true
	}
	return out
}

func Cascade(probes []types.Probe, cfg types.Config) []types.Probe {
	// Determine cycle order and per-cycle loss ratio.
	cycSet := map[int64]bool{}
	for _, p := range probes {
		cycSet[p.CycleID] = true
	}
	cycList := make([]int64, 0, len(cycSet))
	for c := range cycSet {
		cycList = append(cycList, c)
	}
	sort.Slice(cycList, func(i, j int) bool { return cycList[i] < cycList[j] })

	// Per-cycle counts using current verdict.
	probeCount := map[int64]int{}
	lossAnomCount := map[int64]int{}
	for _, p := range probes {
		probeCount[p.CycleID]++
		if p.Verdict == "LOSS_DETECTED" || p.Verdict == "OWD_ANOMALY" {
			lossAnomCount[p.CycleID]++
		}
	}

	// Compute thresholds for each cycle.
	thresholds := map[int64]int64{}
	prevThreshold := cfg.OwdAnomalyThresholdUs
	prevRatioTrips := false
	for _, c := range cycList {
		var thr int64
		if !prevRatioTrips {
			thr = cfg.OwdAnomalyThresholdUs
		} else {
			thr = prevThreshold / 2
		}
		thresholds[c] = thr
		// Determine if this cycle trips the cascade.
		ratio := 0.0
		if probeCount[c] > 0 {
			ratio = float64(lossAnomCount[c]) / float64(probeCount[c])
		}
		if ratio >= 0.02 {
			prevRatioTrips = true
			prevThreshold = thr
		} else {
			prevRatioTrips = false
			prevThreshold = cfg.OwdAnomalyThresholdUs
		}
	}

	// Reclassify WITHIN_BOUNDS that now exceed the tightened threshold,
	// and downgrade OWD_ANOMALY that no longer exceed (cycle 0 only — but
	// since cycle 0 always uses default, downgrade never fires for it).
	// We iterate again: anything WITHIN_BOUNDS becomes OWD_ANOMALY when
	// owd_us > threshold[cycle]; OWD_ANOMALY becomes WITHIN_BOUNDS when
	// owd_us <= threshold[cycle].
	for i := range probes {
		p := &probes[i]
		thr := thresholds[p.CycleID]
		switch p.Verdict {
		case "WITHIN_BOUNDS":
			if p.OwdUs > thr {
				p.Verdict = "OWD_ANOMALY"
			}
		case "OWD_ANOMALY":
			if p.OwdUs <= thr {
				p.Verdict = "WITHIN_BOUNDS"
			}
		}
	}

	// Recompute loss/anom counts after reclassification, then propagate
	// new ratios to influence later cycles. We need to re-run because
	// reclassification in cycle N can change cycle N's ratio.
	// Iterate fixed-point: at most len(cycList) passes.
	for pass := 0; pass < len(cycList)+2; pass++ {
		changed := false
		probeCount = map[int64]int{}
		lossAnomCount = map[int64]int{}
		for _, p := range probes {
			probeCount[p.CycleID]++
			if p.Verdict == "LOSS_DETECTED" || p.Verdict == "OWD_ANOMALY" {
				lossAnomCount[p.CycleID]++
			}
		}
		newThresholds := map[int64]int64{}
		prevTh := cfg.OwdAnomalyThresholdUs
		prevTrips := false
		for _, c := range cycList {
			var thr int64
			if !prevTrips {
				thr = cfg.OwdAnomalyThresholdUs
			} else {
				thr = prevTh / 2
			}
			newThresholds[c] = thr
			ratio := 0.0
			if probeCount[c] > 0 {
				ratio = float64(lossAnomCount[c]) / float64(probeCount[c])
			}
			if ratio >= 0.02 {
				prevTrips = true
				prevTh = thr
			} else {
				prevTrips = false
				prevTh = cfg.OwdAnomalyThresholdUs
			}
		}
		for c, thr := range newThresholds {
			if thr != thresholds[c] {
				changed = true
			}
		}
		thresholds = newThresholds
		if !changed {
			break
		}
		for i := range probes {
			p := &probes[i]
			thr := thresholds[p.CycleID]
			switch p.Verdict {
			case "WITHIN_BOUNDS":
				if p.OwdUs > thr {
					p.Verdict = "OWD_ANOMALY"
				}
			case "OWD_ANOMALY":
				if p.OwdUs <= thr {
					p.Verdict = "WITHIN_BOUNDS"
				}
			}
		}
	}

	// Cache thresholds for later use by CycleThresholds.
	cachedThresholds = thresholds
	return probes
}

var cachedThresholds = map[int64]int64{}

func CycleThresholds(probes []types.Probe, cfg types.Config) map[int64]int64 {
	if len(cachedThresholds) > 0 {
		return cachedThresholds
	}
	out := map[int64]int64{}
	cycles := map[int64]bool{}
	for _, p := range probes {
		cycles[p.CycleID] = true
	}
	for c := range cycles {
		out[c] = cfg.OwdAnomalyThresholdUs
	}
	return out
}

// ApplyMarkers consumes valid quiet_period markers, muting at most ONE
// OWD_ANOMALY per (cycle, reflector) scope. The anomaly chosen is the
// first within the marker's own (window_open_us, window_close_us]
// scoping window, ordered by send_ts then probe_id numeric suffix.
func ApplyMarkers(probes []types.Probe, markers []types.Marker, cfg types.Config) ([]types.Probe, map[string]int) {
	suppressed := map[string]int{}

	// Validate markers and group by (cycle, reflector).
	type validMarker struct {
		open, close int64
	}
	type key struct {
		cyc  int64
		refl string
	}
	groupedMarkers := map[key][]validMarker{}
	for _, m := range markers {
		if m.Kind != "quiet_period" {
			continue
		}
		expected := digest.Seal8(m.MarkerID, m.Kind, m.CycleID, m.ReflectorID, cfg.Secret)
		if m.Seal != expected {
			continue
		}
		k := key{cyc: m.CycleID, refl: m.ReflectorID}
		groupedMarkers[k] = append(groupedMarkers[k], validMarker{open: m.WindowOpenUs, close: m.WindowCloseUs})
	}

	// Stable order over markers per group (by open then close).
	for k := range groupedMarkers {
		ms := groupedMarkers[k]
		sort.SliceStable(ms, func(i, j int) bool {
			if ms[i].open != ms[j].open {
				return ms[i].open < ms[j].open
			}
			return ms[i].close < ms[j].close
		})
		groupedMarkers[k] = ms
	}

	// Group OWD_ANOMALY probes per (cycle, reflector) in send-order.
	anomIdxByKey := map[key][]int{}
	for i, p := range probes {
		if p.Verdict != "OWD_ANOMALY" {
			continue
		}
		k := key{cyc: p.CycleID, refl: p.ReflectorID}
		anomIdxByKey[k] = append(anomIdxByKey[k], i)
	}
	for k := range anomIdxByKey {
		idxs := anomIdxByKey[k]
		sort.SliceStable(idxs, func(a, b int) bool {
			if probes[idxs[a]].SendTsUs != probes[idxs[b]].SendTsUs {
				return probes[idxs[a]].SendTsUs < probes[idxs[b]].SendTsUs
			}
			return types.NumericSuffix(probes[idxs[a]].ProbeID) < types.NumericSuffix(probes[idxs[b]].ProbeID)
		})
		anomIdxByKey[k] = idxs
	}

	for k, ms := range groupedMarkers {
		idxs := anomIdxByKey[k]
		consumed := map[int]bool{}
		for _, m := range ms {
			for _, i := range idxs {
				if consumed[i] {
					continue
				}
				p := &probes[i]
				// marker window (open, close], left-exclusive
				if p.SendTsUs > m.open && p.SendTsUs <= m.close {
					p.Verdict = "QUIET_SUPPRESSED"
					suppressed[p.ReflectorID]++
					consumed[i] = true
					break
				}
			}
		}
	}
	return probes, suppressed
}

// SyntheticOffline appends one synthetic REFLECTOR_OFFLINE row per
// (cycle, reflector) pair that had zero surviving probes in this run.
func SyntheticOffline(probes []types.Probe, refls []types.Reflector) []types.Probe {
	cycles := map[int64]bool{}
	have := map[string]bool{}
	for _, p := range probes {
		cycles[p.CycleID] = true
		have[fmt.Sprintf("%d|%s", p.CycleID, p.ReflectorID)] = true
	}
	cycList := make([]int64, 0, len(cycles))
	for c := range cycles {
		cycList = append(cycList, c)
	}
	sort.Slice(cycList, func(i, j int) bool { return cycList[i] < cycList[j] })
	for _, c := range cycList {
		for _, r := range refls {
			k := fmt.Sprintf("%d|%s", c, r.ReflectorID)
			if have[k] {
				continue
			}
			probes = append(probes, types.Probe{
				ProbeID:     fmt.Sprintf("OFFLINE-%s-%d", r.ReflectorID, c),
				SessionID:   "-",
				CycleID:     c,
				ReflectorID: r.ReflectorID,
				Verdict:     "REFLECTOR_OFFLINE",
				OwdUs:       0,
			})
		}
	}
	return probes
}

func CountVerdict(probes []types.Probe, v string) int {
	n := 0
	for _, p := range probes {
		if p.Verdict == v {
			n++
		}
	}
	return n
}

func ByVerdict(probes []types.Probe) map[string]int {
	out := map[string]int{}
	for _, v := range allVerdicts {
		out[v] = 0
	}
	for _, p := range probes {
		out[p.Verdict]++
	}
	return out
}

func CycleRows(probes []types.Probe, cfg types.Config) []types.CycleRow {
	thresholds := CycleThresholds(probes, cfg)
	contributors := map[int64]map[string]bool{}
	counts := map[int64]int{}
	losses := map[int64]int{}
	anomalies := map[int64]int{}
	for _, p := range probes {
		if p.Verdict == "REFLECTOR_OFFLINE" {
			continue
		}
		counts[p.CycleID]++
		if contributors[p.CycleID] == nil {
			contributors[p.CycleID] = map[string]bool{}
		}
		contributors[p.CycleID][p.ReflectorID] = true
		switch p.Verdict {
		case "LOSS_DETECTED":
			losses[p.CycleID]++
		case "OWD_ANOMALY":
			anomalies[p.CycleID]++
		}
	}
	out := make([]types.CycleRow, 0, len(counts))
	for c := range counts {
		contribs := make([]string, 0, len(contributors[c]))
		for r := range contributors[c] {
			contribs = append(contribs, r)
		}
		sort.SliceStable(contribs, func(i, j int) bool { return types.SuffixLess(contribs[i], contribs[j]) })
		out = append(out, types.CycleRow{
			CycleID:        c,
			ProbeCount:     counts[c],
			LossCount:      losses[c],
			AnomalyCount:   anomalies[c],
			ThresholdOwdUs: thresholds[c],
			Contributors:   contribs,
		})
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].CycleID < out[j].CycleID })
	return out
}

func ReflectorRows(probes []types.Probe, refls []types.Reflector, suppressed map[string]int) []types.ReflectorRow {
	probeCount := map[string]int{}
	anomCount := map[string]int{}
	offlineByCycle := map[string]bool{}
	cycles := map[int64]bool{}
	have := map[string]bool{}
	for _, p := range probes {
		if p.Verdict == "REFLECTOR_OFFLINE" {
			continue
		}
		cycles[p.CycleID] = true
		have[fmt.Sprintf("%d|%s", p.CycleID, p.ReflectorID)] = true
		probeCount[p.ReflectorID]++
		if p.Verdict == "OWD_ANOMALY" {
			anomCount[p.ReflectorID]++
		}
	}
	for _, r := range refls {
		for c := range cycles {
			if !have[fmt.Sprintf("%d|%s", c, r.ReflectorID)] {
				offlineByCycle[r.ReflectorID] = true
			}
		}
	}
	rows := make([]types.ReflectorRow, 0, len(refls))
	for _, r := range refls {
		rows = append(rows, types.ReflectorRow{
			ReflectorID:           r.ReflectorID,
			Station:               r.Station,
			Class:                 r.Class,
			ProbeCount:            probeCount[r.ReflectorID],
			AnomalyCount:          anomCount[r.ReflectorID],
			QuietPeriodSuppressed: suppressed[r.ReflectorID],
			OfflineObserved:       offlineByCycle[r.ReflectorID],
		})
	}
	sort.SliceStable(rows, func(i, j int) bool { return types.SuffixLess(rows[i].ReflectorID, rows[j].ReflectorID) })
	return rows
}

func ProbeRows(probes []types.Probe) []types.ProbeRow {
	rows := make([]types.ProbeRow, 0, len(probes))
	for _, p := range probes {
		rows = append(rows, types.ProbeRow{
			ProbeID:     p.ProbeID,
			SessionID:   p.SessionID,
			CycleID:     p.CycleID,
			ReflectorID: p.ReflectorID,
			OwdUs:       p.OwdUs,
			Verdict:     p.Verdict,
		})
	}
	sort.SliceStable(rows, func(i, j int) bool { return types.SuffixLess(rows[i].ProbeID, rows[j].ProbeID) })
	return rows
}
GOEOF

# allocate.go — tiebreak flips to descending when any reflector observed offline
cat > /app/internal/allocate/allocate.go <<'GOEOF'
package allocate

import (
	"fmt"
	"sort"

	"twampowd/internal/types"
)

func JitterShares(probes []types.Probe, refls []types.Reflector) map[string]int64 {
	weights := map[string]int64{}
	for _, r := range refls {
		weights[r.ReflectorID] = 0
	}
	for _, p := range probes {
		switch p.Verdict {
		case "WITHIN_BOUNDS", "OWD_ANOMALY", "JITTER_FLAGGED", "QUIET_SUPPRESSED":
			weights[p.ReflectorID]++
		}
	}
	// detect offline cycles
	cycles := map[int64]bool{}
	have := map[string]bool{}
	for _, p := range probes {
		if p.Verdict == "REFLECTOR_OFFLINE" {
			continue
		}
		cycles[p.CycleID] = true
		have[fmt.Sprintf("%d|%s", p.CycleID, p.ReflectorID)] = true
	}
	anyOffline := false
	for _, r := range refls {
		for c := range cycles {
			if !have[fmt.Sprintf("%d|%s", c, r.ReflectorID)] {
				anyOffline = true
				break
			}
		}
		if anyOffline {
			break
		}
	}
	out := map[string]int64{}
	var total int64
	for _, w := range weights {
		total += w
	}
	if total == 0 {
		for _, r := range refls {
			out[r.ReflectorID] = 0
		}
		return out
	}
	type pair struct {
		Name  string
		Floor int64
		Rem   int64
	}
	pairs := make([]pair, 0, len(refls))
	var floorSum int64
	for _, r := range refls {
		num := weights[r.ReflectorID] * 1000
		fl := num / total
		out[r.ReflectorID] = fl
		floorSum += fl
		pairs = append(pairs, pair{Name: r.ReflectorID, Floor: fl, Rem: num - fl*total})
	}
	leftover := int64(1000) - floorSum
	sort.SliceStable(pairs, func(a, b int) bool {
		if pairs[a].Rem != pairs[b].Rem {
			return pairs[a].Rem > pairs[b].Rem
		}
		na := types.NumericSuffix(pairs[a].Name)
		nb := types.NumericSuffix(pairs[b].Name)
		if anyOffline {
			if na != nb {
				return na > nb
			}
			return pairs[a].Name > pairs[b].Name
		}
		if na != nb {
			return na < nb
		}
		return pairs[a].Name < pairs[b].Name
	})
	for i := int64(0); i < leftover && i < int64(len(pairs)); i++ {
		out[pairs[i].Name]++
	}
	return out
}
GOEOF

# digest.go — 8-char seal, ## separator
cat > /app/internal/digest/digest.go <<'GOEOF'
package digest

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"
	"strings"

	"twampowd/internal/types"
)

func Seal8(markerID, kind string, cycleID int64, reflectorID, secret string) string {
	s := fmt.Sprintf("%s|%s|%d|%s|%s", markerID, kind, cycleID, reflectorID, secret)
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])[:8]
}

func Report(rep types.Report) string {
	probeLines := make([]string, 0, len(rep.Probes))
	for _, p := range rep.Probes {
		probeLines = append(probeLines, fmt.Sprintf("%s|%s|%s|%d", p.ProbeID, p.ReflectorID, p.Verdict, p.OwdUs))
	}
	keys := make([]string, 0, len(rep.Summary.JitterSharePermille))
	for k := range rep.Summary.JitterSharePermille {
		keys = append(keys, k)
	}
	sort.SliceStable(keys, func(i, j int) bool { return types.SuffixLess(keys[i], keys[j]) })
	shareParts := make([]string, 0, len(keys))
	for _, k := range keys {
		shareParts = append(shareParts, fmt.Sprintf("%s=%d", k, rep.Summary.JitterSharePermille[k]))
	}
	var b strings.Builder
	b.WriteString(strings.Join(probeLines, "\n"))
	b.WriteString("\n##\n")
	b.WriteString(strings.Join(shareParts, "|"))
	b.WriteString("\n##\n")
	b.WriteString(fmt.Sprintf("summary:total=%d;good=%d;cycles=%d\n",
		rep.Summary.TotalProbes, rep.Summary.AlignedGood, rep.Summary.Cycles))
	sum := sha256.Sum256([]byte(b.String()))
	return hex.EncodeToString(sum[:])
}
GOEOF

# emit.go — full closed enum, numeric-suffix order on jitter_share keys
cat > /app/internal/emit/emit.go <<'GOEOF'
package emit

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"twampowd/internal/types"
)

var AllVerdicts = []string{
	"JITTER_FLAGGED",
	"LOSS_DETECTED",
	"OWD_ANOMALY",
	"QUIET_SUPPRESSED",
	"REFLECTOR_OFFLINE",
	"STALE_MEASUREMENT",
	"WITHIN_BOUNDS",
}

func Write(outPath string, rep types.Report) error {
	parent := filepath.Dir(outPath)
	if err := os.MkdirAll(parent, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(parent)
	if err != nil {
		return err
	}
	for _, e := range entries {
		_ = os.RemoveAll(filepath.Join(parent, e.Name()))
	}
	data := render(rep)
	tmp := outPath + ".tmp"
	if err := os.WriteFile(tmp, []byte(data), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, outPath)
}

func render(rep types.Report) string {
	var b strings.Builder
	b.WriteString("{\n")
	b.WriteString(fmt.Sprintf("  \"schema_version\": %q,\n", rep.SchemaVersion))
	b.WriteString("  \"summary\": {\n")
	b.WriteString(fmt.Sprintf("    \"total_probes\": %d,\n", rep.Summary.TotalProbes))
	b.WriteString(fmt.Sprintf("    \"aligned_good\": %d,\n", rep.Summary.AlignedGood))
	b.WriteString(fmt.Sprintf("    \"cycles\": %d,\n", rep.Summary.Cycles))
	b.WriteString("    \"by_verdict\": {\n")
	for i, v := range AllVerdicts {
		comma := ","
		if i == len(AllVerdicts)-1 {
			comma = ""
		}
		b.WriteString(fmt.Sprintf("      %q: %d%s\n", v, rep.Summary.ByVerdict[v], comma))
	}
	b.WriteString("    },\n")
	b.WriteString("    \"jitter_share_permille\": {\n")
	shareKeys := make([]string, 0, len(rep.Summary.JitterSharePermille))
	for k := range rep.Summary.JitterSharePermille {
		shareKeys = append(shareKeys, k)
	}
	sort.SliceStable(shareKeys, func(i, j int) bool { return types.SuffixLess(shareKeys[i], shareKeys[j]) })
	for i, k := range shareKeys {
		comma := ","
		if i == len(shareKeys)-1 {
			comma = ""
		}
		b.WriteString(fmt.Sprintf("      %q: %d%s\n", k, rep.Summary.JitterSharePermille[k], comma))
	}
	b.WriteString("    },\n")
	b.WriteString(fmt.Sprintf("    \"report_digest\": %q\n", rep.Summary.ReportDigest))
	b.WriteString("  },\n")

	b.WriteString("  \"reflectors\": [")
	if len(rep.Reflectors) == 0 {
		b.WriteString("],\n")
	} else {
		b.WriteString("\n")
		for i, r := range rep.Reflectors {
			b.WriteString("    {\n")
			b.WriteString(fmt.Sprintf("      \"reflector_id\": %q,\n", r.ReflectorID))
			b.WriteString(fmt.Sprintf("      \"station\": %q,\n", r.Station))
			b.WriteString(fmt.Sprintf("      \"class\": %q,\n", r.Class))
			b.WriteString(fmt.Sprintf("      \"probe_count\": %d,\n", r.ProbeCount))
			b.WriteString(fmt.Sprintf("      \"anomaly_count\": %d,\n", r.AnomalyCount))
			b.WriteString(fmt.Sprintf("      \"quiet_period_suppressed\": %d,\n", r.QuietPeriodSuppressed))
			b.WriteString(fmt.Sprintf("      \"offline_observed\": %t,\n", r.OfflineObserved))
			b.WriteString(fmt.Sprintf("      \"jitter_share_permille\": %d\n", r.JitterSharePermille))
			comma := ","
			if i == len(rep.Reflectors)-1 {
				comma = ""
			}
			b.WriteString(fmt.Sprintf("    }%s\n", comma))
		}
		b.WriteString("  ],\n")
	}

	b.WriteString("  \"cycles\": [")
	if len(rep.Cycles) == 0 {
		b.WriteString("],\n")
	} else {
		b.WriteString("\n")
		for i, c := range rep.Cycles {
			b.WriteString("    {\n")
			b.WriteString(fmt.Sprintf("      \"cycle_id\": %d,\n", c.CycleID))
			b.WriteString(fmt.Sprintf("      \"probe_count\": %d,\n", c.ProbeCount))
			b.WriteString(fmt.Sprintf("      \"loss_count\": %d,\n", c.LossCount))
			b.WriteString(fmt.Sprintf("      \"anomaly_count\": %d,\n", c.AnomalyCount))
			b.WriteString(fmt.Sprintf("      \"threshold_owd_us\": %d,\n", c.ThresholdOwdUs))
			b.WriteString("      \"contributors\": [")
			for j, name := range c.Contributors {
				sep := ", "
				if j == 0 {
					sep = ""
				}
				b.WriteString(fmt.Sprintf("%s%q", sep, name))
			}
			b.WriteString("]\n")
			comma := ","
			if i == len(rep.Cycles)-1 {
				comma = ""
			}
			b.WriteString(fmt.Sprintf("    }%s\n", comma))
		}
		b.WriteString("  ],\n")
	}

	b.WriteString("  \"probes\": [")
	if len(rep.Probes) == 0 {
		b.WriteString("],\n")
	} else {
		b.WriteString("\n")
		for i, p := range rep.Probes {
			b.WriteString("    {\n")
			b.WriteString(fmt.Sprintf("      \"probe_id\": %q,\n", p.ProbeID))
			b.WriteString(fmt.Sprintf("      \"session_id\": %q,\n", p.SessionID))
			b.WriteString(fmt.Sprintf("      \"cycle_id\": %d,\n", p.CycleID))
			b.WriteString(fmt.Sprintf("      \"reflector_id\": %q,\n", p.ReflectorID))
			b.WriteString(fmt.Sprintf("      \"owd_us\": %d,\n", p.OwdUs))
			b.WriteString(fmt.Sprintf("      \"verdict\": %q\n", p.Verdict))
			comma := ","
			if i == len(rep.Probes)-1 {
				comma = ""
			}
			b.WriteString(fmt.Sprintf("    }%s\n", comma))
		}
		b.WriteString("  ],\n")
	}

	b.WriteString(fmt.Sprintf("  \"report_digest\": %q\n", rep.ReportDigest))
	b.WriteString("}\n")
	return b.String()
}
GOEOF

echo "[oracle] make build start"
if ! make -C /app build 2>&1 | tee /tmp/oracle_build.log; then
    echo "[oracle] FATAL: make build failed" >&2
    tail -50 /tmp/oracle_build.log >&2
    exit 1
fi
if [ ! -x /app/bin/auditor ]; then
    echo "[oracle] FATAL: /app/bin/auditor missing or not executable" >&2
    ls -la /app/bin/ >&2
    exit 1
fi
echo "[oracle] make build done, binary at /app/bin/auditor"

echo "[oracle] running auditor against /app/data"
if ! /app/bin/auditor --data /app/data --out /app/output/report.json 2>&1 | tee /tmp/oracle_run.log; then
    echo "[oracle] FATAL: auditor exited non-zero" >&2
    exit 1
fi
if [ ! -f /app/output/report.json ]; then
    echo "[oracle] FATAL: /app/output/report.json was not produced" >&2
    ls -la /app/output/ >&2
    exit 1
fi
echo "[oracle] report written; size=$(wc -c < /app/output/report.json) bytes"
echo "[oracle] done"
