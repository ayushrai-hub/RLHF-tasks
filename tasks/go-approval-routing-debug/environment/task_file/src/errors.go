package main

import "errors"

var (
	ErrNotFound    = errors.New("not found")
	ErrTerminal    = errors.New("change request is in a terminal state")
	ErrNotEligible = errors.New("approver is not eligible for the current stage")
	ErrDuplicate   = errors.New("approver has already decided this stage")
	ErrBadDecision = errors.New("decision must be approve or reject")
	ErrNoApproval  = errors.New("approver has no active decision to revoke")
	ErrVersion     = errors.New("version mismatch")
	ErrValidation  = errors.New("validation failed")
	ErrInUse       = errors.New("group is referenced by a change request")
)
