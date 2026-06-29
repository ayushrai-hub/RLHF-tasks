#!/bin/bash
set -euo pipefail
cat << 'GOEOF' > /tmp/git_integrity.go
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type Commit struct {
	SHA           string   `json:"sha"`
	Parents       []string `json:"parents"`
	Subject       string   `json:"subject"`
	AuthorDate    string   `json:"author_date"`
	IsMerge       bool     `json:"is_merge"`
}

type ReflogEntry struct {
	Ref     string `json:"ref"`
	NewSHA  string `json:"new_sha"`
	Selector string `json:"selector"`
	Message string `json:"message"`
}

type Policy struct {
	OrphanClassification struct {
		ReflogMessagePatterns []struct {
			MatchSubstring string `json:"match_substring"`
			Reason         string `json:"reason"`
		} `json:"reflog_message_patterns"`
		DefaultReason string `json:"default_reason"`
		InferSupersessionFromSameRef bool `json:"infer_supersession_from_same_ref"`
	} `json:"orphan_classification"`
	MergeConsistency struct {
		RequiredParentCount int     `json:"required_parent_count"`
		RequireParentsInGraph bool  `json:"require_parents_in_graph"`
		EmptyMergesScore    float64 `json:"empty_merges_score"`
	} `json:"merge_consistency"`
	MetricsRoundDecimals int `json:"metrics_round_decimals"`
	HistoryEventFilter struct {
		IncludeReflogActions []string `json:"include_reflog_actions"`
		ExcludeSubstrings    []string `json:"exclude_substrings"`
	} `json:"history_event_filter"`
	Outputs struct {
		HistoryReconstruction struct {
			LineTemplate string `json:"line_template"`
		} `json:"history_reconstruction"`
	} `json:"outputs"`
}

func loadJSON(path string, out interface{}) error {
	raw, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(raw, out)
}

func roundMetric(value float64, decimals int) float64 {
	pow := 1.0
	for i := 0; i < decimals; i++ {
		pow *= 10
	}
	return float64(int(value*pow+0.5)) / pow
}

func ancestors(graph map[string]Commit, sha string) map[string]bool {
	seen := map[string]bool{}
	stack := []string{sha}
	for len(stack) > 0 {
		cur := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if seen[cur] {
			continue
		}
		c, ok := graph[cur]
		if !ok {
			continue
		}
		seen[cur] = true
		stack = append(stack, c.Parents...)
	}
	return seen
}

func firstParentAncestors(graph map[string]Commit, sha string) map[string]bool {
	seen := map[string]bool{}
	cur := sha
	for cur != "" && !seen[cur] {
		c, ok := graph[cur]
		if !ok {
			break
		}
		seen[cur] = true
		if len(c.Parents) == 0 {
			break
		}
		cur = c.Parents[0]
	}
	return seen
}

func mergeBase(graph map[string]Commit, tipA, tipB string) string {
	ancA := ancestors(graph, tipA)
	stack := []string{tipB}
	seen := map[string]bool{}
	candidates := []string{}
	for len(stack) > 0 {
		cur := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if seen[cur] {
			continue
		}
		seen[cur] = true
		if _, ok := graph[cur]; !ok {
			continue
		}
		if ancA[cur] {
			candidates = append(candidates, cur)
		}
		stack = append(stack, graph[cur].Parents...)
	}
	if len(candidates) == 0 {
		return ""
	}
	sort.Slice(candidates, func(i, j int) bool {
		return len(ancestors(graph, candidates[i])) > len(ancestors(graph, candidates[j]))
	})
	return candidates[0]
}

func countAhead(graph map[string]Commit, tip, base string) int {
	reach := ancestors(graph, tip)
	if base == "" {
		return len(reach)
	}
	baseAnc := ancestors(graph, base)
	count := 0
	for sha := range reach {
		if !baseAnc[sha] {
			count++
		}
	}
	return count
}

func selectorIndex(selector string) int {
	start := strings.LastIndex(selector, "@{")
	end := strings.LastIndex(selector, "}")
	if start < 0 || end < 0 {
		return 0
	}
	value, _ := strconv.Atoi(selector[start+2 : end])
	return value
}

