package main

import (
	"errors"
	"net/http"
)

func (h *Handler) listGroups(w http.ResponseWriter, r *http.Request) {
	groups := h.svc.ListGroups()
	page, limit := parsePaging(r)
	total := len(groups)
	start := (page - 1) * limit
	end := start + limit
	start = clamp(start, total)
	end = clamp(end, total)
	pageItems := groups[start:end]
	if pageItems == nil {
		pageItems = []*GroupView{}
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"groups": pageItems,
		"total":  total,
		"page":   page,
		"limit":  limit,
	})
}

func (h *Handler) createGroup(w http.ResponseWriter, r *http.Request) {
	var req GroupCreate
	if !decodeStrict(w, r, &req) {
		return
	}
	g, err := h.svc.CreateGroup(req)
	if errors.Is(err, ErrValidation) {
		writeError(w, http.StatusUnprocessableEntity, "invalid group")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, g)
}

func (h *Handler) singleGroup(w http.ResponseWriter, r *http.Request, id string) {
	switch r.Method {
	case http.MethodGet:
		g, err := h.svc.GetGroup(id)
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "group not found")
			return
		}
		setETag(w, g.Version)
		writeJSON(w, http.StatusOK, g)
	case http.MethodPut:
		h.updateGroup(w, r, id)
	case http.MethodDelete:
		err := h.svc.DeleteGroup(id)
		switch {
		case errors.Is(err, ErrNotFound):
			writeError(w, http.StatusNotFound, "group not found")
		case errors.Is(err, ErrInUse):
			writeError(w, http.StatusConflict, "group is referenced by a change request")
		case err != nil:
			writeError(w, http.StatusInternalServerError, err.Error())
		default:
			w.WriteHeader(http.StatusNoContent)
		}
	default:
		methodNotAllowed(w, http.MethodGet, http.MethodPut, http.MethodDelete)
	}
}

func (h *Handler) updateGroup(w http.ResponseWriter, r *http.Request, id string) {
	im, _ := ifMatch(r)
	var upd GroupUpdate
	if !decodeStrict(w, r, &upd) {
		return
	}
	g, err := h.svc.UpdateGroup(id, upd, im)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "group not found")
	case errors.Is(err, ErrVersion):
		writeError(w, http.StatusPreconditionFailed, "version mismatch")
	case errors.Is(err, ErrValidation):
		writeError(w, http.StatusUnprocessableEntity, "invalid group")
	case err != nil:
		writeError(w, http.StatusInternalServerError, err.Error())
	default:
		setETag(w, g.Version)
		writeJSON(w, http.StatusOK, g)
	}
}
