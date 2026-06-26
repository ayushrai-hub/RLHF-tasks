#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/keyshare_engine /app/bin /app/output

cat > /app/keyshare_engine/main.go <<'EOF_MAIN_GO'
package main

import (
	"bufio"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const (
	dataRoot          = "/app/data"
	serviceTiersPath  = "/app/data/service_inventory/service_tiers.yaml"
	classicGroupsPath = "/app/data/group_catalog/classic_groups.csv"
	hybridGroupsPath  = "/app/data/group_catalog/hybrid_pq_groups.csv"
	deprecatedPath    = "/app/data/group_catalog/deprecated_groups.csv"
	bannedPath        = "/app/data/group_catalog/banned_groups.csv"
	aliasesPath       = "/app/data/group_catalog/group_aliases.csv"
	phasesPath        = "/app/data/rollout_schedule/per_service_phases.toml"
	gracePath         = "/app/data/rollout_schedule/grace_extensions.ini"
	rateCapsPath      = "/app/data/admission_policy/rate_caps.conf"
	envelopePath      = "/app/data/admission_policy/output_envelope.json"
	monthlyAnchorPath = "/app/data/quota_ledger/monthly_anchors.json"
	quotaCapsPath     = "/app/data/quota_ledger/quota_caps.json"
	sealPinsPath      = "/app/data/pin_seals/seal_pins.json"
	pinSecretsPath    = "/app/data/pin_seals/pin_secrets.conf"
	clientOverridePath = "/app/data/tenant_overlay/client_overrides.json"
	outputPath        = "/app/output/expected.json"
)

type Service struct {
	ID         string
	PolicyTier string
	RateTier   string
}

type Phase struct{ Start, End int64 }
type Month struct{ Name string; Start, End int64 }
type QuotaCap struct{ ServiceID, Month string; Cap int }

type Envelope struct {
	VerdictSet               []string `json:"verdict_set"`
	VerdictSeverityHighToLow []string `json:"verdict_severity_high_to_low"`
	SuccessfulVerdicts       []string `json:"successful_verdicts"`
	DigestHexPrefixLength    int      `json:"digest_hex_prefix_length"`
	ObservationShards        []string `json:"observation_shard_paths_relative_to_data_root"`
}

type Decision struct {
	ObservationID string `json:"observation_id"`
	ServiceID     string `json:"service_id"`
	Verdict       string `json:"verdict"`
	MatchedGroup  string `json:"matched_group"`
}

type ByService struct {
	ServiceID              string `json:"service_id"`
	PreRolloutPass         int    `json:"pre_rollout_pass"`
	HybridPqOk             int    `json:"hybrid_pq_ok"`
	ClassicOk              int    `json:"classic_ok"`
	DeprecatedGrace        int    `json:"deprecated_grace"`
	SealRescued            int    `json:"seal_rescued"`
	PolicyDowngradeBlocked int    `json:"policy_downgrade_blocked"`
	GroupBanned            int    `json:"group_banned"`
	RateLimited            int    `json:"rate_limited"`
	QuotaExhausted         int    `json:"quota_exhausted"`
	RejectedType           int    `json:"rejected_type"`
	Invalid                int    `json:"invalid"`
	Total                  int    `json:"total"`
}

func read(path string) []byte {
	b, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read %s: %v\n", path, err)
		os.Exit(1)
	}
	return b
}

func parseServices() []Service {
	var out []Service
	var cur Service
	open := false
	for _, ln := range strings.Split(string(read(serviceTiersPath)), "\n") {
		t := strings.TrimSpace(ln)
		switch {
		case strings.HasPrefix(t, "- service_id:"):
			if open {
				out = append(out, cur)
			}
			cur = Service{ID: strings.TrimSpace(strings.TrimPrefix(t, "- service_id:"))}
			open = true
		case strings.HasPrefix(t, "policy_tier:"):
			cur.PolicyTier = strings.TrimSpace(strings.TrimPrefix(t, "policy_tier:"))
		case strings.HasPrefix(t, "rate_tier:"):
			cur.RateTier = strings.TrimSpace(strings.TrimPrefix(t, "rate_tier:"))
		}
	}
	if open {
		out = append(out, cur)
	}
	return out
}

