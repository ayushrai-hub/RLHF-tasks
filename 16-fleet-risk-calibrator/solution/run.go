package app

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"example.com/fleetrisk/internal/config"
	"example.com/fleetrisk/internal/csvutil"
	"example.com/fleetrisk/internal/domain"
	"example.com/fleetrisk/internal/features"
	"example.com/fleetrisk/internal/model"
	"example.com/fleetrisk/internal/report"
)

type Options struct {
	ModelPath    string
	PolicyPath   string
	CallsPath    string
	WindowsPath  string
	HistoryPath  string
	LabelsPath   string
	CapacityPath string
	OutDir       string
}

func Run(opts Options) error {
	modelConfig, err := config.LoadModel(opts.ModelPath)
	if err != nil {
		return err
	}
	policy, err := config.LoadPolicy(opts.PolicyPath)
	if err != nil {
		return err
	}
	calls, err := csvutil.LoadServiceCalls(opts.CallsPath)
	if err != nil {
		return err
	}
	windows, err := csvutil.LoadSensorWindows(opts.WindowsPath)
	if err != nil {
		return err
	}
	history, err := csvutil.LoadHistory(opts.HistoryPath)
	if err != nil {
		return err
	}
	labels, err := csvutil.LoadLabels(opts.LabelsPath)
	if err != nil {
		return err
	}
	capacity, err := csvutil.LoadCapacity(opts.CapacityPath)
	if err != nil {
		return err
	}

	scored := make([]domain.ScoredCall, 0, len(calls))
	for _, call := range calls {
		window, ok := latestWindow(call, windows)
		if !ok {
			return fmt.Errorf("no sensor window for request %s asset %s", call.RequestID, call.AssetID)
		}
		values, err := features.Extract(call, window, windows, history, modelConfig)
		if err != nil {
			return fmt.Errorf("features for %s: %w", call.RequestID, err)
		}
		score, err := model.Apply(values, modelConfig, call.AssetType)
		if err != nil {
			return fmt.Errorf("score %s: %w", call.RequestID, err)
		}
		scored = append(scored, domain.ScoredCall{
			Call:           call,
			RawScore:       score.RawScore,
			CalibratedRisk: score.CalibratedRisk,
			DowntimeRisk:   score.DowntimeRisk,
			RiskBand:       chooseBand(score.CalibratedRisk, policy),
			Action:         "monitor",
			TopFactor:      score.TopFactor,
			DueWithinHours: policy.DueHours.Monitor,
			DecisionValue:  0,
		})
	}
	schedule, parts, err := optimizeActions(scored, policy, capacity)
	if err != nil {
		return err
	}

	if err := os.MkdirAll(opts.OutDir, 0o755); err != nil {
		return err
	}
	if err := report.WriteScored(filepath.Join(opts.OutDir, "scored_calls.csv"), scored); err != nil {
		return err
	}

	decisions := append([]domain.ScoredCall(nil), scored...)
	sort.Slice(decisions, func(i, j int) bool {
		if decisions[i].CalibratedRisk == decisions[j].CalibratedRisk {
			return decisions[i].Call.RequestID < decisions[j].Call.RequestID
		}
		return decisions[i].CalibratedRisk > decisions[j].CalibratedRisk
	})
	if err := report.WriteDecisions(filepath.Join(opts.OutDir, "maintenance_decisions.csv"), decisions); err != nil {
		return err
	}
	if err := report.WriteSchedule(filepath.Join(opts.OutDir, "crew_schedule.csv"), schedule); err != nil {
		return err
	}
	if err := report.WriteParts(filepath.Join(opts.OutDir, "parts_allocation.csv"), parts); err != nil {
		return err
	}
	manifest, err := buildManifest(opts, modelConfig, policy, len(scored))
	if err != nil {
		return err
	}
	if err := report.WriteJSON(filepath.Join(opts.OutDir, "risk_manifest.json"), manifest); err != nil {
		return err
	}
	evaluation := buildEvaluation(scored, labels)
	if err := report.WriteJSON(filepath.Join(opts.OutDir, "evaluation.json"), evaluation); err != nil {
		return err
	}
	return nil
}

func latestWindow(call domain.ServiceCall, windows []domain.SensorWindow) (domain.SensorWindow, bool) {
	var best domain.SensorWindow
	found := false
	for _, window := range windows {
		if window.AssetID != call.AssetID {
			continue
		}
		if window.WindowEnd.After(call.OpenedAt) {
			continue
		}
		if !found || window.WindowEnd.After(best.WindowEnd) {
			best = window
			found = true
		}
	}
	return best, found
}

