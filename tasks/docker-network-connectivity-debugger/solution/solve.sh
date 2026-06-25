#!/usr/bin/env bash
set -euo pipefail

# Re-exec with LF line endings if checked out with CRLF on Windows.
if grep -q $'\r' "$0" 2>/dev/null; then
  sed -i 's/\r$//' "$0"
  exec bash "$0" "$@"
fi

export PATH="/usr/local/go/bin:/go/bin:${PATH:-}"

cd /app

cat > /app/internal/docker_network_connectivity_debugger_capture/decode.go <<'DECODE_EOF'
package capture

import (
	"encoding/binary"
	"encoding/json"
	"errors"
	"hash/crc32"
	"os"
	"strings"

	"docker-network-connectivity-debugger/internal/docker_network_connectivity_debugger_replay"
)

type Stats struct {
	FormatVersion   int `json:"format_version"`
	RecordsTotal    int `json:"records_total"`
	RecordsValid    int `json:"records_valid"`
	RecordsRejected int `json:"records_rejected"`
	DupSeqRejects   int `json:"dup_seq_rejects"`
	TruncatedTail   int `json:"truncated_tail"`
	PayloadBytes    int `json:"payload_bytes"`
}

func Decode(path string) ([]replay.Event, Stats, error) {
	if !strings.HasPrefix(path, "/app/data/") {
		return nil, Stats{}, errors.New("permission denied: capture path outside /app/data")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, Stats{}, err
	}
	if len(data) < 8 || string(data[:4]) != "CNX1" {
		return nil, Stats{}, errors.New("bad magic")
	}
	formatVersion := int(binary.LittleEndian.Uint32(data[4:8]))
	stats := Stats{FormatVersion: formatVersion}
	if formatVersion != 1 {
		return nil, stats, errors.New("unsupported format_version")
	}

	off := 8
	seen := make(map[uint32]struct{})
	events := make([]replay.Event, 0)

	for off < len(data) {
		if off+12 > len(data) {
			stats.RecordsRejected++
			stats.TruncatedTail = 1
			break
		}
		recordSeq := binary.LittleEndian.Uint32(data[off : off+4])
		flags := binary.LittleEndian.Uint16(data[off+4 : off+6])
		reserved := binary.LittleEndian.Uint16(data[off+6 : off+8])
		payloadLen := binary.LittleEndian.Uint32(data[off+8 : off+12])
		off += 12
		stats.RecordsTotal++

		reason := ""
		if reserved != 0 {
			reason = "BAD_RESERVED"
		} else if flags != 0 {
			reason = "BAD_FLAGS"
		} else if payloadLen > 4096 {
			reason = "LEN_OVERFLOW"
		} else if _, ok := seen[recordSeq]; ok {
			reason = "DUP_SEQ"
		}
		if reason == "LEN_OVERFLOW" {
			if off+int(payloadLen)+4 <= len(data) {
				off += int(payloadLen) + 4
				stats.RecordsRejected++
				seen[recordSeq] = struct{}{}
				continue
			}
			stats.RecordsRejected++
			stats.TruncatedTail = 1
			break
		}
		if off+int(payloadLen)+4 > len(data) {
			stats.RecordsRejected++
			stats.TruncatedTail = 1
			break
		}
		payload := data[off : off+int(payloadLen)]
		off += int(payloadLen)
		checksum := binary.LittleEndian.Uint32(data[off : off+4])
		off += 4
		if reason == "" {
			hdr := make([]byte, 12)
			binary.LittleEndian.PutUint32(hdr[0:4], recordSeq)
			binary.LittleEndian.PutUint16(hdr[4:6], flags)
			binary.LittleEndian.PutUint16(hdr[6:8], reserved)
			binary.LittleEndian.PutUint32(hdr[8:12], payloadLen)
			if crc32.ChecksumIEEE(append(hdr, payload...)) != checksum {
				reason = "BAD_CRC"
			}
		}
		seen[recordSeq] = struct{}{}
		if reason != "" {
			stats.RecordsRejected++
			if reason == "DUP_SEQ" {
				stats.DupSeqRejects++
			}
			continue
		}
		var ev replay.Event
		if err := json.Unmarshal(payload, &ev); err != nil {
			stats.RecordsRejected++
			continue
		}
		stats.RecordsValid++
		stats.PayloadBytes += int(payloadLen)
		events = append(events, ev)
	}
	return events, stats, nil
}
DECODE_EOF

cat > /app/internal/docker_network_connectivity_debugger_replay/replay.go <<'REPLAY_EOF'
package replay

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

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

