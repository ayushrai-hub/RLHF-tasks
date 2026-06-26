package lib

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"
	"strings"

	"lockkit/internal/types"
)

func RenderModuleLock(lock types.LockSnapshot, checksum []types.ChecksumRow) types.ModuleLockStub {
	digestByKey := map[string]string{}
	for _, row := range checksum {
		digestByKey[row.RepoKey] = row.Digest
	}
	keys := make([]string, 0, len(lock.Rows))
	for _, row := range lock.Rows {
		keys = append(keys, row.RepoKey)
	}
	sort.Strings(keys)
	lines := make([]string, 0, len(keys))
	for _, key := range keys {
		mod := strings.SplitN(key, "/", 2)[0]
		dig := digestByKey[key]
		lines = append(lines, fmt.Sprintf("lock(%s,%s)", key, dig))
		_ = mod
	}
	rollupRaw := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return types.ModuleLockStub{
		EntryID:    lock.EntryID,
		Lines:      lines,
		StubRollup: hex.EncodeToString(rollupRaw[:]),
	}
}
