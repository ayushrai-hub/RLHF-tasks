package alias

// ResolvePrincipal maps external id to local principal for map generation mapGen.
func ResolvePrincipal(m *MapStore, ext string, mapGen uint64) (string, bool) {
	if cached, ok := readCache(m, ext, mapGen); ok {
		return cached, true
	}
	return readTable(m, ext, mapGen)
}

func readCache(m *MapStore, ext string, mapGen uint64) (string, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.gen != mapGen {
		return "", false
	}
	p, ok := m.cache[ext]
	return p, ok
}

func readTable(m *MapStore, ext string, mapGen uint64) (string, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.gen != mapGen {
		return "", false
	}
	p, ok := m.table[ext]
	if !ok {
		return "", false
	}
	return p, true
}
