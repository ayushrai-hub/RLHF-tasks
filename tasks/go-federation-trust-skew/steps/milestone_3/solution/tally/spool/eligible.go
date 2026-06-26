package spool

// GenerationEligible reports whether gen matches the live row for kid.
func GenerationEligible(st *Store, kid string, gen uint64) bool {
	live := st.LiveGen(kid)
	if live == 0 {
		return false
	}
	return gen == live
}
