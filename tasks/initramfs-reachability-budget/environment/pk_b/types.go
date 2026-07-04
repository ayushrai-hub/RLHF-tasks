// Package pk_b resolves lane obligations into surviving blob ids.
package pk_b

import "lab/pk_a"

type AliasPack struct {
	Map map[string]string
}

type LanePick struct {
	LaneClass string
	Required  []string
}

type ReachNode struct {
	NodeID string
	Deps   []string
}

type ReachSet struct {
	Nodes []ReachNode
}

type IngestSink = pk_a.IngestSink
