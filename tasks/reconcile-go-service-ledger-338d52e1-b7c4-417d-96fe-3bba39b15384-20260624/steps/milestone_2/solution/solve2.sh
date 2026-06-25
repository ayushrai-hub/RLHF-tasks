#!/bin/bash
set -euo pipefail

cd /app

cat > internal/events/dedupe.go <<'GO'
package events

import "time"

func Dedupe(records []Event) []Event {
	chosen := map[string]Event{}
	order := []string{}
	for _, event := range records {
		key := event.Source + ":" + event.EventID
		current, exists := chosen[key]
		if !exists {
			order = append(order, key)
			chosen[key] = event
			continue
		}
		if newer(event, current) {
			chosen[key] = event
		}
	}
	out := make([]Event, 0, len(order))
	for _, key := range order {
		out = append(out, chosen[key])
	}
	return out
}

func newer(candidate Event, current Event) bool {
	if candidate.Sequence != current.Sequence {
		return candidate.Sequence > current.Sequence
	}
	candidateTime, candidateErr := time.Parse(time.RFC3339, candidate.OccurredAt)
	currentTime, currentErr := time.Parse(time.RFC3339, current.OccurredAt)
	if candidateErr == nil && currentErr == nil {
		return candidateTime.After(currentTime)
	}
	return candidate.OccurredAt > current.OccurredAt
}
GO

cat > internal/summary/types.go <<'GO'
package summary

type MetricSummary struct {
	Count int     `json:"count"`
	Sum   float64 `json:"sum"`
	Min   float64 `json:"min"`
	Max   float64 `json:"max"`
	Avg   float64 `json:"avg"`
}

type ServiceSummary struct {
	Service    string                   `json:"service"`
	Tier       string                   `json:"tier"`
	EventCount int                      `json:"event_count"`
	Sources    []string                 `json:"sources"`
	Metrics    map[string]MetricSummary `json:"metrics"`
}

type Totals struct {
	ServiceCount     int `json:"service_count"`
	EventCount       int `json:"event_count"`
	DroppedEvents    int `json:"dropped_events"`
	SuppressedEvents int `json:"suppressed_events"`
}

type Report struct {
	Services []ServiceSummary `json:"services"`
	Totals   Totals           `json:"totals"`
}
GO

cat > internal/summary/aggregate.go <<'GO'
package summary

import (
	"sort"
	"time"

	"service-ledger/internal/config"
	"service-ledger/internal/events"
)

func Build(cfg config.NormalizedConfig, records []events.Event) Report {
	effective := effectiveEvents(events.Dedupe(records))
	latestByService := latestRecognizedTimes(cfg, effective)
	grouped := map[string]*ServiceSummary{}
	sourceSets := map[string]map[string]bool{}
	dropped := 0
	suppressed := 0

	for _, event := range effective {
		serviceName := cfg.AliasToService[config.CanonicalName(event.Service)]
		if serviceName == "" {
			dropped++
			continue
		}
		if event.Value == 0 {
			suppressed++
			continue
		}
		rule := cfg.Services[serviceName]
		if !withinRetention(event.OccurredAt, latestByService[serviceName], rule.RetentionDays) {
			continue
		}
		if grouped[serviceName] == nil {
			grouped[serviceName] = &ServiceSummary{
				Service: serviceName,
				Tier:    rule.Tier,
				Metrics: map[string]MetricSummary{},
			}
			sourceSets[serviceName] = map[string]bool{}
		}
		row := grouped[serviceName]
		row.EventCount++
		if event.Source != "" {
			sourceSets[serviceName][event.Source] = true
		}
		metric := row.Metrics[event.Metric]
		metric.Count++
		metric.Sum += event.Value
		if metric.Count == 1 || event.Value < metric.Min {
			metric.Min = event.Value
		}
		if metric.Count == 1 || event.Value > metric.Max {
			metric.Max = event.Value
		}
		metric.Avg = metric.Sum / float64(metric.Count)
		row.Metrics[event.Metric] = metric
	}

	names := make([]string, 0, len(grouped))
	for name := range grouped {
		names = append(names, name)
	}
	sort.Strings(names)
	out := Report{Totals: Totals{DroppedEvents: dropped, SuppressedEvents: suppressed}}
	for _, name := range names {
		row := *grouped[name]
		row.Sources = sortedKeys(sourceSets[name])
		out.Services = append(out.Services, row)
		out.Totals.EventCount += row.EventCount
	}
	out.Totals.ServiceCount = len(out.Services)
	return out
}

