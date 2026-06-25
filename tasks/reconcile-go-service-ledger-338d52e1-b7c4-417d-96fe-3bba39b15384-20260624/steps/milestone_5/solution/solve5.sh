#!/bin/bash
set -euo pipefail

cd /app

cat > internal/report/reconcile.go <<'GO'
package report

import (
	"math"
	"sort"

	"service-ledger/internal/summary"
)

type ReconcileAction struct {
	Service        string  `json:"service"`
	Tier           string  `json:"tier"`
	Metric         string  `json:"metric"`
	Status         string  `json:"status"`
	DeltaSum       float64 `json:"delta_sum"`
	AbsoluteDelta  float64 `json:"absolute_delta"`
	ImpactScore    float64 `json:"impact_score"`
	Recommendation string  `json:"recommendation"`
}

type ReconcileTotals struct {
	ActionCount      int            `json:"action_count"`
	TotalImpactScore float64        `json:"total_impact_score"`
	ByStatus         map[string]int `json:"by_status"`
	ByTier           map[string]int `json:"by_tier"`
}

type ReconcileResult struct {
	BaselineReportID  string            `json:"baseline_report_id"`
	CandidateReportID string            `json:"candidate_report_id"`
	MinAbsDelta       float64           `json:"min_abs_delta"`
	SuppressedStatuses []string          `json:"suppressed_statuses"`
	Actions           []ReconcileAction `json:"actions"`
	Totals            ReconcileTotals   `json:"totals"`
	BudgetPlan        *BudgetPlan       `json:"budget_plan,omitempty"`
}

type ImpactBudget struct {
	MaxTotalImpact *float64
	TierLimits     map[string]float64
	ServiceLimits  map[string]float64
	StatusLimits   map[string]float64
}

type BudgetPlan struct {
	MaxTotalImpact  *float64          `json:"max_total_impact,omitempty"`
	TierLimits      map[string]float64 `json:"tier_limits"`
	ServiceLimits   map[string]float64 `json:"service_limits"`
	StatusLimits    map[string]float64 `json:"status_limits"`
	SelectedActions []ReconcileAction  `json:"selected_actions"`
	DeferredActions []ReconcileAction  `json:"deferred_actions"`
	DeferredReasons []DeferredReason   `json:"deferred_reasons"`
	Totals          BudgetTotals       `json:"totals"`
}

type DeferredReason struct {
	Service string   `json:"service"`
	Metric  string   `json:"metric"`
	Reasons []string `json:"reasons"`
}

type BudgetTotals struct {
	SelectedCount       int            `json:"selected_count"`
	DeferredCount       int            `json:"deferred_count"`
	SelectedImpactScore float64        `json:"selected_impact_score"`
	DeferredImpactScore float64        `json:"deferred_impact_score"`
	SelectedByTier      map[string]int `json:"selected_by_tier"`
	DeferredByTier      map[string]int `json:"deferred_by_tier"`
	SelectedByService   map[string]int `json:"selected_by_service"`
	DeferredByService   map[string]int `json:"deferred_by_service"`
}

func Reconcile(baselineID string, candidateID string, baseline summary.Report, candidate summary.Report, minAbsDelta float64, multipliers map[string]float64, suppressed map[string]bool, budget *ImpactBudget) ReconcileResult {
	comparison := Compare(baselineID, candidateID, baseline, candidate, minAbsDelta)
	baselineTiers := serviceTiers(baseline)
	candidateTiers := serviceTiers(candidate)

	result := ReconcileResult{
		BaselineReportID:  baselineID,
		CandidateReportID: candidateID,
		MinAbsDelta:       minAbsDelta,
		SuppressedStatuses: sortedSuppressed(suppressed),
		Actions:           []ReconcileAction{},
		Totals: ReconcileTotals{
			ByStatus: map[string]int{},
			ByTier:   map[string]int{},
		},
	}
	for _, change := range comparison.Changes {
		if suppressed[change.Status] {
			continue
		}
		tier := tierForChange(change, baselineTiers, candidateTiers)
		absoluteDelta := math.Abs(change.DeltaSum)
		impactScore := round2(absoluteDelta * tierMultiplier(tier, multipliers))
		action := ReconcileAction{
			Service:        change.Service,
			Tier:           tier,
			Metric:         change.Metric,
			Status:         change.Status,
			DeltaSum:       change.DeltaSum,
			AbsoluteDelta:  absoluteDelta,
			ImpactScore:    impactScore,
			Recommendation: recommendation(change.Status),
		}
		result.Actions = append(result.Actions, action)
		result.Totals.ActionCount++
		result.Totals.TotalImpactScore = round2(result.Totals.TotalImpactScore + impactScore)
		result.Totals.ByStatus[change.Status]++
		result.Totals.ByTier[tier]++
	}
	sort.Slice(result.Actions, func(i, j int) bool {
		left := result.Actions[i]
		right := result.Actions[j]
		if left.ImpactScore != right.ImpactScore {
			return left.ImpactScore > right.ImpactScore
		}
		if left.Service != right.Service {
			return left.Service < right.Service
		}
		return left.Metric < right.Metric
	})
	result.BudgetPlan = buildBudgetPlan(result.Actions, budget)
	return result
}