func optimizeActions(scored []domain.ScoredCall, policy config.Policy, capacities map[string]domain.SiteCapacity) ([]domain.ScheduledAction, []domain.PartAllocation, error) {
	indexes := make([]int, len(scored))
	for idx, item := range scored {
		if _, ok := capacities[item.Call.Site]; !ok {
			return nil, nil, fmt.Errorf("missing capacity for site %s", item.Call.Site)
		}
		indexes[idx] = idx
	}
	sort.Slice(indexes, func(i, j int) bool {
		return scored[indexes[i]].Call.RequestID < scored[indexes[j]].Call.RequestID
	})
	plan, err := bestGlobalPlan(scored, indexes, policy, capacities)
	if err != nil {
		return nil, nil, err
	}
	for localIdx, action := range plan.actions {
		globalIdx := indexes[localIdx]
		scored[globalIdx].Action = action
		scored[globalIdx].DueWithinHours = dueHours(action, policy)
		scored[globalIdx].DecisionValue = actionUtility(scored[globalIdx], action, policy)
	}
	return plan.schedule, plan.parts, nil
}

type actionUsage struct {
	dispatch  int
	inspect   int
	crewHours float64
}

type globalPlan struct {
	actions       []string
	totalUtility  float64
	dispatchRisk  float64
	inspectRisk   float64
	crewHours     float64
	scheduleEnd   time.Time
	scheduleTravel float64
	partTransfer  float64
	schedule      []domain.ScheduledAction
	parts         []domain.PartAllocation
	planSignature string
}

func bestGlobalPlan(scored []domain.ScoredCall, indexes []int, policy config.Policy, capacities map[string]domain.SiteCapacity) (globalPlan, error) {
	actions := make([]string, len(indexes))
	best := globalPlan{actions: make([]string, len(indexes)), totalUtility: math.Inf(-1)}
	found := false
	siteUsage := make(map[string]*actionUsage)
	regionUsage := make(map[string]*actionUsage)

	var search func(pos int, totalUtility, dispatchRisk, inspectRisk, crewHours float64) error
	search = func(pos int, totalUtility, dispatchRisk, inspectRisk, crewHours float64) error {
		if pos == len(indexes) {
			baseCandidate := globalPlan{
				totalUtility: totalUtility,
				dispatchRisk: dispatchRisk,
				inspectRisk:  inspectRisk,
				crewHours:    crewHours,
			}
			if found && !baseCanStillWin(baseCandidate, best) {
				return nil
			}
			schedule, parts, scheduleEnd, scheduleTravel, partTransfer, ok, err := bestSchedule(scored, indexes, actions, policy)
			if err != nil {
				return err
			}
			if !ok {
				return nil
			}
			candidate := globalPlan{
				actions:        append([]string(nil), actions...),
				totalUtility:   totalUtility,
				dispatchRisk:   dispatchRisk,
				inspectRisk:    inspectRisk,
				crewHours:      crewHours,
				scheduleEnd:    scheduleEnd,
				scheduleTravel: scheduleTravel,
				partTransfer:  partTransfer,
				schedule:       schedule,
				parts:          parts,
				planSignature:  buildPlanSignature(scored, indexes, actions),
			}
			if !found || betterGlobalPlan(candidate, best) {
				best = candidate
				found = true
			}
			return nil
		}

		item := scored[indexes[pos]]
		site := item.Call.Site
		capacity := capacities[site]
		candidates := feasibleActions(item, policy)
		sort.Slice(candidates, func(i, j int) bool {
			left := actionUtility(item, candidates[i], policy)
			right := actionUtility(item, candidates[j], policy)
			if math.Abs(left-right) > 1e-12 {
				return left > right
			}
			return candidates[i] < candidates[j]
		})
		for _, action := range candidates {
			hours := actionCrewHours(item, action, policy)
			siteBucket := usageFor(siteUsage, site)
			if !fitsSite(siteBucket, action, capacity) {
				continue
			}

			var regionBucket *actionUsage
			if action != "monitor" {
				region, ok := policy.Optimizer.SiteRegion[site]
				if !ok || region == "" {
					return fmt.Errorf("missing region for site %s", site)
				}
				limit, ok := policy.Optimizer.RegionalLimits[region]
				if !ok {
					return fmt.Errorf("missing regional limit for region %s", region)
				}
				regionBucket = usageFor(regionUsage, region)
				if !fitsRegion(regionBucket, action, hours, limit) {
					continue
				}
			}

			actions[pos] = action
			changeUsage(siteBucket, action, hours, 1)
			if action != "monitor" {
				changeUsage(regionBucket, action, hours, 1)
			}

			nextDispatchRisk := dispatchRisk
			nextInspectRisk := inspectRisk
			if action == "dispatch" {
				nextDispatchRisk += item.CalibratedRisk
			}
			if action == "inspect" {
				nextInspectRisk += item.CalibratedRisk
			}
			err := search(
				pos+1,
				totalUtility+actionUtility(item, action, policy),
				nextDispatchRisk,
				nextInspectRisk,
				crewHours+hours,
			)

			changeUsage(siteBucket, action, hours, -1)
			if action != "monitor" {
				changeUsage(regionBucket, action, hours, -1)
			}
			if err != nil {
				return err
			}
		}
		return nil
	}
	if err := search(0, 0, 0, 0, 0); err != nil {
		return globalPlan{}, err
	}
	if !found {
		return globalPlan{}, fmt.Errorf("no feasible action plan")
	}
	return best, nil
}

