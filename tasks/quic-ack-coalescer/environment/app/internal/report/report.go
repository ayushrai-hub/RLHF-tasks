package report

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"

	"qack/internal/coalesce"
	"qack/internal/digest"
	"qack/internal/hamilton"
	"qack/internal/load"
	"qack/internal/marker"
	"qack/internal/policy"
)

// Event is the per-frame row in the report.events array. Field declaration
// order is the on-disk JSON key order.
type Event struct {
	ConnID       string `json:"conn_id"`
	PnSpace      string `json:"pn_space"`
	AckTsMs      int64  `json:"ack_ts_ms"`
	PacketNumber int64  `json:"packet_number"`
	LargestAcked int64  `json:"largest_acked"`
	AckDelayUs   int64  `json:"ack_delay_us"`
	EcnCt0       int64  `json:"ecn_ct0"`
	EcnCt1       int64  `json:"ecn_ct1"`
	EcnCe        int64  `json:"ecn_ce"`
	AckEliciting bool   `json:"ack_eliciting"`
	ShardSeq     int64  `json:"shard_seq"`
	Anchor       bool   `json:"anchor"`
	Verdict      string `json:"verdict"`
}

// ConnBlock is the per-connection summary, ordered by numeric-suffix in by_conn.
type ConnBlock struct {
	ConnID      string           `json:"conn_id"`
	Tier        string           `json:"tier"`
	ByVerdict   map[string]int64 `json:"by_verdict"`
	Accepted    int64            `json:"accepted"`
	EventsCount int64            `json:"events_count"`
}

// Summary mirrors the top-level summary block.
type Summary struct {
	Total                  int64            `json:"total"`
	ByVerdict              map[string]int64 `json:"by_verdict"`
	RegisteredConnections  int64            `json:"registered_connections"`
	HamiltonDirection      string           `json:"hamilton_direction"`
	BudgetThreshold        int64            `json:"budget_threshold"`
	PolicyVersion          string           `json:"policy_version"`
}

// Report is the on-disk top-level object. Fields in declaration order = JSON key order.
type Report struct {
	Version      string            `json:"version"`
	Summary      Summary           `json:"summary"`
	ByConn       []ConnBlock       `json:"by_conn"`
	Hamilton     []hamilton.Share  `json:"hamilton"`
	Events       []Event           `json:"events"`
	ReportDigest string            `json:"report_digest"`
}