func sortKey(ev Event) string {
	switch ev.Kind {
	case "ALLOW_EGRESS", "REVOKE_EGRESS":
		return ev.ToContainer
	case "CONNECT_PROBE":
		return ev.TargetID
	case "CREATE_NETWORK":
		return ev.NetworkID
	default:
		return ev.ContainerID
	}
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

func edgeKey(from, to string) string {
	return from + "\x00" + to
}

func splitEdgeKey(key string) []string {
	for i := 0; i < len(key); i++ {
		if key[i] == 0 {
			return []string{key[:i], key[i+1:]}
		}
	}
	return nil
}

func hasEgress(edges map[string]struct{}, from, to string) bool {
	_, ok := edges[edgeKey(from, to)]
	return ok
}

func hasLabel(st *containerState, label string) bool {
	_, ok := st.labels[label]
	return ok
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

func sharedNetworks(members map[string]map[string]struct{}, src, tgt string) []string {
	srcNets, ok1 := members[src]
	tgtNets, ok2 := members[tgt]
	if !ok1 || !ok2 {
		return nil
	}
	out := make([]string, 0)
	for net := range srcNets {
		if _, ok := tgtNets[net]; ok {
			out = append(out, net)
		}
	}
	sort.Strings(out)
	return out
}

func dnsOK(dns map[string]map[string]string, nets []string, alias, target string) bool {
	for _, net := range nets {
		if byNet, ok := dns[net]; ok {
			if byNet[alias] == target {
				return true
			}
		}
	}
	return false
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

	containers := make(map[string]*containerState)
	networks := make(map[string]string)
	networkOrder := make([]string, 0)
	members := make(map[string]map[string]struct{})
	dns := make(map[string]map[string]string)
	egress := make(map[string]struct{})
	findings := make([]Finding, 0)
	dupSkipped := 0
	seenEvent := make(map[string]struct{})
	maxSeq := 0

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
		if seq > maxSeq {
			maxSeq = seq
		}
		kind := ev.Kind
		if ev.EventID != "" {
			if _, dup := seenEvent[ev.EventID]; dup {
				dupSkipped++
				continue
			}
			seenEvent[ev.EventID] = struct{}{}
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
			networkOrder = append(networkOrder, nid)
			dns[nid] = make(map[string]string)
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
			if ev.Alias != "" {
				dns[nid][ev.Alias] = cid
			}
		case "LEAVE_NETWORK":
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
				delete(members[cid], nid)
				for alias, target := range dns[nid] {
					if target == cid {
						delete(dns[nid], alias)
					}
				}
			}
		case "PUBLISH_PORT":
			cid := ev.ContainerID
			st, ok := containers[cid]
			if !ok {
				appendFinding(&findings, sc.ScenarioID, cid, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			st.publishedPorts[portKey(ev.Port, ev.Protocol)] = struct{}{}
		case "BIND_LABEL":
			cid := ev.ContainerID
			st, ok := containers[cid]
			if !ok {
				appendFinding(&findings, sc.ScenarioID, cid, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			st.labels[ev.Label] = struct{}{}
		case "ALLOW_EGRESS":
			from := ev.FromContainer
			to := ev.ToContainer
			if _, ok := containers[from]; !ok {
				appendFinding(&findings, sc.ScenarioID, from, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if _, ok := containers[to]; !ok {
				appendFinding(&findings, sc.ScenarioID, to, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			key := edgeKey(from, to)
			if _, exists := egress[key]; exists {
				appendFinding(&findings, sc.ScenarioID, to, "DUPLICATE_EGRESS", "", from, seq)
				continue
			}
			egress[key] = struct{}{}
		case "REVOKE_EGRESS":
			from := ev.FromContainer
			to := ev.ToContainer
			if _, ok := containers[from]; !ok {
				appendFinding(&findings, sc.ScenarioID, from, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if _, ok := containers[to]; !ok {
				appendFinding(&findings, sc.ScenarioID, to, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			delete(egress, edgeKey(from, to))
		case "REGISTER_DNS":
			nid := ev.NetworkID
			cid := ev.ContainerID
			if _, ok := networks[nid]; !ok {
				appendFinding(&findings, sc.ScenarioID, nid, "UNKNOWN_NETWORK", "", kind, seq)
				continue
			}
			if _, ok := containers[cid]; !ok {
				appendFinding(&findings, sc.ScenarioID, cid, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			dns[nid][ev.Alias] = cid
		case "CONNECT_PROBE":
			src := ev.SourceID
			tgt := ev.TargetID
			proto := ev.Protocol
			if proto == "" {
				proto = "tcp"
			}
			op := strings.ToUpper(proto)
			tgtSt, ok := containers[tgt]
			if !ok {
				appendFinding(&findings, sc.ScenarioID, tgt, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if _, ok := containers[src]; !ok {
				appendFinding(&findings, sc.ScenarioID, src, "UNKNOWN_CONTAINER", "", kind, seq)
				continue
			}
			if ev.DNSAlias != "" {
				nets := sharedNetworks(members, src, tgt)
				if !dnsOK(dns, nets, ev.DNSAlias, tgt) {
					appendFinding(&findings, sc.ScenarioID, src, "DNS_UNRESOLVED", op, ev.DNSAlias, seq)
					continue
				}
			}
			if requireShared && len(sharedNetworks(members, src, tgt)) == 0 {
				appendFinding(&findings, sc.ScenarioID, tgt, "NETWORK_PARTITION", op, src, seq)
				continue
			}
			pk := portKey(ev.Port, ev.Protocol)
			if _, ok := tgtSt.publishedPorts[pk]; !ok {
				appendFinding(&findings, sc.ScenarioID, tgt, "PORT_UNPUBLISHED", op, pk, seq)
				continue
			}
			if !hasEgress(egress, src, tgt) {
				appendFinding(&findings, sc.ScenarioID, tgt, "EGRESS_DENIED", op, src, seq)
				continue
			}
			srcSt := containers[src]
			if blockEdge && srcSt.zone == "edge" && tgtSt.zone == "internal" {
				appendFinding(&findings, sc.ScenarioID, src, "ZONE_BLOCKED", op, tgt, seq)
				continue
			}
			if requireTLS && tgtSt.zone == "internal" && hasLabel(tgtSt, "net:tls") && !ev.UseTLS {
				appendFinding(&findings, sc.ScenarioID, tgt, "TLS_REQUIRED", op, "", seq)
				continue
			}
		}
	}

	auditSeq := maxSeq + 1
	bridgeFlagged := make(map[string]struct{})
	overlayFlagged := make(map[string]struct{})
	openFlagged := make(map[string]struct{})
	inspectFlagged := make(map[string]struct{})

	for _, nid := range networkOrder {
		if networks[nid] != "bridge" {
			continue
		}
		edgeOnNet := make([]string, 0)
		internalOnNet := make([]string, 0)
		for cid, nets := range members {
			if _, ok := nets[nid]; !ok {
				continue
			}
			st := containers[cid]
			if st.zone == "edge" {
				edgeOnNet = append(edgeOnNet, cid)
			}
			if st.zone == "internal" {
				internalOnNet = append(internalOnNet, cid)
			}
		}
		sort.Strings(edgeOnNet)
		sort.Strings(internalOnNet)
		for _, edgeC := range edgeOnNet {
			for _, intC := range internalOnNet {
				bkey := edgeC + "::" + intC
				if _, done := bridgeFlagged[bkey]; done {
					continue
				}
				if !hasEgress(egress, edgeC, intC) {
					bridgeFlagged[bkey] = struct{}{}
					appendFinding(&findings, sc.ScenarioID, intC, "BRIDGE_GAP", "", edgeC, auditSeq)
				}
			}
		}
	}

	for _, nid := range networkOrder {
		if networks[nid] != "overlay" {
			continue
		}
		if _, done := overlayFlagged[nid]; done {
			continue
		}
		edgeOnNet := make([]string, 0)
		internalOnNet := make([]string, 0)
		for cid, nets := range members {
			if _, ok := nets[nid]; !ok {
				continue
			}
			st := containers[cid]
			if st.zone == "edge" {
				edgeOnNet = append(edgeOnNet, cid)
			}
			if st.zone == "internal" {
				internalOnNet = append(internalOnNet, cid)
			}
		}
		if len(edgeOnNet) == 0 || len(internalOnNet) == 0 {
			continue
		}
		sort.Strings(edgeOnNet)
		sort.Strings(internalOnNet)
		hasInternalToEdge := false
		for _, intC := range internalOnNet {
			for _, edgeC := range edgeOnNet {
				if hasEgress(egress, intC, edgeC) {
					hasInternalToEdge = true
					break
				}
			}
			if hasInternalToEdge {
				break
			}
		}
		if !hasInternalToEdge {
			overlayFlagged[nid] = struct{}{}
			appendFinding(&findings, sc.ScenarioID, internalOnNet[0], "OVERLAY_ASYMMETRY", "", edgeOnNet[0], auditSeq)
		}
	}

	for cid, st := range containers {
		if st.zone != "dmz" || len(st.publishedPorts) == 0 {
			continue
		}
		if _, ok := st.labels["net:inspect"]; ok {
			continue
		}
		if _, done := openFlagged[cid]; !done {
			openFlagged[cid] = struct{}{}
			ports := strSlice(st.publishedPorts)
			appendFinding(&findings, sc.ScenarioID, cid, "OPEN_DMZ_PATH", "", ports[0], auditSeq)
		}
	}

	for cid, st := range containers {
		if st.zone != "dmz" {
			continue
		}
		if _, ok := st.labels["net:inspect"]; ok {
			continue
		}
		hasEdgeInbound := false
		for key := range egress {
			parts := splitEdgeKey(key)
			if len(parts) != 2 || parts[1] != cid {
				continue
			}
			if srcSt, ok := containers[parts[0]]; ok && srcSt.zone == "edge" {
				hasEdgeInbound = true
				break
			}
		}
		if hasEdgeInbound {
			if _, done := inspectFlagged[cid]; !done {
				inspectFlagged[cid] = struct{}{}
				appendFinding(&findings, sc.ScenarioID, cid, "INSPECT_UNBOUND", "", "", auditSeq)
			}
		}
	}

	egressOut := make([]EgressOut, 0, len(egress))
	for key := range egress {
		parts := splitEdgeKey(key)
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
REPLAY_EOF

make clean || true
make build
make run

wc -c /app/build/docker_network_connectivity_debugger_report.json
