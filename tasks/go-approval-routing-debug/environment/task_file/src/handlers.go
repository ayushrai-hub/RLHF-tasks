package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

type Handler struct {
	svc *Service
}

func NewHandler(svc *Service) *Handler {
	return &Handler{svc: svc}
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func methodNotAllowed(w http.ResponseWriter, allow ...string) {
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func setETag(w http.ResponseWriter, version int) {
	w.Header().Set("ETag", "\""+strconv.Itoa(version)+"\"")
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimRight(r.URL.Path, "/")
	if path == "" {
		path = "/"
	}

	switch {
	case path == "/healthz":
		if r.Method != http.MethodGet {
			methodNotAllowed(w, http.MethodGet)
			return
		}
		healthzHandler(w, r)
		return

	case path == "/stats":
		if r.Method != http.MethodGet {
			methodNotAllowed(w, http.MethodGet)
			return
		}
		writeJSON(w, http.StatusOK, h.svc.Stats())
		return

	case path == "/change-requests":
		switch r.Method {
		case http.MethodGet:
			h.listCRs(w, r)
		case http.MethodPost:
			h.createCR(w, r)
		default:
			methodNotAllowed(w, http.MethodGet, http.MethodPost)
		}
		return

	case path == "/groups":
		switch r.Method {
		case http.MethodGet:
			h.listGroups(w, r)
		case http.MethodPost:
			h.createGroup(w, r)
		default:
			methodNotAllowed(w, http.MethodGet, http.MethodPost)
		}
		return

	case strings.HasPrefix(path, "/groups/"):
		id := strings.TrimPrefix(path, "/groups/")
		if id == "" || strings.Contains(id, "/") {
			http.NotFound(w, r)
			return
		}
		h.singleGroup(w, r, id)
		return

	case strings.HasPrefix(path, "/approvers/"):
		id := strings.TrimPrefix(path, "/approvers/")
		if id == "" || strings.Contains(id, "/") {
			http.NotFound(w, r)
			return
		}
		if r.Method != http.MethodGet {
			methodNotAllowed(w, http.MethodGet)
			return
		}
		writeJSON(w, http.StatusOK, h.svc.Approver(id))
		return

	case strings.HasPrefix(path, "/change-requests/"):
		rest := strings.TrimPrefix(path, "/change-requests/")
		parts := strings.Split(rest, "/")
		id := parts[0]
		if id == "" {
			http.NotFound(w, r)
			return
		}
		switch len(parts) {
		case 1:
			h.singleCR(w, r, id)
		case 2:
			switch parts[1] {
			case "cancel":
				if r.Method != http.MethodPost {
					methodNotAllowed(w, http.MethodPost)
					return
				}
				h.cancelCR(w, r, id)
			case "approvals":
				switch r.Method {
				case http.MethodGet:
					h.listApprovals(w, r, id)
				case http.MethodPost:
					h.recordApproval(w, r, id)
				default:
					methodNotAllowed(w, http.MethodGet, http.MethodPost)
				}
			default:
				http.NotFound(w, r)
			}
		case 3:
			if parts[1] == "approvals" {
				if r.Method != http.MethodDelete {
					methodNotAllowed(w, http.MethodDelete)
					return
				}
				h.revokeApproval(w, r, id, parts[2])
				return
			}
			http.NotFound(w, r)
		default:
			http.NotFound(w, r)
		}
		return
	}

	http.NotFound(w, r)
}
