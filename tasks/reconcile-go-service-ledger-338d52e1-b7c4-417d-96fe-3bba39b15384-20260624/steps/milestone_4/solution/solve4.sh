#!/bin/bash
set -euo pipefail

cd /app

cat > internal/report/compare.go <<'GO'
package report

import (
	"sort"

	"service-ledger/internal/summary"
)

type CompareChange struct {
	Service        string   `json:"service"`
	Metric         string   `json:"metric"`
	Status         string   `json:"status"`
	BaselineCount  int      `json:"baseline_count"`
	CandidateCount int      `json:"candidate_count"`
	BaselineSum    float64  `json:"baseline_sum"`
	CandidateSum   float64  `json:"candidate_sum"`
	DeltaSum       float64  `json:"delta_sum"`
	PercentChange  *float64 `json:"percent_change"`
}

type CompareTotals struct {
	ChangedMetrics   int `json:"changed_metrics"`
	NewMetrics       int `json:"new_metrics"`
	RemovedMetrics   int `json:"removed_metrics"`
	RegressedMetrics int `json:"regressed_metrics"`
	ImprovedMetrics  int `json:"improved_metrics"`
}

type CompareResult struct {
	BaselineReportID  string          `json:"baseline_report_id"`
	CandidateReportID string          `json:"candidate_report_id"`
	MinAbsDelta       float64         `json:"min_abs_delta"`
	Changes           []CompareChange `json:"changes"`
	Totals            CompareTotals   `json:"totals"`
}

type metricPoint struct {
	Count int
	Sum   float64
	OK    bool
}

func Compare(baselineID string, candidateID string, baseline summary.Report, candidate summary.Report, minAbsDelta float64) CompareResult {
	baselineMetrics := flattenMetrics(baseline)
	candidateMetrics := flattenMetrics(candidate)
	keys := map[string]bool{}
	for key := range baselineMetrics {
		keys[key] = true
	}
	for key := range candidateMetrics {
		keys[key] = true
	}

	orderedKeys := make([]string, 0, len(keys))
	for key := range keys {
		orderedKeys = append(orderedKeys, key)
	}
	sort.Strings(orderedKeys)

	result := CompareResult{
		BaselineReportID:  baselineID,
		CandidateReportID: candidateID,
		MinAbsDelta:       minAbsDelta,
		Changes:           []CompareChange{},
	}
	for _, key := range orderedKeys {
		service, metric := splitKey(key)
		before := baselineMetrics[key]
		after := candidateMetrics[key]
		delta := after.Sum - before.Sum
		status := ""
		switch {
		case !before.OK && after.OK:
			status = "new_metric"
			result.Totals.NewMetrics++
		case before.OK && !after.OK:
			status = "removed_metric"
			result.Totals.RemovedMetrics++
		case delta > minAbsDelta:
			status = "regressed"
			result.Totals.RegressedMetrics++
		case -delta > minAbsDelta:
			status = "improved"
			result.Totals.ImprovedMetrics++
		default:
			continue
		}
		result.Totals.ChangedMetrics++
		result.Changes = append(result.Changes, CompareChange{
			Service:        service,
			Metric:         metric,
			Status:         status,
			BaselineCount:  before.Count,
			CandidateCount: after.Count,
			BaselineSum:    before.Sum,
			CandidateSum:   after.Sum,
			DeltaSum:       delta,
			PercentChange:  percentChange(before.Sum, delta),
		})
	}
	return result
}

func flattenMetrics(rep summary.Report) map[string]metricPoint {
	out := map[string]metricPoint{}
	for _, service := range rep.Services {
		for metric, values := range service.Metrics {
			out[joinKey(service.Service, metric)] = metricPoint{Count: values.Count, Sum: values.Sum, OK: true}
		}
	}
	return out
}

func percentChange(baseline float64, delta float64) *float64 {
	if baseline == 0 {
		return nil
	}
	value := (delta / baseline) * 100
	if value == 0 {
		value = 0
	}
	return &value
}

func joinKey(service string, metric string) string {
	return service + "\x00" + metric
}

func splitKey(key string) (string, string) {
	for i, r := range key {
		if r == 0 {
			return key[:i], key[i+1:]
		}
	}
	return key, ""
}

GO

cat > internal/api/routes.go <<'GO'
package api

import "net/http"

func (s *Server) routes(mux *http.ServeMux) {
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/v1/reports/compare", s.compareReports)
	mux.HandleFunc("/v1/reports", s.createReport)
	mux.HandleFunc("/v1/reports/", s.getReportCSV)
}
GO

cat > internal/api/handlers.go <<'GO'
package api

import (
	"encoding/json"
	"net/http"
	"strings"

	"service-ledger/internal/config"
	"service-ledger/internal/events"
	"service-ledger/internal/report"
	"service-ledger/internal/summary"
)

type reportRequest struct {
	ConfigPath string `json:"config_path"`
	EventsPath string `json:"events_path"`
}

type compareRequest struct {
	BaselineReportID  string   `json:"baseline_report_id"`
	CandidateReportID string   `json:"candidate_report_id"`
	MinAbsDelta       *float64 `json:"min_abs_delta"`
}

func (s *Server) health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte(`{"ok":true}`))
}

func (s *Server) createReport(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req reportRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}
	if req.ConfigPath == "" || req.EventsPath == "" {
		http.Error(w, "config_path and events_path are required", http.StatusBadRequest)
		return
	}
	cfg, err := config.LoadAndNormalize(req.ConfigPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	records, err := events.ReadJSONL(req.EventsPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	rep := summary.Build(cfg, records)
	id := s.store.Put(rep)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(map[string]any{"report_id": id, "summary": rep})
}

func (s *Server) getReportCSV(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	id := strings.TrimPrefix(r.URL.Path, "/v1/reports/")
	id = strings.TrimSuffix(id, ".csv")
	if id == "" || id == r.URL.Path {
		http.NotFound(w, r)
		return
	}
	rep, ok := s.store.Get(id)
	if !ok {
		http.NotFound(w, r)
		return
	}
	data, err := report.ToCSV(rep)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/csv")
	_, _ = w.Write(data)
}

func (s *Server) compareReports(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req compareRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}
	if req.BaselineReportID == "" || req.CandidateReportID == "" {
		http.Error(w, "baseline_report_id and candidate_report_id are required", http.StatusBadRequest)
		return
	}
	minAbsDelta := 0.0
	if req.MinAbsDelta != nil {
		minAbsDelta = *req.MinAbsDelta
	}
	if minAbsDelta < 0 {
		http.Error(w, "min_abs_delta must be non-negative", http.StatusBadRequest)
		return
	}
	baseline, ok := s.store.Get(req.BaselineReportID)
	if !ok {
		http.NotFound(w, r)
		return
	}
	candidate, ok := s.store.Get(req.CandidateReportID)
	if !ok {
		http.NotFound(w, r)
		return
	}
	result := report.Compare(req.BaselineReportID, req.CandidateReportID, baseline, candidate, minAbsDelta)
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(result)
}
GO

go test ./...