func buildBudgetPlan(actions []ReconcileAction, budget *ImpactBudget) *BudgetPlan {
	if budget == nil {
		return nil
	}
	plan := &BudgetPlan{
		MaxTotalImpact:  budget.MaxTotalImpact,
		TierLimits:      copyFloatMap(budget.TierLimits),
		ServiceLimits:   copyFloatMap(budget.ServiceLimits),
		StatusLimits:    copyFloatMap(budget.StatusLimits),
		SelectedActions: []ReconcileAction{},
		DeferredActions: []ReconcileAction{},
		DeferredReasons: []DeferredReason{},
		Totals: BudgetTotals{
			SelectedByTier:    map[string]int{},
			DeferredByTier:    map[string]int{},
			SelectedByService: map[string]int{},
			DeferredByService: map[string]int{},
		},
	}
	usedTotal := 0.0
	usedByTier := map[string]float64{}
	usedByService := map[string]float64{}
	usedByStatus := map[string]float64{}
	for _, action := range actions {
		reasons := budgetDeferReasons(action, budget, usedTotal, usedByTier, usedByService, usedByStatus)
		if len(reasons) == 0 {
			plan.SelectedActions = append(plan.SelectedActions, action)
			plan.Totals.SelectedCount++
			plan.Totals.SelectedImpactScore = round2(plan.Totals.SelectedImpactScore + action.ImpactScore)
			plan.Totals.SelectedByTier[action.Tier]++
			plan.Totals.SelectedByService[action.Service]++
			usedTotal = round2(usedTotal + action.ImpactScore)
			usedByTier[action.Tier] = round2(usedByTier[action.Tier] + action.ImpactScore)
			usedByService[action.Service] = round2(usedByService[action.Service] + action.ImpactScore)
			usedByStatus[action.Status] = round2(usedByStatus[action.Status] + action.ImpactScore)
			continue
		}
		plan.DeferredActions = append(plan.DeferredActions, action)
		plan.DeferredReasons = append(plan.DeferredReasons, DeferredReason{
			Service: action.Service,
			Metric:  action.Metric,
			Reasons: reasons,
		})
		plan.Totals.DeferredCount++
		plan.Totals.DeferredImpactScore = round2(plan.Totals.DeferredImpactScore + action.ImpactScore)
		plan.Totals.DeferredByTier[action.Tier]++
		plan.Totals.DeferredByService[action.Service]++
	}
	return plan
}

func budgetDeferReasons(action ReconcileAction, budget *ImpactBudget, usedTotal float64, usedByTier map[string]float64, usedByService map[string]float64, usedByStatus map[string]float64) []string {
	reasons := []string{}
	if budget.MaxTotalImpact != nil && round2(usedTotal+action.ImpactScore) > *budget.MaxTotalImpact {
		reasons = append(reasons, "max_total_impact")
	}
	if limit, ok := budget.TierLimits[action.Tier]; ok && round2(usedByTier[action.Tier]+action.ImpactScore) > limit {
		reasons = append(reasons, "tier_limit")
	}
	if limit, ok := budget.ServiceLimits[action.Service]; ok && round2(usedByService[action.Service]+action.ImpactScore) > limit {
		reasons = append(reasons, "service_limit")
	}
	if limit, ok := budget.StatusLimits[action.Status]; ok && round2(usedByStatus[action.Status]+action.ImpactScore) > limit {
		reasons = append(reasons, "status_limit")
	}
	return reasons
}

func round2(value float64) float64 {
	return math.Round(value*100) / 100
}

