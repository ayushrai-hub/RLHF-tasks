#!/bin/bash
set -euo pipefail
cd /app/environment

has_profile_field=0
while IFS= read -r line; do
  case "$line" in
    *'json:"profile,omitempty"'*) has_profile_field=1 ;;
  esac
done < model/types.go
tmp_model="$(mktemp)"
in_epoch_meta=0
while IFS= read -r line; do
  case "$line" in
    'type EpochMeta struct {')
      in_epoch_meta=1
      printf '%s\n' "$line" >> "$tmp_model"
      continue
      ;;
  esac
  if [ "$in_epoch_meta" -eq 1 ]; then
    case "$line" in
      *'Epoch   int'*)
        printf '\tEpoch   int    `json:"epoch"`\n' >> "$tmp_model"
        continue
        ;;
      *'Counter int'*)
        printf '\tCounter int    `json:"counter"`\n' >> "$tmp_model"
        continue
        ;;
      *'Tag     string'*)
        printf '\tTag     string `json:"tag"`\n' >> "$tmp_model"
        continue
        ;;
      '}')
        in_epoch_meta=0
        ;;
    esac
  fi
  printf '%s\n' "$line" >> "$tmp_model"
  if [ "$has_profile_field" -eq 0 ]; then
    case "$line" in
      *'Source   string  `json:"source,omitempty"`'*)
        printf '\tProfile  string  `json:"profile,omitempty"`\n' >> "$tmp_model"
        ;;
    esac
  fi
done < model/types.go
mv "$tmp_model" model/types.go

cat > ledger/writer.go <<'EOF'
package ledger

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strconv"

	"nfrd.local/nfrd/model"
)

func AppendBatch(path string, rows []model.Record) {
	prior := loadOne(path)
	merged := append(prior, rows...)
	sort.Slice(merged, func(i, j int) bool {
		if merged[i].Seq == merged[j].Seq {
			return merged[i].RuleID < merged[j].RuleID
		}
		return merged[i].Seq < merged[j].Seq
	})
	model.WriteJSON(path, merged)
}

func BatchPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.json")
}

func ReplayPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.replay.json")
}

func ShadowPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.shadow.json")
}

func SpillPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.spill.json")
}

func Load(path string) []model.Record {
	return loadOne(path)
}

func LoadJournal(profile string) []model.Record {
	paths := []string{BatchPath(profile), ReplayPath(profile), ShadowPath(profile), SpillPath(profile)}
	type ranked struct {
		epoch int
		index int
		row   model.Record
	}
	chosen := map[string]ranked{}
	sourceIndex := 0
	for _, path := range paths {
		for _, rec := range loadOne(path) {
			if rec.Profile != "" && rec.Profile != profile {
				sourceIndex++
				continue
			}
			key := journalKey(rec)
			next := ranked{epoch: rec.Epoch, index: sourceIndex, row: rec}
			if prev, ok := chosen[key]; !ok || next.epoch > prev.epoch || (next.epoch == prev.epoch && next.index >= prev.index) {
				chosen[key] = next
			}
			sourceIndex++
		}
	}
	var out []model.Record
	for _, item := range chosen {
		out = append(out, item.row)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Seq == out[j].Seq {
			if out[i].RunID == out[j].RunID {
				if out[i].Phase == out[j].Phase {
					return out[i].RuleID < out[j].RuleID
				}
				return out[i].Phase < out[j].Phase
			}
			return out[i].RunID < out[j].RunID
		}
		return out[i].Seq < out[j].Seq
	})
	return out
}

func loadOne(path string) []model.Record {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var rows []model.Record
	if err := json.Unmarshal(data, &rows); err != nil {
		return nil
	}
	return rows
}

func journalKey(rec model.Record) string {
	return rec.RunID + "\x00" + rec.Phase + "\x00" + rec.RuleID + "\x00" + rec.Action + "\x00" + strconv.Itoa(rec.Seq)
}
EOF

cat > ledger/segment.go <<'EOF'
package ledger

import (
	"sort"

	"nfrd.local/nfrd/model"
)

func SelectSegments(records []model.Record, ctx model.Context) []model.Record {
	var out []model.Record
	for _, rec := range records {
		if rec.RunID != ctx.RunID || rec.Phase != ctx.Phase {
			continue
		}
		out = append(out, rec)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Seq == out[j].Seq {
			return out[i].RuleID < out[j].RuleID
		}
		return out[i].Seq < out[j].Seq
	})
	return out
}
EOF

cat > phaseconv/settle.go <<'EOF'
package phaseconv

import (
	"sort"

	"nfrd.local/nfrd/model"
)

func ReconcilePhase(state model.ViewState, records []model.Record) model.ViewState {
	rules := map[string]model.RuleView{}
	for _, rec := range records {
		rules[rec.RuleID] = model.RuleView{
			RuleID:   rec.RuleID,
			Priority: rec.Priority,
			Epoch:    rec.Epoch,
			Mark:     rec.Mark,
		}
	}
	var order []string
	for id := range rules {
		order = append(order, id)
	}
	sort.Strings(order)
	var out []model.RuleView
	for _, id := range order {
		out = append(out, rules[id])
	}
	state.Rules = out
	return state
}
EOF

cat > phaseconv/runner.go <<'EOF'
package phaseconv

