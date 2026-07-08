package main

import (
	"bufio"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

var unsignedRe = regexp.MustCompile(`^(0|[1-9][0-9]*)(\.[0-9]{1,3})?$`)
var signedRe = regexp.MustCompile(`^-?(0|[1-9][0-9]*)(\.[0-9]{1,3})?$`)

type Policy struct {
	SchemaVersion       string            `json:"schema_version"`
	OutputSchemaVersion string            `json:"output_schema_version"`
	ChamberRank         map[string]int    `json:"chamber_rank"`
	Thresholds          map[string]string `json:"thresholds"`
}

type Sensor struct {
	ID          string
	Chamber     string
	StationID   string
	Status      string
	InstalledAt string
}

type Batch struct {
	ID        string
	Chamber   string
	Start     time.Time
	End       time.Time
	CapacityM int64
}

type Waiver struct {
	ID       string
	BatchID  string
	SensorID string
	Kind     string
	Expires  time.Time
	BonusM   int64
	RemM     int64
}

type Transfer struct {
	ID            string
	SourceBatchID string
	TargetBatchID string
	Opens         time.Time
	Expires       time.Time
	MaxM          int64
	EfficiencyPPM int64
	RemM          int64
	TransferredM  int64
	ConsumedM     int64
	Status        string
}

type Observation struct {
	ObsID        string `json:"obs_id"`
	SensorID     string `json:"sensor_id"`
	BatchID      string `json:"batch_id"`
	CapturedAt   string `json:"captured_at"`
	VolumeML     string `json:"volume_ml"`
	EC           string `json:"ec_uS_cm"`
	DeltaO18     string `json:"delta_o18"`
	Turbidity    string `json:"turbidity_ntu"`
	Operator     string `json:"operator"`
	capturedTime time.Time
	lineNo       int
}

type Candidate struct {
	Obs       Observation
	Sensor    Sensor
	Batch     Batch
	VolumeM   int64
	ECM       int64
	DeltaM    int64
	TurbM     int64
	Reasons   []string
	RiskBand  string
	RiskScore int
}

type AcceptedRow struct {
	ObsID          string   `json:"obs_id"`
	SensorID       string   `json:"sensor_id"`
	BatchID        string   `json:"batch_id"`
	Chamber        string   `json:"chamber"`
	CapturedAt     string   `json:"captured_at"`
	VolumeML       float64  `json:"volume_ml"`
	RiskBand       string   `json:"risk_band"`
	ReasonCodes    []string `json:"reason_codes"`
	CapacitySource string   `json:"capacity_source"`
	SequenceIndex  int      `json:"sequence_index"`
}

type DeferredRow struct {
	ObsID               string   `json:"obs_id"`
	BatchID             string   `json:"batch_id"`
	Chamber             string   `json:"chamber"`
	RequestedML         float64  `json:"requested_ml"`
	RemainingBaseML     float64  `json:"remaining_base_ml"`
	AvailableTransferML float64  `json:"available_transfer_ml"`
	AvailableBonusML    float64  `json:"available_bonus_ml"`
	ReasonCodes         []string `json:"reason_codes"`
	SequenceIndex       int      `json:"sequence_index"`
}

type QuarantineRow struct {
	RecordID string `json:"record_id"`
	ObsID    string `json:"obs_id"`
	Code     string `json:"code"`
	Detail   string `json:"detail"`
	Chamber  string `json:"-"`
}

type RiskCounts struct {
	Normal   int `json:"normal"`
	Watch    int `json:"watch"`
	Critical int `json:"critical"`
}

type BatchSummary struct {
	BatchID        string     `json:"batch_id"`
	Chamber        string     `json:"chamber"`
	CapacityML     float64    `json:"capacity_ml"`
	TransferInML   float64    `json:"transfer_in_ml"`
	TransferOutML  float64    `json:"transfer_out_ml"`
	BonusGrantedML float64    `json:"bonus_granted_ml"`
	BaseUsedML     float64    `json:"base_used_ml"`
	TransferUsedML float64    `json:"transfer_used_ml"`
	BonusUsedML    float64    `json:"bonus_used_ml"`
	AcceptedCount  int        `json:"accepted_count"`
	DeferredCount  int        `json:"deferred_count"`
	RiskCounts     RiskCounts `json:"risk_counts"`
}

type TransferSummary struct {
	TransferID    string  `json:"transfer_id"`
	SourceBatchID string  `json:"source_batch_id"`
	TargetBatchID string  `json:"target_batch_id"`
	RequestedML   float64 `json:"requested_ml"`
	TransferredML float64 `json:"transferred_ml"`
	ConsumedML    float64 `json:"consumed_ml"`
	Status        string  `json:"status"`
}

type ChamberSummary struct {
	Chamber          string  `json:"chamber"`
	AcceptedVolumeML float64 `json:"accepted_volume_ml"`
	AcceptedCount    int     `json:"accepted_count"`
	DeferredCount    int     `json:"deferred_count"`
	QuarantineCount  int     `json:"quarantine_count"`
}

type Report struct {
	SchemaVersion        string            `json:"schema_version"`
	AllocationOrder      []string          `json:"allocation_order"`
	AcceptedObservations []AcceptedRow     `json:"accepted_observations"`
	DeferredObservations []DeferredRow     `json:"deferred_observations"`
	Quarantine           []QuarantineRow   `json:"quarantine"`
	BatchSummary         []BatchSummary    `json:"batch_summary"`
	TransferSummary      []TransferSummary `json:"transfer_summary"`
	ChamberSummary       []ChamberSummary  `json:"chamber_summary"`
	Digest               string            `json:"digest"`
}

type batchLedger struct {
	baseRemaining int64
	baseUsed      int64
	bonusGranted  int64
	bonusUsed     int64
	transferIn    int64
	transferOut   int64
	transferUsed  int64
	accepted      int
	deferred      int
	risks         RiskCounts
}

type chamberLedger struct {
	acceptedVolume int64
	accepted       int
	deferred       int
	quarantine     int
}

func main() {
	input := flag.String("input", "/app/input", "input directory")
	output := flag.String("output", "/app/output/dripline_report.json", "output report path")
	flag.Parse()

	if err := run(*input, *output); err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
}

func run(inputDir string, outputPath string) error {
	st, err := os.Stat(inputDir)
	if err != nil || !st.IsDir() {
		return fmt.Errorf("missing input directory: %s", inputDir)
	}

	policy, err := loadPolicy(filepath.Join(inputDir, "policy.json"))
	if err != nil {
		return err
	}
	thresholds, err := parseThresholds(policy)
	if err != nil {
		return err
	}
	sensors, err := loadSensors(filepath.Join(inputDir, "sensors.csv"))
	if err != nil {
		return err
	}
	batches, err := loadBatches(filepath.Join(inputDir, "batches.csv"))
	if err != nil {
		return err
	}
	waivers, err := loadWaivers(filepath.Join(inputDir, "waivers.csv"))
	if err != nil {
		return err
	}
	transfers, err := loadTransfers(filepath.Join(inputDir, "transfers.csv"))
	if err != nil {
		return err
	}
	candidates, quarantine, err := loadObservations(filepath.Join(inputDir, "observations.ndjson"), sensors, batches, waivers, thresholds)
	if err != nil {
		return err
	}
	sortCandidates(candidates, policy.ChamberRank)
	report := allocate(policy, sensors, batches, waivers, transfers, candidates, quarantine)

	if err := os.MkdirAll(filepath.Dir(outputPath), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(outputPath, data, 0o644)
}

func loadPolicy(path string) (Policy, error) {
	var policy Policy
	data, err := os.ReadFile(path)
	if err != nil {
		return policy, err
	}
	if err := json.Unmarshal(data, &policy); err != nil {
		return policy, err
	}
	if policy.ChamberRank == nil {
		policy.ChamberRank = map[string]int{}
	}
	return policy, nil
}

func parseThresholds(policy Policy) (map[string]int64, error) {
	keys := []string{"ec_min", "ec_max", "turbidity_max", "delta_o18_min", "delta_o18_max"}
	out := map[string]int64{}
	for _, key := range keys {
		val, ok := policy.Thresholds[key]
		if !ok {
			return nil, fmt.Errorf("missing policy threshold: %s", key)
		}
		parsed, ok := parseDecimal(val, true)
		if !ok {
			return nil, fmt.Errorf("bad policy threshold: %s", key)
		}
		out[key] = parsed
	}
	return out, nil
}

func loadSensors(path string) (map[string]Sensor, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	sensors := map[string]Sensor{}
	for _, r := range rows {
		sensors[r[0]] = Sensor{ID: r[0], Chamber: r[1], StationID: r[2], Status: r[3], InstalledAt: r[4]}
	}
	return sensors, nil
}

func loadBatches(path string) (map[string]Batch, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	batches := map[string]Batch{}
	for _, r := range rows {
		start, err := time.Parse(time.RFC3339, r[2])
		if err != nil {
			return nil, err
		}
		end, err := time.Parse(time.RFC3339, r[3])
		if err != nil {
			return nil, err
		}
		capM, ok := parseDecimal(r[4], false)
		if !ok {
			return nil, fmt.Errorf("bad batch capacity: %s", r[0])
		}
		batches[r[0]] = Batch{ID: r[0], Chamber: r[1], Start: start, End: end, CapacityM: capM}
	}
	return batches, nil
}

func loadWaivers(path string) ([]*Waiver, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	waivers := make([]*Waiver, 0, len(rows))
	for _, r := range rows {
		expires, err := time.Parse(time.RFC3339, r[4])
		if err != nil {
			return nil, err
		}
		bonus, ok := parseDecimal(r[5], false)
		if !ok {
			return nil, fmt.Errorf("bad waiver bonus: %s", r[0])
		}
		w := &Waiver{ID: r[0], BatchID: r[1], SensorID: r[2], Kind: r[3], Expires: expires, BonusM: bonus, RemM: bonus}
		waivers = append(waivers, w)
	}
	sort.SliceStable(waivers, func(i, j int) bool { return waivers[i].ID < waivers[j].ID })
	return waivers, nil
}

func loadTransfers(path string) ([]*Transfer, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	transfers := make([]*Transfer, 0, len(rows))
	for _, r := range rows {
		opens, err := time.Parse(time.RFC3339, r[3])
		if err != nil {
			return nil, err
		}
		expires, err := time.Parse(time.RFC3339, r[4])
		if err != nil {
			return nil, err
		}
		maxM, ok := parseDecimal(r[5], false)
		if !ok {
			return nil, fmt.Errorf("bad transfer max: %s", r[0])
		}
		effM, ok := parseDecimal(r[6], false)
		if !ok || effM%1000 != 0 || effM < 0 || effM > 1000000*1000 {
			return nil, fmt.Errorf("bad transfer efficiency: %s", r[0])
		}
		t := &Transfer{ID: r[0], SourceBatchID: r[1], TargetBatchID: r[2], Opens: opens, Expires: expires, MaxM: maxM, EfficiencyPPM: effM / 1000, RemM: 0, Status: "pending"}
		transfers = append(transfers, t)
	}
	sort.SliceStable(transfers, func(i, j int) bool { return transfers[i].ID < transfers[j].ID })
	return transfers, nil
}

func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	all, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(all) == 0 {
		return nil, errors.New("empty csv")
	}
	return all[1:], nil
}

func loadObservations(path string, sensors map[string]Sensor, batches map[string]Batch, waivers []*Waiver, thresholds map[string]int64) ([]Candidate, []QuarantineRow, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	var candidates []Candidate
	var quarantine []QuarantineRow
	seen := map[string]bool{}
	scanner := bufio.NewScanner(f)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		raw := scanner.Text()
		var obs Observation
		if err := json.Unmarshal([]byte(raw), &obs); err != nil {
			quarantine = append(quarantine, q(lineNo, "", "bad_json", fmt.Sprintf("line:%d|json", lineNo), "unknown"))
			continue
		}
		obs.lineNo = lineNo
		if strings.TrimSpace(obs.ObsID) == "" {
			quarantine = append(quarantine, q(lineNo, "", "missing_obs_id", "obs_id missing", chamberFromRaw(obs.SensorID, obs.BatchID, sensors, batches)))
			continue
		}
		if seen[obs.ObsID] {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "duplicate_obs_id", "obs_id:"+obs.ObsID, chamberFromRaw(obs.SensorID, obs.BatchID, sensors, batches)))
			continue
		}
		seen[obs.ObsID] = true

		sensor, ok := sensors[obs.SensorID]
		if !ok {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "unknown_sensor", "sensor:"+obs.SensorID, chamberFromRaw(obs.SensorID, obs.BatchID, sensors, batches)))
			continue
		}
		batch, ok := batches[obs.BatchID]
		if !ok {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "unknown_batch", "batch:"+obs.BatchID, sensor.Chamber))
			continue
		}
		if sensor.Chamber != batch.Chamber {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "chamber_mismatch", "sensor:"+sensor.Chamber+"|batch:"+batch.Chamber, sensor.Chamber))
			continue
		}
		captured, err := time.Parse(time.RFC3339, obs.CapturedAt)
		if err != nil {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "bad_timestamp", "captured_at:"+obs.CapturedAt, sensor.Chamber))
			continue
		}
		obs.capturedTime = captured
		if captured.Before(batch.Start) || !captured.Before(batch.End) {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "outside_batch_window", "batch:"+obs.BatchID, sensor.Chamber))
			continue
		}

		reasons := []string{}
		if sensor.Status != "active" {
			if activeMaintenanceWaiver(waivers, obs.BatchID, obs.SensorID, captured) {
				reasons = append(reasons, "maintenance_waived")
			} else {
				quarantine = append(quarantine, q(lineNo, obs.ObsID, "sensor_not_active", "sensor:"+obs.SensorID+"|status:"+sensor.Status, sensor.Chamber))
				continue
			}
		}

		vol, ok := parseDecimal(obs.VolumeML, false)
		if !ok {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "bad_numeric", "volume_ml:"+obs.VolumeML, sensor.Chamber))
			continue
		}
		ec, ok := parseDecimal(obs.EC, false)
		if !ok {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "bad_numeric", "ec_uS_cm:"+obs.EC, sensor.Chamber))
			continue
		}
		delta, ok := parseDecimal(obs.DeltaO18, true)
		if !ok {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "bad_numeric", "delta_o18:"+obs.DeltaO18, sensor.Chamber))
			continue
		}
		turb, ok := parseDecimal(obs.Turbidity, false)
		if !ok {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "bad_numeric", "turbidity_ntu:"+obs.Turbidity, sensor.Chamber))
			continue
		}
		if vol == 0 {
			quarantine = append(quarantine, q(lineNo, obs.ObsID, "nonpositive_volume", "volume_ml:0", sensor.Chamber))
			continue
		}

		riskReasons := 0
		if ec < thresholds["ec_min"] || ec > thresholds["ec_max"] {
			reasons = append(reasons, "ec_out_of_range")
			riskReasons++
		}
		if turb > thresholds["turbidity_max"] {
			reasons = append(reasons, "turbidity_high")
			riskReasons++
		}
		if delta < thresholds["delta_o18_min"] || delta > thresholds["delta_o18_max"] {
			reasons = append(reasons, "isotope_shift")
			riskReasons++
		}
		risk := "normal"
		if riskReasons == 1 {
			risk = "watch"
		} else if riskReasons >= 2 {
			risk = "critical"
		}
		candidates = append(candidates, Candidate{Obs: obs, Sensor: sensor, Batch: batch, VolumeM: vol, ECM: ec, DeltaM: delta, TurbM: turb, Reasons: reasons, RiskBand: risk, RiskScore: riskReasons})
	}
	if err := scanner.Err(); err != nil {
		return nil, nil, err
	}
	return candidates, quarantine, nil
}

