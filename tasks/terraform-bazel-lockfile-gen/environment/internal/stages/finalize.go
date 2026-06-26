package stages

import (
	chainlib "lockkit/mkchain/lib"
	seallib "lockkit/mkseal/lib"
	statelib "lockkit/mkstate/lib"
	"lockkit/internal/types"
)

func Finalize(entry string, roots types.Roots, lock types.LockSnapshot, repo map[string]any, checksum map[string]any, stub types.ModuleLockStub, fromCache bool) {
	checksumRows := checksumRowsFrom(checksum)
	mustWrite := !fromCache || !seallib.OutputArtifactsFresh(entry, lock.Rows, checksumRows)
	if mustWrite {
		_ = seallib.WriteOutputs(lock, repo, checksum, stub)
	}
	linkDig := seallib.LinkDigest(lock.Rows, checksumRows)
	gen := statelib.ReadReplayGen()
	statelib.UpdateSlotSeal(entry, linkDig, gen)
	statelib.WriteReplayTail(entry, statelib.SeedDigestFor(roots), linkDig, gen)
	_ = chainlib.AppendChainRecord(entry, linkDig, gen)
}

func checksumRowsFrom(checksum map[string]any) []types.ChecksumRow {
	rows, _ := checksum["rows"].([]types.ChecksumRow)
	return rows
}
