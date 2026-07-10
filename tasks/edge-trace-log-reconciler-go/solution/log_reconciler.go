package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"
)

var reasonOrder = []string{
	"invalid_schema", "unknown_kind", "unknown_service", "trace_not_active",
	"trace_already_active", "service_mismatch", "route_not_allowed",
	"capacity_full", "loop_blocked", "target_missing", "target_not_voidable",
	"target_trace_mismatch", "target_already_voided", "void_too_late",
}

type Config struct {
	Routes           map[string][]string `json:"routes"`
	Capacities       map[string]int      `json:"capacities"`
	TrustedNodes     []string            `json:"trusted_nodes"`
	VoidGraceMS      int                 `json:"void_grace_ms"`
	TraceByteCap     int                 `json:"trace_byte_cap"`
	BillableStatuses []int               `json:"billable_statuses"`
}

type Event struct {
	EventID     string   `json:"event_id"`
	TS          string   `json:"ts"`
	Node        string   `json:"node"`
	Seq         int      `json:"seq"`
	Trace       string   `json:"trace"`
	Kind        string   `json:"kind"`
	Service     *string  `json:"service"`
	NextService *string  `json:"next_service"`
	Bytes       *int     `json:"bytes"`
	Status      *int     `json:"status"`
	Target      *string  `json:"target"`
	Flags       []string `json:"flags"`
	Req         *string  `json:"req"`
	Line        int      `json:"-"`
	ParsedTS    time.Time
	Invalid     bool
}

type Request struct {
	Trace         string   `json:"trace"`
	Req           string   `json:"req"`
	OpenedAt      string   `json:"opened_at"`
	ClosedAt      *string  `json:"closed_at"`
	Status        string   `json:"status"`
	StatusCode    *int     `json:"status_code"`
	FinalService  string   `json:"final_service"`
	Path          []string `json:"path"`
	RawBytes      int      `json:"raw_bytes"`
	BillableBytes int      `json:"billable_bytes"`
	Warnings      []string `json:"warnings"`
	StartEvent    string   `json:"-"`
	EndEvent      *string  `json:"-"`
}

type Audit struct {
	EventID string   `json:"event_id"`
	Line    int      `json:"line"`
	Action  string   `json:"action"`
	Reasons []string `json:"reasons"`
}

type Adjustment struct {
	Trace       string  `json:"trace"`
	Kind        string  `json:"kind"`
	Amount      int     `json:"amount"`
	EventID     *string `json:"event_id"`
	SourceEvent *string `json:"source_event"`
}

type Peak struct {
	Service string `json:"service"`
	Peak    int    `json:"peak"`
}

type Summary struct {
	Processed      int `json:"processed"`
	Accepted       int `json:"accepted"`
	Rejected       int `json:"rejected"`
	Ignored        int `json:"ignored"`
	OpenRequests   int `json:"open_requests"`
	ClosedRequests int `json:"closed_requests"`
	BillableTotal  int `json:"billable_total"`
}

type Report struct {
	Requests    []Request    `json:"requests"`
	Audit       []Audit      `json:"audit"`
	Adjustments []Adjustment `json:"adjustments"`
	Peaks       []Peak       `json:"peaks"`
	Summary     Summary      `json:"summary"`
}

func main() {
	if len(os.Args) != 4 {
		fatal("usage: log_reconciler config.json events.jsonl report.json")
	}
	config, err := readConfig(os.Args[1])
	if err != nil {
		fatal(err.Error())
	}
	events, err := readEvents(os.Args[2])
	if err != nil {
		fatal(err.Error())
	}
	report := reconcile(config, events)
	if err := os.MkdirAll(filepath.Dir(os.Args[3]), 0o755); err != nil {
		fatal(err.Error())
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		fatal(err.Error())
	}
	if err := os.WriteFile(os.Args[3], append(data, '\n'), 0o644); err != nil {
		fatal(err.Error())
	}
}