func q(lineNo int, obsID string, code string, detail string, chamber string) QuarantineRow {
	if chamber == "" {
		chamber = "unknown"
	}
	return QuarantineRow{RecordID: fmt.Sprintf("line:%d", lineNo), ObsID: obsID, Code: code, Detail: detail, Chamber: chamber}
}

func chamberFromRaw(sensorID string, batchID string, sensors map[string]Sensor, batches map[string]Batch) string {
	if s, ok := sensors[sensorID]; ok {
		return s.Chamber
	}
	if b, ok := batches[batchID]; ok {
		return b.Chamber
	}
	return "unknown"
}

func parseDecimal(raw string, signed bool) (int64, bool) {
	if signed {
		if !signedRe.MatchString(raw) {
			return 0, false
		}
	} else if !unsignedRe.MatchString(raw) {
		return 0, false
	}
	sign := int64(1)
	s := raw
	if strings.HasPrefix(s, "-") {
		sign = -1
		s = strings.TrimPrefix(s, "-")
	}
	parts := strings.SplitN(s, ".", 2)
	whole := int64(0)
	for _, ch := range parts[0] {
		whole = whole*10 + int64(ch-'0')
	}
	frac := int64(0)
	scale := int64(100)
	if len(parts) == 2 {
		scale = 100
		for _, ch := range parts[1] {
			frac += int64(ch-'0') * scale
			scale /= 10
		}
	}
	return sign * (whole*1000 + frac), true
}