// Run executes the full pipeline: load → classify → cascade → hamilton → digest → emit.
func Run(dataDir, outDir string) error {
	p, err := policy.Load(dataDir)
	if err != nil {
		return err
	}
	frames, err := load.LoadFrames(dataDir)
	if err != nil {
		return err
	}
	rawMarkers, err := load.LoadMarkers(dataDir)
	if err != nil {
		return err
	}
	conns, err := load.LoadConnections(dataDir)
	if err != nil {
		return err
	}

	connTier := map[string]string{}
	connUrgent := map[string]bool{}
	connOrder := make([]string, 0, len(conns))
	for _, c := range conns {
		connTier[c.ConnID] = p.CanonicalTier(c.Tier)
		connUrgent[c.ConnID] = c.Urgent
		connOrder = append(connOrder, c.ConnID)
	}

	markers := marker.Validate(rawMarkers, p)
	events := coalesce.Classify(frames, markers, p, connTier)

	// Final event sort.
	sort.SliceStable(events, func(i, j int) bool {
		a, b := events[i].Frame, events[j].Frame
		if a.ConnID != b.ConnID {
			return a.ConnID < b.ConnID
		}
		if a.AckTsMs != b.AckTsMs {
			return a.AckTsMs < b.AckTsMs
		}
		if a.PnSpace != b.PnSpace {
			return a.PnSpace < b.PnSpace
		}
		return a.PacketNumber < b.PacketNumber
	})

	// Build by_conn blocks (every registered conn included even at zero events).
	allVerdicts := coalesce.AllVerdicts()
	emptyBy := func() map[string]int64 {
		m := map[string]int64{}
		for _, v := range allVerdicts {
			m[v] = 0
		}
		return m
	}
	byConn := map[string]*ConnBlock{}
	for _, cid := range connOrder {
		byConn[cid] = &ConnBlock{
			ConnID:    cid,
			Tier:      connTier[cid],
			ByVerdict: emptyBy(),
		}
	}
	summaryBy := emptyBy()
	for _, ev := range events {
		cid := ev.Frame.ConnID
		blk, ok := byConn[cid]
		if !ok {
			blk = &ConnBlock{
				ConnID:    cid,
				Tier:      "STANDARD",
				ByVerdict: emptyBy(),
			}
			byConn[cid] = blk
		}
		blk.ByVerdict[ev.Verdict]++
		blk.EventsCount++
		if isAccepted(ev.Verdict) {
			blk.Accepted++
		}
		summaryBy[ev.Verdict]++
	}
	connsSorted := make([]string, 0, len(byConn))
	for k := range byConn {
		connsSorted = append(connsSorted, k)
	}
	sort.Strings(connsSorted)
	byConnArr := make([]ConnBlock, 0, len(connsSorted))
	for _, cid := range connsSorted {
		byConnArr = append(byConnArr, *byConn[cid])
	}

	// Hamilton input: weight per registered conn = accepted count from byConn.
	registered := connOrder
	weight := map[string]int64{}
	anyUrgent := false
	for _, cid := range registered {
		if connUrgent[cid] {
			anyUrgent = true
		}
		weight[cid] = byConn[cid].Accepted
	}
	shares, direction := hamilton.Distribute(registered, weight, anyUrgent)

	// Build out events slice.
	outEvents := make([]Event, len(events))
	for i, ev := range events {
		outEvents[i] = Event{
			ConnID:       ev.Frame.ConnID,
			PnSpace:      ev.Frame.PnSpace,
			AckTsMs:      ev.Frame.AckTsMs,
			PacketNumber: ev.Frame.PacketNumber,
			LargestAcked: ev.Frame.LargestAcked,
			AckDelayUs:   ev.Frame.AckDelayUs,
			EcnCt0:       ev.Frame.EcnCt0,
			EcnCt1:       ev.Frame.EcnCt1,
			EcnCe:        ev.Frame.EcnCe,
			AckEliciting: ev.Frame.AckEliciting,
			ShardSeq:     ev.Frame.ShardSeq,
			Anchor:       ev.Anchor,
			Verdict:      ev.Verdict,
		}
	}

	r := Report{
		Version: "2026.06.07",
		Summary: Summary{
			Total:                 int64(len(events)),
			ByVerdict:             summaryBy,
			RegisteredConnections: int64(len(registered)),
			HamiltonDirection:     direction,
			BudgetThreshold:       p.BudgetThreshold,
			PolicyVersion:         p.Version,
		},
		ByConn:       byConnArr,
		Hamilton:     shares,
		Events:       outEvents,
		ReportDigest: "pending",
	}
	pre, err := marshal(r)
	if err != nil {
		return err
	}
	r.ReportDigest = digest.Sha256Hex(pre)
	final, err := marshal(r)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}
	// Clear /app/output of stale files first.
	entries, err := os.ReadDir(outDir)
	if err == nil {
		for _, e := range entries {
			os.Remove(filepath.Join(outDir, e.Name()))
		}
	}
	dest := filepath.Join(outDir, "report.json")
	final = append(final, '\n')
	return os.WriteFile(dest, final, 0o644)
}

func marshal(r Report) ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	if err := enc.Encode(r); err != nil {
		return nil, err
	}
	// encoder appends a newline. Strip it for canonical bytes; caller re-adds.
	b := buf.Bytes()
	if len(b) > 0 && b[len(b)-1] == '\n' {
		b = b[:len(b)-1]
	}
	return b, nil
}

func isAccepted(v string) bool {
	switch v {
	case coalesce.VerdictDelivered, coalesce.VerdictCoalesced, coalesce.VerdictReordered:
		return true
	}
	return false
}