func loadGroupSet(path string) map[string]bool {
	r := csv.NewReader(strings.NewReader(string(read(path))))
	rows, err := r.ReadAll()
	if err != nil {
		fmt.Fprintf(os.Stderr, "csv %s: %v\n", path, err)
		os.Exit(1)
	}
	s := map[string]bool{}
	for i, row := range rows {
		if i == 0 || len(row) == 0 {
			continue
		}
		s[strings.ToLower(strings.TrimSpace(row[0]))] = true
	}
	return s
}

func loadAliases() map[string]string {
	r := csv.NewReader(strings.NewReader(string(read(aliasesPath))))
	rows, err := r.ReadAll()
	if err != nil {
		fmt.Fprintf(os.Stderr, "csv %s: %v\n", aliasesPath, err)
		os.Exit(1)
	}
	out := map[string]string{}
	for i, row := range rows {
		if i == 0 || len(row) < 2 {
			continue
		}
		out[strings.ToLower(strings.TrimSpace(row[0]))] = strings.ToLower(strings.TrimSpace(row[1]))
	}
	return out
}

func parsePhases() map[string]Phase {
	out := map[string]Phase{}
	var key string
	cur := Phase{}
	flush := func() {
		if key != "" {
			out[key] = cur
		}
	}
	for _, ln := range strings.Split(string(read(phasesPath)), "\n") {
		t := strings.TrimSpace(ln)
		if strings.HasPrefix(t, "[") && strings.HasSuffix(t, "]") {
			flush()
			key = t[1 : len(t)-1]
			cur = Phase{}
			continue
		}
		if strings.HasPrefix(t, "rollout_start_ns") {
			v := strings.TrimSpace(strings.SplitN(t, "=", 2)[1])
			cur.Start, _ = strconv.ParseInt(v, 10, 64)
		} else if strings.HasPrefix(t, "rollout_end_ns") {
			v := strings.TrimSpace(strings.SplitN(t, "=", 2)[1])
			cur.End, _ = strconv.ParseInt(v, 10, 64)
		}
	}
	flush()
	return out
}

func parseGrace() map[string]int64 {
	out := map[string]int64{}
	var key string
	for _, ln := range strings.Split(string(read(gracePath)), "\n") {
		t := strings.TrimSpace(ln)
		if strings.HasPrefix(t, "[") && strings.HasSuffix(t, "]") {
			key = t[1 : len(t)-1]
			continue
		}
		if strings.HasPrefix(t, "grace_extension_ns") {
			v := strings.TrimSpace(strings.SplitN(t, "=", 2)[1])
			n, _ := strconv.ParseInt(v, 10, 64)
			out[key] = n
		}
	}
	return out
}

func parseRate() (int64, int, map[string]int) {
	var window int64
	base := 0
	mult := map[string]int{}
	for _, ln := range strings.Split(string(read(rateCapsPath)), "\n") {
		t := strings.TrimSpace(ln)
		if t == "" {
			continue
		}
		parts := strings.SplitN(t, "=", 2)
		if len(parts) != 2 {
			continue
		}
		k := strings.TrimSpace(parts[0])
		v := strings.TrimSpace(parts[1])
		switch {
		case k == "window_ns":
			window, _ = strconv.ParseInt(v, 10, 64)
		case k == "base_cap":
			base, _ = strconv.Atoi(v)
		case strings.HasSuffix(k, "_multiplier"):
			tier := strings.TrimSuffix(k, "_multiplier")
			n, _ := strconv.Atoi(v)
			mult[tier] = n
		}
	}
	return window, base, mult
}

func loadEnvelope() Envelope {
	var e Envelope
	if err := json.Unmarshal(read(envelopePath), &e); err != nil {
		fmt.Fprintf(os.Stderr, "envelope: %v\n", err)
		os.Exit(1)
	}
	return e
}

func loadMonths() []Month {
	var doc struct {
		Months []struct {
			Name    string `json:"name"`
			StartNs int64  `json:"start_ns"`
			EndNs   int64  `json:"end_ns"`
		} `json:"months"`
	}
	if err := json.Unmarshal(read(monthlyAnchorPath), &doc); err != nil {
		fmt.Fprintf(os.Stderr, "months: %v\n", err)
		os.Exit(1)
	}
	out := make([]Month, len(doc.Months))
	for i, m := range doc.Months {
		out[i] = Month{Name: m.Name, Start: m.StartNs, End: m.EndNs}
	}
	return out
}

