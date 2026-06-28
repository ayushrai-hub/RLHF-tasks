package phaseconv

import (
	"nfrd.local/nfrd/ledger"
	"nfrd.local/nfrd/model"
	"nfrd.local/nfrd/windowfuse"
)

func RunPhase(profile model.ProfileSpec, runID, phaseName string, epochVal int) model.ViewState {
	ctx := model.Context{Profile: profile.Name, Epoch: epochVal, Phase: phaseName, RunID: runID}
	records := ledger.Load(ledger.BatchPath(profile.Name))
	segments := ledger.SelectSegments(records, ctx)
	state := model.ViewState{Phase: phaseName, RunID: runID}
	state = ReconcilePhase(state, segments)
	_ = windowfuse.LoadEpoch(profile.Name)
	return state
}
