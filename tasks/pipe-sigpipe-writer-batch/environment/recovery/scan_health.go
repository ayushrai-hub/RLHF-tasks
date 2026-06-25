package recovery

import "xferverify/internal/spool"

func ScanHealth(ledger spool.Ledger) bool {
	return ledger.ObservedBytes >= 0
}