func reasonFromMessage(message string, policy Policy) string {
	lower := strings.ToLower(message)
	for _, rule := range policy.OrphanClassification.ReflogMessagePatterns {
		if strings.Contains(lower, rule.MatchSubstring) {
			return rule.Reason
		}
	}
	return ""
}

func classifyOrphan(sha, pickRef string, reflog []ReflogEntry, policy Policy) string {
	defaultReason := policy.OrphanClassification.DefaultReason
	var refEntries []ReflogEntry
	for _, entry := range reflog {
		if entry.Ref == pickRef {
			refEntries = append(refEntries, entry)
		}
	}
	sort.Slice(refEntries, func(i, j int) bool {
		return selectorIndex(refEntries[i].Selector) < selectorIndex(refEntries[j].Selector)
	})
	orphanIndex := -1
	for index, entry := range refEntries {
		if entry.NewSHA == sha {
			orphanIndex = index
			break
		}
	}
	if orphanIndex >= 0 {
		for _, newer := range refEntries[:orphanIndex] {
			if reason := reasonFromMessage(newer.Message, policy); reason != "" {
				return reason
			}
		}
	}
	for _, entry := range reflog {
		if entry.NewSHA == sha && entry.Ref == pickRef {
			if reason := reasonFromMessage(entry.Message, policy); reason != "" {
				return reason
			}
		}
	}
	return defaultReason
}

func writeJSON(path string, value interface{}) error {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	return os.WriteFile(path, raw, 0o644)
}