func usageFor(usages map[string]*actionUsage, key string) *actionUsage {
	usage := usages[key]
	if usage == nil {
		usage = &actionUsage{}
		usages[key] = usage
	}
	return usage
}

func fitsSite(usage *actionUsage, action string, capacity domain.SiteCapacity) bool {
	dispatchUsed := usage.dispatch
	inspectUsed := usage.inspect
	switch action {
	case "dispatch":
		dispatchUsed++
	case "inspect":
		inspectUsed++
	}
	return dispatchUsed <= capacity.DispatchSlots && inspectUsed <= capacity.InspectSlots
}

func fitsRegion(usage *actionUsage, action string, hours float64, limit config.RegionalLimit) bool {
	const eps = 1e-12
	dispatchUsed := usage.dispatch
	inspectUsed := usage.inspect
	switch action {
	case "dispatch":
		dispatchUsed++
	case "inspect":
		inspectUsed++
	}
	if dispatchUsed > limit.DispatchSlots || inspectUsed > limit.InspectSlots {
		return false
	}
	return usage.crewHours+hours <= limit.CrewHours+eps
}

func changeUsage(usage *actionUsage, action string, hours float64, delta int) {
	switch action {
	case "dispatch":
		usage.dispatch += delta
	case "inspect":
		usage.inspect += delta
	}
	usage.crewHours += float64(delta) * hours
}

func actionCrewHours(item domain.ScoredCall, action string, policy config.Policy) float64 {
	if action == "monitor" {
		return 0
	}
	if byAction, ok := policy.Optimizer.ActionHours[action]; ok {
		return byAction[item.Call.AssetType]
	}
	return 0
}

func buildPlanSignature(scored []domain.ScoredCall, indexes []int, actions []string) string {
	signature := make([]string, 0, len(indexes))
	for i, action := range actions {
		item := scored[indexes[i]]
		signature = append(signature, item.Call.RequestID+"="+action)
	}
	return strings.Join(signature, "|")
}

func baseCanStillWin(candidate, incumbent globalPlan) bool {
	const eps = 1e-12
	if candidate.totalUtility > incumbent.totalUtility+eps {
		return true
	}
	if math.Abs(candidate.totalUtility-incumbent.totalUtility) > eps {
		return false
	}
	if candidate.dispatchRisk > incumbent.dispatchRisk+eps {
		return true
	}
	if math.Abs(candidate.dispatchRisk-incumbent.dispatchRisk) > eps {
		return false
	}
	if candidate.inspectRisk > incumbent.inspectRisk+eps {
		return true
	}
	if math.Abs(candidate.inspectRisk-incumbent.inspectRisk) > eps {
		return false
	}
	if candidate.crewHours < incumbent.crewHours-eps {
		return true
	}
	if math.Abs(candidate.crewHours-incumbent.crewHours) > eps {
		return false
	}
	return true
}

func betterGlobalPlan(candidate, incumbent globalPlan) bool {
	const eps = 1e-12
	if candidate.totalUtility > incumbent.totalUtility+eps {
		return true
	}
	if math.Abs(candidate.totalUtility-incumbent.totalUtility) > eps {
		return false
	}
	if candidate.dispatchRisk > incumbent.dispatchRisk+eps {
		return true
	}
	if math.Abs(candidate.dispatchRisk-incumbent.dispatchRisk) > eps {
		return false
	}
	if candidate.inspectRisk > incumbent.inspectRisk+eps {
		return true
	}
	if math.Abs(candidate.inspectRisk-incumbent.inspectRisk) > eps {
		return false
	}
	if candidate.crewHours < incumbent.crewHours-eps {
		return true
	}
	if math.Abs(candidate.crewHours-incumbent.crewHours) > eps {
		return false
	}
	if candidate.scheduleEnd.Before(incumbent.scheduleEnd) {
		return true
	}
	if !candidate.scheduleEnd.Equal(incumbent.scheduleEnd) {
		return false
	}
	if candidate.scheduleTravel < incumbent.scheduleTravel-eps {
		return true
	}
	if math.Abs(candidate.scheduleTravel-incumbent.scheduleTravel) > eps {
		return false
	}
	if candidate.partTransfer < incumbent.partTransfer-eps {
		return true
	}
	if math.Abs(candidate.partTransfer-incumbent.partTransfer) > eps {
		return false
	}
	return candidate.planSignature < incumbent.planSignature
}

