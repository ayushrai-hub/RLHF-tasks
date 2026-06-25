package replay

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"

	"docker-network-connectivity-debugger/internal/docker_network_connectivity_debugger_policy"
)

type Event struct {
	Seq           int    `json:"seq"`
	EventID       string `json:"event_id"`
	ContainerID   string `json:"container_id"`
	Kind          string `json:"kind"`
	Zone          string `json:"zone"`
	NetworkID     string `json:"network_id"`
	Driver        string `json:"driver"`
	Alias         string `json:"alias"`
	Port          int    `json:"port"`
	Protocol      string `json:"protocol"`
	Label         string `json:"label"`
	FromContainer string `json:"from_container"`
	ToContainer   string `json:"to_container"`
	SourceID      string `json:"source_id"`
	TargetID      string `json:"target_id"`
	DNSAlias      string `json:"dns_alias"`
	UseTLS        bool   `json:"use_tls"`
}

type Scenario struct {
	ScenarioID           string                 `json:"scenario_id"`
	RequireSharedNetwork *bool                  `json:"require_shared_network"`
	BlockEdgeToInternal  *bool                  `json:"block_edge_to_internal"`
	RequireTLSOnInternal *bool                  `json:"require_tls_on_internal"`
	PolicyOverrides      map[string]interface{} `json:"policy_overrides"`
	Events               []Event                `json:"events"`
}

type EgressOut struct {
	FromContainer string `json:"from_container"`
	ToContainer   string `json:"to_container"`
}

type ContainerOut struct {
	ContainerID      string   `json:"container_id"`
	Zone             string   `json:"zone"`
	Labels           []string `json:"labels"`
	PublishedPorts   []string `json:"published_ports"`
	ConnectivityRisk string   `json:"connectivity_risk"`
}

type CaptureOut struct {
	FormatVersion   int `json:"format_version"`
	RecordsTotal    int `json:"records_total"`
	RecordsValid    int `json:"records_valid"`
	RecordsRejected int `json:"records_rejected"`
	DupSeqRejects   int `json:"dup_seq_rejects"`
	TruncatedTail   int `json:"truncated_tail"`
	PayloadBytes    int `json:"payload_bytes"`
}

type Finding struct {
	FindingID string `json:"finding_id"`
	EntityID  string `json:"entity_id"`
	Kind      string `json:"kind"`
	EventSeq  int    `json:"event_seq"`
	Operation string `json:"operation"`
	Detail    string `json:"detail"`
}

type ScenarioOut struct {
	ScenarioID             string         `json:"scenario_id"`
	Status                 string         `json:"status"`
	DuplicateEventsSkipped int            `json:"duplicate_events_skipped"`
	Capture                CaptureOut     `json:"capture"`
	EgressRules            []EgressOut    `json:"egress_rules"`
	Containers             []ContainerOut `json:"containers"`
	Findings               []Finding      `json:"findings"`
}

type Report struct {
	Scenarios []ScenarioOut `json:"scenarios"`
}

type containerState struct {
	zone           string
	labels         map[string]struct{}
	publishedPorts map[string]struct{}
}

func LoadScenario(path string) (Scenario, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Scenario{}, err
	}
	var sc Scenario
	if err := json.Unmarshal(data, &sc); err != nil {
		return Scenario{}, err
	}
	return sc, nil
}

// sortKey uses container_id for stable replay ordering (see DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_RULES.md).
func sortKey(ev Event) string {
	return ev.ContainerID
}

func findingID(scenarioID, entityID string, seq int) string {
	return scenarioID + "::" + entityID + "::" + formatSeq(seq)
}

func formatSeq(seq int) string {
	if seq < 0 {
		seq = 0
	}
	s := []byte("0000")
	n := seq
	for i := 3; i >= 0; i-- {
		s[i] = byte('0' + n%10)
		n /= 10
	}
	return string(s)
}

