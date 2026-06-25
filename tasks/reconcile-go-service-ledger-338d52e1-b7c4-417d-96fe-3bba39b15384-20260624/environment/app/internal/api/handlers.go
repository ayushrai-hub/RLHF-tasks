package api

import (
	"encoding/json"
	"net/http"
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
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(map[string]any{"report_id": "pending", "summary": map[string]any{}})
}

func (s *Server) getReportCSV(w http.ResponseWriter, r *http.Request) {
	http.NotFound(w, r)
}