func feasibleActions(item domain.ScoredCall, policy config.Policy) []string {
	actions := []string{"monitor"}
	if item.CalibratedRisk >= policy.Optimizer.MinimumRisk["inspect"] || (item.Call.Priority == "urgent" && item.CalibratedRisk >= policy.Thresholds.UrgentInspectFloor) {
		actions = append(actions, "inspect")
	}
	if item.CalibratedRisk >= policy.Optimizer.MinimumRisk["dispatch"] {
		actions = append(actions, "dispatch")
	}
	return actions
}

func actionUtility(item domain.ScoredCall, action string, policy config.Policy) float64 {
	if action == "monitor" {
		return 0
	}
	bonus := 0.0
	if byAction, ok := policy.Optimizer.PriorityBonus[item.Call.Priority]; ok {
		bonus = byAction[action]
	}
	return item.CalibratedRisk*policy.Optimizer.RiskEffect[action] +
		item.DowntimeRisk*policy.Optimizer.DowntimeEffect[action] +
		bonus -
		policy.Optimizer.ActionCost[action]
}

type scheduleTask struct {
	item     domain.ScoredCall
	action   string
	region   string
	hours    float64
	duration time.Duration
	dueBy    time.Time
}

type crewState struct {
	crew               config.Crew
	shiftStart         time.Time
	shiftEnd           time.Time
	available          time.Time
	site               string
	maxContinuousHours float64
	continuousHours    float64
}

type schedulePlan struct {
	rows      []domain.ScheduledAction
	parts     []domain.PartAllocation
	maxEnd    time.Time
	travel    float64
	transfer  float64
	signature string
	partSig   string
}

type partOption struct {
	allocations []domain.PartAllocation
	readyAt     time.Time
	transfer    float64
	signature   string
}

