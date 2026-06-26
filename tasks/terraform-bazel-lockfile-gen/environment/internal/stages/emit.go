package stages

import (
	blinelib "lockkit/mkbline/lib"
	hostslib "lockkit/mkhosts/lib"
	rowslib "lockkit/mkrows/lib"
	"lockkit/internal/types"
)

func Emit(nodeMap types.NodeMap, policy types.PolicyCtx) (types.LockSnapshot, map[string]any, map[string]any, types.ModuleLockStub) {
	lock := rowslib.RenderBlockY(nodeMap, policy)
	repo, checksum := hostslib.RenderBlockZ(nodeMap, policy)
	checksumRows, _ := checksum["rows"].([]types.ChecksumRow)
	stub := blinelib.RenderModuleLock(lock, checksumRows)
	return lock, repo, checksum, stub
}
