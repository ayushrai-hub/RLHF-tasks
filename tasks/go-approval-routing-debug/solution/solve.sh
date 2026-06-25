#!/usr/bin/env bash
# Reference solution for the change-request approval-routing service.
# Rewrites the buggy source files under /app/src with correct implementations.
# Use POSIX-portable shell options only: this script must apply the fix whether
# it is invoked as `bash solve.sh` or `sh solve.sh`. dash rejects `-o pipefail`
# ("Illegal option -o pipefail") and aborts at this line before any file is
# written, leaving the buggy source in place. There are no pipelines here, so
# `set -eu` is sufficient.
set -eu

SRC=/app/src

cat > "$SRC/service.go" << 'GO_EOF'
package main

import (
	"fmt"
	"sort"
	"sync"
)

// Service holds all change requests and approver groups in memory and
// implements the routing rules. All exported methods are safe for concurrent
// use and never hand back references to internal mutable state
// (copy-on-return), so callers cannot race with in-flight mutations.
type Service struct {
	mu      sync.RWMutex
	crs     map[string]*ChangeRequest
	groups  map[string]*ApproverGroup
	cache   map[string]*CRView
	nextID  int
	nextGID int
	nextSeq int

	// lifetime counters (survive deletion)
	crsCreated      int
	groupsCreated   int
	approvalsTotal  int
	revokesTotal    int
	givenByApprover map[string]int
}

func NewService() *Service {
	return &Service{
		crs:             make(map[string]*ChangeRequest),
		groups:          make(map[string]*ApproverGroup),
		cache:           make(map[string]*CRView),
		givenByApprover: make(map[string]int),
	}
}

// effEligible resolves a stage's effective eligible roster: the literal
// eligible ids unioned with the live members of every referenced group. The
// caller must hold s.mu.
func (s *Service) effEligible(st Stage) map[string]bool {
	set := make(map[string]bool)
	for _, a := range st.Eligible {
		set[a] = true
	}
	for _, gid := range st.EligibleGroups {
		if g, ok := s.groups[gid]; ok {
			for _, m := range g.Members {
				set[m] = true
			}
		}
	}
	return set
}

// evaluate walks the pipeline stage by stage and derives the routing state from
// the recorded (non-revoked) approvals, resolving each stage's eligible roster
// live. A stage is satisfied when at least Required distinct eligible approvers
// have approved it. A rejection at the first unsatisfied stage rejects the whole
// request. The caller must hold s.mu.
func (s *Service) evaluate(cr *ChangeRequest) Derived {
	for i, st := range cr.Stages {
		eff := s.effEligible(st)
		rejecter := ""
		approvers := make(map[string]bool)
		for _, a := range cr.Approvals {
			if a.Revoked || a.StageIndex != i {
				continue
			}
			if !eff[a.Approver] {
				continue
			}
			if a.Decision == "reject" {
				if rejecter == "" {
					rejecter = a.Approver
				}
			} else if a.Decision == "approve" {
				approvers[a.Approver] = true
			}
		}
		if rejecter != "" {
			return Derived{Status: "rejected", CurrentStage: i, RejectedBy: rejecter, RejectedStage: i}
		}
		if len(approvers) < st.Required {
			return Derived{Status: "pending", CurrentStage: i, RejectedStage: -1}
		}
	}
	return Derived{Status: "approved", CurrentStage: len(cr.Stages), RejectedStage: -1}
}

func (s *Service) terminal(cr *ChangeRequest) bool {
	if cr.Canceled {
		return true
	}
	d := s.evaluate(cr)
	return d.Status == "approved" || d.Status == "rejected"
}

// buildView produces a fully detached JSON projection. The caller must hold
// s.mu.
func (s *Service) buildView(cr *ChangeRequest) *CRView {
	stages := make([]Stage, len(cr.Stages))
	for i, st := range cr.Stages {
		elig := make([]string, len(st.Eligible))
		copy(elig, st.Eligible)
		var groups []string
		if len(st.EligibleGroups) > 0 {
			groups = make([]string, len(st.EligibleGroups))
			copy(groups, st.EligibleGroups)
		}
		stages[i] = Stage{Name: st.Name, Required: st.Required, Eligible: elig, EligibleGroups: groups}
	}
	active := make([]*Approval, 0)
	for _, a := range cr.Approvals {
		if a.Revoked {
			continue
		}
		cp := *a
		active = append(active, &cp)
	}
	sort.Slice(active, func(i, j int) bool { return active[i].Seq < active[j].Seq })

	v := &CRView{
		ID:        cr.ID,
		Title:     cr.Title,
		Author:    cr.Author,
		Stages:    stages,
		Approvals: active,
		Revision:  cr.Revision,
		Version:   cr.Version,
	}
	if cr.Canceled {
		v.Status = "canceled"
		v.CurrentStage = 0
		return v
	}
	d := s.evaluate(cr)
	v.Status = d.Status
	v.CurrentStage = d.CurrentStage
	if d.Status == "rejected" {
		v.RejectedBy = d.RejectedBy
		rs := d.RejectedStage
		v.RejectedStage = &rs
	}
	return v
}