func bestSchedule(scored []domain.ScoredCall, indexes []int, actions []string, policy config.Policy) ([]domain.ScheduledAction, []domain.PartAllocation, time.Time, float64, float64, bool, error) {
	reportAt, err := time.Parse(time.RFC3339, policy.ReportGeneratedAt)
	if err != nil {
		return nil, nil, time.Time{}, 0, 0, false, fmt.Errorf("parse report_generated_at: %w", err)
	}
	tasks := make([]scheduleTask, 0)
	for i, action := range actions {
		if action == "monitor" {
			continue
		}
		item := scored[indexes[i]]
		region := policy.Optimizer.SiteRegion[item.Call.Site]
		if region == "" {
			return nil, nil, time.Time{}, 0, 0, false, fmt.Errorf("missing region for site %s", item.Call.Site)
		}
		hours := actionCrewHours(item, action, policy)
		tasks = append(tasks, scheduleTask{
			item:     item,
			action:   action,
			region:   region,
			hours:    hours,
			duration: hoursDuration(hours),
			dueBy:    reportAt.Add(time.Duration(dueHours(action, policy)) * time.Hour),
		})
	}
	if len(tasks) == 0 {
		return []domain.ScheduledAction{}, []domain.PartAllocation{}, reportAt, 0, 0, true, nil
	}

	inventory := buildPartInventory(policy)
	crews := make([]crewState, 0, len(policy.Optimizer.CrewRoster))
	for _, crew := range policy.Optimizer.CrewRoster {
		shiftStart, err := time.Parse(time.RFC3339, crew.ShiftStart)
		if err != nil {
			return nil, nil, time.Time{}, 0, 0, false, fmt.Errorf("parse shift_start for crew %s: %w", crew.CrewID, err)
		}
		shiftEnd, err := time.Parse(time.RFC3339, crew.ShiftEnd)
		if err != nil {
			return nil, nil, time.Time{}, 0, 0, false, fmt.Errorf("parse shift_end for crew %s: %w", crew.CrewID, err)
		}
		maxContinuous := crew.MaxContinuousHours
		if maxContinuous <= 0 {
			maxContinuous = math.Inf(1)
		}
		crews = append(crews, crewState{
			crew:               crew,
			shiftStart:         shiftStart,
			shiftEnd:           shiftEnd,
			available:          shiftStart,
			site:               crew.HomeSite,
			maxContinuousHours: maxContinuous,
		})
	}
	sort.Slice(crews, func(i, j int) bool {
		return crews[i].crew.CrewID < crews[j].crew.CrewID
	})

	used := make([]bool, len(tasks))
	currentRows := make([]domain.ScheduledAction, 0, len(tasks))
	currentParts := make([]domain.PartAllocation, 0)
	var best schedulePlan
	found := false
	var search func(done int, totalTravel, totalTransfer float64) error
	search = func(done int, totalTravel, totalTransfer float64) error {
		if done == len(tasks) {
			rows := sortScheduleRows(append([]domain.ScheduledAction(nil), currentRows...))
			parts := sortPartAllocations(append([]domain.PartAllocation(nil), currentParts...))
			candidate := schedulePlan{
				rows:      rows,
				parts:     parts,
				maxEnd:    scheduleMaxEnd(rows, reportAt),
				travel:    totalTravel,
				transfer:  totalTransfer,
				signature: scheduleSignature(rows),
				partSig:   partSignature(parts),
			}
			if !found || betterSchedule(candidate, best) {
				best = candidate
				found = true
			}
			return nil
		}
		for taskIdx := range tasks {
			if used[taskIdx] {
				continue
			}
			task := tasks[taskIdx]
			used[taskIdx] = true
			for crewIdx := range crews {
				if crews[crewIdx].crew.Region != task.region {
					continue
				}
				available := crews[crewIdx].available
				continuous := crews[crewIdx].continuousHours
				if task.hours > crews[crewIdx].maxContinuousHours+1e-12 {
					continue
				}
				if continuous+task.hours > crews[crewIdx].maxContinuousHours+1e-12 {
					available = available.Add(hoursDuration(policy.Optimizer.BreakHours))
					continuous = 0
				}
				travel, ok := travelHours(policy, task.region, crews[crewIdx].site, task.item.Call.Site)
				if !ok {
					return fmt.Errorf("missing travel time for region %s from %s to %s", task.region, crews[crewIdx].site, task.item.Call.Site)
				}
				options, err := partOptions(policy, inventory, reportAt, task)
				if err != nil {
					return err
				}
				for _, option := range options {
					arrival := available.Add(hoursDuration(travel))
					start := maxTime(arrival, option.readyAt)
					end := start.Add(task.duration)
					if end.After(crews[crewIdx].shiftEnd) || end.After(task.dueBy) {
						continue
					}
					previousAvailable := crews[crewIdx].available
					previousSite := crews[crewIdx].site
					previousContinuous := crews[crewIdx].continuousHours
					applyPartOption(inventory, option, -1)
					crews[crewIdx].available = end
					crews[crewIdx].site = task.item.Call.Site
					crews[crewIdx].continuousHours = continuous + task.hours
					currentRows = append(currentRows, domain.ScheduledAction{
						RequestID:   task.item.Call.RequestID,
						CrewID:      crews[crewIdx].crew.CrewID,
						Region:      task.region,
						Site:        task.item.Call.Site,
						Action:      task.action,
						StartAt:     start,
						EndAt:       end,
						TravelHours: travel,
					})
					currentParts = append(currentParts, option.allocations...)
					if err := search(done+1, totalTravel+travel, totalTransfer+option.transfer); err != nil {
						return err
					}
					currentParts = currentParts[:len(currentParts)-len(option.allocations)]
					currentRows = currentRows[:len(currentRows)-1]
					crews[crewIdx].available = previousAvailable
					crews[crewIdx].site = previousSite
					crews[crewIdx].continuousHours = previousContinuous
					applyPartOption(inventory, option, 1)
				}
			}
			used[taskIdx] = false
		}
		return nil
	}
	if err := search(0, 0, 0); err != nil {
		return nil, nil, time.Time{}, 0, 0, false, err
	}
	return best.rows, best.parts, best.maxEnd, best.travel, best.transfer, found, nil
}

func travelHours(policy config.Policy, region, fromSite, toSite string) (float64, bool) {
	byFrom, ok := policy.Optimizer.TravelHours[region]
	if !ok {
		return 0, false
	}
	byTo, ok := byFrom[fromSite]
	if !ok {
		return 0, false
	}
	value, ok := byTo[toSite]
	return value, ok
}

