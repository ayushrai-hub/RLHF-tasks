package drive

import (
	"fmt"
	"os"

	"localauthz/internal/audit"
	"localauthz/internal/directory"
	"localauthz/internal/gate"
	"localauthz/internal/ledger"
	"localauthz/internal/manifest"
	"localauthz/internal/model"
	"localauthz/internal/report"
	"localauthz/internal/ring"
)

type Runner struct {
	casePath       string
	statePath      string
	resume         bool
	stopAfterStep  int
	book           *directory.Book
	casePayload    []byte
	caseDigest     string
	active         *model.DirectorySnapshot
	store          *ledger.Store
	idx            *ring.MembershipIndex
	catalog        gate.Catalog
	refreshes      []model.RefreshRecord
	decisions      []model.DecisionRecord
	auditCollector *audit.Collector
	startStep          int
	refreshEpoch       int
	resumeFromStep     int
	epochAtResumeStart int
}

func NewRunner(casePath string, statePath string, resume bool, stopAfterStep int) (*Runner, error) {
	book, payload, err := directory.LoadScenario(casePath)
	if err != nil {
		return nil, err
	}
	digest := report.CaseDigest(payload)
	r := &Runner{
		casePath:       casePath,
		statePath:      statePath,
		resume:         resume,
		stopAfterStep:  stopAfterStep,
		book:           book,
		casePayload:    payload,
		caseDigest:     digest,
		store:          ledger.NewStore(),
		idx:            ring.NewMembershipIndex(),
		catalog:        gate.BuildCatalog(book.Scenario.Resources),
		auditCollector: audit.NewCollector(),
		startStep:      0,
	}
	if resume {
		if err := r.loadResumeState(digest); err != nil {
			return nil, err
		}
	}
	return r, nil
}

func (r *Runner) loadResumeState(digest string) error {
	m, ok, err := manifest.Load(r.statePath)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("resume requested but no run manifest in %s", r.statePath)
	}
	if m.CaseDigest != digest {
		return fmt.Errorf("run manifest case digest mismatch")
	}
	store, err := ledger.LoadStore(r.statePath)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("resume requested but cache state is missing")
		}
		return err
	}
	rows, err := ring.LoadRows(r.statePath)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("resume requested but group index is missing")
		}
		return err
	}
	r.store = store
	r.idx = ring.IndexFromRows(rows)
	r.startStep = m.CompletedStep
	r.refreshEpoch = m.RefreshEpoch
	r.resumeFromStep = m.CompletedStep
	r.epochAtResumeStart = m.RefreshEpoch
	_ = m.LastAccepted
	if m.HeadRevision != 0 {
		if snap, found := r.book.Snapshot(m.HeadRevision); found {
			active := snap
			r.active = &active
		}
	}
	return nil
}

func (r *Runner) Run() (model.Trace, error) {
	for stepNo, step := range r.book.Scenario.Steps {
		pos := stepNo + 1
		if pos <= r.startStep {
			continue
		}
		switch step.Op {
		case "publish":
			if err := r.publish(pos, step); err != nil {
				return model.Trace{}, err
			}
		case "refresh":
			if err := r.refresh(pos, step); err != nil {
				return model.Trace{}, err
			}
		case "authorize":
			if err := r.authorize(pos, step); err != nil {
				return model.Trace{}, err
			}
		default:
			return model.Trace{}, fmt.Errorf("step %d: unknown op %q", pos, step.Op)
		}
		if err := r.persistManifest(pos); err != nil {
			return model.Trace{}, err
		}
		if r.stopAfterStep > 0 && pos >= r.stopAfterStep {
			break
		}
	}
	trace := model.Trace{
		Case:           r.book.Scenario.Name,
		SchemaVersion:  1,
		FreshnessBound: r.book.Scenario.FreshnessBound,
		Refreshes:      r.refreshes,
		Decisions:      r.decisions,
		CacheEntries:   r.store.Entries(),
		GroupIndex:     r.idx.Rows(),
		Audit:          r.auditCollector.Events(),
		Provenance: model.Provenance{
			GeneratedBy: "authzctl",
			CaseDigest:  r.caseDigest,
			OutputPath:  "",
			Resume: model.ResumeState{
				Used:       r.resume,
				FromStep:   r.resumeFromStep,
				EpochStart: r.refreshEpoch,
			},
		},
	}
	return trace, nil
}

func (r *Runner) persistManifest(completedStep int) error {
	head := 0
	if r.active != nil {
		head = r.active.Revision
	}
	lastAccepted := false
	if len(r.refreshes) > 0 {
		lastAccepted = r.refreshes[len(r.refreshes)-1].Accepted
	}
	return manifest.Save(r.statePath, manifest.RunManifest{
		CaseDigest:    r.caseDigest,
		CompletedStep: completedStep,
		HeadRevision:  head,
		RefreshEpoch:  r.refreshEpoch,
		LastAccepted:  lastAccepted,
	})
}