func main() {
	dataDir := "/app/data"
	var policy Policy
	var metadata struct {
		RepositoryID  string `json:"repository_id"`
		DefaultBranch string `json:"default_branch"`
	}
	var graphDoc struct {
		Commits []Commit `json:"commits"`
	}
	var branchDoc struct {
		Branches []struct {
			Name string `json:"name"`
			Tip  string `json:"tip"`
		} `json:"branches"`
	}
	var mergeDoc struct {
		Merges []struct {
			SHA     string   `json:"sha"`
			Parents []string `json:"parents"`
		} `json:"merges"`
	}
	var tagDoc struct {
		Tags []struct {
			Peeled string `json:"peeled"`
		} `json:"tags"`
	}
	var reflogDoc struct {
		Entries []ReflogEntry `json:"entries"`
	}

	must := func(err error) {
		if err != nil {
			panic(err)
		}
	}
	must(loadJSON(filepath.Join(dataDir, "integrity_policy.json"), &policy))
	must(loadJSON(filepath.Join(dataDir, "repository_metadata.json"), &metadata))
	must(loadJSON(filepath.Join(dataDir, "commit_graph.json"), &graphDoc))
	must(loadJSON(filepath.Join(dataDir, "branch_refs.json"), &branchDoc))
	must(loadJSON(filepath.Join(dataDir, "merge_commits.json"), &mergeDoc))
	must(loadJSON(filepath.Join(dataDir, "tag_history.json"), &tagDoc))
	must(loadJSON(filepath.Join(dataDir, "reflog_snapshots.json"), &reflogDoc))

	graph := map[string]Commit{}
	for _, c := range graphDoc.Commits {
		graph[c.SHA] = c
	}
	branches := map[string]string{}
	names := []string{}
	for _, b := range branchDoc.Branches {
		branches[b.Name] = b.Tip
		names = append(names, b.Name)
	}
	sort.Strings(names)

	advertised := map[string]bool{}
	for _, tip := range branches {
		for sha := range ancestors(graph, tip) {
			advertised[sha] = true
		}
	}
	for _, tag := range tagDoc.Tags {
		for sha := range ancestors(graph, tag.Peeled) {
			advertised[sha] = true
		}
	}

	reflogBySHA := map[string][]ReflogEntry{}
	for _, entry := range reflogDoc.Entries {
		reflogBySHA[entry.NewSHA] = append(reflogBySHA[entry.NewSHA], entry)
	}

	shaKeys := make([]string, 0, len(graph))
	for sha := range graph {
		shaKeys = append(shaKeys, sha)
	}
	sort.Strings(shaKeys)

	type Orphan struct {
		SHA              string `json:"sha"`
		Subject          string `json:"subject"`
		OrphanReason     string `json:"orphan_reason"`
		DiscoveredViaRef string `json:"discovered_via_ref"`
		ReflogMessage    string `json:"reflog_message"`
	}
	orphans := []Orphan{}
	for _, sha := range shaKeys {
		if advertised[sha] {
			continue
		}
		entries := reflogBySHA[sha]
		if len(entries) == 0 {
			continue
		}
		sort.Slice(entries, func(i, j int) bool { return entries[i].Ref < entries[j].Ref })
		pick := entries[0]
		orphans = append(orphans, Orphan{
			SHA: sha, Subject: graph[sha].Subject,
			OrphanReason: classifyOrphan(sha, pick.Ref, reflogDoc.Entries, policy),
			DiscoveredViaRef: pick.Ref, ReflogMessage: pick.Message,
		})
	}
	orphanDoc := map[string]interface{}{
		"repository_id": metadata.RepositoryID,
		"orphans":       orphans,
		"count":         len(orphans),
	}

	type Pair struct {
		BranchA         string `json:"branch_a"`
		BranchB         string `json:"branch_b"`
		MergeBase       string `json:"merge_base"`
		AheadA          int    `json:"ahead_a"`
		AheadB          int    `json:"ahead_b"`
		DivergenceTotal int    `json:"divergence_total"`
	}
	pairs := []Pair{}
	for i := 0; i < len(names); i++ {
		for j := i + 1; j < len(names); j++ {
			a, b := names[i], names[j]
			base := mergeBase(graph, branches[a], branches[b])
			aheadA := countAhead(graph, branches[a], base)
			aheadB := countAhead(graph, branches[b], base)
			pairs = append(pairs, Pair{
				BranchA: a, BranchB: b, MergeBase: base,
				AheadA: aheadA, AheadB: aheadB, DivergenceTotal: aheadA + aheadB,
			})
		}
	}
	divergenceDoc := map[string]interface{}{
		"repository_id": metadata.RepositoryID,
		"pairs":         pairs,
	}

	decimals := policy.MetricsRoundDecimals
	fpAnc := firstParentAncestors(graph, branches[metadata.DefaultBranch])
	validMerges := 0
	findings := []string{}
	required := policy.MergeConsistency.RequiredParentCount
	for _, merge := range mergeDoc.Merges {
		ok := len(merge.Parents) == required
		if policy.MergeConsistency.RequireParentsInGraph {
			for _, parent := range merge.Parents {
				if _, exists := graph[parent]; !exists {
					ok = false
				}
			}
		}
		if ok && len(merge.Parents) > 0 {
			ok = fpAnc[merge.Parents[0]]
		}
		if ok {
			validMerges++
		} else {
			onMain := false
			if len(merge.Parents) > 0 {
				onMain = fpAnc[merge.Parents[0]]
			}
			findings = append(findings, fmt.Sprintf(
				"merge %s inconsistent: parents=%d first_parent_on_mainline=%t",
				merge.SHA[:7], len(merge.Parents), onMain,
			))
		}
	}
	mergeScore := policy.MergeConsistency.EmptyMergesScore
	if len(mergeDoc.Merges) > 0 {
		mergeScore = roundMetric(100.0*float64(validMerges)/float64(len(mergeDoc.Merges)), decimals)
	}

	checks, passed := 0, 0
	checks++
	passed++
	for _, commit := range graph {
		for _, parent := range commit.Parents {
			checks++
			if _, ok := graph[parent]; ok {
				passed++
			}
		}
	}
	for _, branch := range branchDoc.Branches {
		checks++
		if _, ok := graph[branch.Tip]; ok {
			passed++
		}
	}
	for _, tag := range tagDoc.Tags {
		checks++
		if _, ok := graph[tag.Peeled]; ok {
			passed++
		}
	}
	graphScore := roundMetric(100.0*float64(passed)/float64(checks), decimals)

	reportLines := []string{
		fmt.Sprintf("# Repository Integrity Report — %s", metadata.RepositoryID),
		"",
		"## Repository Summary",
		"",
		fmt.Sprintf("- Repository ID: `%s`", metadata.RepositoryID),
		fmt.Sprintf("- Commits in graph: %d", len(graph)),
		fmt.Sprintf("- Active branches: %d", len(branches)),
		"",
		"## Integrity Metrics",
		"",
		fmt.Sprintf("- graph_integrity_score: %.1f", graphScore),
		fmt.Sprintf("- merge_consistency_score: %.1f", mergeScore),
		fmt.Sprintf("- orphan_commit_count: %d", len(orphans)),
		fmt.Sprintf("- branch_pair_count: %d", len(pairs)),
		"",
		"## Merge Findings",
		"",
	}
	if len(findings) == 0 {
		reportLines = append(reportLines, "- all merge commits satisfy policy checks")
	} else {
		reportLines = append(reportLines, findings...)
	}
	reportLines = append(reportLines, "", "## Orphan Summary", "")
	if len(orphans) == 0 {
		reportLines = append(reportLines, "- no orphan commits detected")
	} else {
		for _, orphan := range orphans {
			reportLines = append(reportLines, fmt.Sprintf(
				"- `%s` %s (%s)", orphan.SHA[:7], orphan.Subject, orphan.OrphanReason,
			))
		}
	}
	reportLines = append(reportLines, "")

	type Event struct {
		AuthorDate string
		Ref        string
		Selector   string
		Summary    string
	}
	events := []Event{}
	for _, entry := range reflogDoc.Entries {
		skip := false
		for _, fragment := range policy.HistoryEventFilter.ExcludeSubstrings {
			if strings.Contains(entry.Message, fragment) {
				skip = true
				break
			}
		}
		if skip {
			continue
		}
		action := strings.ToLower(strings.Split(entry.Message, ":")[0])
		action = strings.ReplaceAll(action, "commit (", "commit")
		action = strings.ReplaceAll(action, ")", "")
		match := false
		for _, prefix := range policy.HistoryEventFilter.IncludeReflogActions {
			if strings.HasPrefix(action, prefix) {
				match = true
				break
			}
		}
		if !match {
			continue
		}
		authorDate := "unknown"
		if commit, ok := graph[entry.NewSHA]; ok {
			authorDate = commit.AuthorDate
		}
		events = append(events, Event{
			AuthorDate: authorDate, Ref: entry.Ref,
			Selector: entry.Selector, Summary: entry.Message,
		})
	}
	sort.Slice(events, func(i, j int) bool {
		if events[i].AuthorDate != events[j].AuthorDate {
			return events[i].AuthorDate < events[j].AuthorDate
		}
		if events[i].Ref != events[j].Ref {
			return events[i].Ref < events[j].Ref
		}
		return events[i].Selector < events[j].Selector
	})

	historyLines := []string{fmt.Sprintf("# History Reconstruction — %s", metadata.RepositoryID), ""}
	template := policy.Outputs.HistoryReconstruction.LineTemplate
	for _, event := range events {
		line := template
		line = strings.ReplaceAll(line, "{author_date}", event.AuthorDate)
		line = strings.ReplaceAll(line, "{ref}", event.Ref)
		line = strings.ReplaceAll(line, "{summary}", event.Summary)
		historyLines = append(historyLines, line)
	}
	historyLines = append(historyLines, "")

	must(writeJSON("/app/branch_divergence.json", divergenceDoc))
	must(writeJSON("/app/orphan_commits.json", orphanDoc))
	must(os.WriteFile("/app/repository_integrity_report.md", []byte(strings.Join(reportLines, "\n")), 0o644))
	must(os.WriteFile("/app/history_reconstruction.md", []byte(strings.Join(historyLines, "\n")), 0o644))
}
GOEOF
go run /tmp/git_integrity.go