func partTransferHours(policy config.Policy, region, fromSite, toSite string) (float64, bool) {
	byFrom, ok := policy.Optimizer.PartTransfer[region]
	if !ok {
		return 0, false
	}
	byTo, ok := byFrom[fromSite]
	if !ok {
		return 0, false
	}
	value, ok := byTo[toSite]
	return value, ok
}

func buildPartInventory(policy config.Policy) map[string]map[string]int {
	inventory := make(map[string]map[string]int)
	for _, row := range policy.Optimizer.PartsInventory {
		available := row.OnHand - row.ReserveMin
		if available < 0 {
			available = 0
		}
		if inventory[row.Site] == nil {
			inventory[row.Site] = make(map[string]int)
		}
		inventory[row.Site][row.PartID] += available
	}
	return inventory
}

func actionParts(item domain.ScoredCall, action string, policy config.Policy) map[string]int {
	byAction, ok := policy.Optimizer.ActionParts[action]
	if !ok {
		return nil
	}
	byAsset, ok := byAction[item.Call.AssetType]
	if !ok {
		return nil
	}
	parts := make(map[string]int, len(byAsset))
	for partID, qty := range byAsset {
		if qty > 0 {
			parts[partID] = qty
		}
	}
	return parts
}

func partOptions(policy config.Policy, inventory map[string]map[string]int, reportAt time.Time, task scheduleTask) ([]partOption, error) {
	requirements := actionParts(task.item, task.action, policy)
	if len(requirements) == 0 {
		return []partOption{{readyAt: reportAt}}, nil
	}
	partIDs := make([]string, 0, len(requirements))
	for partID := range requirements {
		partIDs = append(partIDs, partID)
	}
	sort.Strings(partIDs)
	sites := make([]string, 0, len(inventory))
	for site := range inventory {
		if policy.Optimizer.SiteRegion[site] == task.region {
			sites = append(sites, site)
		}
	}
	sort.Strings(sites)

	options := make([]partOption, 0)
	current := make([]domain.PartAllocation, 0, len(partIDs))
	var search func(pos int, readyAt time.Time, transfer float64)
	search = func(pos int, readyAt time.Time, transfer float64) {
		if pos == len(partIDs) {
			allocations := sortPartAllocations(append([]domain.PartAllocation(nil), current...))
			options = append(options, partOption{
				allocations: allocations,
				readyAt:     readyAt,
				transfer:    transfer,
				signature:   partSignature(allocations),
			})
			return
		}
		partID := partIDs[pos]
		qty := requirements[partID]
		for _, source := range sites {
			if inventory[source][partID] < qty {
				continue
			}
			transferHours, ok := partTransferHours(policy, task.region, source, task.item.Call.Site)
			if !ok {
				continue
			}
			partReady := reportAt.Add(hoursDuration(transferHours))
			inventory[source][partID] -= qty
			current = append(current, domain.PartAllocation{
				RequestID:     task.item.Call.RequestID,
				PartID:        partID,
				SourceSite:    source,
				DestSite:      task.item.Call.Site,
				Quantity:      qty,
				ReadyAt:       partReady,
				TransferHours: transferHours,
			})
			search(pos+1, maxTime(readyAt, partReady), transfer+transferHours*float64(qty))
			current = current[:len(current)-1]
			inventory[source][partID] += qty
		}
	}
	search(0, reportAt, 0)
	sort.Slice(options, func(i, j int) bool {
		if !options[i].readyAt.Equal(options[j].readyAt) {
			return options[i].readyAt.Before(options[j].readyAt)
		}
		if math.Abs(options[i].transfer-options[j].transfer) > 1e-12 {
			return options[i].transfer < options[j].transfer
		}
		return options[i].signature < options[j].signature
	})
	return options, nil
}

func applyPartOption(inventory map[string]map[string]int, option partOption, delta int) {
	for _, allocation := range option.allocations {
		inventory[allocation.SourceSite][allocation.PartID] += delta * allocation.Quantity
	}
}

func hoursDuration(hours float64) time.Duration {
	return time.Duration(math.Round(hours * float64(time.Hour)))
}

func maxTime(left, right time.Time) time.Time {
	if right.After(left) {
		return right
	}
	return left
}

func sortScheduleRows(rows []domain.ScheduledAction) []domain.ScheduledAction {
	sort.Slice(rows, func(i, j int) bool {
		if !rows[i].StartAt.Equal(rows[j].StartAt) {
			return rows[i].StartAt.Before(rows[j].StartAt)
		}
		if rows[i].CrewID != rows[j].CrewID {
			return rows[i].CrewID < rows[j].CrewID
		}
		return rows[i].RequestID < rows[j].RequestID
	})
	return rows
}

