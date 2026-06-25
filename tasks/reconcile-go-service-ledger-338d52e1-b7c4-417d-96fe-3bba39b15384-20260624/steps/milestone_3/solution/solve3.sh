#!/bin/bash
set -euo pipefail

cd /app

cat > internal/report/id.go <<'GO'
package report

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"

	"service-ledger/internal/summary"
)

func ID(rep summary.Report) string {
	data, _ := json.Marshal(rep)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])[:16]
}
GO

cat > internal/report/csv.go <<'GO'
package report

import (
	"bytes"
	"encoding/csv"
	"sort"
	"strings"

	"service-ledger/internal/summary"
)

func ToCSV(rep summary.Report) ([]byte, error) {
	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)
	if err := writer.Write([]string{"service", "tier", "metric", "count", "sum", "min", "max", "avg", "sources"}); err != nil {
		return nil, err
	}
	services := append([]summary.ServiceSummary{}, rep.Services...)
	sort.Slice(services, func(i, j int) bool {
		return services[i].Service < services[j].Service
	})
	for _, service := range services {
		metrics := make([]string, 0, len(service.Metrics))
		for metric := range service.Metrics {
			metrics = append(metrics, metric)
		}
		sort.Strings(metrics)
		for _, metric := range metrics {
			values := service.Metrics[metric]
			if err := writer.Write([]string{
				service.Service,
				service.Tier,
				metric,
				intString(values.Count),
				floatString(values.Sum),
				floatString(values.Min),
				floatString(values.Max),
				floatString(values.Avg),
				strings.Join(service.Sources, ";"),
			}); err != nil {
				return nil, err
			}
		}
	}
	writer.Flush()
	return buf.Bytes(), writer.Error()
}
GO

cat > internal/report/format.go <<'GO'
package report

import "strconv"

func floatString(value float64) string {
	return strconv.FormatFloat(value, 'f', -1, 64)
}

func intString(value int) string {
	return strconv.Itoa(value)
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
GO

go test ./...
