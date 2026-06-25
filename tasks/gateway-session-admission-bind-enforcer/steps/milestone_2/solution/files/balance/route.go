package balance

import (
	"fmt"
	"sort"
)

func SelectBackend(backends map[string]int, counter int) string {
	type pair struct {
		id     string
		weight int
	}
	list := make([]pair, 0, len(backends))
	for id, w := range backends {
		if w <= 0 {
			continue
		}
		list = append(list, pair{id, w})
	}
	if len(list) == 0 {
		return ""
	}
	sort.Slice(list, func(i, j int) bool { return list[i].id < list[j].id })
	total := 0
	for _, p := range list {
		total += p.weight
	}
	if total == 0 {
		return list[0].id
	}
	slot := counter % total
	acc := 0
	for _, p := range list {
		acc += p.weight
		if slot < acc {
			return p.id
		}
	}
	return list[len(list)-1].id
}

func StateDigest(
	buckets map[string]int,
	configGen int,
	routeCounter int,
	scopeGen int,
	seq int,
	pendingCount int,
) string {
	return BuildStateDigest(
		buckets,
		configGen,
		routeCounter,
		scopeGen,
		seq,
		pendingCount,
	)
}

func FormatReject(backend string, cost int) string {
	return fmt.Sprintf("reject:%s:%d", backend, cost)
}
