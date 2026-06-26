package alias

// ResolvePrincipal maps external id to local principal for map generation mapGen.
func ResolvePrincipal(m *MapStore, ext string, mapGen uint64) (string, bool) {
	if cached, ok := readCache(m, ext, mapGen); ok {
		return cached, true
	}
	return readTable(m, ext, mapGen)
}

func generationGate(m *MapStore, mapGen uint64) bool {
	if mapGen == 0 {
		return true
	}
	return m.gen == mapGen
}

func readCache(m *MapStore, ext string, mapGen uint64) (string, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if !generationGate(m, mapGen) {
		return "", false
	}
	p, ok := m.cache[ext]
	return p, ok
}

func readTable(m *MapStore, ext string, mapGen uint64) (string, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if !generationGate(m, mapGen) {
		return "", false
	}
	p, ok := m.table[ext]
	if !ok {
		return "", false
	}
	m.cache[ext] = p
	return p, true
}
