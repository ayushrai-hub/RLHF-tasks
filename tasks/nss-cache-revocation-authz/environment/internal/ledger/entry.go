package ledger

import (
	"sort"

	"localauthz/internal/model"
)

func NewEntry(p model.Principal, revision int, proof model.Proof, tick int, bound int, proofAge int, refreshEpoch int) model.CacheEntry {
	groups := append([]string(nil), p.Groups...)
	sort.Strings(groups)
	return model.CacheEntry{
		Username:          p.Username,
		SubjectID:         p.SubjectID,
		Generation:        p.Generation,
		Groups:            groups,
		DirectoryRevision: revision,
		ProofRevision:     proof.Revision,
		ProofAge:          proofAge,
		RefreshedAt:       tick,
		ExpiresAt:         tick + bound,
		RefreshEpoch:      refreshEpoch,
		Revoked:           !p.Active,
	}
}

func RevokedEntry(p model.Principal, revision int, proof model.Proof, tick int, bound int, proofAge int, refreshEpoch int) model.CacheEntry {
	entry := NewEntry(p, revision, proof, tick, bound, proofAge, refreshEpoch)
	entry.Groups = []string{}
	entry.Revoked = true
	return entry
}

func ProofIssuedAt(entry model.CacheEntry) int {
	return entry.RefreshedAt - entry.ProofAge
}
