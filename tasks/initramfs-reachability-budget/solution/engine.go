package main

import (
	"encoding/json"
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
	"lab/pk_a"
	"lab/pk_b"
	"lab/pk_c"
)

type packSpec struct {
	PackID     string `toml:"id"`
	DepsFile   string `toml:"deps_file"`
	RelFile    string `toml:"rel_file"`
	BlobFile   string `toml:"blob_file"`
	VstampFile string `toml:"vstamp_file"`
}

type depsDoc struct {
	Seeds    []string                       `json:"seeds"`
	Nodes    []struct {
		ID   string   `json:"id"`
		Deps []string `json:"deps"`
	} `json:"nodes"`
	Registry map[string]json.RawMessage `json:"registry"`
}

func envRoot() string {
	if v := os.Getenv("Q7_ENV_ROOT"); v != "" {
		return v
	}
	return "/app/environment"
}

func loadPackSpec(packID string) (packSpec, error) {
	var spec packSpec
	_, err := toml.DecodeFile(filepath.Join(envRoot(), "scenarios", packID+".toml"), &spec)
	if err != nil {
		return spec, err
	}
	if spec.PackID == "" {
		spec.PackID = packID
	}
	return spec, nil
}

func registryNode(nodeID string, meta json.RawMessage) pk_a.GraphNode {
	var asList []string
	if err := json.Unmarshal(meta, &asList); err == nil {
		return pk_a.GraphNode{NodeID: nodeID, Deps: asList}
	}
	var asObj struct {
		Deps []string `json:"deps"`
	}
	if err := json.Unmarshal(meta, &asObj); err == nil {
		return pk_a.GraphNode{NodeID: nodeID, Deps: asObj.Deps}
	}
	return pk_a.GraphNode{NodeID: nodeID}
}

func loadGraph(path string) ([]pk_a.GraphNode, map[string]pk_a.GraphNode, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, err
	}
	var doc depsDoc
	if err := json.Unmarshal(raw, &doc); err != nil {
		return nil, nil, err
	}
	registry := make(map[string]pk_a.GraphNode)
	for _, entry := range doc.Nodes {
		registry[entry.ID] = pk_a.GraphNode{NodeID: entry.ID, Deps: entry.Deps}
	}
	for nid, meta := range doc.Registry {
		if _, ok := registry[nid]; !ok {
			registry[nid] = registryNode(nid, meta)
		}
	}
	if doc.Seeds == nil {
		all := make([]pk_a.GraphNode, 0, len(registry))
		for _, n := range registry {
			all = append(all, n)
		}
		return all, registry, nil
	}
	seeds := make([]pk_a.GraphNode, 0, len(doc.Seeds))
	for _, sid := range doc.Seeds {
		if n, ok := registry[sid]; ok {
			seeds = append(seeds, n)
		}
	}
	return seeds, registry, nil
}

func loadAlias(path string) (pk_b.AliasPack, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return pk_b.AliasPack{}, err
	}
	var doc struct {
		Map map[string]string `json:"map"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		return pk_b.AliasPack{}, err
	}
	return pk_b.AliasPack{Map: doc.Map}, nil
}

func loadBlobs(path string) (pk_c.BlobPack, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return pk_c.BlobPack{}, err
	}
	var doc struct {
		Sizes map[string]int `json:"sizes"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		return pk_c.BlobPack{}, err
	}
	return pk_c.BlobPack{Sizes: doc.Sizes}, nil
}

func loadLane(path string) (pk_b.LanePick, error) {
	var doc struct {
		LaneClass string   `toml:"lane_class"`
		Required  []string `toml:"required"`
	}
	if _, err := toml.DecodeFile(path, &doc); err != nil {
		return pk_b.LanePick{}, err
	}
	laneClass := doc.LaneClass
	return pk_b.LanePick{LaneClass: laneClass, Required: doc.Required}, nil
}

func applyStageA(nodes []pk_a.GraphNode, registry map[string]pk_a.GraphNode) *pk_a.IngestSink {
	sink := &pk_a.IngestSink{Registry: registry, Rows: make(map[string]pk_a.GraphNode)}
	pk_a.OpA(nodes, sink)
	return sink
}

func applyStageB(rows *pk_a.IngestSink, aliasMaps pk_b.AliasPack, lane pk_b.LanePick, blobs pk_c.BlobPack) pk_b.ReachSet {
	return pk_b.PhaseB(rows, aliasMaps, lane, blobs.Sizes)
}

func applyStageC(reachable pk_b.ReachSet, blobs pk_c.BlobPack, out pk_c.PackEmitter, ledger *pk_c.LedgerEmitter) error {
	return pk_c.ReconcileC(reachable, blobs, out, ledger)
}

func runPack(packID, bundleOut, ledgerOut string) error {
	root := envRoot()
	spec, err := loadPackSpec(packID)
	if err != nil {
		return err
	}
	seeds, registry, err := loadGraph(filepath.Join(root, spec.DepsFile))
	if err != nil {
		return err
	}
	sink := applyStageA(seeds, registry)
	aliasMaps, err := loadAlias(filepath.Join(root, spec.RelFile))
	if err != nil {
		return err
	}
	lane, err := loadLane(filepath.Join(root, spec.VstampFile))
	if err != nil {
		return err
	}
	blobs, err := loadBlobs(filepath.Join(root, spec.BlobFile))
	if err != nil {
		return err
	}
	reachable := applyStageB(sink, aliasMaps, lane, blobs)
	out := pk_c.PackEmitter{Path: bundleOut}
	ledger := &pk_c.LedgerEmitter{Path: ledgerOut, PackID: spec.PackID}
	
	if err := applyStageC(reachable, blobs, out, ledger); err != nil {
		return err
	}
	return pk_c.BumpIncSeq()
}
