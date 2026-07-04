// Package pk_c emits gzip bytes and JSON row materialization.
package pk_c

import "lab/pk_b"

type BlobPack struct {
	Sizes map[string]int
}

type PackEmitter struct {
	Path string
}

type LedgerEmitter struct {
	Path          string
	PackID        string
	BundleDigest  string
	Rows          []LedgerRow
	AuditTrail    []int
}

type LedgerRow struct {
	BlobID string `json:"blob_id"`
	RowFP  string `json:"row_fp"`
	OrdIdx int    `json:"ord_idx"`
}

type ReachSet = pk_b.ReachSet
