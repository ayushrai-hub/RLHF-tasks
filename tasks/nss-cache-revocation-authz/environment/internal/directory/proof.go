package directory

import "localauthz/internal/model"

func ProofAge(proof model.Proof, tick int) int {
	return tick - proof.IssuedAt
}

func ProofStatus(proof model.Proof, snapshotRevision int, tick int, bound int) (bool, string, int) {
	age := ProofAge(proof, tick)
	if proof.Revision != snapshotRevision {
		return false, "proof-revision-mismatch", age
	}
	if age < 0 {
		return false, "proof-from-future", age
	}
	if age > bound {
		return false, "proof-expired", age
	}
	return true, "fresh-proof", age
}

func AgeOnlyStatus(proof model.Proof, tick int, bound int) (bool, string, int) {
	age := ProofAge(proof, tick)
	if age < 0 {
		return false, "proof-from-future", age
	}
	if age > bound {
		return false, "proof-expired", age
	}
	return true, "fresh-proof", age
}