func copyFloatMap(values map[string]float64) map[string]float64 {
	out := map[string]float64{}
	for key, value := range values {
		out[key] = value
	}
	return out
}

func serviceTiers(rep summary.Report) map[string]string {
	out := map[string]string{}
	for _, service := range rep.Services {
		out[service.Service] = service.Tier
	}
	return out
}

func tierForChange(change CompareChange, baseline map[string]string, candidate map[string]string) string {
	if change.Status == "removed_metric" {
		return baseline[change.Service]
	}
	if tier := candidate[change.Service]; tier != "" {
		return tier
	}
	return baseline[change.Service]
}

func tierMultiplier(tier string, overrides map[string]float64) float64 {
	if value, ok := overrides[tier]; ok {
		return value
	}
	if tier == "critical" {
		return 2
	}
	return 1
}

func recommendation(status string) string {
	switch status {
	case "new_metric", "regressed":
		return "investigate_candidate"
	default:
		return "verify_reduction"
	}
}

func sortedSuppressed(suppressed map[string]bool) []string {
	values := make([]string, 0, len(suppressed))
	for status := range suppressed {
		values = append(values, status)
	}
	sort.Strings(values)
	return values
}
GO

cat > internal/api/routes.go <<'GO'
package api

import "net/http"

func (s *Server) routes(mux *http.ServeMux) {
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/v1/reports/compare", s.compareReports)
	mux.HandleFunc("/v1/reports/reconcile", s.reconcileReports)
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

type reconcileRequest struct {
	BaselineReportID  string             `json:"baseline_report_id"`
	CandidateReportID string             `json:"candidate_report_id"`
	MinAbsDelta       *float64           `json:"min_abs_delta"`
	TierMultipliers   map[string]float64 `json:"tier_multipliers"`
	SuppressStatuses  []string           `json:"suppress_statuses"`
	ImpactBudget      *impactBudgetRequest `json:"impact_budget"`
}

type impactBudgetRequest struct {
	MaxTotalImpact *float64           `json:"max_total_impact"`
	TierLimits     map[string]float64 `json:"tier_limits"`
	ServiceLimits  map[string]float64 `json:"service_limits"`
	StatusLimits   map[string]float64 `json:"status_limits"`
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

func (s *Server) reconcileReports(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req reconcileRequest
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
	for tier, value := range req.TierMultipliers {
		if tier == "" || value <= 0 {
			http.Error(w, "tier_multipliers must contain positive values", http.StatusBadRequest)
			return
		}
	}
	suppressed := map[string]bool{}
	for _, status := range req.SuppressStatuses {
		if !knownStatus(status) {
			http.Error(w, "suppress_statuses contains an unknown status", http.StatusBadRequest)
			return
		}
		suppressed[status] = true
	}
	budget, ok := parseImpactBudget(req.ImpactBudget)
	if !ok {
		http.Error(w, "impact_budget must contain non-negative limits", http.StatusBadRequest)
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
	result := report.Reconcile(req.BaselineReportID, req.CandidateReportID, baseline, candidate, minAbsDelta, req.TierMultipliers, suppressed, budget)
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(result)
}

func parseImpactBudget(req *impactBudgetRequest) (*report.ImpactBudget, bool) {
	if req == nil {
		return nil, true
	}
	if req.MaxTotalImpact != nil && *req.MaxTotalImpact < 0 {
		return nil, false
	}
	limits := map[string]float64{}
	for tier, value := range req.TierLimits {
		if value < 0 {
			return nil, false
		}
		limits[tier] = value
	}
	serviceLimits := map[string]float64{}
	for service, value := range req.ServiceLimits {
		normalizedService := config.CanonicalName(service)
		if normalizedService == "" || value < 0 {
			return nil, false
		}
		serviceLimits[normalizedService] = value
	}
	statusLimits := map[string]float64{}
	for status, value := range req.StatusLimits {
		if !knownStatus(status) || value < 0 {
			return nil, false
		}
		statusLimits[status] = value
	}
	return &report.ImpactBudget{MaxTotalImpact: req.MaxTotalImpact, TierLimits: limits, ServiceLimits: serviceLimits, StatusLimits: statusLimits}, true
}

func knownStatus(status string) bool {
	switch status {
	case "new_metric", "removed_metric", "regressed", "improved":
		return true
	default:
		return false
	}
}
GO

go test ./...