func sortPartAllocations(rows []domain.PartAllocation) []domain.PartAllocation {
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].RequestID != rows[j].RequestID {
			return rows[i].RequestID < rows[j].RequestID
		}
		if rows[i].PartID != rows[j].PartID {
			return rows[i].PartID < rows[j].PartID
		}
		if rows[i].SourceSite != rows[j].SourceSite {
			return rows[i].SourceSite < rows[j].SourceSite
		}
		return rows[i].DestSite < rows[j].DestSite
	})
	return rows
}

func scheduleMaxEnd(rows []domain.ScheduledAction, fallback time.Time) time.Time {
	maxEnd := fallback
	for _, row := range rows {
		if row.EndAt.After(maxEnd) {
			maxEnd = row.EndAt
		}
	}
	return maxEnd
}

func scheduleSignature(rows []domain.ScheduledAction) string {
	ordered := append([]domain.ScheduledAction(nil), rows...)
	sort.Slice(ordered, func(i, j int) bool {
		return ordered[i].RequestID < ordered[j].RequestID
	})
	parts := make([]string, 0, len(ordered))
	for _, row := range ordered {
		parts = append(parts, row.RequestID+"="+row.CrewID+"@"+row.StartAt.Format("2006-01-02T15:04:05Z"))
	}
	return strings.Join(parts, "|")
}

func partSignature(rows []domain.PartAllocation) string {
	parts := make([]string, 0, len(rows))
	for _, row := range rows {
		parts = append(parts, fmt.Sprintf("%s:%s=%s>%s@%s", row.RequestID, row.PartID, row.SourceSite, row.DestSite, row.ReadyAt.Format("2006-01-02T15:04:05Z")))
	}
	return strings.Join(parts, "|")
}

func betterSchedule(candidate, incumbent schedulePlan) bool {
	const eps = 1e-12
	if candidate.maxEnd.Before(incumbent.maxEnd) {
		return true
	}
	if !candidate.maxEnd.Equal(incumbent.maxEnd) {
		return false
	}
	if candidate.travel < incumbent.travel-eps {
		return true
	}
	if math.Abs(candidate.travel-incumbent.travel) > eps {
		return false
	}
	if candidate.transfer < incumbent.transfer-eps {
		return true
	}
	if math.Abs(candidate.transfer-incumbent.transfer) > eps {
		return false
	}
	if candidate.signature != incumbent.signature {
		return candidate.signature < incumbent.signature
	}
	return candidate.partSig < incumbent.partSig
}

func chooseBand(risk float64, policy config.Policy) string {
	if risk >= policy.Thresholds.Dispatch {
		return "high"
	}
	if risk >= policy.Thresholds.Inspect {
		return "medium"
	}
	if risk >= policy.Thresholds.Watch {
		return "watch"
	}
	return "low"
}

func dueHours(action string, policy config.Policy) int {
	switch action {
	case "dispatch":
		return policy.DueHours.Dispatch
	case "inspect":
		return policy.DueHours.Inspect
	default:
		return policy.DueHours.Monitor
	}
}

func buildManifest(opts Options, modelConfig config.Model, policy config.Policy, rows int) (report.Manifest, error) {
	hashes := make(map[string]string)
	for name, path := range map[string]string{
		"calls":    opts.CallsPath,
		"windows":  opts.WindowsPath,
		"history":  opts.HistoryPath,
		"labels":   opts.LabelsPath,
		"capacity": opts.CapacityPath,
		"model":    opts.ModelPath,
		"policy":   opts.PolicyPath,
	} {
		digest, err := fileSHA256(path)
		if err != nil {
			return report.Manifest{}, err
		}
		hashes[name] = digest
	}
	return report.Manifest{
		GeneratedAt: policy.ReportGeneratedAt,
		ModelID:     modelConfig.ModelID,
		PolicyID:    policy.PolicyID,
		RowCount:    rows,
		OutputFiles: []string{"scored_calls.csv", "maintenance_decisions.csv", "crew_schedule.csv", "parts_allocation.csv", "risk_manifest.json", "evaluation.json"},
		InputSHA256: hashes,
	}, nil
}

