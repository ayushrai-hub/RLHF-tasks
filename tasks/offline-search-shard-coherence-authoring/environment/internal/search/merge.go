package search

import (
	"sort"

	"offline-search-shard-coherence/internal/model"
)

func MergeResults(candidates []model.Result, limit int) []model.Result {
	// Group candidates before final ordering.
	groups := map[string][]model.Result{}
	for _, r := range candidates {
		groups[r.SelectedURL] = append(groups[r.SelectedURL], r)
	}
	merged := make([]model.Result, 0, len(groups))
	for _, group := range groups {
		sort.Slice(group, func(i, j int) bool { return better(group[i], group[j]) })
		best := group[0]
		urls := make([]string, 0, len(group))
		for _, r := range group {
			urls = append(urls, r.SelectedURL)
		}
		sort.Strings(urls)
		best.SupportingURLs = urls
		merged = append(merged, best)
	}
	sort.Slice(merged, func(i, j int) bool { return better(merged[i], merged[j]) })
	if limit > 0 && len(merged) > limit {
		merged = merged[:limit]
	}
	for i := range merged {
		merged[i].Rank = i + 1
	}
	return merged
}

func better(a, b model.Result) bool {
	if a.Score != b.Score {
		return a.Score > b.Score
	}
	if a.Published != b.Published {
		return a.Published > b.Published
	}
	return a.CanonicalURL < b.CanonicalURL
}