func activeMaintenanceWaiver(waivers []*Waiver, batchID string, sensorID string, captured time.Time) bool {
	for _, w := range waivers {
		if w.Kind == "maintenance_override" && w.BatchID == batchID && (w.SensorID == sensorID || w.SensorID == "*") && !w.Expires.Before(captured) {
			return true
		}
	}
	return false
}

func sortCandidates(candidates []Candidate, ranks map[string]int) {
	riskOrder := map[string]int{"critical": 0, "watch": 1, "normal": 2}
	sort.SliceStable(candidates, func(i, j int) bool {
		a, b := candidates[i], candidates[j]
		if !a.Batch.Start.Equal(b.Batch.Start) {
			return a.Batch.Start.Before(b.Batch.Start)
		}
		ar, br := rankOf(ranks, a.Batch.Chamber), rankOf(ranks, b.Batch.Chamber)
		if ar != br {
			return ar < br
		}
		if a.Batch.Chamber != b.Batch.Chamber {
			return a.Batch.Chamber < b.Batch.Chamber
		}
		if riskOrder[a.RiskBand] != riskOrder[b.RiskBand] {
			return riskOrder[a.RiskBand] < riskOrder[b.RiskBand]
		}
		if !a.Obs.capturedTime.Equal(b.Obs.capturedTime) {
			return a.Obs.capturedTime.Before(b.Obs.capturedTime)
		}
		return a.Obs.ObsID < b.Obs.ObsID
	})
}

