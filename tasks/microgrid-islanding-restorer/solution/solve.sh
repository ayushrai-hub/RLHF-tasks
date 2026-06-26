#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="${TASK_DIR:-/app/task_file}"
mkdir -p "$TASK_DIR/output_data" "$TASK_DIR/src"
cat > "$TASK_DIR/src/main.go" <<'GO'
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Feeder struct {
	ID         string `json:"id"`
	District   string `json:"district"`
	Kw         int    `json:"kw"`
	Surge      int    `json:"surge"`
	Fault      int    `json:"fault"`
	Resilience int    `json:"resilience"`
	Value      int    `json:"value"`
	Critical   bool   `json:"critical"`
}

type Island struct {
	ID                string   `json:"id"`
	KwCap             int      `json:"kw_cap"`
	SurgeCap          int      `json:"surge_cap"`
	FaultCap          int      `json:"fault_cap"`
	MinResilience     int      `json:"min_resilience"`
	RequiredDistricts []string `json:"required_districts"`
}

type Config struct {
	Islands            []Island       `json:"islands"`
	MandatoryFeeders   []string       `json:"mandatory_feeders"`
	DistrictFloor      map[string]int `json:"district_floor"`
	ResonanceLimit     int            `json:"resonance_limit"`
	BalanceSpreadLimit int            `json:"balance_spread_limit"`
	ScoreNormalizer    int            `json:"score_normalizer"`
}

type Assignment struct {
	FeederID string `json:"feeder_id"`
	IslandID string `json:"island_id"`
}

type Plan struct {
	Assignments []Assignment `json:"assignments"`
}

func tokenSum(s string) int {
	total := 0
	for _, ch := range s {
		total += int(ch)
	}
	return total
}

func resonance(left Feeder, right Feeder, islandID string) int {
	coupled := left.Surge*right.Fault + right.Surge*left.Fault
	diff := left.Value - right.Value
	if diff < 0 {
		diff = -diff
	}
	return (tokenSum(left.ID+right.ID+islandID) + coupled + diff) % 11
}

func readFeeders(path string) ([]Feeder, error) {
	fh, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer fh.Close()
	out := []Feeder{}
	scanner := bufio.NewScanner(fh)
	for scanner.Scan() {
		if scanner.Text() == "" {
			continue
		}
		var row Feeder
		if err := json.Unmarshal([]byte(scanner.Text()), &row); err != nil {
			return nil, err
		}
		out = append(out, row)
	}
	return out, scanner.Err()
}

func contains(items []string, want string) bool {
	for _, item := range items {
		if item == want {
			return true
		}
	}
	return false
}

func validFull(assign []int, feeders []Feeder, config Config) bool {
	districts := map[string]int{}
	for key := range config.DistrictFloor {
		districts[key] = 0
	}
	mandatory := map[string]bool{}
	for _, id := range config.MandatoryFeeders {
		mandatory[id] = false
	}
	for idx, islandIdx := range assign {
		if islandIdx >= 0 {
			if _, ok := districts[feeders[idx].District]; ok {
				districts[feeders[idx].District]++
			}
			if _, ok := mandatory[feeders[idx].ID]; ok {
				mandatory[feeders[idx].ID] = true
			}
		}
	}
	for _, ok := range mandatory {
		if !ok {
			return false
		}
	}
	for name, floor := range config.DistrictFloor {
		if districts[name] < floor {
			return false
		}
	}
	for i, island := range config.Islands {
		kw, surge, fault, resilience := 0, 0, 0, 0
		localDistricts := map[string]bool{}
		local := []Feeder{}
		for idx, islandIdx := range assign {
			if islandIdx == i {
				row := feeders[idx]
				kw += row.Kw
				surge += row.Surge
				fault += row.Fault
				resilience += row.Resilience
				localDistricts[row.District] = true
				local = append(local, row)
			}
		}
		if kw > island.KwCap || surge > island.SurgeCap || fault > island.FaultCap || resilience < island.MinResilience {
			return false
		}
		for _, district := range island.RequiredDistricts {
			if !localDistricts[district] {
				return false
			}
		}
		for a := 0; a < len(local); a++ {
			for b := a + 1; b < len(local); b++ {
				if resonance(local[a], local[b], island.ID) <= config.ResonanceLimit {
					return false
				}
			}
		}
	}
	return true
}

func rawScore(assign []int, feeders []Feeder) int {
	score := 0
	for idx, islandIdx := range assign {
		if islandIdx >= 0 {
			score += feeders[idx].Value*10 + feeders[idx].Resilience
			if feeders[idx].Critical {
				score += 45
			}
		}
	}
	return score
}

func main() {
	inputDir := "/app/task_file/input_data"
	outputDir := "/app/task_file/output_data"
	if len(os.Args) > 1 {
		inputDir = os.Args[1]
	}
	if len(os.Args) > 2 {
		outputDir = os.Args[2]
	}
	feeders, err := readFeeders(filepath.Join(inputDir, "feeders.jsonl"))
	if err != nil {
		panic(err)
	}
	var config Config
	data, err := os.ReadFile(filepath.Join(inputDir, "config.json"))
	if err != nil {
		panic(err)
	}
	if err := json.Unmarshal(data, &config); err != nil {
		panic(err)
	}
	mandatory := map[string]bool{}
	for _, id := range config.MandatoryFeeders {
		mandatory[id] = true
	}
	bestScore := -1
	bestAssign := make([]int, len(feeders))
	assign := make([]int, len(feeders))
	for i := range assign {
		assign[i] = -1
	}
	type caps struct{ kw, surge, fault int }
	used := make([]caps, len(config.Islands))
	var dfs func(int)
	dfs = func(idx int) {
		if idx == len(feeders) {
			if validFull(assign, feeders, config) {
				score := rawScore(assign, feeders)
				if score > bestScore {
					bestScore = score
					copy(bestAssign, assign)
				}
			}
			return
		}
		row := feeders[idx]
		if !mandatory[row.ID] {
			assign[idx] = -1
			dfs(idx + 1)
		}
		for islandIdx, island := range config.Islands {
			next := caps{used[islandIdx].kw + row.Kw, used[islandIdx].surge + row.Surge, used[islandIdx].fault + row.Fault}
			if next.kw > island.KwCap || next.surge > island.SurgeCap || next.fault > island.FaultCap {
				continue
			}
			ok := true
			for prev := 0; prev < idx; prev++ {
				if assign[prev] == islandIdx && resonance(feeders[prev], row, island.ID) <= config.ResonanceLimit {
					ok = false
					break
				}
			}
			if !ok {
				continue
			}
			old := used[islandIdx]
			used[islandIdx] = next
			assign[idx] = islandIdx
			dfs(idx + 1)
			assign[idx] = -1
			used[islandIdx] = old
		}
	}
	dfs(0)
	if bestScore < 0 {
		panic("no feasible restoration plan")
	}
	plan := Plan{Assignments: []Assignment{}}
	for idx, islandIdx := range bestAssign {
		if islandIdx >= 0 {
			plan.Assignments = append(plan.Assignments, Assignment{FeederID: feeders[idx].ID, IslandID: config.Islands[islandIdx].ID})
		}
	}
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		panic(err)
	}
	payload, err := json.MarshalIndent(plan, "", "  ")
	if err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(outputDir, "restoration_plan.json"), payload, 0o644); err != nil {
		panic(err)
	}
	fmt.Printf("restored score %d\n", bestScore)
}
GO
cd "$TASK_DIR"
GOPROXY=off go build -o microgrid_restorer ./src
./microgrid_restorer
echo "Oracle complete."
