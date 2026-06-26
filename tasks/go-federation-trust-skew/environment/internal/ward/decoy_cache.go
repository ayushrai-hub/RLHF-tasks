package ward

// Decoy cache scaffold — not on admission path.
type decoyCache struct {
	items map[string]string
}

func newDecoyCache() *decoyCache {
	return &decoyCache{items: make(map[string]string)}
}

func (d *decoyCache) put(k, v string) {
	d.items[k] = v
}