func rankOf(ranks map[string]int, chamber string) int {
	if r, ok := ranks[chamber]; ok {
		return r
	}
	return 999999
}

func allocate(policy Policy, sensors map[string]Sensor, batches map[string]Batch, waivers []*Waiver, transfers []*Transfer, candidates []Candidate, quarantine []QuarantineRow) Report {
	ledgers := map[string]*batchLedger{}
	chamberLedgers := map[string]*chamberLedger{}
	for _, b := range batches {
		ledgers[b.ID] = &batchLedger{baseRemaining: b.CapacityM}
		ensureChamber(chamberLedgers, b.Chamber)
	}
	for _, w := range waivers {
		if w.Kind == "capacity_bonus" {
			if l, ok := ledgers[w.BatchID]; ok {
				l.bonusGranted += w.BonusM
			}
		}
	}

	transfersBySource := map[string][]*Transfer{}
	transfersByTarget := map[string][]*Transfer{}
	for _, t := range transfers {
		transfersBySource[t.SourceBatchID] = append(transfersBySource[t.SourceBatchID], t)
		transfersByTarget[t.TargetBatchID] = append(transfersByTarget[t.TargetBatchID], t)
	}
	for id := range transfersBySource {
		sort.SliceStable(transfersBySource[id], func(i, j int) bool { return transfersBySource[id][i].ID < transfersBySource[id][j].ID })
	}
	for id := range transfersByTarget {
		sort.SliceStable(transfersByTarget[id], func(i, j int) bool { return transfersByTarget[id][i].ID < transfersByTarget[id][j].ID })
	}

	candidateCount := map[string]int{}
	lastIndex := map[string]int{}
	for i, cand := range candidates {
		candidateCount[cand.Batch.ID]++
		lastIndex[cand.Batch.ID] = i
	}
	closed := map[string]bool{}
	closeBatch := func(batchID string) {
		if closed[batchID] {
			return
		}
		closed[batchID] = true
		b, ok := batches[batchID]
		if !ok {
			return
		}
		for _, t := range transfersBySource[batchID] {
			if t.Status != "pending" {
				continue
			}
			if _, ok := batches[t.TargetBatchID]; !ok {
				t.Status = "unknown_target_batch"
				continue
			}
			if b.End.Before(t.Opens) || t.Expires.Before(b.End) {
				t.Status = "inactive_window"
				continue
			}
			bl := ledgers[batchID]
			reserve := bl.baseRemaining
			if reserve > t.MaxM {
				reserve = t.MaxM
			}
			if reserve <= 0 {
				t.Status = "no_source_capacity"
				continue
			}
			transferred := reserve * t.EfficiencyPPM / 1000000
			bl.baseRemaining -= reserve
			if transferred <= 0 {
				t.Status = "no_source_capacity"
				continue
			}
			t.TransferredM = transferred
			t.RemM = transferred
			t.Status = "materialized"
			bl.transferOut += transferred
			ledgers[t.TargetBatchID].transferIn += transferred
		}
	}
	closeNoCandidateSources := func(now time.Time) {
		ids := make([]string, 0, len(batches))
		for id, b := range batches {
			if candidateCount[id] == 0 && !closed[id] && !b.End.After(now) {
				ids = append(ids, id)
			}
		}
		sort.SliceStable(ids, func(i, j int) bool {
			bi, bj := batches[ids[i]], batches[ids[j]]
			if !bi.End.Equal(bj.End) {
				return bi.End.Before(bj.End)
			}
			return ids[i] < ids[j]
		})
		for _, id := range ids {
			closeBatch(id)
		}
	}

	for _, qr := range quarantine {
		ch := quarantineChamber(qr, sensors, batches, candidates)
		ensureChamber(chamberLedgers, ch).quarantine++
	}

	accepted := []AcceptedRow{}
	deferred := []DeferredRow{}
	allocationOrder := []string{}

	for idx, cand := range candidates {
		closeNoCandidateSources(cand.Obs.capturedTime)
		seq := idx + 1
		allocationOrder = append(allocationOrder, cand.Obs.ObsID)
		bl := ledgers[cand.Batch.ID]
		bonusApplicable := applicableBonusWaivers(waivers, cand)
		transferApplicable := applicableTransfers(transfersByTarget[cand.Batch.ID])
		availableBonus := sumRemaining(bonusApplicable)
		availableTransfer := sumTransferRemaining(transferApplicable)
		totalAvailable := bl.baseRemaining + availableTransfer + availableBonus
		if totalAvailable >= cand.VolumeM {
			need := cand.VolumeM
			usedBase := int64(0)
			usedTransfer := int64(0)
			usedBonus := int64(0)
			if bl.baseRemaining > 0 {
				usedBase = bl.baseRemaining
				if usedBase > need {
					usedBase = need
				}
				bl.baseRemaining -= usedBase
				bl.baseUsed += usedBase
				need -= usedBase
			}
			if need > 0 {
				usedTransfer = consumeTransfers(transferApplicable, need)
				bl.transferUsed += usedTransfer
				need -= usedTransfer
			}
			if need > 0 {
				usedBonus = consumeBonusAmount(bonusApplicable, need)
				bl.bonusUsed += usedBonus
				need -= usedBonus
			}
			bl.accepted++
			addRisk(&bl.risks, cand.RiskBand)
			cl := ensureChamber(chamberLedgers, cand.Batch.Chamber)
			cl.accepted++
			cl.acceptedVolume += cand.VolumeM
			reasons := append([]string{}, cand.Reasons...)
			if usedTransfer > 0 {
				reasons = append(reasons, "transfer_capacity")
			}
			if usedBonus > 0 {
				reasons = append(reasons, "capacity_waived")
			}
			cand.Reasons = reasons
			accepted = append(accepted, acceptedRow(cand, capacitySource(usedBase, usedTransfer, usedBonus), seq))
		} else {
			bl.deferred++
			ensureChamber(chamberLedgers, cand.Batch.Chamber).deferred++
			reasons := append([]string{}, cand.Reasons...)
			reasons = append(reasons, "capacity_exhausted")
			deferred = append(deferred, DeferredRow{ObsID: cand.Obs.ObsID, BatchID: cand.Batch.ID, Chamber: cand.Batch.Chamber, RequestedML: toFloat(cand.VolumeM), RemainingBaseML: toFloat(bl.baseRemaining), AvailableTransferML: toFloat(availableTransfer), AvailableBonusML: toFloat(availableBonus), ReasonCodes: reasons, SequenceIndex: seq})
		}
		if lastIndex[cand.Batch.ID] == idx {
			closeBatch(cand.Batch.ID)
		}
	}
	remainingIDs := make([]string, 0, len(batches))
	for id := range batches {
		remainingIDs = append(remainingIDs, id)
	}
	sort.SliceStable(remainingIDs, func(i, j int) bool {
		bi, bj := batches[remainingIDs[i]], batches[remainingIDs[j]]
		if !bi.End.Equal(bj.End) {
			return bi.End.Before(bj.End)
		}
		return remainingIDs[i] < remainingIDs[j]
	})
	for _, id := range remainingIDs {
		closeBatch(id)
	}
	for _, t := range transfers {
		if t.Status == "pending" {
			t.Status = "inactive_window"
		}
	}

	batchSummary := makeBatchSummary(batches, ledgers)
	transferSummary := makeTransferSummary(transfers)
	chamberSummary := makeChamberSummary(chamberLedgers, policy.ChamberRank)
	report := Report{SchemaVersion: policy.OutputSchemaVersion, AllocationOrder: allocationOrder, AcceptedObservations: accepted, DeferredObservations: deferred, Quarantine: quarantine, BatchSummary: batchSummary, TransferSummary: transferSummary, ChamberSummary: chamberSummary}
	report.Digest = digestReport(report)
	return report
}

