package packset

import (
	"fmt"
	"strings"

	"terminal.local/objectmanifest/internal/hashutil"
)

func CanonicalRow(batchID string, obj Object) string {
	return fmt.Sprintf("%s\t%s\t%s\t%d\t%s\n", batchID, obj.LogicalKey, obj.RelativePath, obj.Size, obj.SHA256)
}

func HashObjectRows(batchID string, objects []Object) string {
	var b strings.Builder
	for _, obj := range objects {
		b.WriteString(CanonicalRow(batchID, obj))
	}
	return hashutil.SHA256Hex([]byte(b.String()))
}

func HashAllRows(batches []Batch) string {
	var b strings.Builder
	for _, batch := range batches {
		for _, obj := range batch.Objects {
			b.WriteString(CanonicalRow(batch.BatchID, obj))
		}
	}
	return hashutil.SHA256Hex([]byte(b.String()))
}