func fatal(message string) {
	fmt.Fprintln(os.Stderr, message)
	os.Exit(1)
}

func readConfig(path string) (Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, err
	}
	var config Config
	err = json.Unmarshal(data, &config)
	return config, err
}

func readEvents(path string) ([]Event, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var events []Event
	scanner := bufio.NewScanner(file)
	line := 0
	for scanner.Scan() {
		line++
		var event Event
		if err := json.Unmarshal(scanner.Bytes(), &event); err != nil {
			event.Invalid = true
		}
		event.Line = line
		if parsed, ok := parseTS(event.TS); ok {
			event.ParsedTS = parsed
		} else {
			event.Invalid = true
			event.ParsedTS = time.Date(9999, 1, 1, 0, 0, 0, 0, time.UTC)
		}
		if event.EventID == "" || event.Node == "" || event.Trace == "" || event.Kind == "" || event.Flags == nil {
			event.Invalid = true
		}
		for _, flag := range event.Flags {
			if flag == "" {
				event.Invalid = true
			}
		}
		if event.Bytes != nil && *event.Bytes < 0 {
			event.Invalid = true
		}
		events = append(events, event)
	}
	return events, scanner.Err()
}

func parseTS(value string) (time.Time, bool) {
	if len(value) == 0 || value[len(value)-1] != 'Z' {
		return time.Time{}, false
	}
	parsed, err := time.Parse(time.RFC3339Nano, value)
	return parsed, err == nil
}

