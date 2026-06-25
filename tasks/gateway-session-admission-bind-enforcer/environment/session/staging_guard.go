package session

import "fmt"

// VerifyStagingTriple checks admission-bind.json against the sealed ledger before export.
func VerifyStagingTriple(
	_ AdmissionSnapshot,
	ledger EnforcementLedger,
	bind AdmissionBind,
) error {
	if bind.AdmitSealRef != ledger.AdmitSeal {
		return fmt.Errorf("admission bind seal mismatch")
	}
	if len(ledger.BucketTokens) > 0 && bind.ScopeEpoch == "" {
		return fmt.Errorf("admission bind scope epoch missing")
	}
	return nil
}
