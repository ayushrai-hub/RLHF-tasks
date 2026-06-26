package merge

import "logrecover/pkg/api"

func reconcile_b(a, b api.Event) bool {
	if a.Lamport != b.Lamport {
		return a.Lamport < b.Lamport
	}
	if a.Seq != b.Seq {
		return a.Seq < b.Seq
	}
	return a.NodeID < b.NodeID
}

func ReconcileLess(a, b api.Event) bool {
	return reconcile_b(a, b)
}
