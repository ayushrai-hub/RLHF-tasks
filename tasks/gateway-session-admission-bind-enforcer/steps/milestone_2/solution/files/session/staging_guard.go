package session

import "fmt"

// VerifyStagingTriple checks bind, ledger, and snapshot alignment before export.
func VerifyStagingTriple(
	snap AdmissionSnapshot,
	ledger EnforcementLedger,
	bind AdmissionBind,
) error {
	if err := verifyAdmissionBind(ledger, bind); err != nil {
		return err
	}
	if snap.Seq != ledger.Seq {
		return fmt.Errorf("staging seq mismatch")
	}
	if len(snap.BucketTokens) != len(ledger.BucketTokens) {
		return fmt.Errorf("staging bucket count mismatch")
	}
	for id, tok := range ledger.BucketTokens {
		if snap.BucketTokens[id] != tok {
			return fmt.Errorf("staging bucket token mismatch")
		}
	}
	return nil
}