func buildEvaluation(scored []domain.ScoredCall, labels map[string]domain.Label) report.Evaluation {
	var matrix report.ConfusionMatrix
	siteAcc := map[string]*siteAccumulator{}
	positiveActions := 0
	brier := 0.0
	for _, item := range scored {
		label := labels[item.Call.RequestID].FailureWithin30
		predicted := item.Action == "dispatch" || item.Action == "inspect"
		if predicted {
			positiveActions++
		}
		if predicted && label == 1 {
			matrix.TruePositive++
		} else if predicted && label == 0 {
			matrix.FalsePositive++
		} else if !predicted && label == 0 {
			matrix.TrueNegative++
		} else {
			matrix.FalseNegative++
		}
		diff := item.CalibratedRisk - float64(label)
		brier += diff * diff
		acc := siteAcc[item.Call.Site]
		if acc == nil {
			acc = &siteAccumulator{}
			siteAcc[item.Call.Site] = acc
		}
		acc.count++
		if predicted {
			acc.positiveActions++
		}
		if label == 1 {
			acc.observedFailures++
		}
		acc.riskSum += item.CalibratedRisk
	}
	metrics := report.Metrics{
		Precision:        ratio(matrix.TruePositive, matrix.TruePositive+matrix.FalsePositive),
		Recall:           ratio(matrix.TruePositive, matrix.TruePositive+matrix.FalseNegative),
		BrierScore:       ratioFloat(brier, len(scored)),
		ROCAUC:           rocAUC(scored, labels),
		AveragePrecision: averagePrecision(scored, labels),
	}
	if metrics.Precision+metrics.Recall == 0 {
		metrics.F1 = 0
	} else {
		metrics.F1 = 2 * metrics.Precision * metrics.Recall / (metrics.Precision + metrics.Recall)
	}
	sites := make(map[string]report.SiteMetrics, len(siteAcc))
	for site, acc := range siteAcc {
		sites[site] = report.SiteMetrics{
			Count:                acc.count,
			PositiveActionCount:  acc.positiveActions,
			ObservedFailureCount: acc.observedFailures,
			MeanCalibratedRisk:   ratioFloat(acc.riskSum, acc.count),
		}
	}
	return report.Evaluation{
		RowCount:            len(scored),
		PositiveActionCount: positiveActions,
		ConfusionMatrix:     matrix,
		Metrics:             metrics,
		SiteMetrics:         sites,
	}
}

type siteAccumulator struct {
	count            int
	positiveActions  int
	observedFailures int
	riskSum          float64
}

type rankedLabel struct {
	requestID string
	score     float64
	label     int
}

func rocAUC(scored []domain.ScoredCall, labels map[string]domain.Label) float64 {
	ranked := make([]rankedLabel, 0, len(scored))
	positives := 0
	for _, item := range scored {
		label := labels[item.Call.RequestID].FailureWithin30
		positives += label
		ranked = append(ranked, rankedLabel{score: item.CalibratedRisk, label: label})
	}
	negatives := len(ranked) - positives
	if positives == 0 || negatives == 0 {
		return 0
	}
	sort.Slice(ranked, func(i, j int) bool {
		return ranked[i].score < ranked[j].score
	})
	rankSum := 0.0
	for i := 0; i < len(ranked); {
		j := i + 1
		for j < len(ranked) && ranked[j].score == ranked[i].score {
			j++
		}
		averageRank := float64(i+1+j) / 2.0
		for _, item := range ranked[i:j] {
			if item.label == 1 {
				rankSum += averageRank
			}
		}
		i = j
	}
	return (rankSum - float64(positives*(positives+1))/2.0) / float64(positives*negatives)
}

func averagePrecision(scored []domain.ScoredCall, labels map[string]domain.Label) float64 {
	ranked := make([]rankedLabel, 0, len(scored))
	positives := 0
	for _, item := range scored {
		label := labels[item.Call.RequestID].FailureWithin30
		positives += label
		ranked = append(ranked, rankedLabel{
			requestID: item.Call.RequestID,
			score:     item.CalibratedRisk,
			label:     label,
		})
	}
	if positives == 0 {
		return 0
	}
	sort.Slice(ranked, func(i, j int) bool {
		if ranked[i].score == ranked[j].score {
			return ranked[i].requestID < ranked[j].requestID
		}
		return ranked[i].score > ranked[j].score
	})
	found := 0
	precisionSum := 0.0
	for i, item := range ranked {
		if item.label == 1 {
			found++
			precisionSum += float64(found) / float64(i+1)
		}
	}
	return precisionSum / float64(positives)
}

func fileSHA256(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("hash %s: %w", path, err)
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

func ratio(numerator, denominator int) float64 {
	if denominator == 0 {
		return 0
	}
	return float64(numerator) / float64(denominator)
}

func ratioFloat(numerator float64, denominator int) float64 {
	if denominator == 0 {
		return 0
	}
	return numerator / float64(denominator)
}
