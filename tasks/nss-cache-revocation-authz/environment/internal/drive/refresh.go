package drive

import (
	"fmt"
	"os"
	"path/filepath"

	"localauthz/internal/directory"
	"localauthz/internal/journal"
	"localauthz/internal/ledger"
	"localauthz/internal/model"
	"localauthz/internal/ring"
)

func (r *Runner) publish(stepNo int, step model.Step) error {
	snap, ok := r.book.Snapshot(step.Revision)
	if !ok {
		return fmt.Errorf("step %d: unknown revision %d", stepNo, step.Revision)
	}
	r.active = &snap
	r.auditCollector.Add(stepNo, step.Tick, "publish", snap.Revision, "active directory revision selected")
	return nil
}

func (r *Runner) refresh(stepNo int, step model.Step) error {
	if r.active == nil {
		return fmt.Errorf("step %d: refresh before publish", stepNo)
	}
	ok, reason, proofAge := directory.AgeOnlyStatus(r.active.Proof, step.Tick, r.book.Scenario.FreshnessBound)
	rec := model.RefreshRecord{
		Step:          stepNo,
		Tick:          step.Tick,
		Revision:      r.active.Revision,
		ProofRevision: r.active.Proof.Revision,
		ProofAge:      proofAge,
		Accepted:      ok,
		Reason:        reason,
	}
	r.refreshes = append(r.refreshes, rec)
	_ = journal.Append(r.statePath, journal.RefreshEvent{
		Step:          stepNo,
		Tick:          step.Tick,
		Revision:      r.active.Revision,
		ProofRevision: r.active.Proof.Revision,
		Accepted:      ok,
		Reason:        reason,
	})
	if !ok {
		r.auditCollector.Add(stepNo, step.Tick, "refresh", r.active.Revision, reason)
		return nil
	}
	stampEpoch := r.refreshEpoch
	seen := map[string]bool{}
	for _, principal := range r.active.Principals {
		seen[principal.Username] = true
		if principal.Active {
			r.store.Upsert(ledger.NewEntry(principal, r.active.Revision, r.active.Proof, step.Tick, r.book.Scenario.FreshnessBound, proofAge, stampEpoch))
		} else {
			r.store.Upsert(ledger.RevokedEntry(principal, r.active.Revision, r.active.Proof, step.Tick, r.book.Scenario.FreshnessBound, proofAge, stampEpoch))
		}
		r.idx.ApplyPrincipal(principal)
	}
	r.store.MarkMissingAsRevoked(seen, r.active.Revision, r.active.Proof, step.Tick, r.book.Scenario.FreshnessBound, proofAge, stampEpoch)
	if err := os.MkdirAll(r.statePath, 0o755); err != nil {
		return err
	}
	if err := ledger.SaveEntries(r.statePath, r.store.Entries()); err != nil {
		return err
	}
	if err := ring.SaveRows(r.statePath, r.idx.Rows()); err != nil {
		return err
	}
	r.refreshEpoch++
	r.auditCollector.Add(stepNo, step.Tick, "refresh", r.active.Revision, "local cache and group index refreshed")
	_ = filepath.Clean(r.statePath)
	return nil
}
