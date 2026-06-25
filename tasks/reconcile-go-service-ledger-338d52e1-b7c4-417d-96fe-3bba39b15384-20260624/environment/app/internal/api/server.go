package api

import (
	"net/http"

	"service-ledger/internal/report"
)

type Server struct {
	store *report.Store
}

func NewServer() *Server {
	return &Server{store: report.NewStore()}
}

func (s *Server) Listen(addr string) error {
	mux := http.NewServeMux()
	s.routes(mux)
	return http.ListenAndServe(addr, mux)
}
