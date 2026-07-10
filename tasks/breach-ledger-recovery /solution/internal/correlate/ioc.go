package correlate

import "breach-ledger/internal/fold"

func UniqueStrings(values []string) []string {
	return fold.UniqueStrings(values)
}