func loadQuotaCaps() map[string]map[string]int {
	var doc struct {
		Caps []struct {
			ServiceID string `json:"service_id"`
			Month     string `json:"month"`
			AdmitCap  int    `json:"admit_cap"`
		} `json:"caps"`
	}
	if err := json.Unmarshal(read(quotaCapsPath), &doc); err != nil {
		fmt.Fprintf(os.Stderr, "quota: %v\n", err)
		os.Exit(1)
	}
	out := map[string]map[string]int{}
	for _, c := range doc.Caps {
		if _, ok := out[c.ServiceID]; !ok {
			out[c.ServiceID] = map[string]int{}
		}
		out[c.ServiceID][c.Month] = c.AdmitCap
	}
	return out
}

func loadSealPins() map[string]string {
	var doc struct {
		Pins []struct {
			ObservationID string `json:"observation_id"`
			Hmac8         string `json:"hmac8"`
		} `json:"pins"`
	}
	if err := json.Unmarshal(read(sealPinsPath), &doc); err != nil {
		fmt.Fprintf(os.Stderr, "pins: %v\n", err)
		os.Exit(1)
	}
	out := map[string]string{}
	for _, p := range doc.Pins {
		out[p.ObservationID] = strings.ToLower(strings.TrimSpace(p.Hmac8))
	}
	return out
}

type PinSecrets struct {
	Key       string
	Algorithm string
	PrefixLen int
}

func loadPinSecrets() PinSecrets {
	ps := PinSecrets{Algorithm: "sha256", PrefixLen: 16}
	for _, ln := range strings.Split(string(read(pinSecretsPath)), "\n") {
		t := strings.TrimSpace(ln)
		if t == "" {
			continue
		}
		parts := strings.SplitN(t, "=", 2)
		if len(parts) != 2 {
			continue
		}
		k := strings.TrimSpace(parts[0])
		v := strings.TrimSpace(parts[1])
		switch k {
		case "hmac_key":
			ps.Key = v
		case "hmac_algorithm":
			ps.Algorithm = v
		case "hmac_hex_prefix_length":
			ps.PrefixLen, _ = strconv.Atoi(v)
		}
	}
	return ps
}

func loadClientOverrides() map[string]string {
	var doc struct {
		Overrides []struct {
			ClientID          string `json:"client_id"`
			OverridePolicyTier string `json:"override_policy_tier"`
		} `json:"overrides"`
	}
	if err := json.Unmarshal(read(clientOverridePath), &doc); err != nil {
		fmt.Fprintf(os.Stderr, "overrides: %v\n", err)
		os.Exit(1)
	}
	out := map[string]string{}
	for _, o := range doc.Overrides {
		out[o.ClientID] = o.OverridePolicyTier
	}
	return out
}

func computeHmac8(key, preimage string, prefixLen int) string {
	h := hmac.New(sha256.New, []byte(key))
	h.Write([]byte(preimage))
	return hex.EncodeToString(h.Sum(nil))[:prefixLen]
}

type RawObs struct {
	Raw     map[string]json.RawMessage
	ShardID int
	Index   int
}

func loadAllObservations(envelope Envelope) []RawObs {
	var obs []RawObs
	for shardIdx, rel := range envelope.ObservationShards {
		path := filepath.Join(dataRoot, rel)
		fp, err := os.Open(path)
		if err != nil {
			fmt.Fprintf(os.Stderr, "open %s: %v\n", path, err)
			os.Exit(1)
		}
		sc := bufio.NewScanner(fp)
		sc.Buffer(make([]byte, 1024*1024), 1024*1024)
		i := 0
		for sc.Scan() {
			line := strings.TrimSpace(sc.Text())
			if line == "" {
				continue
			}
			var raw map[string]json.RawMessage
			if err := json.Unmarshal([]byte(line), &raw); err != nil {
				obs = append(obs, RawObs{Raw: nil, ShardID: shardIdx, Index: i})
				i++
				continue
			}
			obs = append(obs, RawObs{Raw: raw, ShardID: shardIdx, Index: i})
			i++
		}
		fp.Close()
	}
	return obs
}

func monthOf(ts int64, months []Month) string {
	for _, m := range months {
		if ts >= m.Start && ts < m.End {
			return m.Name
		}
	}
	return ""
}