func reconcile(config Config, events []Event) Report {
	sort.SliceStable(events, func(i, j int) bool {
		a := events[i]
		b := events[j]
		if !a.ParsedTS.Equal(b.ParsedTS) {
			return a.ParsedTS.Before(b.ParsedTS)
		}
		if a.Node != b.Node {
			return a.Node < b.Node
		}
		if a.Seq != b.Seq {
			return a.Seq < b.Seq
		}
		return a.Line < b.Line
	})

	activeCounts := map[string]int{}
	peaks := map[string]int{}
	for service := range config.Capacities {
		activeCounts[service] = 0
		peaks[service] = 0
	}
	active := map[string]*Request{}
	requests := map[string]*Request{}
	acceptedEvents := map[string]Event{}
	bytesEvents := map[string]int{}
	voided := map[string]bool{}
	seenPositions := map[string]bool{}
	audit := []Audit{}
	adjustments := []Adjustment{}
	accepted := 0
	rejected := 0
	ignored := 0

	for _, event := range events {
		position := fmt.Sprintf("%s\x00%d", event.Node, event.Seq)
		if seenPositions[position] {
			ignored++
			audit = append(audit, Audit{EventID: event.EventID, Line: event.Line, Action: "ignored", Reasons: []string{"duplicate_position"}})
			continue
		}
		seenPositions[position] = true

		if event.Invalid {
			rejected++
			audit = append(audit, Audit{EventID: event.EventID, Line: event.Line, Action: "rejected", Reasons: []string{"invalid_schema"}})
			continue
		}

		reasons := map[string]bool{}
		knownService := event.Service == nil || hasService(config, *event.Service)
		if !in(event.Kind, []string{"start", "hop", "bytes", "end", "void"}) {
			reasons["unknown_kind"] = true
		}
		if in(event.Kind, []string{"start", "bytes", "end"}) {
			if event.Service == nil || !hasService(config, *event.Service) {
				reasons["unknown_service"] = true
				knownService = false
			}
		}
		if event.Kind == "hop" {
			if event.Service == nil || event.NextService == nil || !hasService(config, *event.Service) || !hasService(config, *event.NextService) {
				reasons["unknown_service"] = true
				knownService = false
			}
		}

		switch event.Kind {
		case "start":
			if knownService {
				if _, exists := active[event.Trace]; exists {
					reasons["trace_already_active"] = true
				}
				if event.Service != nil && activeCounts[*event.Service] >= config.Capacities[*event.Service] {
					reasons["capacity_full"] = true
				}
			}
			if event.Req == nil {
				reasons["invalid_schema"] = true
			}
		case "hop":
			current := active[event.Trace]
			if current == nil {
				reasons["trace_not_active"] = true
			} else if event.Service == nil || *event.Service != current.FinalService {
				reasons["service_mismatch"] = true
			}
			if current != nil && knownService && event.Service != nil && event.NextService != nil {
				allowed := stringIn(*event.NextService, config.Routes[*event.Service])
				if !allowed {
					reasons["route_not_allowed"] = true
				}
				loop := stringIn(*event.NextService, current.Path)
				if loop && !hasFlag(event, "loop_ok") {
					reasons["loop_blocked"] = true
				}
				if allowed {
					remaining := activeCounts[*event.NextService]
					if *event.Service == *event.NextService {
						remaining--
					}
					if (!loop || hasFlag(event, "loop_ok")) && remaining >= config.Capacities[*event.NextService] {
						reasons["capacity_full"] = true
					}
				}
			}
		case "bytes", "end":
			current := active[event.Trace]
			if current == nil {
				reasons["trace_not_active"] = true
			} else if event.Service == nil || *event.Service != current.FinalService {
				reasons["service_mismatch"] = true
			}
			if event.Kind == "bytes" && event.Bytes == nil {
				reasons["invalid_schema"] = true
			}
			if event.Kind == "end" && event.Status == nil {
				reasons["invalid_schema"] = true
			}
		case "void":
			if event.Target == nil {
				reasons["target_missing"] = true
			} else {
				target, ok := acceptedEvents[*event.Target]
				if !ok {
					reasons["target_missing"] = true
				} else {
					if target.Kind != "bytes" {
						reasons["target_not_voidable"] = true
					}
					if target.Trace != event.Trace {
						reasons["target_trace_mismatch"] = true
					}
					if voided[target.EventID] {
						reasons["target_already_voided"] = true
					}
					if event.ParsedTS.Sub(target.ParsedTS) > time.Duration(config.VoidGraceMS)*time.Millisecond {
						reasons["void_too_late"] = true
					}
				}
			}
		}

		ordered := orderReasons(reasons)
		if len(ordered) > 0 {
			rejected++
			audit = append(audit, Audit{EventID: event.EventID, Line: event.Line, Action: "rejected", Reasons: ordered})
			continue
		}

		accepted++
		audit = append(audit, Audit{EventID: event.EventID, Line: event.Line, Action: "accepted", Reasons: []string{}})
		acceptedEvents[event.EventID] = event
		switch event.Kind {
		case "start":
			request := &Request{
				Trace: event.Trace, Req: *event.Req, OpenedAt: event.TS, Status: "open",
				FinalService: *event.Service, Path: []string{*event.Service},
				Warnings: []string{}, StartEvent: event.EventID,
			}
			requests[event.Trace] = request
			active[event.Trace] = request
			activeCounts[*event.Service]++
			if activeCounts[*event.Service] > peaks[*event.Service] {
				peaks[*event.Service] = activeCounts[*event.Service]
			}
		case "hop":
			request := active[event.Trace]
			old := request.FinalService
			if stringIn(*event.NextService, request.Path) {
				addWarning(request, "loop_allowed")
			}
			activeCounts[old]--
			activeCounts[*event.NextService]++
			if activeCounts[*event.NextService] > peaks[*event.NextService] {
				peaks[*event.NextService] = activeCounts[*event.NextService]
			}
			request.FinalService = *event.NextService
			request.Path = append(request.Path, *event.NextService)
		case "bytes":
			contribution := *event.Bytes
			if hasFlag(event, "sampled") {
				contribution /= 2
				addWarning(active[event.Trace], "sampled_bytes")
			}
			active[event.Trace].RawBytes += contribution
			bytesEvents[event.EventID] = contribution
		case "end":
			request := active[event.Trace]
			request.ClosedAt = &event.TS
			request.Status = "closed"
			request.StatusCode = event.Status
			request.EndEvent = &event.EventID
			delete(active, event.Trace)
			activeCounts[*event.Service]--
		case "void":
			target := acceptedEvents[*event.Target]
			contribution := bytesEvents[target.EventID]
			voided[target.EventID] = true
			requests[target.Trace].RawBytes -= contribution
			eventID := event.EventID
			source := target.EventID
			adjustments = append(adjustments, Adjustment{
				Trace: target.Trace, Kind: "void", Amount: -contribution,
				EventID: &eventID, SourceEvent: &source,
			})
		}
	}

	billableStatuses := map[int]bool{}
	for _, status := range config.BillableStatuses {
		billableStatuses[status] = true
	}
	var requestList []Request
	billableTotal := 0
	openRequests := 0
	closedRequests := 0
	for _, request := range requests {
		sort.Strings(request.Warnings)
		if request.Status == "closed" {
			closedRequests++
			if request.StatusCode != nil && billableStatuses[*request.StatusCode] {
				request.BillableBytes = min(request.RawBytes, config.TraceByteCap)
			}
		} else {
			openRequests++
		}
		if request.RawBytes != request.BillableBytes {
			kind := "cap"
			if request.Status != "closed" || request.StatusCode == nil || !billableStatuses[*request.StatusCode] {
				kind = "nonbillable"
			}
			source := request.StartEvent
			adjustments = append(adjustments, Adjustment{
				Trace: request.Trace, Kind: kind, Amount: request.BillableBytes - request.RawBytes,
				EventID: request.EndEvent, SourceEvent: &source,
			})
		}
		billableTotal += request.BillableBytes
		requestList = append(requestList, *request)
	}
	sort.Slice(requestList, func(i, j int) bool { return requestList[i].Trace < requestList[j].Trace })
	sort.Slice(adjustments, func(i, j int) bool {
		return adjustmentKey(adjustments[i]) < adjustmentKey(adjustments[j])
	})
	var peakList []Peak
	for service, peak := range peaks {
		peakList = append(peakList, Peak{Service: service, Peak: peak})
	}
	sort.Slice(peakList, func(i, j int) bool { return peakList[i].Service < peakList[j].Service })
	return Report{
		Requests: requestList, Audit: audit, Adjustments: adjustments, Peaks: peakList,
		Summary: Summary{
			Processed: len(events), Accepted: accepted, Rejected: rejected, Ignored: ignored,
			OpenRequests: openRequests, ClosedRequests: closedRequests, BillableTotal: billableTotal,
		},
	}
}

func hasService(config Config, service string) bool {
	_, ok := config.Capacities[service]
	return ok
}

func in(value string, values []string) bool {
	for _, item := range values {
		if value == item {
			return true
		}
	}
	return false
}

func stringIn(value string, values []string) bool {
	return in(value, values)
}

func hasFlag(event Event, flag string) bool {
	return stringIn(flag, event.Flags)
}

func addWarning(request *Request, warning string) {
	if !stringIn(warning, request.Warnings) {
		request.Warnings = append(request.Warnings, warning)
	}
}

func orderReasons(reasons map[string]bool) []string {
	if reasons["invalid_schema"] {
		return []string{"invalid_schema"}
	}
	var ordered []string
	for _, reason := range reasonOrder {
		if reasons[reason] {
			ordered = append(ordered, reason)
		}
	}
	return ordered
}

func adjustmentKey(item Adjustment) string {
	source := ""
	event := ""
	if item.SourceEvent != nil {
		source = *item.SourceEvent
	}
	if item.EventID != nil {
		event = *item.EventID
	}
	return item.Trace + "\x00" + item.Kind + "\x00" + source + "\x00" + event
}

func min(a int, b int) int {
	if a < b {
		return a
	}
	return b
}