func (s *Service) invalidate(id string) {
	delete(s.cache, id)
}

// invalidateReferencing drops the cached view of every request whose pipeline
// references the given group, so a membership change is observed immediately.
func (s *Service) invalidateReferencing(gid string) {
	for id, cr := range s.crs {
		for _, st := range cr.Stages {
			if contains(st.EligibleGroups, gid) {
				delete(s.cache, id)
				break
			}
		}
	}
}

// validateStages enforces that a pipeline is well-formed and satisfiable against
// the current set of groups. The caller must hold s.mu.
func (s *Service) validateStages(stages []Stage) error {
	if len(stages) < 1 {
		return ErrValidation
	}
	for _, st := range stages {
		if st.Name == "" {
			return ErrValidation
		}
		if st.Required < 1 {
			return ErrValidation
		}
		for _, gid := range st.EligibleGroups {
			if _, ok := s.groups[gid]; !ok {
				return ErrValidation
			}
		}
		eff := s.effEligible(st)
		if len(eff) == 0 {
			return ErrValidation
		}
		// A stage that needs more approvers than are eligible can never be
		// satisfied, so it is rejected up front.
		if st.Required > len(eff) {
			return ErrValidation
		}
	}
	return nil
}

func (s *Service) validateCreate(req CreateRequest) error {
	if req.Title == "" || req.Author == "" {
		return ErrValidation
	}
	return s.validateStages(req.Stages)
}

// ---- change requests -------------------------------------------------------

func (s *Service) Create(req CreateRequest) (*CRView, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.validateCreate(req); err != nil {
		return nil, err
	}
	s.nextID++
	s.nextSeq++
	cr := &ChangeRequest{
		ID:      fmt.Sprintf("cr_%d", s.nextID),
		Title:   req.Title,
		Author:  req.Author,
		Stages:  req.Stages,
		Version: 1,
		Seq:     s.nextSeq,
	}
	s.crs[cr.ID] = cr
	s.crsCreated++
	return s.buildView(cr), nil
}

func (s *Service) Get(id string) (*CRView, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if v, ok := s.cache[id]; ok {
		cp := *v
		return &cp, nil
	}
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	v := s.buildView(cr)
	s.cache[id] = v
	cp := *v
	return &cp, nil
}

func (s *Service) List(status, sortKey string) []*CRView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*CRView, 0)
	for _, cr := range s.crs {
		v := s.buildView(cr)
		if status != "" && v.Status != status {
			continue
		}
		out = append(out, v)
	}
	switch sortKey {
	case "title":
		sort.Slice(out, func(i, j int) bool { return out[i].Title < out[j].Title })
	case "stages":
		sort.Slice(out, func(i, j int) bool {
			if len(out[i].Stages) != len(out[j].Stages) {
				return len(out[i].Stages) > len(out[j].Stages)
			}
			return out[i].ID < out[j].ID
		})
	default:
		sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	}
	return out
}

func (s *Service) checkVersion(version, ifMatch int) error {
	if ifMatch != version {
		return ErrVersion
	}
	return nil
}

func (s *Service) Update(id string, upd ChangeRequestUpdate, ifMatch int) (*CRView, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	if err := s.checkVersion(cr.Version, ifMatch); err != nil {
		return nil, err
	}
	if cr.Canceled {
		return nil, ErrTerminal
	}
	newStages := cr.Stages
	if upd.Stages != nil {
		newStages = *upd.Stages
	}
	newTitle := cr.Title
	if upd.Title != nil {
		newTitle = *upd.Title
	}
	if err := s.validateStages(newStages); err != nil {
		return nil, err
	}
	if upd.Title != nil && newTitle == "" {
		return nil, ErrValidation
	}
	cr.Title = newTitle
	cr.Stages = newStages
	cr.Approvals = nil
	cr.Revision++
	cr.Version++
	s.invalidate(id)
	return s.buildView(cr), nil
}

func (s *Service) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.crs[id]; !ok {
		return ErrNotFound
	}
	delete(s.crs, id)
	s.invalidate(id)
	return nil
}

func (s *Service) Cancel(id string, ifMatch int) (*CRView, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	if err := s.checkVersion(cr.Version, ifMatch); err != nil {
		return nil, err
	}
	if s.terminal(cr) {
		return nil, ErrTerminal
	}
	cr.Canceled = true
	cr.Version++
	s.invalidate(id)
	return s.buildView(cr), nil
}

