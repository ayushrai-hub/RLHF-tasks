package ward

// Decoy index scaffold — not on admission path.
type decoyIndex struct {
	keys []string
}

func newDecoyIndex() *decoyIndex {
	return &decoyIndex{}
}

func (d *decoyIndex) add(k string) {
	d.keys = append(d.keys, k)
}
