package auditx

import (
	"fmt"
	"sort"
	"strings"

	"terminal.local/objectmanifest/internal/hashutil"
)

func InputRow(batchID string, logicalKey string, rel string, sha string, sidecar string) string {
	return fmt.Sprintf("%s\t%s\t%s\t%s\t%s\n", batchID, logicalKey, rel, sha, sidecar)
}

func InputDigest(rows []string) string {
	stable := append([]string(nil), rows...)
	sort.Strings(stable)
	return hashutil.SHA256Hex([]byte(strings.Join(stable, "")))
}
