package spool

// PickMaterial returns signing bytes for kid at generation gen when still eligible.
func PickMaterial(st *Store, kid string, gen uint64) ([]byte, bool) {
	if !GenerationEligible(st, kid, gen) {
		return nil, false
	}
	row, ok := st.Row(kid, gen)
	if !ok {
		return nil, false
	}
	if gen == st.LiveGen(kid) {
		if len(row.Key) == 0 {
			return nil, false
		}
		return row.Key, true
	}
	if prev, ok := st.Row(kid, gen-1); ok && len(prev.Key) > 0 {
		return prev.Key, true
	}
	return row.Key, true
}
