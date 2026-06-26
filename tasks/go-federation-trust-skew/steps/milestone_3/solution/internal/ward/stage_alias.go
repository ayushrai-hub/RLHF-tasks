package ward

import (
	"fedenv/relay/alias"
)

func resolveAlias(e *Engine, ext string) (string, bool, uint64) {
	live := e.mp.Generation()
	p, ok := alias.ResolvePrincipal(e.mp, ext, live)
	return p, ok, live
}
