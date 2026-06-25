package packset

import (
	"fmt"
	"sort"

	"terminal.local/objectmanifest/internal/report"
	"terminal.local/objectmanifest/internal/store"
)

const generatedBy = "ostore-manifest-v1"
const storeName = "offline-object-store"

func Build(layout store.Layout) (BuildResult, error) {
	tree, err := store.ScanObjectTree(layout)
	if err != nil {
		return BuildResult{}, err
	}

	seenLogical := map[string]bool{}
	grouped := map[string][]Object{}
	epochs := map[string]int{}
	sidecars := map[string]string{}

	for _, obj := range tree {
		if seenLogical[obj.LogicalKey] {
			continue
		}
		seenLogical[obj.LogicalKey] = true
		grouped[obj.BatchID] = append(grouped[obj.BatchID], Object{
			LogicalKey:   obj.LogicalKey,
			RelativePath: obj.RelativePath,
			Size:         obj.Size,
			SHA256:       obj.SHA256,
		})
		if epochs[obj.BatchID] == 0 {
			if receipt, err := store.ReadReceipt(layout.ReceiptPath(obj.BatchID)); err == nil {
				epochs[obj.BatchID] = receipt.Epoch
			}
		}
		digest, err := store.ReadSidecarDigest(obj.SidecarPath)
		if err != nil {
			return BuildResult{}, fmt.Errorf("%s: %w", obj.RelativePath, err)
		}
		sidecars[obj.BatchID+"\x00"+obj.LogicalKey] = digest
	}

	batchIDs := make([]string, 0, len(grouped))
	for id := range grouped {
		batchIDs = append(batchIDs, id)
	}
	sort.Strings(batchIDs)

	batches := make([]Batch, 0, len(batchIDs))
	rows := make([]report.Row, 0)
	inputRows := make([]string, 0)
	objectCount := 0
	for _, id := range batchIDs {
		objects := grouped[id]
		sort.Slice(objects, func(i, j int) bool { return objects[i].LogicalKey < objects[j].LogicalKey })
		batch := Batch{BatchID: id, Epoch: epochs[id], ObjectCount: len(objects), Objects: objects}
		batch.BatchSHA256 = HashObjectRows(id, objects)
		batches = append(batches, batch)
		objectCount += len(objects)
		for _, obj := range objects {
			sideDigest := sidecars[id+"\x00"+obj.LogicalKey]
			rows = append(rows, report.Row{BatchID: id, LogicalKey: obj.LogicalKey, RelativePath: obj.RelativePath, Size: obj.Size, SHA256: obj.SHA256, SidecarSHA256: sideDigest})
			inputRows = append(inputRows, fmt.Sprintf("%s\t%s\t%s\t%s\t%s\n", id, obj.LogicalKey, obj.RelativePath, obj.SHA256, sideDigest))
		}
	}

	m := Manifest{SchemaVersion: 1, Store: storeName, GeneratedBy: generatedBy, CommitCount: len(batches), ObjectCount: objectCount, Batches: batches}
	m.ContentRoot = HashAllRows(batches)
	return BuildResult{Manifest: m, ReportRows: rows, InputRows: inputRows}, nil
}