func (s *Service) RecordApproval(id string, req ApprovalRequest) (*CRView, error) {
	if req.Decision != "approve" && req.Decision != "reject" {
		return nil, ErrBadDecision
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	if s.terminal(cr) {
		return nil, ErrTerminal
	}
	d := s.evaluate(cr)
	cur := d.CurrentStage
	eff := s.effEligible(cr.Stages[cur])
	if !eff[req.Approver] {
		return nil, ErrNotEligible
	}
	for _, a := range cr.Approvals {
		if !a.Revoked && a.StageIndex == cur && a.Approver == req.Approver {
			return nil, ErrDuplicate
		}
	}
	s.nextSeq++
	cr.Approvals = append(cr.Approvals, &Approval{
		Approver:   req.Approver,
		StageIndex: cur,
		Decision:   req.Decision,
		Seq:        s.nextSeq,
	})
	s.approvalsTotal++
	if req.Decision == "approve" {
		s.givenByApprover[req.Approver]++
	}
	cr.Version++
	s.invalidate(id)
	return s.buildView(cr), nil
}

func (s *Service) Revoke(id, approver string, ifMatch int) (*CRView, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	if err := s.checkVersion(cr.Version, ifMatch); err != nil {
		return nil, err
	}
	if cr.Canceled {
		return nil, ErrTerminal
	}
	var target *Approval
	for _, a := range cr.Approvals {
		if a.Revoked || a.Approver != approver {
			continue
		}
		if target == nil || a.Seq > target.Seq {
			target = a
		}
	}
	if target == nil {
		return nil, ErrNoApproval
	}
	target.Revoked = true
	d := s.evaluate(cr)
	cutoff := d.CurrentStage
	for _, a := range cr.Approvals {
		if !a.Revoked && a.StageIndex > cutoff {
			a.Revoked = true
		}
	}
	s.revokesTotal++
	cr.Version++
	s.invalidate(id)
	return s.buildView(cr), nil
}

func (s *Service) ListApprovals(id string) ([]*Approval, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	out := make([]*Approval, 0)
	for _, a := range cr.Approvals {
		if a.Revoked {
			continue
		}
		cp := *a
		out = append(out, &cp)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Seq < out[j].Seq })
	return out, nil
}

func (s *Service) Approver(id string) *ApproverView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v := &ApproverView{
		Approver:        id,
		ApprovalsGiven:  s.givenByApprover[id],
		PendingRequests: make([]string, 0),
	}
	for _, cr := range s.crs {
		if cr.Canceled {
			continue
		}
		for _, a := range cr.Approvals {
			if !a.Revoked && a.Approver == id && a.Decision == "approve" {
				v.ActiveApprovals++
			}
		}
		d := s.evaluate(cr)
		if d.Status != "pending" {
			continue
		}
		eff := s.effEligible(cr.Stages[d.CurrentStage])
		if !eff[id] {
			continue
		}
		already := false
		for _, a := range cr.Approvals {
			if !a.Revoked && a.StageIndex == d.CurrentStage && a.Approver == id {
				already = true
				break
			}
		}
		if !already {
			v.PendingRequests = append(v.PendingRequests, cr.ID)
		}
	}
	sort.Strings(v.PendingRequests)
	return v
}

func (s *Service) Stats() StatsView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	active := 0
	for _, cr := range s.crs {
		if !s.terminal(cr) {
			active++
		}
	}
	return StatsView{
		CRsCreated:        s.crsCreated,
		CRsActive:         active,
		ApprovalsRecorded: s.approvalsTotal,
		RevokesProcessed:  s.revokesTotal,
		GroupsCreated:     s.groupsCreated,
	}
}

// ---- approver groups -------------------------------------------------------

func (s *Service) groupView(g *ApproverGroup) *GroupView {
	members := make([]string, len(g.Members))
	copy(members, g.Members)
	refs := make([]string, 0)
	for _, cr := range s.crs {
		for _, st := range cr.Stages {
			if contains(st.EligibleGroups, g.ID) {
				refs = append(refs, cr.ID)
				break
			}
		}
	}
	sort.Strings(refs)
	return &GroupView{
		ID:                  g.ID,
		Name:                g.Name,
		Members:             members,
		MemberCount:         distinct(g.Members),
		ReferencingRequests: refs,
		Version:             g.Version,
	}
}

