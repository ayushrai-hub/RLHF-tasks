package report

import (
	"fmt"
	"sort"
	"strings"
)

func RenderTSV(rows []Row) []byte {
	sorted := append([]Row(nil), rows...)
	sort.Slice(sorted, func(i, j int) bool {
		if sorted[i].BatchID != sorted[j].BatchID {
			return sorted[i].BatchID < sorted[j].BatchID
		}
		return sorted[i].LogicalKey < sorted[j].LogicalKey
	})
	var b strings.Builder
	b.WriteString("batch_id\tlogical_key\trelative_path\tsize\tsha256\t" + "sidecar_sha256\n")
	for _, row := range sorted {
		b.WriteString(fmt.Sprintf("%s\t%s\t%s\t%d\t%s\t%s\n", row.BatchID, row.LogicalKey, row.RelativePath, row.Size, row.SHA256, row.SidecarSHA256))
	}
	return []byte(b.String())
}