func acceptedRow(c Candidate, source string, seq int) AcceptedRow {
	return AcceptedRow{ObsID: c.Obs.ObsID, SensorID: c.Obs.SensorID, BatchID: c.Batch.ID, Chamber: c.Batch.Chamber, CapturedAt: c.Obs.CapturedAt, VolumeML: toFloat(c.VolumeM), RiskBand: c.RiskBand, ReasonCodes: c.Reasons, CapacitySource: source, SequenceIndex: seq}
}

func applicableBonusWaivers(waivers []*Waiver, cand Candidate) []*Waiver {
	out := []*Waiver{}
	for _, w := range waivers {
		if w.Kind != "capacity_bonus" || w.BatchID != cand.Batch.ID {
			continue
		}
		if w.SensorID != cand.Obs.SensorID && w.SensorID != "*" {
			continue
		}
		if w.Expires.Before(cand.Obs.capturedTime) {
			continue
		}
		if w.RemM > 0 {
			out = append(out, w)
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

func sumRemaining(waivers []*Waiver) int64 {
	total := int64(0)
	for _, w := range waivers {
		total += w.RemM
	}
	return total
}

func applicableTransfers(transfers []*Transfer) []*Transfer {
	out := []*Transfer{}
	for _, t := range transfers {
		if t.Status == "materialized" && t.RemM > 0 {
			out = append(out, t)
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

func sumTransferRemaining(transfers []*Transfer) int64 {
	total := int64(0)
	for _, t := range transfers {
		total += t.RemM
	}
	return total
}

func consumeTransfers(transfers []*Transfer, need int64) int64 {
	used := int64(0)
	for _, t := range transfers {
		if need <= 0 {
			return used
		}
		take := t.RemM
		if take > need {
			take = need
		}
		t.RemM -= take
		t.ConsumedM += take
		used += take
		need -= take
	}
	return used
}

func consumeBonusAmount(waivers []*Waiver, need int64) int64 {
	used := int64(0)
	for _, w := range waivers {
		if need <= 0 {
			return used
		}
		take := w.RemM
		if take > need {
			take = need
		}
		w.RemM -= take
		used += take
		need -= take
	}
	return used
}

func capacitySource(baseUsed int64, transferUsed int64, bonusUsed int64) string {
	parts := []string{}
	if baseUsed > 0 {
		parts = append(parts, "base")
	}
	if transferUsed > 0 {
		parts = append(parts, "transfer")
	}
	if bonusUsed > 0 {
		parts = append(parts, "bonus")
	}
	if len(parts) == 0 {
		return "none"
	}
	return strings.Join(parts, "+")
}

func addRisk(r *RiskCounts, band string) {
	switch band {
	case "normal":
		r.Normal++
	case "watch":
		r.Watch++
	case "critical":
		r.Critical++
	}
}

func ensureChamber(m map[string]*chamberLedger, chamber string) *chamberLedger {
	if chamber == "" {
		chamber = "unknown"
	}
	if _, ok := m[chamber]; !ok {
		m[chamber] = &chamberLedger{}
	}
	return m[chamber]
}

func quarantineChamber(qr QuarantineRow, sensors map[string]Sensor, batches map[string]Batch, candidates []Candidate) string {
	if qr.Chamber == "" {
		return "unknown"
	}
	return qr.Chamber
}

func makeBatchSummary(batches map[string]Batch, ledgers map[string]*batchLedger) []BatchSummary {
	ids := make([]string, 0, len(batches))
	for id := range batches {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	out := []BatchSummary{}
	for _, id := range ids {
		b := batches[id]
		l := ledgers[id]
		out = append(out, BatchSummary{BatchID: id, Chamber: b.Chamber, CapacityML: toFloat(b.CapacityM), TransferInML: toFloat(l.transferIn), TransferOutML: toFloat(l.transferOut), BonusGrantedML: toFloat(l.bonusGranted), BaseUsedML: toFloat(l.baseUsed), TransferUsedML: toFloat(l.transferUsed), BonusUsedML: toFloat(l.bonusUsed), AcceptedCount: l.accepted, DeferredCount: l.deferred, RiskCounts: l.risks})
	}
	return out
}

func makeTransferSummary(transfers []*Transfer) []TransferSummary {
	sort.SliceStable(transfers, func(i, j int) bool { return transfers[i].ID < transfers[j].ID })
	out := []TransferSummary{}
	for _, t := range transfers {
		out = append(out, TransferSummary{TransferID: t.ID, SourceBatchID: t.SourceBatchID, TargetBatchID: t.TargetBatchID, RequestedML: toFloat(t.MaxM), TransferredML: toFloat(t.TransferredM), ConsumedML: toFloat(t.ConsumedM), Status: t.Status})
	}
	return out
}

func makeChamberSummary(ledgers map[string]*chamberLedger, ranks map[string]int) []ChamberSummary {
	chambers := make([]string, 0, len(ledgers))
	for chamber := range ledgers {
		chambers = append(chambers, chamber)
	}
	sort.SliceStable(chambers, func(i, j int) bool {
		ri, rj := rankOf(ranks, chambers[i]), rankOf(ranks, chambers[j])
		if ri != rj {
			return ri < rj
		}
		return chambers[i] < chambers[j]
	})
	out := []ChamberSummary{}
	for _, ch := range chambers {
		l := ledgers[ch]
		out = append(out, ChamberSummary{Chamber: ch, AcceptedVolumeML: toFloat(l.acceptedVolume), AcceptedCount: l.accepted, DeferredCount: l.deferred, QuarantineCount: l.quarantine})
	}
	return out
}

func digestReport(r Report) string {
	lines := []string{}
	for _, a := range r.AcceptedObservations {
		lines = append(lines, fmt.Sprintf("A|%s|%s|%s|%s|%s|%s|%s|%d", a.ObsID, a.BatchID, a.SensorID, f2float(a.VolumeML), a.RiskBand, reasonDigest(a.ReasonCodes), a.CapacitySource, a.SequenceIndex))
	}
	for _, d := range r.DeferredObservations {
		lines = append(lines, fmt.Sprintf("D|%s|%s|%s|%s|%s|%s|%s|%d", d.ObsID, d.BatchID, f2float(d.RequestedML), f2float(d.RemainingBaseML), f2float(d.AvailableTransferML), f2float(d.AvailableBonusML), reasonDigest(d.ReasonCodes), d.SequenceIndex))
	}
	for _, q := range r.Quarantine {
		lines = append(lines, fmt.Sprintf("Q|%s|%s|%s|%s", q.RecordID, q.ObsID, q.Code, q.Detail))
	}
	for _, b := range r.BatchSummary {
		lines = append(lines, fmt.Sprintf("B|%s|%s|%s|%s|%s|%s|%s|%s|%d|%d|%d/%d/%d", b.BatchID, f2float(b.CapacityML), f2float(b.TransferInML), f2float(b.TransferOutML), f2float(b.BonusGrantedML), f2float(b.BaseUsedML), f2float(b.TransferUsedML), f2float(b.BonusUsedML), b.AcceptedCount, b.DeferredCount, b.RiskCounts.Normal, b.RiskCounts.Watch, b.RiskCounts.Critical))
	}
	for _, t := range r.TransferSummary {
		lines = append(lines, fmt.Sprintf("T|%s|%s|%s|%s|%s|%s|%s", t.TransferID, t.SourceBatchID, t.TargetBatchID, f2float(t.RequestedML), f2float(t.TransferredML), f2float(t.ConsumedML), t.Status))
	}
	for _, c := range r.ChamberSummary {
		lines = append(lines, fmt.Sprintf("C|%s|%s|%d|%d|%d", c.Chamber, f2float(c.AcceptedVolumeML), c.AcceptedCount, c.DeferredCount, c.QuarantineCount))
	}
	h := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return hex.EncodeToString(h[:])
}

func reasonDigest(reasons []string) string {
	if len(reasons) == 0 {
		return "-"
	}
	return strings.Join(reasons, ",")
}

func toFloat(m int64) float64 {
	if m >= 0 {
		return float64((m+5)/10) / 100.0
	}
	return -float64(((-m)+5)/10) / 100.0
}

func f2float(v float64) string {
	return fmt.Sprintf("%.2f", v)
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}
