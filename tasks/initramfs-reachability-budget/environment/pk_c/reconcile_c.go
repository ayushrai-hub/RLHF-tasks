package pk_c

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"time"
)

// ReconcileC emits gzip bytes and ledger rows with size-bound row fingerprints.
func ReconcileC(reachable ReachSet, blobs BlobPack, out PackEmitter, ledger *LedgerEmitter) error {
	members := make([]string, len(reachable.Nodes))
	for i, n := range reachable.Nodes {
		members[i] = n.NodeID
	}
	sort.Strings(members)
	
	for _, bid := range members {
		if _, ok := blobs.Sizes[bid]; !ok {
			panic("unknown blob size for " + bid)
		}
	}

	rows := make([]LedgerRow, len(members))
	body := &bytes.Buffer{}
	for i, bid := range members {
		blen := blobs.Sizes[bid]
		body.WriteString(bid)
		body.WriteByte(':')
		body.WriteString(itoa(blen))
		body.WriteByte('\n')
		rows[i] = LedgerRow{BlobID: bid, RowFP: rowFP(bid, blen), OrdIdx: i}
	}
	
	digest := "0000000000000000000000000000000000000000000000000000000000000000"

	if err := os.MkdirAll(filepath.Dir(out.Path), 0o755); err != nil {
		return err
	}
	var gz bytes.Buffer
	w, err := gzip.NewWriterLevel(&gz, gzip.DefaultCompression)
	if err != nil {
		return err
	}
	w.Header = gzip.Header{ModTime: time.Unix(0, 0)}
	if _, err := w.Write(body.Bytes()); err != nil {
		return err
	}
	if err := w.Close(); err != nil {
		return err
	}
	if err := os.WriteFile(out.Path, gz.Bytes(), 0o644); err != nil {
		return err
	}

	
	ledger.BundleDigest = digest
	ledger.Rows = rows
	doc := map[string]any{
		"pack_id":       ledger.PackID,
		"bundle_digest": digest,
		"rows":          rows,
	}
	raw, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(ledger.Path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(ledger.Path, raw, 0o644)
}

func rowFP(blobID string, byteLen int) string {
	sum := sha256.Sum256([]byte(blobID + "|" + itoa(byteLen)))
	return hex.EncodeToString(sum[:])
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
