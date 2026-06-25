package main

import (
	"errors"
	"net/http"
)

func (h *Handler) listApprovals(w http.ResponseWriter, r *http.Request, id string) {
	approvals, err := h.svc.ListApprovals(id)
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "change request not found")
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"approvals": approvals,
		"total":     len(approvals),
	})
}

func (h *Handler) recordApproval(w http.ResponseWriter, r *http.Request, id string) {
	var req ApprovalRequest
	if !decodeStrict(w, r, &req) {
		return
	}
	v, err := h.svc.RecordApproval(id, req)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "change request not found")
	case errors.Is(err, ErrBadDecision):
		writeError(w, http.StatusUnprocessableEntity, "decision must be approve or reject")
	case errors.Is(err, ErrTerminal):
		writeError(w, http.StatusConflict, "change request is in a terminal state")
	case errors.Is(err, ErrNotEligible):
		writeError(w, http.StatusUnprocessableEntity, "approver is not eligible for the current stage")
	case errors.Is(err, ErrDuplicate):
		writeError(w, http.StatusConflict, "approver has already decided this stage")
	case err != nil:
		writeError(w, http.StatusInternalServerError, err.Error())
	default:
		setETag(w, v.Version)
		writeJSON(w, http.StatusOK, v)
	}
}

func (h *Handler) revokeApproval(w http.ResponseWriter, r *http.Request, id, approver string) {
	im, _ := ifMatch(r)
	v, err := h.svc.Revoke(id, approver, im)
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "change request not found")
	case errors.Is(err, ErrVersion):
		writeError(w, http.StatusPreconditionFailed, "version mismatch")
	case errors.Is(err, ErrTerminal):
		writeError(w, http.StatusConflict, "change request is canceled")
	case errors.Is(err, ErrNoApproval):
		writeError(w, http.StatusNotFound, "approver has no active decision to revoke")
	case err != nil:
		writeError(w, http.StatusInternalServerError, err.Error())
	default:
		setETag(w, v.Version)
		writeJSON(w, http.StatusOK, v)
	}
}