import (
	"nfrd.local/nfrd/ledger"
	"nfrd.local/nfrd/model"
)

func RunPhase(profile model.ProfileSpec, runID, phaseName string, epochVal int) model.ViewState {
	ctx := model.Context{Profile: profile.Name, Epoch: epochVal, Phase: phaseName, RunID: runID}
	records := ledger.LoadJournal(profile.Name)
	segments := ledger.SelectSegments(records, ctx)
	state := model.ViewState{Phase: phaseName, RunID: runID}
	return ReconcilePhase(state, segments)
}
EOF

cat > windowfuse/merge.go <<'EOF'
package windowfuse

import "nfrd.local/nfrd/model"

func CombineEpoch(base, incoming model.EpochMeta) model.EpochMeta {
	out := base
	if incoming.Epoch > out.Epoch {
		out.Epoch = incoming.Epoch
	}
	if incoming.Counter > out.Counter {
		out.Counter = incoming.Counter
	}
	if incoming.Tag != "" {
		out.Tag = incoming.Tag
	}
	return out
}
EOF

cat > emit/builder.go <<'EOF'
package emit

import (
	"path/filepath"
	"sort"

	"nfrd.local/nfrd/ledger"
	"nfrd.local/nfrd/model"
	"nfrd.local/nfrd/phaseconv"
	"nfrd.local/nfrd/windowfuse"
)

func BuildReport(profile model.ProfileSpec) model.Report {
	rows := ledger.LoadJournal(profile.Name)
	auth := windowfuse.Authority(profile.Name)
	for _, row := range rows {
		if row.Epoch > auth.Epoch {
			auth.Epoch = row.Epoch
		}
	}
	if len(rows) > auth.Counter {
		auth.Counter = len(rows)
	}
	var runs []model.RunRecord
	var entries []model.EntryRecord
	var checkpoints []model.CheckpointRecord
	for _, runID := range profile.Runs {
		for _, phaseName := range []string{"apply", "settle"} {
			ctx := model.Context{Profile: profile.Name, Epoch: auth.Epoch, Phase: phaseName, RunID: runID}
			segments := ledger.SelectSegments(rows, ctx)
			state := model.ViewState{Phase: phaseName, RunID: runID}
			state = phaseconv.ReconcilePhase(state, segments)
			hash := model.TreeHash(state.Rules)
			runs = append(runs, model.RunRecord{RunID: runID, Phase: phaseName, TreeHash: hash})
			checkpoints = append(checkpoints, spanRecord(runID, phaseName, hash, segments))
			for _, rule := range state.Rules {
				entries = append(entries, model.EntryRecord{
					RuleID:       rule.RuleID,
					Action:       phaseName,
					Epoch:        rule.Epoch,
					ObservedHash: model.ObservedHash(rule),
				})
			}
		}
	}
	sort.Slice(runs, func(i, j int) bool {
		if runs[i].RunID == runs[j].RunID {
			return runs[i].Phase < runs[j].Phase
		}
		return runs[i].RunID < runs[j].RunID
	})
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].RuleID == entries[j].RuleID {
			if entries[i].Epoch == entries[j].Epoch {
				return entries[i].Action < entries[j].Action
			}
			return entries[i].Epoch < entries[j].Epoch
		}
		return entries[i].RuleID < entries[j].RuleID
	})
	sort.Slice(checkpoints, func(i, j int) bool {
		if checkpoints[i].RunID == checkpoints[j].RunID {
			return checkpoints[i].Phase < checkpoints[j].Phase
		}
		return checkpoints[i].RunID < checkpoints[j].RunID
	})
	return model.Report{
		Profile:     profile.Name,
		Epoch:       auth.Epoch,
		Counter:     auth.Counter,
		Runs:        runs,
		Entries:     entries,
		Checkpoints: checkpoints,
	}
}

func spanRecord(runID, phaseName, hash string, rows []model.Record) model.CheckpointRecord {
	point := model.CheckpointRecord{
		RunID:       runID,
		Phase:       phaseName,
		RecordCount: len(rows),
		TreeHash:    hash,
	}
	for i, row := range rows {
		if i == 0 || row.Seq < point.FirstSeq {
			point.FirstSeq = row.Seq
		}
		if i == 0 || row.Seq > point.LastSeq {
			point.LastSeq = row.Seq
		}
		if i == 0 || row.Epoch < point.EpochFloor {
			point.EpochFloor = row.Epoch
		}
		if i == 0 || row.Epoch > point.EpochCeil {
			point.EpochCeil = row.Epoch
		}
	}
	return point
}

func WriteReport(profile string, report model.Report) {
	path := filepath.Join(model.OutDir, "audit_report.json")
	auth := windowfuse.Authority(profile)
	windowfuse.SaveEpoch(profile, model.EpochMeta{Epoch: report.Epoch, Counter: report.Counter, Tag: auth.Tag})
	model.WriteJSON(path, report)
}
EOF

gofmt -w model/types.go ledger/writer.go ledger/segment.go phaseconv/settle.go phaseconv/runner.go windowfuse/merge.go emit/builder.go
go build -o /app/bin/nfrd ./cmd/nfrd
for profile in gate depot yard; do
  rm -rf "/app/output/state/${profile}" "/app/output/audit_report.json"
  /app/bin/nfrd audit --profile "$profile"
done