func main() {
	services := parseServices()
	svcByID := map[string]Service{}
	for _, s := range services {
		svcByID[s.ID] = s
	}
	classics := loadGroupSet(classicGroupsPath)
	hybrids := loadGroupSet(hybridGroupsPath)
	deprecated := loadGroupSet(deprecatedPath)
	banned := loadGroupSet(bannedPath)
	aliases := loadAliases()
	phases := parsePhases()
	grace := parseGrace()
	window, base, mult := parseRate()
	envelope := loadEnvelope()
	months := loadMonths()
	quotaCaps := loadQuotaCaps()
	pins := loadSealPins()
	secrets := loadPinSecrets()
	clientOverrides := loadClientOverrides()

	severity := map[string]int{}
	for i, v := range envelope.VerdictSeverityHighToLow {
		severity[v] = i
	}
	successful := map[string]bool{}
	for _, v := range envelope.SuccessfulVerdicts {
		successful[v] = true
	}

	// Stage 1: load all shards
	rawObs := loadAllObservations(envelope)

	// Stage 2: extract parsed records preserving order info for sort
	type Parsed struct {
		Idx          int
		ObsID        string
		SvcID        string
		ClientID     string
		Ts           int64
		Offered      []string
		TsPresent    bool
		OfferedPresent bool
		RejType      bool
		Decision     Decision
		Done         bool
	}
	parsed := make([]Parsed, 0, len(rawObs))
	for idx, ro := range rawObs {
		p := Parsed{Idx: idx}
		if ro.Raw == nil {
			p.Decision = Decision{Verdict: "INVALID"}
			p.Done = true
			parsed = append(parsed, p)
			continue
		}
		raw := ro.Raw
		if v, ok := raw["observation_id"]; ok {
			if json.Unmarshal(v, &p.ObsID) != nil {
				p.RejType = true
			}
		}
		if v, ok := raw["service_id"]; ok {
			if json.Unmarshal(v, &p.SvcID) != nil {
				p.RejType = true
			}
		}
		if v, ok := raw["observed_ts_ns"]; ok {
			p.TsPresent = true
			if json.Unmarshal(v, &p.Ts) != nil {
				p.RejType = true
			}
		}
		if v, ok := raw["offered_groups"]; ok {
			p.OfferedPresent = true
			if json.Unmarshal(v, &p.Offered) != nil {
				p.RejType = true
			}
			for i, g := range p.Offered {
				p.Offered[i] = strings.ToLower(strings.TrimSpace(g))
			}
		}
		if v, ok := raw["client_id"]; ok {
			if json.Unmarshal(v, &p.ClientID) != nil {
				p.RejType = true
			}
		}
		p.Decision.ObservationID = p.ObsID
		p.Decision.ServiceID = p.SvcID
		parsed = append(parsed, p)
	}

	// Stage 3: GLOBAL sort by observed_ts_ns ASC, observation_id ASC for processing
	sort.SliceStable(parsed, func(i, j int) bool {
		// Parse-failed and reject-type rows still need a stable position; use Ts then ObsID
		if parsed[i].Ts != parsed[j].Ts {
			return parsed[i].Ts < parsed[j].Ts
		}
		return parsed[i].ObsID < parsed[j].ObsID
	})

	rateHistory := map[string][]int64{}
	quotaCount := map[string]map[string]int{}

	for i := range parsed {
		p := &parsed[i]
		if p.Done {
			continue
		}
		d := &p.Decision

		// Stage 4: type-strict gate
		if p.RejType {
			d.Verdict = "REJECTED_TYPE"
			continue
		}
		// Stage 5: required-fields gate
		if p.ObsID == "" || p.SvcID == "" || !p.TsPresent || !p.OfferedPresent {
			d.Verdict = "INVALID"
			continue
		}
		// Stage 6: service lookup
		svc, found := svcByID[p.SvcID]
		if !found {
			d.Verdict = "UNKNOWN_SERVICE"
			continue
		}

		// Stage 7: banned check — with seal-pin override
		bannedHit := ""
		for _, g := range p.Offered {
			canon := g
			if c, ok := aliases[g]; ok {
				canon = c
			}
			if banned[g] || banned[canon] {
				bannedHit = g
				break
			}
		}
		if bannedHit != "" {
			pinHmac, hasPin := pins[p.ObsID]
			if hasPin {
				expected := computeHmac8(secrets.Key,
					p.ObsID+"|"+p.SvcID+"|"+p.ClientID, secrets.PrefixLen)
				if hmac.Equal([]byte(pinHmac), []byte(expected)) {
					d.Verdict = "SEAL_RESCUED"
					d.MatchedGroup = bannedHit
					continue
				}
			}
			d.Verdict = "GROUP_BANNED"
			d.MatchedGroup = bannedHit
			continue
		}

		// Stage 8: quota check (per-service per-month)
		monthName := monthOf(p.Ts, months)
		cap := 0
		if monthName != "" {
			if svcCaps, ok := quotaCaps[p.SvcID]; ok {
				cap = svcCaps[monthName]
			}
		}
		if quotaCount[p.SvcID] == nil {
			quotaCount[p.SvcID] = map[string]int{}
		}
		if monthName != "" && cap > 0 {
			cur := quotaCount[p.SvcID][monthName]
			if cur >= cap {
				d.Verdict = "QUOTA_EXHAUSTED"
				continue
			}
			quotaCount[p.SvcID][monthName] = cur + 1
		}

		// Stage 9: rate-limit (per-service sliding window in ts)
		capRate := base * mult[svc.RateTier]
		cutoff := p.Ts - window
		hist := rateHistory[p.SvcID]
		count := 0
		for _, h := range hist {
			if h >= cutoff {
				count++
			}
		}
		if count >= capRate {
			d.Verdict = "RATE_LIMITED"
			continue
		}
		rateHistory[p.SvcID] = append(hist, p.Ts)

		// Stage 10: effective tier (client override wins)
		effectiveTier := svc.PolicyTier
		if ov, ok := clientOverrides[p.ClientID]; ok {
			effectiveTier = ov
		}

		// Stage 11: phase resolution
		ph := phases[p.SvcID]
		graceExt := grace[svc.RateTier]
		graceEnd := ph.End + graceExt
		var phase string
		switch {
		case p.Ts < ph.Start:
			phase = "pre"
		case p.Ts < ph.End:
			phase = "rollout"
		case p.Ts < graceEnd:
			phase = "grace"
		default:
			phase = "post"
		}

		// Stage 12: classify offered groups (with alias resolution)
		var hybridHit, classicHit, deprecatedHit string
		resolve := func(g string) string {
			if c, ok := aliases[g]; ok {
				return c
			}
			return g
		}
		for _, g := range p.Offered {
			canon := resolve(g)
			if hybridHit == "" && hybrids[canon] {
				hybridHit = canon
			}
			if classicHit == "" && classics[canon] {
				classicHit = canon
			}
			if deprecatedHit == "" && deprecated[canon] {
				deprecatedHit = canon
			}
		}

		// Stage 13: verdict by phase + effective tier + group classes
		switch phase {
		case "pre":
			d.Verdict = "PRE_ROLLOUT_PASS"
		case "rollout":
			switch {
			case hybridHit != "":
				d.Verdict = "HYBRID_PQ_OK"
				d.MatchedGroup = hybridHit
			case classicHit != "":
				d.Verdict = "CLASSIC_OK"
				d.MatchedGroup = classicHit
			case deprecatedHit != "":
				d.Verdict = "DEPRECATED_GRACE"
				d.MatchedGroup = deprecatedHit
			default:
				d.Verdict = "POLICY_DOWNGRADE_BLOCKED"
			}
		case "grace":
			switch {
			case hybridHit != "":
				d.Verdict = "HYBRID_PQ_OK"
				d.MatchedGroup = hybridHit
			case effectiveTier == "pq_mandatory":
				d.Verdict = "POLICY_DOWNGRADE_BLOCKED"
			case classicHit != "":
				d.Verdict = "CLASSIC_OK"
				d.MatchedGroup = classicHit
			case deprecatedHit != "":
				d.Verdict = "DEPRECATED_GRACE"
				d.MatchedGroup = deprecatedHit
			default:
				d.Verdict = "POLICY_DOWNGRADE_BLOCKED"
			}
		case "post":
			switch {
			case hybridHit != "":
				d.Verdict = "HYBRID_PQ_OK"
				d.MatchedGroup = hybridHit
			case effectiveTier == "pq_mandatory":
				d.Verdict = "POLICY_DOWNGRADE_BLOCKED"
			case classicHit != "":
				d.Verdict = "CLASSIC_OK"
				d.MatchedGroup = classicHit
			default:
				d.Verdict = "POLICY_DOWNGRADE_BLOCKED"
			}
		}
	}

	// Collect decisions
	decisions := make([]Decision, 0, len(parsed))
	for _, p := range parsed {
		decisions = append(decisions, p.Decision)
	}

	// Aggregate by_verdict
	byVerdict := map[string]int{}
	for _, v := range envelope.VerdictSet {
		byVerdict[v] = 0
	}
	for _, d := range decisions {
		byVerdict[d.Verdict]++
	}

	// Aggregate by_service
	bsm := map[string]*ByService{}
	for _, s := range services {
		bsm[s.ID] = &ByService{ServiceID: s.ID}
	}
	for _, d := range decisions {
		if d.ServiceID == "" {
			continue
		}
		bs, ok := bsm[d.ServiceID]
		if !ok {
			continue
		}
		bs.Total++
		switch d.Verdict {
		case "PRE_ROLLOUT_PASS":
			bs.PreRolloutPass++
		case "HYBRID_PQ_OK":
			bs.HybridPqOk++
		case "CLASSIC_OK":
			bs.ClassicOk++
		case "DEPRECATED_GRACE":
			bs.DeprecatedGrace++
		case "SEAL_RESCUED":
			bs.SealRescued++
		case "POLICY_DOWNGRADE_BLOCKED":
			bs.PolicyDowngradeBlocked++
		case "GROUP_BANNED":
			bs.GroupBanned++
		case "RATE_LIMITED":
			bs.RateLimited++
		case "QUOTA_EXHAUSTED":
			bs.QuotaExhausted++
		case "REJECTED_TYPE":
			bs.RejectedType++
		case "INVALID":
			bs.Invalid++
		}
	}
	var bsList []*ByService
	var svcIds []string
	for id := range bsm {
		svcIds = append(svcIds, id)
	}
	sort.Strings(svcIds)
	for _, id := range svcIds {
		bsList = append(bsList, bsm[id])
	}

	// Output decision sort: severity desc, service_id asc, observed_ts_ns asc, observation_id asc
	tsByObs := map[string]int64{}
	for _, p := range parsed {
		tsByObs[p.ObsID] = p.Ts
	}
	sort.SliceStable(decisions, func(i, j int) bool {
		si, sj := severity[decisions[i].Verdict], severity[decisions[j].Verdict]
		if si != sj {
			return si < sj
		}
		if decisions[i].ServiceID != decisions[j].ServiceID {
			return decisions[i].ServiceID < decisions[j].ServiceID
		}
		ti, tj := tsByObs[decisions[i].ObservationID], tsByObs[decisions[j].ObservationID]
		if ti != tj {
			return ti < tj
		}
		return decisions[i].ObservationID < decisions[j].ObservationID
	})

	total := len(decisions)
	succ := 0
	for _, d := range decisions {
		if successful[d.Verdict] {
			succ++
		}
	}
	rejected := total - succ

	// Digest preimage: D|... lines, S|... lines, T|... line
	var pre []string
	for _, d := range decisions {
		pre = append(pre, fmt.Sprintf("D|%s|%s|%s|%s",
			d.ObservationID, d.ServiceID, d.Verdict, d.MatchedGroup))
	}
	for _, bs := range bsList {
		pre = append(pre, fmt.Sprintf("S|%s|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d",
			bs.ServiceID, bs.PreRolloutPass, bs.HybridPqOk, bs.ClassicOk,
			bs.DeprecatedGrace, bs.SealRescued, bs.PolicyDowngradeBlocked,
			bs.GroupBanned, bs.RateLimited, bs.QuotaExhausted,
			bs.RejectedType, bs.Invalid, bs.Total))
	}
	pre = append(pre, fmt.Sprintf("T|%d|%d|%d", total, succ, rejected))
	h := sha256.Sum256([]byte(strings.Join(pre, "\n")))
	digest := hex.EncodeToString(h[:])[:envelope.DigestHexPrefixLength]

	out := map[string]any{
		"decisions":  decisions,
		"by_service": bsList,
		"by_verdict": byVerdict,
		"summary": map[string]any{
			"total_observations": total,
			"successful":         succ,
			"rejected":           rejected,
			"report_digest":      digest,
		},
	}

	if err := os.MkdirAll("/app/output", 0o755); err != nil {
		os.Exit(1)
	}
	fout, err := os.Create(outputPath)
	if err != nil {
		os.Exit(1)
	}
	defer fout.Close()
	enc := json.NewEncoder(fout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(out); err != nil {
		os.Exit(1)
	}
}
EOF_MAIN_GO

cat > /app/keyshare_engine/go.mod <<'EOF_GO_MOD'
module keyshare_witness

go 1.24
EOF_GO_MOD

cd /app/keyshare_engine
go build -o /app/bin/keyshare_witness .

/app/bin/keyshare_witness
