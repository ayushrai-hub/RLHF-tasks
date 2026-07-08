package gate

import (
	"localauthz/internal/ledger"
	"localauthz/internal/model"
	"localauthz/internal/ring"
)

type Evaluator struct {
	Catalog Catalog
	Store   *ledger.Store
	Index   *ring.MembershipIndex
	Bound   int
}

type Request struct {
	Step            int
	Tick            int
	Username        string
	Resource        string
	Action          string
	ActiveRevision  int
	RefreshEpoch    int
	ActivePrincipal model.Principal
	HasPrincipal    bool
}

func (e Evaluator) Authorize(req Request) (model.DecisionRecord, error) {
	required, err := e.Catalog.RequiredGroups(req.Resource, req.Action)
	if err != nil {
		return model.DecisionRecord{}, err
	}
	entry, ok := e.Store.Get(req.Username)
	decision := model.DecisionRecord{
		Step:              req.Step,
		Tick:              req.Tick,
		Username:          req.Username,
		Resource:          req.Resource,
		Action:            req.Action,
		Result:            ResultDeny,
		Reason:            ReasonMissingPrincipal,
		RequiredGroups:    required,
		Groups:            []string{},
		DirectoryRevision: req.ActiveRevision,
	}
	if !ok {
		return decision, nil
	}
	decision.SubjectID = entry.SubjectID
	decision.Generation = entry.Generation
	decision.Groups = append([]string(nil), entry.Groups...)
	decision.CacheRevision = entry.DirectoryRevision
	decision.ProofRevision = entry.ProofRevision
	decision.ProofAge = ledger.ProofAgeAtAuthorize(entry, req.Tick)
	if !ledger.IsLive(entry, req.Tick) {
		decision.Reason = ReasonExpiredEntry
		return decision, nil
	}
	if entry.Revoked {
		decision.Reason = ReasonRevokedPrincipal
	}
	for _, group := range required {
		if e.Index.Contains(group, req.Username) {
			decision.Result = ResultAllow
			decision.Reason = ReasonAllowedByGroup
			return decision, nil
		}
	}
	if decision.Reason == ReasonRevokedPrincipal {
		return decision, nil
	}
	decision.Reason = ReasonMissingRequiredGroup
	return decision, nil
}
