package api

import "net/http"

func (s *Server) routes(mux *http.ServeMux) {
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/v1/reports", s.createReport)
	mux.HandleFunc("/v1/reports/", s.getReportCSV)
}