func latestRecognizedTimes(cfg config.NormalizedConfig, records []events.Event) map[string]time.Time {
	latest := map[string]time.Time{}
	for _, event := range records {
		serviceName := cfg.AliasToService[config.CanonicalName(event.Service)]
		if serviceName == "" || event.Value == 0 {
			continue
		}
		occurredAt, err := time.Parse(time.RFC3339, event.OccurredAt)
		if err != nil {
			continue
		}
		if current, ok := latest[serviceName]; !ok || occurredAt.After(current) {
			latest[serviceName] = occurredAt
		}
	}
	return latest
}

func withinRetention(occurredAtRaw string, latest time.Time, retentionDays int) bool {
	if latest.IsZero() || retentionDays <= 0 {
		return true
	}
	occurredAt, err := time.Parse(time.RFC3339, occurredAtRaw)
	if err != nil {
		return true
	}
	cutoff := latest.AddDate(0, 0, -retentionDays)
	return !occurredAt.Before(cutoff)
}

func effectiveEvents(records []events.Event) []events.Event {
	byID := map[string]events.Event{}
	order := []string{}
	seenOrder := map[string]bool{}
	allByID := map[string]events.Event{}
	correctionRoots := []string{}
	seenRoots := map[string]bool{}
	correctionsByRoot := map[string]events.Event{}

	for _, event := range records {
		allByID[event.EventID] = event
	}

	for _, event := range records {
		if event.Kind == "correction" && event.CorrectionOf != "" {
			root := rootCorrectionTarget(event.CorrectionOf, allByID)
			current, exists := correctionsByRoot[root]
			if !exists {
				if !seenRoots[root] {
					correctionRoots = append(correctionRoots, root)
					seenRoots[root] = true
				}
				correctionsByRoot[root] = event
			} else if newerEvent(event, current) {
				correctionsByRoot[root] = event
			}
			continue
		}
		if !seenOrder[event.EventID] {
			order = append(order, event.EventID)
			seenOrder[event.EventID] = true
		}
		byID[event.EventID] = event
	}
	for _, target := range correctionRoots {
		correction := correctionsByRoot[target]
		delete(byID, target)
		if !seenOrder[correction.EventID] {
			order = append(order, correction.EventID)
			seenOrder[correction.EventID] = true
		}
		byID[correction.EventID] = correction
	}

	out := make([]events.Event, 0, len(byID))
	for _, id := range order {
		if event, ok := byID[id]; ok {
			out = append(out, event)
		}
	}
	return out
}

func rootCorrectionTarget(target string, byID map[string]events.Event) string {
	seen := map[string]bool{}
	current := target
	for {
		if seen[current] {
			return current
		}
		seen[current] = true
		event, ok := byID[current]
		if !ok || event.Kind != "correction" || event.CorrectionOf == "" {
			return current
		}
		current = event.CorrectionOf
	}
}

func newerEvent(candidate events.Event, current events.Event) bool {
	if candidate.Sequence != current.Sequence {
		return candidate.Sequence > current.Sequence
	}
	candidateTime, candidateErr := time.Parse(time.RFC3339, candidate.OccurredAt)
	currentTime, currentErr := time.Parse(time.RFC3339, current.OccurredAt)
	if candidateErr == nil && currentErr == nil {
		return candidateTime.After(currentTime)
	}
	return candidate.OccurredAt > current.OccurredAt
}

func sortedKeys(values map[string]bool) []string {
	out := make([]string, 0, len(values))
	for value := range values {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}
GO

go test ./...
