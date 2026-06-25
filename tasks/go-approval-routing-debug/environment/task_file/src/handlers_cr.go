package main

import (
	"errors"
	"net/http"
)

func (h *Handler) listCRs(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	sortKey := r.URL.Query().Get("sort")
	page, limit := parsePaging(r)

	items := h.svc.List(status, sortKey)

	start := page * limit
	end := start + limit
	start = clamp(start, len(items))
	end = clamp(end, len(items))
	pageItems := items[start:end]

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"change_requests": pageItems,
		"total":           len(pageItems),
		"page":            page,
		"limit":           limit,
	})
}

func (h *Handler) createCR(w http.ResponseWriter, r *http.Request) {
	var req CreateRequest
	if !decodeStrict(w, r, &req) {
		return
	}
	v, err := h.svc.Create(req)
	if errors.Is(err, ErrValidation) {
		writeError(w, http.StatusUnprocessableEntity, "invalid change request")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	setETag(w, v.Version)
	writeJSON(w, http.StatusCreated, v)
}

func (h *Handler) singleCR(w http.ResponseWriter, r *http.Request, id string) {
	switch r.Method {
	case http.MethodGet:
		v, err := h.svc.Get(id)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "change request not found")
			return
		}
		writeJSON(w, http.StatusOK, v)
	case http.MethodPut:
		h.updateCR(w, r, id)
	case http.MethodDelete:
		err := h.svc.Delete(id)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "change request not found")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
	}
}

func (h *Handler) updateCR(w http.ResponseWriter, r *http.Request, id string) {
	im, _ := ifMatch(r)
	var upd ChangeRequestUpdate
	if !decodeStrict(w, r, &upd) {
		return
	}
	v, err := h.svc.Update(id, upd, im)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "change request not found")
	case errors.Is(err, ErrVersion):
		writeError(w, http.StatusPreconditionFailed, "version mismatch")
	case errors.Is(err, ErrTerminal):
		writeError(w, http.StatusConflict, "change request is in a terminal state")
	case errors.Is(err, ErrValidation):
		writeError(w, http.StatusUnprocessableEntity, "invalid change request")
	case err != nil:
		writeError(w, http.StatusInternalServerError, err.Error())
	default:
		setETag(w, v.Version)
		writeJSON(w, http.StatusOK, v)
	}
}

func (h *Handler) cancelCR(w http.ResponseWriter, r *http.Request, id string) {
	im, _ := ifMatch(r)
	v, err := h.svc.Cancel(id, im)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "change request not found")
	case errors.Is(err, ErrVersion):
		writeError(w, http.StatusPreconditionFailed, "version mismatch")
	case errors.Is(err, ErrTerminal):
		writeError(w, http.StatusConflict, "change request is already in a terminal state")
	case err != nil:
		writeError(w, http.StatusInternalServerError, err.Error())
	default:
		setETag(w, v.Version)
		writeJSON(w, http.StatusOK, v)
	}
}
