package drive

import (
	"fmt"

	"localauthz/internal/directory"
	"localauthz/internal/gate"
	"localauthz/internal/model"
)

func (r *Runner) authorize(stepNo int, step model.Step) error {
	if r.active == nil {
		return fmt.Errorf("step %d: authorize before publish", stepNo)
	}
	evaluator := gate.Evaluator{Catalog: r.catalog, Store: r.store, Index: r.idx, Bound: r.book.Scenario.FreshnessBound}
	principal, hasPrincipal := directory.PrincipalByName(*r.active, step.Username)
	decision, err := evaluator.Authorize(gate.Request{
		Step:            stepNo,
		Tick:            step.Tick,
		Username:        step.Username,
		Resource:        step.Resource,
		Action:          step.Action,
		ActiveRevision:  r.active.Revision,
		RefreshEpoch:    r.refreshEpoch,
		ActivePrincipal: principal,
		HasPrincipal:    hasPrincipal,
	})
	if err != nil {
		return err
	}
	r.decisions = append(r.decisions, decision)
	r.auditCollector.Add(stepNo, step.Tick, "authorize", r.active.Revision, decision.Username+":"+decision.Result+":"+decision.Reason)
	return nil
}