func strSlice(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func connectivityRisk(zone string) string {
	switch zone {
	case "edge":
		return "elevated"
	case "dmz":
		return "critical"
	default:
		return "none"
	}
}

func portKey(port int, protocol string) string {
	if protocol == "" {
		protocol = "tcp"
	}
	return fmt.Sprintf("%d/%s", port, protocol)
}

func appendFinding(findings *[]Finding, scenarioID, entityID, kind, operation, detail string, seq int) {
	*findings = append(*findings, Finding{
		FindingID: findingID(scenarioID, entityID, seq),
		EntityID:  entityID,
		Kind:      kind,
		EventSeq:  seq,
		Operation: operation,
		Detail:    detail,
	})
}

func Analyze(sc Scenario, cap CaptureOut) ScenarioOut {
	requireShared := true
	if sc.RequireSharedNetwork != nil {
		requireShared = *sc.RequireSharedNetwork
	}
	blockEdge := true
	if sc.BlockEdgeToInternal != nil {
		blockEdge = *sc.BlockEdgeToInternal
	}
	requireTLS := true
	if sc.RequireTLSOnInternal != nil {
		requireTLS = *sc.RequireTLSOnInternal
	}
	requireShared, blockEdge, requireTLS = policy.ResolveBools(
		requireShared,
		blockEdge,
		requireTLS,
		sc.PolicyOverrides,
	)
	_ = requireShared

	containers := make(map[string]*containerState)
	networks := make(map[string]string)
	members := make(map[string]map[string]struct{})
	egress := make(map[string]struct{})
	findings := make([]Finding, 0)
	dupSkipped := 0
	seenEvent := make(map[string]struct{})
	maxProcessedSeq := 0

	events := append([]Event(nil), sc.Events...)
	sort.Slice(events, func(i, j int) bool {
		if events[i].Seq != events[j].Seq {
			return events[i].Seq < events[j].Seq
		}
		a := sortKey(events[i])
		b := sortKey(events[j])
		if a != b {
			return a < b
		}
		return events[i].EventID < events[j].EventID
	})

	for _, ev := range events {
		seq := ev.Seq
		kind := ev.Kind
		if ev.EventID != "" {
			if _, dup := seenEvent[ev.EventID]; dup {
				dupSkipped++
				continue
			}
			seenEvent[ev.EventID] = struct{}{}
		}
		if seq > maxProcessedSeq {
			maxProcessedSeq = seq
		}

		switch kind {
		case "REGISTER_CONTAINER":
			cid := ev.ContainerID
			if _, exists := containers[cid]; exists {
				appendFinding(&findings, sc.ScenarioID, cid, "DUPLICATE_CONTAINER", "", "", seq)
				continue
			}
			containers[cid] = &containerState{
				zone:           ev.Zone,
				labels:         make(map[string]struct{}),
				publishedPorts: make(map[string]struct{}),
			}
			members[cid] = make(map[string]struct{})
		case "CREATE_NETWORK":
			nid := ev.NetworkID
			if _, exists := networks[nid]; exists {
				appendFinding(&findings, sc.ScenarioID, nid, "DUPLICATE_NETWORK", "", "", seq)
				continue
			}
			networks[nid] = ev.Driver
		case "JOIN_NETWORK":
			cid := ev.ContainerID
			nid := ev.NetworkID
			if _, ok := containers[cid]; !ok {
				appendFinding(&findings, sc.ScenarioID, cid, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if _, ok := networks[nid]; !ok {
				appendFinding(&findings, sc.ScenarioID, nid, "UNKNOWN_NETWORK", "", kind, seq)
				continue
			}
			if _, ok := members[cid][nid]; ok {
				appendFinding(&findings, sc.ScenarioID, cid, "DUPLICATE_JOIN", "", nid, seq)
				continue
			}
			members[cid][nid] = struct{}{}
			// JOIN_NETWORK alias is informational only; DNS aliases come from REGISTER_DNS rows.
		case "PUBLISH_PORT":
			cid := ev.ContainerID
			if _, ok := containers[cid]; !ok {
				appendFinding(&findings, sc.ScenarioID, cid, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			containers[cid].publishedPorts[portKey(ev.Port, ev.Protocol)] = struct{}{}
		case "BIND_LABEL":
			cid := ev.ContainerID
			if _, ok := containers[cid]; !ok {
				appendFinding(&findings, sc.ScenarioID, cid, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if ev.Label != "" {
				containers[cid].labels[ev.Label] = struct{}{}
			}
		case "ALLOW_EGRESS":
			from := ev.FromContainer
			to := ev.ToContainer
			key := from + "->" + to
			egress[key] = struct{}{}
		case "CONNECT_PROBE":
			src := ev.SourceID
			tgt := ev.TargetID
			proto := ev.Protocol
			if proto == "" {
				proto = "tcp"
			}
			// CONNECT_PROBE operation is always the lowercased protocol string.
			op := proto
			if _, ok := containers[tgt]; !ok {
				appendFinding(&findings, sc.ScenarioID, tgt, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if _, ok := containers[src]; !ok {
				appendFinding(&findings, sc.ScenarioID, src, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			srcSt := containers[src]
			tgtSt := containers[tgt]
			if blockEdge && srcSt.zone == "edge" && tgtSt.zone == "internal" {
				appendFinding(&findings, sc.ScenarioID, src, "ZONE_BLOCKED", op, tgt, seq)
				continue
			}
			key := src + "->" + tgt
			if _, ok := egress[key]; !ok {
				appendFinding(&findings, sc.ScenarioID, tgt, "EGRESS_DENIED", op, src, seq)
				continue
			}
			if requireTLS && tgtSt.zone == "internal" && !ev.UseTLS {
				appendFinding(&findings, sc.ScenarioID, tgt, "TLS_REQUIRED", op, "", seq)
			}
		}
	}

	egressOut := make([]EgressOut, 0)
	for key := range egress {
		parts := splitEdge(key)
		if len(parts) == 2 {
			egressOut = append(egressOut, EgressOut{FromContainer: parts[0], ToContainer: parts[1]})
		}
	}
	sort.Slice(egressOut, func(i, j int) bool {
		if egressOut[i].FromContainer != egressOut[j].FromContainer {
			return egressOut[i].FromContainer < egressOut[j].FromContainer
		}
		return egressOut[i].ToContainer < egressOut[j].ToContainer
	})

	outContainers := make([]ContainerOut, 0, len(containers))
	cids := make([]string, 0, len(containers))
	for id := range containers {
		cids = append(cids, id)
	}
	sort.Strings(cids)
	for _, id := range cids {
		st := containers[id]
		outContainers = append(outContainers, ContainerOut{
			ContainerID:      id,
			Zone:             st.zone,
			Labels:           strSlice(st.labels),
			PublishedPorts:   strSlice(st.publishedPorts),
			ConnectivityRisk: connectivityRisk(st.zone),
		})
	}

	sort.Slice(findings, func(i, j int) bool {
		return findings[i].FindingID < findings[j].FindingID
	})

	status := "VALID"
	if len(findings) > 0 {
		status = "INVALID"
	}

	_ = maxProcessedSeq

	return ScenarioOut{
		ScenarioID:             sc.ScenarioID,
		Status:                 status,
		DuplicateEventsSkipped: dupSkipped,
		Capture:                cap,
		EgressRules:            egressOut,
		Containers:             outContainers,
		Findings:               findings,
	}
}

func splitEdge(key string) []string {
	for i := 0; i < len(key); i++ {
		if i+1 < len(key) && key[i] == '-' && key[i+1] == '>' {
			return []string{key[:i], key[i+2:]}
		}
	}
	return nil
}
