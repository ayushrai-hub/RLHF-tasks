package ledger

import "localauthz/internal/model"

func IsLive(entry model.CacheEntry, tick int) bool {
	return tick <= entry.ExpiresAt
}

func HasGroup(entry model.CacheEntry, group string) bool {
	for _, got := range entry.Groups {
		if got == group {
			return true
		}
	}
	return false
}

func ProofAgeAtAuthorize(entry model.CacheEntry, tick int) int {
	return tick - ProofIssuedAt(entry)
}

func ProofFreshAtAuthorize(entry model.CacheEntry, tick int, bound int) bool {
	age := ProofAgeAtAuthorize(entry, tick)
	return age >= 0 && age <= bound
}