func (s *Service) CreateGroup(req GroupCreate) (*GroupView, error) {
	if err := validateGroup(req.Name, req.Members); err != nil {
		return nil, err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextGID++
	s.nextSeq++
	g := &ApproverGroup{
		ID:      fmt.Sprintf("grp_%d", s.nextGID),
		Name:    req.Name,
		Members: req.Members,
		Version: 1,
		Seq:     s.nextSeq,
	}
	s.groups[g.ID] = g
	s.groupsCreated++
	return s.groupView(g), nil
}

func (s *Service) GetGroup(id string) (*GroupView, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	g, ok := s.groups[id]
	if !ok {
		return nil, ErrNotFound
	}
	return s.groupView(g), nil
}

func (s *Service) ListGroups() []*GroupView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*GroupView, 0)
	for _, g := range s.groups {
		out = append(out, s.groupView(g))
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

func (s *Service) UpdateGroup(id string, upd GroupUpdate, ifMatch int) (*GroupView, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	g, ok := s.groups[id]
	if !ok {
		return nil, ErrNotFound
	}
	if err := s.checkVersion(g.Version, ifMatch); err != nil {
		return nil, err
	}
	newName := g.Name
	if upd.Name != nil {
		newName = *upd.Name
	}
	newMembers := g.Members
	if upd.Members != nil {
		newMembers = *upd.Members
	}
	if err := validateGroup(newName, newMembers); err != nil {
		return nil, err
	}
	g.Name = newName
	g.Members = newMembers
	g.Version++
	// Roster changes re-route every referencing request; drop their caches so
	// the new effective eligibility is observed immediately.
	s.invalidateReferencing(id)
	return s.groupView(g), nil
}

func (s *Service) DeleteGroup(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.groups[id]; !ok {
		return ErrNotFound
	}
	for _, cr := range s.crs {
		for _, st := range cr.Stages {
			if contains(st.EligibleGroups, id) {
				return ErrInUse
			}
		}
	}
	delete(s.groups, id)
	return nil
}
GO_EOF

cat > "$SRC/validate.go" << 'GO_EOF'
package main

// validateGroup checks that an approver group is well-formed.
func validateGroup(name string, members []string) error {
	if name == "" {
		return ErrValidation
	}
	if len(members) == 0 {
		return ErrValidation
	}
	for _, m := range members {
		if m == "" {
			return ErrValidation
		}
	}
	return nil
}
GO_EOF

cat > "$SRC/handlers.go" << 'GO_EOF'
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
	w.Header().Set("Allow", strings.Join(allow, ", "))
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
GO_EOF

cat > "$SRC/handlers_cr.go" << 'GO_EOF'
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
	total := len(items)

	start := (page - 1) * limit
	end := start + limit
	start = clamp(start, total)
	end = clamp(end, total)
	pageItems := items[start:end]
	if pageItems == nil {
		pageItems = []*CRView{}
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"change_requests": pageItems,
		"total":           total,
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
		setETag(w, v.Version)
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
	im, ok := ifMatch(r)
	if !ok {
		writeError(w, http.StatusPreconditionRequired, "If-Match header is required")
		return
	}
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
	im, ok := ifMatch(r)
	if !ok {
		writeError(w, http.StatusPreconditionRequired, "If-Match header is required")
		return
	}
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
GO_EOF

cat > "$SRC/handlers_approvals.go" << 'GO_EOF'
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
	im, ok := ifMatch(r)
	if !ok {
		writeError(w, http.StatusPreconditionRequired, "If-Match header is required")
		return
	}
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
GO_EOF

cat > "$SRC/middleware.go" << 'GO_EOF'
package main

import (
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"strings"
)

// decodeStrict enforces a JSON content type and rejects unknown fields. It
// returns false (after writing the response) when the body is unacceptable.
func decodeStrict(w http.ResponseWriter, r *http.Request, dst interface{}) bool {
	ct := r.Header.Get("Content-Type")
	if i := strings.IndexByte(ct, ';'); i >= 0 {
		ct = ct[:i]
	}
	if strings.TrimSpace(ct) != "application/json" {
		writeError(w, http.StatusUnsupportedMediaType, "content-type must be application/json")
		return false
	}
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return false
	}
	if dec.More() {
		writeError(w, http.StatusBadRequest, "request body must contain a single JSON object")
		return false
	}
	_, _ = io.Copy(io.Discard, r.Body)
	return true
}

// ifMatch parses the If-Match header. ok is false when the header is absent.
func ifMatch(r *http.Request) (val int, ok bool) {
	raw := r.Header.Get("If-Match")
	if raw == "" {
		return 0, false
	}
	raw = strings.Trim(raw, "\"")
	v, err := strconv.Atoi(raw)
	if err != nil {
		return 0, false
	}
	return v, true
}
GO_EOF

cat > "$SRC/handlers_groups.go" << 'GO_EOF'
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
	setETag(w, g.Version)
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
	im, ok := ifMatch(r)
	if !ok {
		writeError(w, http.StatusPreconditionRequired, "If-Match header is required")
		return
	}
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
GO_EOF

echo "All approval-routing bugs fixed."
