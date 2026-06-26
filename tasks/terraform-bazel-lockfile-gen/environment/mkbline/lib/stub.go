package lib

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"

	"lockkit/internal/types"
)

func RenderModuleLock(lock types.LockSnapshot, checksum []types.ChecksumRow) types.ModuleLockStub {
	digestByKey := map[string]string{}
	for _, row := range checksum {
		digestByKey[row.RepoKey] = row.Digest
	}
	lines := []string{}
	for _, row := range lock.Rows {
		dig := digestByKey[row.RepoKey]
		if dig == "" {
			dig = "0"
		}
		lines = append(lines, fmt.Sprintf("lock(%s,%s)", row.ModuleID, dig))
	}
	rollupRaw := sha256.Sum256([]byte(lock.EntryID))
	return types.ModuleLockStub{
		EntryID:    lock.EntryID,
		Lines:      lines,
		StubRollup: hex.EncodeToString(rollupRaw[:]),
	}
}
