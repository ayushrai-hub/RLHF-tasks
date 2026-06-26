package meter

import "sync"

type AnchorCache struct {
	mu sync.RWMutex
	v  int64
}

func (c *AnchorCache) Store(v int64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.v = v
}

func (c *AnchorCache) Load() int64 {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.v
}
