package main

import (
	"fmt"
	"sort"
	"sync"
)

// Service holds all change requests and approver groups in memory.
type Service struct {
	mu      sync.RWMutex
	crs     map[string]*ChangeRequest
	groups  map[string]*ApproverGroup
	cache   map[string]*CRView
	nextID  int
	nextGID int
	nextSeq int

	crsCreated     int
	groupsCreated  int
	approvalsTotal int
	revokesTotal   int
}

func NewService() *Service {
	return &Service{
		crs:    make(map[string]*ChangeRequest),
		groups: make(map[string]*ApproverGroup),
		cache:  make(map[string]*CRView),
	}
}

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

func (s *Service) evaluate(cr *ChangeRequest) Derived {
	for i, st := range cr.Stages {
		eff := s.effEligible(st)
		approvers := make(map[string]bool)
		for _, a := range cr.Approvals {
			if a.Revoked || a.StageIndex != i {
				continue
			}
			if !eff[a.Approver] {
				continue
			}
			if a.Decision == "approve" {
				approvers[a.Approver] = true
			}
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

func (s *Service) buildView(cr *ChangeRequest) *CRView {
	active := make([]*Approval, 0)
	for _, a := range cr.Approvals {
		if a.Revoked {
			continue
		}
		active = append(active, a)
	}
	sort.Slice(active, func(i, j int) bool { return active[i].Seq < active[j].Seq })

	v := &CRView{
		ID:        cr.ID,
		Title:     cr.Title,
		Author:    cr.Author,
		Stages:    cr.Stages,
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

func (s *Service) validateStages(stages []Stage) error {
	if len(stages) < 1 {
		return ErrValidation
	}
	for _, st := range stages {
		if st.Name == "" {
			return ErrValidation
		}
		if st.Required < 0 {
			return ErrValidation
		}
		eff := s.effEligible(st)
		if len(eff) == 0 {
			return ErrValidation
		}
	}
	return nil
}

func (s *Service) validateCreate(req CreateRequest) error {
	if req.Title == "" {
		return ErrValidation
	}
	return s.validateStages(req.Stages)
}

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
	s.mu.RLock()
	defer s.mu.RUnlock()
	if v, ok := s.cache[id]; ok {
		return v, nil
	}
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	v := s.buildView(cr)
	s.cache[id] = v
	return v, nil
}

func (s *Service) List(status, sortKey string) []*CRView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*CRView, 0)
	for _, cr := range s.crs {
		out = append(out, s.buildView(cr))
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
	cr.Version++
	if v, ok := s.cache[id]; ok {
		v.Title = cr.Title
		v.Stages = cr.Stages
		v.Version = cr.Version
	}
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
	s.mu.Lock()
	defer s.mu.Unlock()
	cr, ok := s.crs[id]
	if !ok {
		return nil, ErrNotFound
	}
	d := s.evaluate(cr)
	cur := d.CurrentStage
	s.nextSeq++
	cr.Approvals = append(cr.Approvals, &Approval{
		Approver:   req.Approver,
		StageIndex: cur,
		Decision:   req.Decision,
		Seq:        s.nextSeq,
	})
	s.approvalsTotal++
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
		out = append(out, a)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Seq < out[j].Seq })
	return out, nil
}

func (s *Service) Approver(id string) *ApproverView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v := &ApproverView{
		Approver:        id,
		PendingRequests: make([]string, 0),
	}
	for _, cr := range s.crs {
		for _, a := range cr.Approvals {
			if a.Approver == id && a.Decision == "approve" {
				v.ActiveApprovals++
				v.ApprovalsGiven++
			}
		}
		if len(cr.Stages) > 0 && contains(cr.Stages[0].Eligible, id) {
			v.PendingRequests = append(v.PendingRequests, cr.ID)
		}
	}
	sort.Strings(v.PendingRequests)
	return v
}

func (s *Service) Stats() StatsView {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return StatsView{
		CRsCreated:        len(s.crs),
		CRsActive:         len(s.crs),
		ApprovalsRecorded: s.approvalsTotal,
		RevokesProcessed:  s.revokesTotal,
		GroupsCreated:     len(s.groups),
	}
}

func (s *Service) groupView(g *ApproverGroup) *GroupView {
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
		Members:             g.Members,
		MemberCount:         len(g.Members),
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
	return s.groupView(g), nil
}

func (s *Service) DeleteGroup(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.groups[id]; !ok {
		return ErrNotFound
	}
	delete(s.groups, id)
	return nil
}
